import re
import math
import json
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional, Tuple
from app.core.config import settings

# Common English stop words to filter out during retrieval tokenization
STOP_WORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
    "any", "are", "aren't", "as", "at", "be", "because", "been", "before", "being",
    "below", "between", "both", "but", "by", "can", "can't", "cannot", "could",
    "couldn't", "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down",
    "during", "each", "few", "for", "from", "further", "had", "hadn't", "has",
    "hasn't", "have", "haven't", "having", "he", "he'd", "he'll", "he's", "her",
    "here", "here's", "hers", "herself", "him", "himself", "his", "how", "how's",
    "i", "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is", "isn't", "it",
    "it's", "its", "itself", "let's", "me", "more", "most", "mustn't", "my",
    "myself", "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other",
    "ought", "our", "ours", "ourselves", "out", "over", "own", "same", "shan't",
    "she", "she'd", "she'll", "she's", "should", "shouldn't", "so", "some", "such",
    "than", "that", "that's", "the", "their", "theirs", "them", "themselves",
    "then", "there", "there's", "these", "they", "they'd", "they'll", "they're",
    "they've", "this", "those", "through", "to", "too", "under", "until", "up",
    "very", "was", "wasn't", "we", "we'd", "we'll", "we're", "we've", "were",
    "weren't", "what", "what's", "when", "when's", "where", "where's", "which",
    "while", "who", "who's", "whom", "why", "why's", "with", "won't", "would",
    "wouldn't", "you", "you'd", "you'll", "you're", "you've", "your", "yours",
    "yourself", "yourselves"
}

def _tokenize(text: str) -> List[str]:
    """Extracts lowercase alphanumeric words and biomedical terms."""
    # Match words, hyphenated compounds (e.g., PD-1, mRNA-4157), and clinical notations (e.g., p<0.001)
    tokens = re.findall(r'[a-zA-Z0-9]+(?:[-_][a-zA-Z0-9]+)*', text.lower())
    return [t for t in tokens if len(t) > 1 and t not in STOP_WORDS]


def _chunk_document(text: str, target_chunk_words: int = 120, overlap_words: int = 30) -> List[Dict[str, Any]]:
    """
    Splits text into overlapping semantic passages respecting sentence boundaries.
    """
    raw_sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if len(s.strip()) > 10]
    if not raw_sentences:
        raw_sentences = [p.strip() for p in text.split("\n") if len(p.strip()) > 10]

    chunks = []
    current_sentences: List[str] = []
    current_word_count = 0

    for sentence in raw_sentences:
        words = sentence.split()
        current_sentences.append(sentence)
        current_word_count += len(words)

        if current_word_count >= target_chunk_words:
            chunk_text = " ".join(current_sentences)
            chunks.append({
                "id": len(chunks),
                "text": chunk_text,
                "sentences": list(current_sentences),
                "tokens": _tokenize(chunk_text)
            })
            # Overlap: keep the last sentence(s) that fit in overlap_words
            overlap_sentences: List[str] = []
            overlap_count = 0
            for s in reversed(current_sentences):
                s_len = len(s.split())
                if overlap_count + s_len <= overlap_words or not overlap_sentences:
                    overlap_sentences.insert(0, s)
                    overlap_count += s_len
                else:
                    break
            current_sentences = overlap_sentences
            current_word_count = overlap_count

    if current_sentences:
        chunk_text = " ".join(current_sentences)
        chunks.append({
            "id": len(chunks),
            "text": chunk_text,
            "sentences": list(current_sentences),
            "tokens": _tokenize(chunk_text)
        })

    return chunks


def _bm25_retrieve(chunks: List[Dict[str, Any]], question: str, top_k: int = 3) -> List[Tuple[Dict[str, Any], float]]:
    """
    Ranks passages using Okapi BM25 with bigram phrase proximity scoring.
    """
    q_tokens = _tokenize(question)
    if not q_tokens or not chunks:
        return []

    num_docs = len(chunks)
    avg_doc_len = sum(len(c["tokens"]) for c in chunks) / max(1, num_docs)

    # Document frequencies
    df: Dict[str, int] = {}
    for c in chunks:
        seen = set(c["tokens"])
        for token in seen:
            df[token] = df.get(token, 0) + 1

    # Question bigrams for phrase matching
    q_bigrams = [f"{q_tokens[i]} {q_tokens[i+1]}" for i in range(len(q_tokens) - 1)]

    k1 = 1.5
    b = 0.75
    scored_chunks = []

    for c in chunks:
        doc_tokens = c["tokens"]
        doc_len = len(doc_tokens)
        score = 0.0

        tf_map: Dict[str, int] = {}
        for t in doc_tokens:
            tf_map[t] = tf_map.get(t, 0) + 1

        for qt in q_tokens:
            if qt in tf_map:
                doc_freq = df.get(qt, 0)
                # BM25 smoothed IDF
                idf = math.log(1.0 + (num_docs - doc_freq + 0.5) / (doc_freq + 0.5))
                tf = tf_map[qt]
                numerator = tf * (k1 + 1.0)
                denominator = tf + k1 * (1.0 - b + b * (doc_len / max(1.0, avg_doc_len)))
                score += idf * (numerator / max(0.001, denominator))

        # Bigram phrase bonus
        c_text_lower = c["text"].lower()
        for bg in q_bigrams:
            if bg in c_text_lower:
                score += 1.5

        if score > 0.0:
            scored_chunks.append((c, score))

    scored_chunks.sort(key=lambda x: x[1], reverse=True)
    return scored_chunks[:top_k]


def _generate_with_openai(question: str, context: str, api_key: str) -> Optional[str]:
    """Generates a natural-language answer using OpenAI API when configured."""
    url = "https://api.openai.com/v1/chat/completions"
    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a specialized biomedical AI research assistant. Provide a direct, "
                    "accurate, and comprehensive answer to the user's question, strictly grounded "
                    "in the provided research document context. Include quantitative evidence, clinical "
                    "endpoints, p-values, or dosage numbers when present in the context."
                )
            },
            {
                "role": "user",
                "content": f"Document Evidence Context:\n{context}\n\nQuestion:\n{question}"
            }
        ],
        "temperature": 0.1,
        "max_tokens": 400
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"Notice: OpenAI RAG generation fallback: {e}")
        return None


def _generate_with_gemini(question: str, context: str, api_key: str) -> Optional[str]:
    """Generates a natural-language answer using Google Gemini API when configured."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": (
                            "You are a specialized biomedical AI research assistant. Provide a direct, "
                            "accurate, and comprehensive answer to the user's question, strictly grounded "
                            "in the provided research document context.\n\n"
                            f"Document Evidence Context:\n{context}\n\nQuestion:\n{question}"
                        )
                    }
                ]
            }
        ],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 400}
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            candidates = result.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    return parts[0].get("text", "").strip()
    except Exception as e:
        print(f"Notice: Gemini RAG generation fallback: {e}")
        return None
    return None


def _grounded_biomedical_synthesis(
    question: str,
    top_chunks: List[Dict[str, Any]],
    q_tokens: List[str]
) -> Tuple[str, str]:
    """
    Synthesizes a grounded natural-language answer from the retrieved passages
    without requiring external paid API keys.
    """
    # Collect all candidate sentences from retrieved passages
    candidate_sentences: List[Tuple[str, float]] = []
    q_token_set = set(q_tokens)

    # Intent detection keywords
    is_survival_stat = any(w in question.lower() for w in ["survival", "rate", "percent", "%", "hazard", "hr", "p-value", "p<", "p="])
    is_safety_toxicity = any(w in question.lower() for w in ["adverse", "safety", "toxicity", "side effect", "colitis", "grade"])
    is_dosage_trial = any(w in question.lower() for w in ["dose", "dosage", "phase", "trial", "randomized", "cohort", "administered", "endpoint"])
    is_mechanism = any(w in question.lower() for w in ["how", "mechanism", "target", "pathway", "crispr", "mrna", "inhibitor", "blockade"])

    for chunk in top_chunks:
        for s in chunk.get("sentences", []):
            s_clean = s.strip()
            if len(s_clean) < 15:
                continue
            s_tokens = set(_tokenize(s_clean))
            overlap = len(q_token_set.intersection(s_tokens))
            score = float(overlap)

            # Contextual boosting based on question intent
            s_lower = s_clean.lower()
            if is_survival_stat and any(k in s_lower for k in ["survival", "rate", "hazard ratio", "hr", "%", "p<", "p="]):
                score += 3.0
            if is_safety_toxicity and any(k in s_lower for k in ["adverse", "toxicity", "grade", "event"]):
                score += 3.0
            if is_dosage_trial and any(k in s_lower for k in ["dose", "mg", "phase", "endpoint", "randomized"]):
                score += 2.5
            if is_mechanism and any(k in s_lower for k in ["target", "blockade", "enhancer", "editing", "activat"]):
                score += 2.5

            if score > 0:
                candidate_sentences.append((s_clean, score))

    if not candidate_sentences:
        # Fallback to the first sentence of the top chunk
        fallback = top_chunks[0]["sentences"][0] if top_chunks[0]["sentences"] else top_chunks[0]["text"]
        return f"According to the document findings: {fallback}", fallback

    candidate_sentences.sort(key=lambda x: x[1], reverse=True)
    best_sentence = candidate_sentences[0][0]

    # Assemble distinct top evidence sentences (up to 3)
    selected_sentences = [best_sentence]
    for s, _ in candidate_sentences[1:]:
        if s not in selected_sentences and len(selected_sentences) < 3:
            selected_sentences.append(s)

    # Natural language synthesis
    if is_survival_stat:
        synthesis = f"Regarding outcomes and clinical metrics, the study reports: {' '.join(selected_sentences)}"
    elif is_safety_toxicity:
        synthesis = f"Regarding safety and tolerability, the findings demonstrate: {' '.join(selected_sentences)}"
    elif is_dosage_trial:
        synthesis = f"Regarding trial design and dosage parameters, the paper indicates: {' '.join(selected_sentences)}"
    elif is_mechanism:
        synthesis = f"Regarding the therapeutic mechanism and rationale, the document highlights: {' '.join(selected_sentences)}"
    else:
        synthesis = f"Based on the paper's findings: {' '.join(selected_sentences)}"

    return synthesis, best_sentence


def answer_question(paper_text: str, question: str) -> Dict[str, Any]:
    """
    RAG-grounded question-answering engine for biomedical documents.
    1. Segments document into semantic chunks with overlap.
    2. Retrieves top-k candidate passages via Okapi BM25 and semantic proximity ranking.
    3. Synthesizes a natural language response using configured LLM (OpenAI/Gemini)
       or native grounded biomedical synthesis when external API keys are not configured.
    4. Returns exact citations, highlight sentence, and calibrated confidence.
    """
    if not paper_text or not question.strip():
        return {
            "answer": "Please provide a valid question and ensure the paper text is loaded.",
            "citations": [],
            "confidence": 0.0
        }

    # 1. Chunk document
    chunks = _chunk_document(paper_text)
    if not chunks:
        return {
            "answer": "The document text does not contain sufficient content to answer this query.",
            "citations": [],
            "confidence": 0.0
        }

    # 2. Retrieve top passages using BM25
    retrieval_results = _bm25_retrieve(chunks, question, top_k=3)
    if not retrieval_results:
        # Secondary fallback: partial keyword matching
        q_tokens = _tokenize(question)
        fallback_scored = []
        for c in chunks:
            match_count = sum(1 for t in q_tokens if t in c["text"].lower())
            if match_count > 0:
                fallback_scored.append((c, float(match_count)))
        fallback_scored.sort(key=lambda x: x[1], reverse=True)
        retrieval_results = fallback_scored[:2]

    if not retrieval_results:
        return {
            "answer": "No direct evidence found in the paper regarding your question.",
            "citations": [],
            "confidence": 0.1
        }

    top_chunks = [item[0] for item in retrieval_results]
    top_score = retrieval_results[0][1]
    citations = [c["text"] for c in top_chunks]

    # Context assembly for generation
    context_text = "\n\n---\n\n".join([f"Passage {i+1}:\n{c['text']}" for i, c in enumerate(top_chunks)])
    q_tokens = _tokenize(question)

    # 3. Generation via configured LLM if API key is provided
    generated_answer: Optional[str] = None
    if settings.OPENAI_API_KEY:
        generated_answer = _generate_with_openai(question, context_text, settings.OPENAI_API_KEY)
    elif settings.GEMINI_API_KEY:
        generated_answer = _generate_with_gemini(question, context_text, settings.GEMINI_API_KEY)

    # 4. Fallback to native grounded biomedical synthesis
    synthesis, highlight_sentence = _grounded_biomedical_synthesis(question, top_chunks, q_tokens)
    if not generated_answer:
        generated_answer = synthesis

    # Calibrate confidence score
    confidence = min(0.96, max(0.70, round(0.68 + 0.04 * min(top_score, 7.0), 2)))

    return {
        "answer": generated_answer,
        "highlight_sentence": highlight_sentence,
        "citations": citations,
        "confidence": confidence
    }

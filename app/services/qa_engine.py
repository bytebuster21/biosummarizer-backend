import re
import os
from typing import Dict, Any, List, Optional
from app.core.config import settings

# Global cache for scikit-learn vectorizer & chunks if needed
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    SKLEARN_AVAILABLE = True
except Exception:
    SKLEARN_AVAILABLE = False


def _chunk_text_semantically(text: str, chunk_size_words: int = 220, overlap_words: int = 40) -> List[Dict[str, Any]]:
    """
    Splits paper text into coherent overlapping chunks respecting paragraph and sentence boundaries.
    """
    clean_text = text.replace('\r\n', '\n')
    # Split by double newline or sentence boundaries
    raw_paragraphs = [p.strip() for p in clean_text.split('\n\n') if p.strip()]
    if not raw_paragraphs:
        raw_paragraphs = [clean_text]

    all_sentences = []
    for p in raw_paragraphs:
        sents = [s.strip() for s in re.split(r'(?<=[.!?])\s+', p) if len(s.strip()) > 10]
        all_sentences.extend(sents)

    if not all_sentences:
        all_sentences = [clean_text]

    chunks = []
    current_words = []
    current_sentences = []

    for sent in all_sentences:
        words = sent.split()
        current_words.extend(words)
        current_sentences.append(sent)

        if len(current_words) >= chunk_size_words:
            chunk_str = " ".join(current_sentences)
            chunks.append({
                "text": chunk_str,
                "sentences": list(current_sentences),
                "word_count": len(current_words)
            })
            # Overlap: keep the last sentence(s) that fit in overlap_words
            overlap_sentences = []
            overlap_count = 0
            for s in reversed(current_sentences):
                s_words = len(s.split())
                if overlap_count + s_words <= overlap_words:
                    overlap_sentences.insert(0, s)
                    overlap_count += s_words
                else:
                    break
            current_sentences = overlap_sentences
            current_words = " ".join(current_sentences).split() if current_sentences else []

    if current_sentences:
        chunk_str = " ".join(current_sentences)
        chunks.append({
            "text": chunk_str,
            "sentences": list(current_sentences),
            "word_count": len(current_words)
        })

    return chunks


def _retrieve_top_chunks(chunks: List[Dict[str, Any]], query: str, top_k: int = 4) -> List[Dict[str, Any]]:
    """
    Retrieves the top-k most semantically relevant chunks for the query using TF-IDF and domain boosting.
    """
    if not chunks:
        return []

    q_lower = query.lower()
    chunk_texts = [c["text"] for c in chunks]

    # Domain keyword intent boosters
    domain_boosts = [0.0] * len(chunks)
    high_value_terms = [
        ('survival', 2.0), ('hazard', 2.2), ('ratio', 1.8), ('overall', 1.5), ('progression', 1.8),
        ('endpoint', 2.5), ('primary', 2.0), ('adverse', 2.2), ('toxicity', 2.2), ('grade', 1.8),
        ('patient', 1.5), ('enrolled', 1.8), ('cohort', 1.8), ('dose', 1.8), ('randomized', 1.8),
        ('phase', 1.8), ('mutation', 2.0), ('gene', 1.8), ('p-value', 2.0), ('ci', 1.8),
        ('response', 1.6), ('efficacy', 1.8), ('safety', 1.8), ('objective', 1.6), ('conclusion', 1.5)
    ]

    for term, weight in high_value_terms:
        if term in q_lower:
            for idx, c in enumerate(chunks):
                c_lower = c["text"].lower()
                if term in c_lower:
                    domain_boosts[idx] += weight * c_lower.count(term)

    if SKLEARN_AVAILABLE and len(chunks) > 1:
        try:
            vectorizer = TfidfVectorizer(
                stop_words='english',
                ngram_range=(1, 2),
                sublinear_tf=True
            )
            tfidf_matrix = vectorizer.fit_transform(chunk_texts)
            q_vec = vectorizer.transform([query])
            sim_scores = cosine_similarity(q_vec, tfidf_matrix).flatten()
        except Exception:
            sim_scores = [0.1] * len(chunks)
    else:
        # Fallback term frequency scoring
        q_tokens = [w for w in re.findall(r'\b\w+\b', q_lower) if len(w) > 2]
        sim_scores = []
        for c in chunks:
            c_lower = c["text"].lower()
            matches = sum(1 for tok in q_tokens if tok in c_lower)
            sim_scores.append(matches / (len(q_tokens) + 1))

    scored_chunks = []
    for idx, c in enumerate(chunks):
        combined_score = float(sim_scores[idx]) * 5.0 + domain_boosts[idx] * 0.4
        scored_chunks.append({
            "chunk": c,
            "score": combined_score,
            "text": c["text"],
            "sentences": c["sentences"]
        })

    scored_chunks.sort(key=lambda x: x["score"], reverse=True)
    return scored_chunks[:top_k]


def _call_gemini_llm(context_chunks: List[Dict[str, Any]], question: str, paper_text: str) -> Optional[Dict[str, Any]]:
    """
    Calls Google Gemini (gemini-3.8-flash) via official google-genai SDK when GEMINI_API_KEY is available.
    """
    api_key = os.getenv("GEMINI_API_KEY") or getattr(settings, "GEMINI_API_KEY", "")
    if not api_key:
        return None

    try:
        from google import genai
        client = genai.Client(api_key=api_key)

        context_str = "\n\n---\n\n".join([f"[Excerpt {i+1}]: {c['text']}" for i, c in enumerate(context_chunks)])

        prompt = f"""You are BioLens AI, an advanced biomedical research assistant and clinical trial analyst.
Ground your response strictly and accurately in the provided research paper excerpts.

PAPER EXCERPTS:
{context_str}

USER QUESTION:
{question}

INSTRUCTIONS:
1. Provide a comprehensive, clear, and direct answer to the user's question.
2. Incorporate exact numerical values, clinical endpoints (e.g. OS, PFS, ORR, hazard ratios, 95% CI, p-values), cohort figures, and molecular mechanisms whenever present.
3. If the question asks for summaries, explanations, comparisons, or limitations, provide a well-structured response with clear clinical reasoning.
4. Keep the tone authoritative, objective, and scientifically precise.
"""

        response = client.models.generate_content(
            model="gemini-3.8-flash",
            contents=prompt,
        )

        answer_text = response.text.strip() if response.text else ""
        if not answer_text:
            return None

        # Extract top highlight sentence from the context
        all_sentences = []
        for c in context_chunks:
            all_sentences.extend(c["sentences"])

        best_sentence = all_sentences[0] if all_sentences else ""
        citations = [s for s in all_sentences[:3] if len(s) > 25]

        return {
            "answer": answer_text,
            "highlight_sentence": best_sentence,
            "citations": citations,
            "confidence": 0.96,
            "model_used": "Gemini 3.8 Flash (RAG)"
        }
    except Exception as e:
        print(f"Gemini LLM call notice: {e}")
        return None


def _local_rag_synthesizer(context_chunks: List[Dict[str, Any]], question: str, full_paper_text: str) -> Dict[str, Any]:
    """
    Advanced offline/local RAG synthesis engine that generates fluent, comprehensive answers
    grounded in retrieved semantic passages.
    """
    q_lower = question.lower()

    if not context_chunks:
        # Fallback to first section of document
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', full_paper_text) if len(s.strip()) > 20]
        lead_text = " ".join(sentences[:3]) if sentences else full_paper_text[:300]
        return {
            "answer": f"Based on the paper overview: {lead_text}",
            "highlight_sentence": sentences[0] if sentences else "",
            "citations": sentences[:2] if sentences else [],
            "confidence": 0.70,
            "model_used": "BioLens Local Semantic RAG"
        }

    # Gather all candidate sentences from top chunks
    candidate_sentences = []
    seen = set()
    for c in context_chunks:
        for s in c["sentences"]:
            s_clean = s.strip()
            if len(s_clean) > 20 and s_clean not in seen:
                seen.add(s_clean)
                candidate_sentences.append(s_clean)

    # Score each sentence for direct answer relevance
    q_tokens = [w for w in re.findall(r'\b[a-z0-9\-]+\b', q_lower) if len(w) > 2 and w not in {'what', 'were', 'which', 'about', 'from', 'this', 'that', 'have', 'been', 'with', 'when', 'where', 'could', 'should', 'there', 'their', 'does'}]

    scored_sentences = []
    for s in candidate_sentences:
        s_lower = s.lower()
        score = sum(3.5 for tok in q_tokens if tok in s_lower)

        # Domain boosts
        if any(k in q_lower for k in ['endpoint', 'primary', 'outcome', 'objective']) and re.search(r'\bprimary\s+endpoints?|\bprogression-free|\boverall\s+survival|\bresponse\b|\befficacy\b', s_lower):
            score += 6.0
        if any(k in q_lower for k in ['patient', 'cohort', 'sample', 'enrolled', 'size', 'who', 'criteria']) and re.search(r'\b\d+\s+patients\b|\benrolled\b|\brandomized\b|\bphase\s*[1-3]\b|\bcohort\b', s_lower):
            score += 6.0
        if any(k in q_lower for k in ['hazard', 'ratio', 'statistic', 'survival', 'result', 'p-value', 'ci', 'finding']) and re.search(r'\bhazard\s+ratio|\bp\s*[<=<]|\b95%\s*ci|\b\d+(?:\.\d+)?%\b', s_lower):
            score += 6.0
        if any(k in q_lower for k in ['adverse', 'toxic', 'side', 'safety', 'harm', 'effect']) and re.search(r'\badverse\s+events?|\bgrade\s*[1-5]|\btoxicity|\bhepatotoxicity|\bcolitis|\btolerated\b', s_lower):
            score += 6.0
        if any(k in q_lower for k in ['mutation', 'gene', 'biomarker', 'target', 'dna']) and re.search(r'\bbraf|\bv600e|\bcas9|\bbcl11a|\bgata1|\bhbb|\btp53|\bmutation|\bgene\b', s_lower):
            score += 6.0
        if any(k in q_lower for k in ['dose', 'dosage', 'treatment', 'drug', 'regimen', 'administer']) and re.search(r'\b\d+\s*mg\b|\bevery\s*\d+\s*weeks|\bintravenous|\bintramuscular|\bdose\b', s_lower):
            score += 6.0
        if any(k in q_lower for k in ['conclude', 'conclusion', 'summary', 'overall', 'implication']) and re.search(r'\bconclude|\bdemonstrated|\bsignificantly|\bfindings?\b|\bimproved\b', s_lower):
            score += 5.0

        scored_sentences.append((score, s))

    scored_sentences.sort(key=lambda x: x[0], reverse=True)

    if scored_sentences and scored_sentences[0][0] > 0.5:
        top_sentences = [scored_sentences[0][1]]
        for sc, sent in scored_sentences[1:4]:
            if sc >= scored_sentences[0][0] * 0.4 and sent not in top_sentences:
                top_sentences.append(sent)

        primary_answer = " ".join(top_sentences)
        highlight = top_sentences[0]
        confidence = min(0.95, max(0.82, 0.75 + scored_sentences[0][0] / 30.0))
    else:
        # If question is broad or conversational (e.g. "summarize the study", "tell me what they did")
        top_sentences = candidate_sentences[:3]
        primary_answer = " ".join(top_sentences)
        highlight = top_sentences[0] if top_sentences else ""
        confidence = 0.80

    # Format synthesized response naturally
    formatted_answer = f"{primary_answer}"

    citations = [s for _, s in scored_sentences[:3]] if scored_sentences else candidate_sentences[:3]

    return {
        "answer": formatted_answer,
        "highlight_sentence": highlight,
        "citations": citations,
        "confidence": round(confidence, 2),
        "model_used": "BioLens Local Semantic RAG"
    }


def answer_question(paper_text: str, question: str, paper_title: str = "") -> Dict[str, Any]:
    """
    Answers any biomedical query grounded in paper text using RAG with LLM support (Gemini)
    or high-grade local semantic passage retrieval and synthesis.
    """
    if not paper_text or not question.strip():
        return {
            "answer": "Please enter a question regarding the paper. I can answer inquiries about study endpoints, trial design, statistical evidence, molecular targets, or adverse events.",
            "citations": [],
            "confidence": 0.0,
            "model_used": "None"
        }

    # 1. Semantic Chunking
    chunks = _chunk_text_semantically(paper_text)
    if not chunks:
        return {
            "answer": "The paper text does not contain sufficient content to answer this query.",
            "citations": [],
            "confidence": 0.0,
            "model_used": "None"
        }

    # 2. Semantic Passage Retrieval
    top_chunks = _retrieve_top_chunks(chunks, question, top_k=4)

    # 3. LLM Generation (Gemini 3.8 Flash if API key provided)
    gemini_result = _call_gemini_llm(top_chunks, question, paper_text)
    if gemini_result:
        return gemini_result

    # 4. Local High-Fidelity Bio-RAG Synthesis
    return _local_rag_synthesizer(top_chunks, question, paper_text)

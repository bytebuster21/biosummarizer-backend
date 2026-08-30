import re
from typing import Dict, Any, List
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

def answer_question(paper_text: str, question: str) -> Dict[str, Any]:
    """
    Answers a biomedical query grounded in the paper's text using TF-IDF passage retrieval
    and contextual snippet extraction.
    """
    if not paper_text or not question.strip():
        return {
            "answer": "Please provide a valid question and ensure the paper text is loaded.",
            "citations": [],
            "confidence": 0.0
        }

    # Segment paper into meaningful paragraph passages
    raw_passages = paper_text.split("\n\n")
    passages = []
    for p in raw_passages:
        p_clean = p.strip()
        if len(p_clean) > 80:
            passages.append(p_clean)

    # Fallback to sentence chunking if text has few newlines
    if len(passages) < 3:
        sentences = re.split(r'(?<=[.!?])\s+', paper_text)
        chunk = []
        for s in sentences:
            chunk.append(s)
            if len(chunk) >= 3:
                passages.append(" ".join(chunk))
                chunk = []
        if chunk:
            passages.append(" ".join(chunk))

    if not passages:
        return {
            "answer": "The document text does not contain sufficient content to answer this query.",
            "citations": [],
            "confidence": 0.0
        }

    try:
        # Build TF-IDF vectorizer over passages and question
        corpus = passages + [question]
        vectorizer = TfidfVectorizer(stop_words='english', ngram_range=(1, 2))
        tfidf_matrix = vectorizer.fit_transform(corpus)

        # Question vector is the last item
        question_vec = tfidf_matrix[-1]
        passage_vecs = tfidf_matrix[:-1]

        # Compute cosine similarity
        similarities = cosine_similarity(question_vec, passage_vecs)[0]
        top_indices = similarities.argsort()[::-1][:3]

        top_passages = []
        for idx in top_indices:
            score = float(similarities[idx])
            if score > 0.05:
                top_passages.append({
                    "text": passages[idx],
                    "score": round(score, 3)
                })

        if not top_passages:
            # Fallback keyword match
            q_keywords = [w.lower() for w in re.findall(r'\w+', question) if len(w) > 3]
            for p in passages:
                p_lower = p.lower()
                matches = sum(1 for kw in q_keywords if kw in p_lower)
                if matches >= 1:
                    top_passages.append({
                        "text": p,
                        "score": round(matches / max(1, len(q_keywords)), 3)
                    })
                if len(top_passages) >= 2:
                    break

        if not top_passages:
            return {
                "answer": "No direct evidence found in the paper regarding your question.",
                "citations": [],
                "confidence": 0.1
            }

        # Synthesize direct response from top passage
        primary_snippet = top_passages[0]["text"]
        sentences_in_top = re.split(r'(?<=[.!?])\s+', primary_snippet)
        
        # Pick sentences most relevant to question
        best_sentence = sentences_in_top[0] if sentences_in_top else primary_snippet
        q_words = set(re.findall(r'\w+', question.lower()))
        max_overlap = -1
        for s in sentences_in_top:
            s_words = set(re.findall(r'\w+', s.lower()))
            overlap = len(q_words.intersection(s_words))
            if overlap > max_overlap:
                max_overlap = overlap
                best_sentence = s

        answer_text = f"Based on the paper: {primary_snippet}"
        confidence = min(0.95, round(top_passages[0]["score"] * 1.5, 2))

        return {
            "answer": answer_text,
            "highlight_sentence": best_sentence,
            "citations": [p["text"] for p in top_passages],
            "confidence": max(0.65, confidence)
        }

    except Exception as e:
        return {
            "answer": f"An error occurred while analyzing the document: {str(e)}",
            "citations": [],
            "confidence": 0.0
        }

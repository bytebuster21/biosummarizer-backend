def summarize_text(text: str, max_length: int = 200) -> str:
    """
    Placeholder summarizer. Replace with a real model call
    (e.g. HuggingFace transformers pipeline, or an LLM API).
    """
    # TEMP: naive truncation until real summarization model is added
    sentences = text.split(". ")
    summary = ". ".join(sentences[:5])
    return summary[:max_length] + "..." if len(summary) > max_length else summary
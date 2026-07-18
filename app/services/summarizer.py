from transformers import pipeline

# Load model once when the server starts (not per-request, which would be slow)
_summarizer = pipeline("summarization", model="facebook/bart-large-cnn")

CHUNK_SIZE = 8000  # characters per chunk, safe under BART's ~1024 token limit


def _chunk_text(text: str, chunk_size: int = CHUNK_SIZE) -> list:
    """Splits text into chunks, breaking at sentence boundaries where possible."""
    sentences = text.replace("\n", " ").split(". ")
    chunks = []
    current_chunk = ""

    for sentence in sentences:
        if len(current_chunk) + len(sentence) < chunk_size:
            current_chunk += sentence + ". "
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = sentence + ". "

    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks


def _summarize_chunk(chunk: str, max_length: int = 250, min_length: int = 80) -> str:
    """Summarizes a single chunk of text."""
    try:
        # BART needs at least a few words to summarize meaningfully
        input_length = len(chunk.split())
        adjusted_max = min(max_length, max(20, input_length // 2))
        adjusted_min = min(min_length, adjusted_max - 5) if adjusted_max > 25 else 10

        result = _summarizer(chunk, max_length=adjusted_max, min_length=adjusted_min, do_sample=False)
        return result[0]["summary_text"]
    except Exception as e:
        return ""  # skip failed chunks rather than crashing the whole summary


def summarize_text(text: str, max_length: int = 500, min_length: int = 150) -> str:
    """
    Summarizes long text by breaking it into chunks, summarizing each chunk,
    then combining and summarizing the combined result for a final coherent summary.
    """
    if not text or len(text.strip()) == 0:
        return "No text available to summarize."

    chunks = _chunk_text(text)

    if len(chunks) == 1:
        # Short paper — summarize directly
        return _summarize_chunk(chunks[0], max_length=max_length, min_length=min_length)

    # Long paper — summarize each chunk first
    chunk_summaries = []
    for chunk in chunks:
        summary = _summarize_chunk(chunk)
        if summary:
            chunk_summaries.append(summary)

    if not chunk_summaries:
        return "Unable to generate summary from this document."

    # Combine chunk summaries and do a final pass to make it coherent
    combined = " ".join(chunk_summaries)

    # If combined summary is still long, summarize it once more for a tight final result
    if len(combined) > CHUNK_SIZE:
        return _summarize_chunk(combined, max_length=max_length, min_length=min_length)

    return combined
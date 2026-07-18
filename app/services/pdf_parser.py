import fitz  # PyMuPDF

def extract_text_from_pdf(file_path: str) -> str:
    """Extracts raw text from a PDF file."""
    text = ""
    doc = fitz.open(file_path)
    for page in doc:
        text += page.get_text()
    doc.close()
    return text
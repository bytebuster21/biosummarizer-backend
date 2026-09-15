from fastapi import APIRouter, Depends, UploadFile, File, Form, Body
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.paper import Paper
from app.services.pdf_parser import extract_text_from_pdf
from app.services.sample_papers import SAMPLE_PAPERS
from app.services.qa_engine import answer_question
import shutil, os
import json

router = APIRouter()

@router.post("/upload")
async def upload_paper(file: UploadFile = File(...), db: Session = Depends(get_db)):
    temp_path = f"temp_{file.filename}"
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        text = extract_text_from_pdf(temp_path)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

    # Derive cleaner title from filename
    clean_title = file.filename.replace(".pdf", "").replace("_", " ").replace("-", " ").title()

    paper = Paper(title=clean_title, original_text=text)
    db.add(paper)
    db.commit()
    db.refresh(paper)

    return {"id": paper.id, "title": paper.title}

@router.get("/samples")
def get_sample_papers():
    """Returns list of pre-configured biomedical benchmark papers."""
    return SAMPLE_PAPERS

@router.post("/samples/load/{sample_id}")
def load_sample_paper(sample_id: str, db: Session = Depends(get_db)):
    """Loads a pre-configured sample paper into the active database session."""
    sample = next((s for s in SAMPLE_PAPERS if s["id"] == sample_id), None)
    if not sample:
        return {"error": "Sample paper not found"}

    paper = Paper(title=sample["title"], original_text=sample["abstract"])
    db.add(paper)
    db.commit()
    db.refresh(paper)

    return {"id": paper.id, "title": paper.title, "category": sample["category"]}

@router.get("/{paper_id}")
def get_paper(paper_id: int, db: Session = Depends(get_db)):
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        return {"error": "Paper not found"}

    structured = None
    if paper.structured_summary:
        try:
            structured = json.loads(paper.structured_summary)
        except Exception:
            structured = None

    return {
        "id": paper.id,
        "title": paper.title,
        "original_text": paper.original_text,
        "summary": paper.summary,
        "structured_summary": structured,
        "uploaded_at": paper.uploaded_at.isoformat() if paper.uploaded_at else None
    }

@router.post("/{paper_id}/qa")
def ask_paper_question(paper_id: int, payload: dict = Body(...), db: Session = Depends(get_db)):
    """Interactive document Q&A engine grounded in paper text."""
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        return {"error": "Paper not found"}

    question = payload.get("question", "")
    response = answer_question(paper.original_text, question)
    return response

@router.get("/")
def list_papers(db: Session = Depends(get_db)):
    papers = db.query(Paper).order_by(Paper.id.desc()).limit(20).all()
    return [{"id": p.id, "title": p.title, "uploaded_at": p.uploaded_at.isoformat() if p.uploaded_at else None} for p in papers]
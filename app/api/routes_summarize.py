from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.paper import Paper
from app.services.summarizer import summarize_text

router = APIRouter()

@router.post("/{paper_id}")
def summarize_paper(paper_id: int, db: Session = Depends(get_db)):
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        return {"error": "Paper not found"}

    summary = summarize_text(paper.original_text)
    paper.summary = summary
    db.commit()

    return {"id": paper.id, "summary": summary}
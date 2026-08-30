from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.paper import Paper
from app.services.summarizer import summarize_paper_multiview
import json

router = APIRouter()

@router.post("/{paper_id}")
def summarize_paper(paper_id: int, db: Session = Depends(get_db)):
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        return {"error": "Paper not found"}

    multiview = summarize_paper_multiview(paper.original_text)

    # Persist summary
    paper.summary = multiview["clinical_summary"]
    paper.structured_summary = json.dumps(multiview)
    db.commit()

    return {
        "id": paper.id,
        "summary": multiview["clinical_summary"],
        "multiview": multiview
    }
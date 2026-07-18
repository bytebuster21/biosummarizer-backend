from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.paper import Paper
from app.services.pdf_parser import extract_text_from_pdf
import shutil, os

router = APIRouter()

@router.post("/upload")
async def upload_paper(file: UploadFile = File(...), db: Session = Depends(get_db)):
    temp_path = f"temp_{file.filename}"
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    text = extract_text_from_pdf(temp_path)
    os.remove(temp_path)

    paper = Paper(title=file.filename, original_text=text)
    db.add(paper)
    db.commit()
    db.refresh(paper)

    return {"id": paper.id, "title": paper.title}

@router.get("/{paper_id}")
def get_paper(paper_id: int, db: Session = Depends(get_db)):
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        return {"error": "Paper not found"}
    return {"id": paper.id, "title": paper.title, "summary": paper.summary}

@router.get("/")
def list_papers(db: Session = Depends(get_db)):
    papers = db.query(Paper).all()
    return [{"id": p.id, "title": p.title} for p in papers]
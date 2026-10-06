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
    """Interactive document Q&A engine grounded in paper text using RAG and LLMs."""
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        return {"error": "Paper not found"}

    question = payload.get("question", "")
    response = answer_question(paper.original_text, question, paper_title=paper.title)
    return response

@router.get("/")
def list_papers(db: Session = Depends(get_db)):
    papers = db.query(Paper).order_by(Paper.id.desc()).limit(20).all()
    return [{"id": p.id, "title": p.title, "uploaded_at": p.uploaded_at.isoformat() if p.uploaded_at else None} for p in papers]

@router.get("/{paper_id}/drug-discovery")
def get_paper_drug_discovery(paper_id: int, db: Session = Depends(get_db)):
    """Extracts disease and returns historical milestones, approved drugs, and pipeline landscape."""
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        return {"error": "Paper not found"}

    from app.services.drug_discovery import get_drug_discovery_landscape
    landscape = get_drug_discovery_landscape(paper.original_text, paper_title=paper.title)
    return landscape

@router.post("/compare")
def compare_papers_by_id(payload: dict = Body(...), db: Session = Depends(get_db)):
    """Compares two uploaded or loaded papers head-to-head."""
    paper1_id = payload.get("paper_id_1")
    paper2_id = payload.get("paper_id_2")

    if not paper1_id or not paper2_id:
        return {"error": "Both paper_id_1 and paper_id_2 must be provided."}

    p1 = db.query(Paper).filter(Paper.id == paper1_id).first()
    p2 = db.query(Paper).filter(Paper.id == paper2_id).first()

    if not p1 or not p2:
        return {"error": "One or both papers could not be found."}

    from app.services.paper_comparator import compare_two_papers
    paper1_dict = {"id": p1.id, "title": p1.title, "original_text": p1.original_text}
    paper2_dict = {"id": p2.id, "title": p2.title, "original_text": p2.original_text}

    report = compare_two_papers(paper1_dict, paper2_dict)
    report["paper1_id"] = p1.id
    report["paper2_id"] = p2.id
    return report

@router.post("/compare/upload")
async def compare_uploaded_papers(
    file1: UploadFile = File(...),
    file2: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Uploads two PDF files simultaneously and performs comparative analysis."""
    temp_path1 = f"temp_comp1_{file1.filename}"
    temp_path2 = f"temp_comp2_{file2.filename}"

    with open(temp_path1, "wb") as buffer:
        shutil.copyfileobj(file1.file, buffer)
    with open(temp_path2, "wb") as buffer:
        shutil.copyfileobj(file2.file, buffer)

    try:
        text1 = extract_text_from_pdf(temp_path1)
        text2 = extract_text_from_pdf(temp_path2)
    finally:
        if os.path.exists(temp_path1):
            os.remove(temp_path1)
        if os.path.exists(temp_path2):
            os.remove(temp_path2)

    t1 = file1.filename.replace(".pdf", "").replace("_", " ").replace("-", " ").title()
    t2 = file2.filename.replace(".pdf", "").replace("_", " ").replace("-", " ").title()

    p1 = Paper(title=t1, original_text=text1)
    p2 = Paper(title=t2, original_text=text2)
    db.add(p1)
    db.add(p2)
    db.commit()
    db.refresh(p1)
    db.refresh(p2)

    from app.services.paper_comparator import compare_two_papers
    paper1_dict = {"id": p1.id, "title": p1.title, "original_text": p1.original_text}
    paper2_dict = {"id": p2.id, "title": p2.title, "original_text": p2.original_text}

    report = compare_two_papers(paper1_dict, paper2_dict)
    report["paper1_id"] = p1.id
    report["paper2_id"] = p2.id
    return report
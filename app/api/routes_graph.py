from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.paper import Paper
from app.services.entity_extractor import extract_entities
from app.services.graph_builder import build_graph

router = APIRouter()

@router.get("/{paper_id}")
def get_graph(paper_id: int, db: Session = Depends(get_db)):
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        return {"error": "Paper not found"}

    entities = extract_entities(paper.original_text)
    graph = build_graph(entities)

    return graph
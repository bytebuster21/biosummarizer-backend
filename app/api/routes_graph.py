from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.paper import Paper
from app.services.entity_extractor import extract_entities
from app.services.graph_builder import build_graph
import json

router = APIRouter()

@router.get("/{paper_id}")
def get_graph(paper_id: int, db: Session = Depends(get_db)):
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        return {"error": "Paper not found"}

    entities = extract_entities(paper.original_text)
    graph = build_graph(entities, full_text=paper.original_text)

    # Persist graph data
    try:
        paper.graph_data = json.dumps(graph)
        db.commit()
    except Exception as e:
        print(f"Graph persistence notice: {e}")

    return {
        "paper_id": paper.id,
        "nodes": graph["nodes"],
        "edges": graph["edges"],
        "summary_stats": graph.get("summary_stats", {}),
        "entities": entities
    }
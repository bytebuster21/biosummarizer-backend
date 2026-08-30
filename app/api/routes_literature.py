from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.models.paper import Paper
from app.services.entity_extractor import extract_entities
from app.services.external_databases import fetch_related_papers_pubmed

router = APIRouter()

@router.get("/related/{paper_id}")
def get_related_papers(paper_id: int, db: Session = Depends(get_db)):
    """
    Fetches real-time related literature from NCBI PubMed based on
    the uploaded paper's key extracted biomedical entities and title.
    """
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        return {"error": "Paper not found", "papers": []}

    # Extract key entities to query PubMed
    entities = extract_entities(paper.original_text)
    query_terms = [e["name"] for e in entities[:4]]
    if not query_terms:
        query_terms = [paper.title]

    related = fetch_related_papers_pubmed(query_terms, max_results=6)
    return {
        "paper_id": paper.id,
        "query_terms": query_terms,
        "related_papers": related
    }

@router.get("/search")
def search_pubmed(query: str = Query(..., min_length=2), limit: int = 5):
    """Direct search of PubMed articles by custom keyword/query."""
    terms = [query]
    results = fetch_related_papers_pubmed(terms, max_results=limit)
    return {"query": query, "results": results}

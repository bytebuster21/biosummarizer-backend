from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import routes_papers, routes_summarize, routes_graph, routes_literature
from app.core.config import settings
from app.core.database import engine, Base
from app.models import paper, graph

# Ensure all database tables exist
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="BioLens: Biomedical Research Intelligence Platform",
    description="Advanced Biomedical Research Paper Summarizer, Semantic Knowledge Graph Generator & External DB Hub",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes_papers.router, prefix="/api/papers", tags=["papers"])
app.include_router(routes_summarize.router, prefix="/api/summarize", tags=["summarize"])
app.include_router(routes_graph.router, prefix="/api/graph", tags=["graph"])
app.include_router(routes_literature.router, prefix="/api/literature", tags=["literature"])

@app.get("/")
def root():
    return {
        "message": "BioLens Biomedical Intelligence API is operational",
        "version": "2.0.0",
        "endpoints": [
            "/api/papers",
            "/api/summarize",
            "/api/graph",
            "/api/literature"
        ]
    }
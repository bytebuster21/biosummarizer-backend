from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import routes_papers, routes_summarize, routes_graph
from app.core.config import settings

app = FastAPI(title="Biomedical Research Paper Summarizer & Knowledge Graph Generator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes_papers.router, prefix="/api/papers", tags=["papers"])
app.include_router(routes_summarize.router, prefix="/api/summarize", tags=["summarize"])
app.include_router(routes_graph.router, prefix="/api/graph", tags=["graph"])

@app.get("/")
def root():
    return {"message": "Biomedical Summarizer API is running"}
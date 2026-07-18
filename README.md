# Biomedical Research Paper Summarizer & Knowledge Graph Generator — Backend

## Setup
1. Create virtual environment: `python -m venv venv`
2. Activate: `venv\Scripts\activate` (Windows)
3. Install dependencies: `pip install -r requirements.txt`
4. Copy `.env.example` to `.env` and fill in values
5. Run server: `uvicorn app.main:app --reload`
6. Visit `http://localhost:8000/docs` for API documentation
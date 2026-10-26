import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.database import Base
from app.models.paper import Paper
from app.api.routes_papers import list_papers, load_sample_paper, get_paper, ask_paper_question
from app.api.routes_summarize import summarize_paper
from app.api.routes_graph import get_graph
from app.services.qa_engine import (
    answer_question,
    _chunk_document,
    _bm25_retrieve,
    _tokenize,
    _grounded_biomedical_synthesis
)
from app.services.sample_papers import SAMPLE_PAPERS


class TestRAGEngine(unittest.TestCase):
    def setUp(self):
        self.sample = SAMPLE_PAPERS[0]
        self.text = self.sample["abstract"]

    def test_tokenization(self):
        tokens = _tokenize("The PD-1 inhibitor pembrolizumab showed 74.1% survival (p=0.0005).")
        self.assertIn("pd-1", tokens)
        self.assertIn("pembrolizumab", tokens)
        self.assertIn("survival", tokens)
        self.assertNotIn("the", tokens)

    def test_chunking(self):
        chunks = _chunk_document(self.text, target_chunk_words=50, overlap_words=15)
        self.assertGreater(len(chunks), 1)
        for c in chunks:
            self.assertIn("text", c)
            self.assertIn("sentences", c)
            self.assertIn("tokens", c)

    def test_bm25_retrieval(self):
        chunks = _chunk_document(self.text, target_chunk_words=60, overlap_words=20)
        results = _bm25_retrieve(chunks, "What was the progression-free survival rate?")
        self.assertGreater(len(results), 0)
        top_chunk, score = results[0]
        self.assertGreater(score, 0.0)
        self.assertTrue(
            "progression-free survival" in top_chunk["text"].lower() or "pembrolizumab" in top_chunk["text"].lower()
        )

    def test_answer_generation_grounded(self):
        question = "What was the 1-year overall survival rate for pembrolizumab vs ipilimumab?"
        res = answer_question(self.text, question)

        self.assertIn("answer", res)
        self.assertIn("citations", res)
        self.assertIn("confidence", res)
        self.assertIn("highlight_sentence", res)
        self.assertGreater(len(res["citations"]), 0)
        self.assertGreaterEqual(res["confidence"], 0.65)
        # Verify the answer contains grounded clinical facts from the paper
        self.assertTrue("74.1%" in res["answer"] or "pembrolizumab" in res["answer"])

    def test_empty_or_invalid_query(self):
        res_empty = answer_question(self.text, "")
        self.assertEqual(res_empty["confidence"], 0.0)

        res_no_text = answer_question("", "What is the survival rate?")
        self.assertEqual(res_no_text["confidence"], 0.0)


class TestBackendPerformanceAndRoutes(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        Base.metadata.create_all(bind=self.engine)
        self.db = self.SessionLocal()

    def tearDown(self):
        self.db.close()

    def test_sample_load_and_deduplication(self):
        # First load
        paper1 = load_sample_paper("sample-1", db=self.db)
        self.assertIn("id", paper1)

        # Second load should return existing paper without duplication
        paper2 = load_sample_paper("sample-1", db=self.db)
        self.assertEqual(paper1["id"], paper2["id"])

        count = self.db.query(Paper).count()
        self.assertEqual(count, 1)

    def test_list_papers_columns(self):
        load_sample_paper("sample-1", db=self.db)
        papers = list_papers(db=self.db)
        self.assertEqual(len(papers), 1)
        self.assertIn("id", papers[0])
        self.assertIn("title", papers[0])
        self.assertIn("uploaded_at", papers[0])

    def test_qa_endpoint(self):
        paper = load_sample_paper("sample-2", db=self.db)
        res = ask_paper_question(
            paper["id"],
            {"question": "How did CRISPR gene editing affect vaso-occlusive crises?"},
            db=self.db
        )
        self.assertIn("answer", res)
        self.assertIn("citations", res)
        self.assertIn("confidence", res)
        self.assertTrue("vaso-occlusive" in res["answer"].lower() or "crispr" in res["answer"].lower())

    def test_graph_caching(self):
        paper = load_sample_paper("sample-1", db=self.db)
        # First call computes and caches graph
        g1 = get_graph(paper["id"], db=self.db)
        self.assertIn("nodes", g1)
        self.assertIn("edges", g1)

        db_paper = self.db.query(Paper).filter(Paper.id == paper["id"]).first()
        self.assertIsNotNone(db_paper.graph_data)

        # Second call returns cached graph
        g2 = get_graph(paper["id"], db=self.db)
        self.assertEqual(len(g1["nodes"]), len(g2["nodes"]))
        self.assertEqual(len(g1["edges"]), len(g2["edges"]))

    def test_summarize_caching(self):
        paper = load_sample_paper("sample-1", db=self.db)
        s1 = summarize_paper(paper["id"], db=self.db)
        self.assertIn("summary", s1)
        self.assertIn("multiview", s1)

        db_paper = self.db.query(Paper).filter(Paper.id == paper["id"]).first()
        self.assertIsNotNone(db_paper.structured_summary)

        # Second call returns cached summary
        s2 = summarize_paper(paper["id"], db=self.db)
        self.assertEqual(s1["summary"], s2["summary"])


if __name__ == "__main__":
    unittest.main()

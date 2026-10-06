import unittest
from fastapi.testclient import TestClient
from app.main import app
from app.services.sample_papers import SAMPLE_PAPERS
from app.services.qa_engine import answer_question
from app.services.summarizer import summarize_paper_multiview
from app.services.drug_discovery import get_drug_discovery_landscape
from app.services.paper_comparator import compare_two_papers

class TestBioLensFeatures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_rag_qa_engine(self):
        paper = SAMPLE_PAPERS[0]
        # Test specific clinical question
        res = answer_question(paper["abstract"], "What were the primary endpoints and hazard ratios?", paper_title=paper["title"])
        self.assertIn("answer", res)
        self.assertGreater(len(res["answer"]), 20)
        self.assertIn("confidence", res)
        self.assertIn("model_used", res)

        # Test broad/general question
        res2 = answer_question(paper["abstract"], "Can you summarize the main findings and conclusions?", paper_title=paper["title"])
        self.assertIn("answer", res2)
        self.assertGreater(len(res2["answer"]), 20)

    def test_detailed_summarizer(self):
        paper = SAMPLE_PAPERS[0]
        summary = summarize_paper_multiview(paper["abstract"])
        self.assertIn("tldr", summary)
        self.assertIn("plain_language", summary)
        self.assertIn("clinical_summary", summary)
        self.assertIn("structured_sections", summary)
        
        sections = summary["structured_sections"]
        self.assertIn("background", sections)
        self.assertIn("methodology", sections)
        self.assertIn("findings", sections)
        self.assertIn("safety", sections)
        self.assertIn("conclusion", sections)
        
        self.assertGreaterEqual(len(summary["key_highlights"]), 3)
        self.assertGreaterEqual(len(summary["evidence_grounding"]), 3)

    def test_drug_discovery_service(self):
        paper = SAMPLE_PAPERS[0] # Melanoma paper
        dd = get_drug_discovery_landscape(paper["abstract"], paper_title=paper["title"])
        self.assertIn("disease_name", dd)
        self.assertIn("Melanoma", dd["disease_name"])
        self.assertGreater(len(dd["timeline"]), 0)
        self.assertGreater(len(dd["approved_therapies"]), 0)
        self.assertGreater(len(dd["pipeline_modalities"]), 0)
        self.assertGreater(len(dd["targets_and_pathways"]), 0)
        self.assertIn("external_registries", dd)

    def test_paper_comparator_service(self):
        p1 = SAMPLE_PAPERS[0] # KEYNOTE-006 (Melanoma: Pembro vs Ipi)
        p2 = SAMPLE_PAPERS[2] # KEYNOTE-942 (Melanoma: mRNA-4157 + Pembro)
        comp = compare_two_papers(p1, p2)
        self.assertIn("comparative_summary", comp)
        self.assertIn("verdict", comp)
        self.assertIn("pico_comparison", comp)
        self.assertIn("efficacy_comparison", comp)
        self.assertIn("safety_comparison", comp)
        self.assertIn("entity_overlap", comp)
        self.assertGreater(len(comp["takeaways"]), 0)

    def test_api_endpoints(self):
        # 1. Load sample papers
        res1 = self.client.post("/api/papers/samples/load/sample-1")
        self.assertEqual(res1.status_code, 200)
        p1_id = res1.json()["id"]

        res2 = self.client.post("/api/papers/samples/load/sample-3")
        self.assertEqual(res2.status_code, 200)
        p2_id = res2.json()["id"]

        # 2. Test QA endpoint
        qa_res = self.client.post(f"/api/papers/{p1_id}/qa", json={"question": "What were the high grade adverse events?"})
        self.assertEqual(qa_res.status_code, 200)
        self.assertIn("answer", qa_res.json())

        # 3. Test Drug Discovery endpoint
        dd_res = self.client.get(f"/api/papers/{p1_id}/drug-discovery")
        self.assertEqual(dd_res.status_code, 200)
        self.assertIn("approved_therapies", dd_res.json())

        # 4. Test Compare endpoint
        comp_res = self.client.post("/api/papers/compare", json={"paper_id_1": p1_id, "paper_id_2": p2_id})
        self.assertEqual(comp_res.status_code, 200)
        self.assertIn("verdict", comp_res.json())
        self.assertIn("pico_comparison", comp_res.json())

if __name__ == "__main__":
    unittest.main()

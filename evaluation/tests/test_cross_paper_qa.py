import unittest
import json
from pathlib import Path

from cross_paper_qa import (
    ComparisonPoint,
    CrossPaperAnswer,
    PaperClaim,
    explicit_source_file,
    is_reference_like_chunk,
    render_answer,
    validate_claim_sources,
)
from evaluation.text_matching import evaluate_q04_answer


ROOT = Path(__file__).resolve().parents[2]
Q16_RESULT = (
    ROOT
    / "evaluation"
    / "results"
    / "cross_paper_qa_20261110T095522Z.json"
)
PILOT_RESULT = (
    ROOT
    / "evaluation"
    / "results"
    / "formal_benchmark_pilot_20261110.json"
)


class CrossPaperQATests(unittest.TestCase):
    def setUp(self):
        self.evidence = [
            {
                "evidence_id": "S1",
                "source_type": "local_pdf",
                "source_file": "entropy.pdf",
                "page_number": 1,
                "chunk_id": "entropy:1",
                "supporting_text": "entropy evidence",
            },
            {
                "evidence_id": "S2",
                "source_type": "local_pdf",
                "source_file": "pzo.pdf",
                "page_number": 1,
                "chunk_id": "pzo:1",
                "supporting_text": "PZO evidence",
            },
        ]
        self.evidence_by_id = {
            item["evidence_id"]: item for item in self.evidence
        }
        self.source_to_paper = {
            "entropy.pdf": "P1",
            "pzo.pdf": "P2",
        }
        self.answer = CrossPaperAnswer(
            paper_claims=[
                PaperClaim(
                    paper_code="P1",
                    design_approach="Entropy design",
                    methodological_details="Entropy method",
                    evidence_ids=["S1"],
                ),
                PaperClaim(
                    paper_code="P2",
                    design_approach="Domain modulation",
                    methodological_details="Phase-field method",
                    evidence_ids=["S2"],
                ),
            ],
            comparison_points=[
                ComparisonPoint(
                    dimension="method",
                    summary="Different methods",
                    paper_codes=["P1", "P2"],
                    evidence_ids=["S1", "S2"],
                )
            ],
        )

    def test_correct_evidence_ownership_passes(self):
        result = validate_claim_sources(
            self.answer,
            self.evidence_by_id,
            self.source_to_paper,
        )
        self.assertTrue(result["passed"])

    def test_entropy_chunk_cannot_be_labeled_as_pzo(self):
        bad = self.answer.model_copy(deep=True)
        bad.paper_claims[1].evidence_ids = ["S1"]
        result = validate_claim_sources(
            bad,
            self.evidence_by_id,
            self.source_to_paper,
        )
        self.assertFalse(result["passed"])
        self.assertTrue(
            any("belongs to P1, not P2" in error for error in result["errors"])
        )

    def test_program_renders_source_file_and_page(self):
        rendered = render_answer(
            self.answer,
            self.evidence,
            self.source_to_paper,
        )
        self.assertIn("entropy.pdf", rendered)
        self.assertIn("pzo.pdf", rendered)
        self.assertIn("[S1]", rendered)
        self.assertIn("[S2]", rendered)

    def test_reference_list_chunk_is_excluded_from_evidence(self):
        self.assertTrue(
            is_reference_like_chunk(
                "[1] Alpha [2] Beta [3] Gamma [4] Delta"
            )
        )
        self.assertTrue(
            is_reference_like_chunk(
                "Reference: [1] Alpha [2] Beta"
            )
        )
        self.assertFalse(
            is_reference_like_chunk(
                "The antiferroelectric domain method improves energy storage."
            )
        )

    def test_explicit_source_file_filter_is_opt_in(self):
        self.assertIsNone(
            explicit_source_file("Compare two imported papers.")
        )
        self.assertEqual(
            explicit_source_file(
                "Only use materials-4180042.pdf for this question."
            ),
            "materials-4180042.pdf",
        )
        self.assertIsNone(
            explicit_source_file("Compare a.pdf and b.pdf.")
        )

    def test_q16_lightweight_result_has_two_sources_and_valid_ownership(self):
        result = json.loads(Q16_RESULT.read_text(encoding="utf-8"))
        self.assertEqual(result["status"], "completed_pending_human_review")
        self.assertEqual(result["source_count"], 2)
        self.assertTrue(result["evidence_ownership_validation"]["passed"])
        self.assertTrue(result["citation_validation"]["passed"])
        codes = {
            claim["paper_code"] for claim in result["paper_claims"]["paper_claims"]
        }
        self.assertEqual(codes, {"P1", "P2"})
        self.assertEqual(result["llm_call_count"], 2)
        self.assertEqual(result["total_tokens"], 5493)

    def test_existing_q04_and_q10_deep_results_still_pass_regression(self):
        payload = json.loads(PILOT_RESULT.read_text(encoding="utf-8"))
        q04 = next(
            run
            for run in payload["runs"]
            if run["question_id"] == "q04"
            and run["system_variant"] == "D_deep"
        )
        q10 = next(
            run
            for run in payload["runs"]
            if run["question_id"] == "q10"
            and run["system_variant"] == "D_deep"
        )
        self.assertTrue(evaluate_q04_answer(q04["final_answer"])["passed"])
        self.assertIn("证据不足", q10["final_answer"])


if __name__ == "__main__":
    unittest.main()

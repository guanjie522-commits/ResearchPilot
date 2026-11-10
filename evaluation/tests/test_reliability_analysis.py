import json
import unittest
from pathlib import Path

from evaluation.metrics import calculate_metrics
from evaluation.reliability_analysis import (
    PILOT_PATH,
    build_diagnostics,
    q04_before_after,
)
from evaluation.text_matching import evaluate_q04_answer


ROOT = Path(__file__).resolve().parents[2]


class HistoricalReliabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dataset = json.loads(
            (ROOT / "evaluation" / "dataset.json").read_text(encoding="utf-8")
        )
        cls.pilot = json.loads(PILOT_PATH.read_text(encoding="utf-8"))
        cls.question_map = {
            question["question_id"]: question
            for question in cls.dataset["questions"]
        }

    def test_q04_direct_answer_is_corrected_to_pass(self):
        direct = next(
            run
            for run in self.pilot["runs"]
            if run["question_id"] == "q04"
            and run["system_variant"] == "B_direct_rag"
        )
        before = direct["automated_quality_signal"]["keyword_check_passed"]
        after = evaluate_q04_answer(direct["final_answer"])["passed"]
        self.assertFalse(before)
        self.assertTrue(after)
        self.assertEqual(q04_before_after(self.pilot["runs"])["after_passed"], 3)

    def test_q09_is_located_at_executor_tool_selection(self):
        diagnostics = build_diagnostics(
            self.question_map,
            self.pilot["runs"],
        )
        q09 = diagnostics["q09"]
        self.assertEqual(q09["observed_tool_call"]["name"], "search_papers")
        self.assertEqual(q09["local_pdf_evidence_ids"], [])
        self.assertIn("Executor layer", q09["confirmed_findings"][2])
        self.assertEqual(
            q09["planner_plan"],
            "unavailable_not_persisted_in_historical_result",
        )

    def test_q16_premature_termination_is_not_overclaimed(self):
        diagnostics = build_diagnostics(
            self.question_map,
            self.pilot["runs"],
        )
        q16 = diagnostics["q16"]
        self.assertTrue(q16["retrieval_miss"])
        self.assertTrue(q16["incorrect_abstention"])
        self.assertEqual(q16["premature_termination"], "unknown")

    def test_partial_deep_token_metrics_remain_null(self):
        question_ids = {run["question_id"] for run in self.pilot["runs"]}
        questions = [
            question
            for question in self.dataset["questions"]
            if question["question_id"] in question_ids
        ]
        metrics = calculate_metrics(self.pilot["runs"], questions)
        deep = metrics["variants"]["D_deep"]
        self.assertIsNone(deep["total_tokens"])
        self.assertEqual(deep["total_tokens_available_sum"], 43192)
        self.assertEqual(deep["total_token_metric_status"], "partial")
        self.assertEqual(deep["total_token_metric_missing_runs"], 2)


if __name__ == "__main__":
    unittest.main()

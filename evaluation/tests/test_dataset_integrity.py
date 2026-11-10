import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DATASET_PATH = ROOT / "evaluation" / "dataset.json"
PILOT_PATH = (
    ROOT
    / "evaluation"
    / "results"
    / "formal_benchmark_pilot_20261110.json"
)
Q16_DIAGNOSIS_PATH = (
    ROOT
    / "evaluation"
    / "results"
    / "q16_retrieval_diagnosis_20261110.json"
)
HUMAN_REVIEW_PATH = ROOT / "evaluation" / "human_review.md"
EXPECTED_PILOT_SHA256 = (
    "0d02a575a9ef5cbf845c84179c0ec76e18b56ba74fe6d7ab3900f1e7b69eae54"
)


class DatasetIntegrityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
        cls.questions = {
            item["question_id"]: item for item in cls.dataset["questions"]
        }

    def test_every_question_has_valid_task_metadata(self):
        task_types = set(self.dataset["task_type_taxonomy"])
        source_scopes = set(self.dataset["source_scope_taxonomy"])
        for question in self.questions.values():
            with self.subTest(question_id=question["question_id"]):
                self.assertTrue(question["task_types"])
                self.assertTrue(set(question["task_types"]).issubset(task_types))
                self.assertIn(question["source_scope"], source_scopes)
                self.assertTrue(question["expected_tools"])

    def test_q09_original_and_explicit_local_variant_both_exist(self):
        original = self.questions["q09"]
        variant = self.questions["q09_local_pdf"]
        self.assertEqual(
            original["question"],
            "请用中文说明这个扰动模型为何能处理以前常系数或各向同性近似难以处理的问题。",
        )
        self.assertFalse(original["source_scope_is_explicit"])
        self.assertIn("ambiguity_notes", original)
        self.assertTrue(variant["source_scope_is_explicit"])
        self.assertEqual(variant["derived_from"], "q09")
        self.assertEqual(variant["execution_status"], "not_run")
        self.assertIn("本地 PDF", variant["question"])

    def test_original_pilot_result_was_not_overwritten(self):
        digest = hashlib.sha256(PILOT_PATH.read_bytes()).hexdigest()
        self.assertEqual(digest, EXPECTED_PILOT_SHA256)

    def test_pending_review_status_is_not_upgraded(self):
        reviewed_ids = {"q01", "q04", "q09", "q16", "q10"}
        for question_id in reviewed_ids:
            self.assertEqual(
                self.questions[question_id]["verification_status"],
                "pending_human_review",
            )

    def test_q16_diagnosis_records_miss_and_present_target_chunks(self):
        diagnosis = json.loads(
            Q16_DIAGNOSIS_PATH.read_text(encoding="utf-8")
        )
        retrieval = diagnosis["original_retrieval"]
        self.assertEqual(retrieval["query"], "entropy")
        self.assertEqual(retrieval["top_k"], 4)
        self.assertEqual(retrieval["results_passing_threshold"], [])
        self.assertIn("Evidence insufficient", retrieval["current_tool_result"])
        self.assertTrue(
            all(
                item["present_in_index"]
                for item in diagnosis["target_presence_in_index"]
            )
        )

    def test_human_review_contains_all_requested_items(self):
        text = HUMAN_REVIEW_PATH.read_text(encoding="utf-8")
        for question_id in ("q01", "q04", "q09", "q16", "q10"):
            self.assertIn(f"## {question_id}", text)
        labels = (
            "Question ID",
            "原始问题",
            "候选参考答案",
            "支持原文",
            "PDF 文件名",
            "页码",
            "Baseline 回答",
            "Direct RAG 回答",
            "Fast Mode 回答",
            "Deep Mode 回答",
            "真实引用来源",
            "待审核问题",
        )
        for item_number, label in enumerate(labels, start=1):
            self.assertEqual(
                text.count(f"{item_number}. **{label}"),
                5,
                msg=f"item {item_number}",
            )
        self.assertIn("q09_local_pdf", text)
        self.assertIn("pending_human_review", text)
        self.assertIn("q16 诊断", text)


if __name__ == "__main__":
    unittest.main()

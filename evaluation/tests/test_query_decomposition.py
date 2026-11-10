import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
EXPERIMENT_PATH = (
    ROOT
    / "evaluation"
    / "results"
    / "q16_query_experiments_20261110.json"
)
Q09_VARIANT_RESULT_PATH = (
    ROOT
    / "evaluation"
    / "results"
    / "benchmark_20261110T063228Z.json"
)
INTEGRATED_RETRIEVAL_PATH = (
    ROOT
    / "evaluation"
    / "results"
    / "q16_integrated_retrieval_20261110.json"
)
Q16_DECOMPOSED_TIMEOUT_PATH = (
    ROOT
    / "evaluation"
    / "results"
    / "benchmark_20261110T090436Z.json"
)
GATE_CHECK_PATH = (
    ROOT
    / "evaluation"
    / "results"
    / "query_decomposition_gate_checks_20261110.json"
)


class QueryDecompositionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.experiment = json.loads(
            EXPERIMENT_PATH.read_text(encoding="utf-8")
        )

    def test_coverage_ladder(self):
        self.assertEqual(
            self.experiment["A_original_query"]["coverage"][
                "target_coverage"
            ],
            "0/2",
        )
        self.assertEqual(
            self.experiment["B_complete_semantic_query"]["coverage"][
                "target_coverage"
            ],
            "1/2",
        )
        self.assertEqual(
            self.experiment["C_decomposed_global"]["coverage"][
                "target_coverage"
            ],
            "2/2",
        )
        self.assertEqual(
            self.experiment["C_decomposed_source_filtered"]["coverage"][
                "target_coverage"
            ],
            "2/2",
        )

    def test_source_filter_condition_is_explicit(self):
        filtered = self.experiment["C_decomposed_source_filtered"]
        for query in filtered["queries"]:
            self.assertTrue(query["source_filter_enabled"])
            self.assertIsNotNone(query["source_filter"])
        for query in self.experiment["C_decomposed_global"]["queries"]:
            self.assertFalse(query["source_filter_enabled"])
            self.assertIsNone(query["source_filter"])

    def test_production_threshold_was_not_changed(self):
        config = self.experiment["configuration"]
        self.assertFalse(config["production_threshold_changed"])
        self.assertEqual(config["relevance_threshold"], 0.25)
        self.assertEqual(
            config["score_type"],
            "chroma_relevance_1_minus_cosine_distance_higher_is_better",
        )

    def test_raw_scores_are_descending_within_each_query(self):
        group_queries = [
            self.experiment["A_original_query"],
            self.experiment["B_complete_semantic_query"],
            *self.experiment["C_decomposed_global"]["queries"],
        ]
        for query in group_queries:
            scores = [
                item["relevance_score"]
                for item in query["raw_results"]
            ]
            self.assertEqual(scores, sorted(scores, reverse=True))

    def test_queries_are_not_copies_of_target_supporting_text(self):
        dataset = json.loads(
            (ROOT / "evaluation" / "dataset.json").read_text(encoding="utf-8")
        )
        q16 = next(
            item
            for item in dataset["questions"]
            if item["question_id"] == "q16"
        )
        target_excerpts = [
            source["supporting_excerpt"]
            for source in q16["supporting_sources"]
        ]
        queries = [
            self.experiment["A_original_query"]["query"],
            self.experiment["B_complete_semantic_query"]["query"],
            *[
                item["query"]
                for item in self.experiment["C_decomposed_global"][
                    "queries"
                ]
            ],
        ]
        for query in queries:
            for excerpt in target_excerpts:
                self.assertNotEqual(query.casefold(), excerpt.casefold())

    def test_q09_explicit_variant_used_local_retriever_and_evidence(self):
        payload = json.loads(
            Q09_VARIANT_RESULT_PATH.read_text(encoding="utf-8")
        )
        run = payload["runs"][0]
        self.assertEqual(run["question_id"], "q09_local_pdf")
        self.assertEqual(
            run["tool_calls"][0]["name"],
            "retrieve_paper_evidence",
        )
        self.assertTrue(run["tool_calls"][0]["evidence_ids"])
        self.assertEqual(
            {source["source_file"] for source in run["cited_sources"]},
            {"materials-4180042.pdf"},
        )

    def test_integrated_decomposition_retrieval_covers_both_target_papers(self):
        payload = json.loads(
            INTEGRATED_RETRIEVAL_PATH.read_text(encoding="utf-8")
        )
        self.assertEqual(len(payload["queries"]), 2)
        self.assertEqual(len(payload["trace"]), 2)
        files = {
            source
            for item in payload["trace"]
            for source in item["source_files"]
        }
        self.assertIn("s41467-025-56194-1.pdf", files)
        self.assertIn("1-s2.0-S2352847824001278-main.pdf", files)
        self.assertTrue(
            all(item["source_filter_enabled"] is False for item in payload["trace"])
        )

    def test_full_integrated_run_timeout_is_recorded_honestly(self):
        payload = json.loads(
            Q16_DECOMPOSED_TIMEOUT_PATH.read_text(encoding="utf-8")
        )
        self.assertEqual(payload["runs"][0]["run_status"], "timeout")
        self.assertIsNone(
            payload["runs"][0]["performance"].get("total_tokens")
            if payload["runs"][0]["performance"]
            else None
        )

    def test_gate_disables_simple_tasks_and_enables_q16(self):
        payload = json.loads(GATE_CHECK_PATH.read_text(encoding="utf-8"))
        decisions = {
            item["question_id"]: item["validated_eligible"]
            for item in payload["checks"]
        }
        self.assertFalse(decisions["q04"])
        self.assertFalse(decisions["q09_local_pdf"])
        self.assertFalse(decisions["q10"])
        self.assertTrue(decisions["q16"])


if __name__ == "__main__":
    unittest.main()

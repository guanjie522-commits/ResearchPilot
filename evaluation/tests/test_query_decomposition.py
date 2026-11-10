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


if __name__ == "__main__":
    unittest.main()

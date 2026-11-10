import unittest

from evaluation.metrics import calculate_metrics


def make_run(
    *,
    variant: str,
    performance: dict,
    tool_calls: list[dict] | None = None,
) -> dict:
    return {
        "system_variant": variant,
        "run_status": "success",
        "elapsed_seconds": 1.0,
        "performance": performance,
        "tool_calls": tool_calls or [],
        "citation_validation": {"passed": True, "unknown_citation_ids": []},
    }


class MetricsReliabilityTests(unittest.TestCase):
    def test_partial_token_metrics_are_not_reported_as_a_complete_sum(self):
        metrics = calculate_metrics(
            [
                make_run(
                    variant="D_deep",
                    performance={
                        "llm_call_count": 5,
                        "prompt_tokens": 100,
                        "completion_tokens": 200,
                        "total_tokens": 300,
                    },
                ),
                make_run(variant="D_deep", performance={}),
            ],
            [],
        )
        variant = metrics["variants"]["D_deep"]
        self.assertIsNone(variant["llm_call_count"])
        self.assertEqual(variant["llm_call_count_available_sum"], 5)
        self.assertIsNone(variant["total_tokens"])
        self.assertEqual(variant["total_tokens_available_sum"], 300)
        self.assertEqual(variant["total_token_metric_status"], "partial")
        self.assertEqual(variant["total_token_metric_missing_runs"], 1)

    def test_no_llm_call_is_zero_tokens_when_metadata_is_present(self):
        metrics = calculate_metrics(
            [
                make_run(
                    variant="B_direct_rag",
                    performance={
                        "llm_call_count": 0,
                        "prompt_tokens": None,
                        "completion_tokens": None,
                        "total_tokens": None,
                    },
                )
            ],
            [],
        )
        variant = metrics["variants"]["B_direct_rag"]
        self.assertEqual(variant["llm_call_count"], 0)
        self.assertEqual(variant["total_tokens"], 0)
        self.assertEqual(variant["total_token_metric_status"], "available")

    def test_missing_tool_response_metadata_is_unavailable(self):
        metrics = calculate_metrics(
            [
                make_run(
                    variant="D_deep",
                    performance={"llm_call_count": 1},
                    tool_calls=[
                        {
                            "name": "retrieve_paper_evidence",
                            "args": {"query": "entropy"},
                        }
                    ],
                )
            ],
            [],
        )
        variant = metrics["variants"]["D_deep"]
        self.assertEqual(variant["tool_call_success_status"], "unavailable")
        self.assertEqual(variant["tool_call_success_missing"], 1)

    def test_recorded_tool_response_success_is_counted(self):
        metrics = calculate_metrics(
            [
                make_run(
                    variant="D_deep",
                    performance={"llm_call_count": 1},
                    tool_calls=[
                        {
                            "name": "retrieve_paper_evidence",
                            "args": {"query": "entropy"},
                            "response_received": True,
                        }
                    ],
                )
            ],
            [],
        )
        variant = metrics["variants"]["D_deep"]
        self.assertEqual(variant["tool_call_success"], 1)
        self.assertEqual(variant["tool_call_success_status"], "available")


if __name__ == "__main__":
    unittest.main()

import json
import inspect
import unittest

from langchain_core.tools import StructuredTool

from query_decomposition import (
    QueryDecompositionRetriever,
    remove_ungrounded_domain_terms,
    validate_decomposition_plan,
)
from researchpilot_rag import build_research_graph


def evidence_result(query: str, source_file: str, chunk_id: str) -> str:
    return (
        f"query: {query}\n"
        "returned_evidence_count: 1\n\n"
        "Evidence 1:\n"
        f"  source_file: {source_file}\n"
        "  page_number: 1\n"
        f"  chunk_id: {chunk_id}\n"
        "  retrieval_score: 0.6\n"
        "  score_type: cosine_relevance\n"
        "  doi:\n"
        f"  text: evidence for {query}"
    )


class QueryDecompositionIntegrationTests(unittest.IsolatedAsyncioTestCase):
    def test_stable_graph_defaults_to_decomposition_disabled(self):
        default = inspect.signature(build_research_graph).parameters[
            "enable_query_decomposition"
        ].default
        self.assertFalse(default)

    def test_plan_validation_limits_queries_and_rejects_broad_terms(self):
        self.assertEqual(
            validate_decomposition_plan(
                (
                    "Compare the entropy paper and the PZO domain-modulation "
                    "paper."
                ),
                "Current corpus covers materials, phase-field simulation, and energy storage.",
                True,
                [
                    "How does increasing entropy improve antiferroelectric energy storage performance?",
                    "How does domain modulation use phase-field simulation for energy storage?",
                ],
            )[0],
            True,
        )
        self.assertFalse(
            validate_decomposition_plan(
                "Compare two papers across sources.",
                "Current corpus covers materials, phase-field simulation, and energy storage.",
                True,
                ["What design approach does the entropy paper use?"],
            )[0]
        )
        self.assertFalse(
            validate_decomposition_plan(
                "What is the critical temperature in these papers?",
                "Current corpus covers materials, phase-field simulation, and energy storage.",
                True,
                [
                    "What is the critical temperature reported in the entropy paper?",
                    "What is the critical temperature reported in the PZO paper?",
                ],
            )[0]
        )

    def test_ungrounded_domain_terms_are_removed_without_dropping_valid_query(self):
        query = (
            "How does the PZO domain-modulation paper implement magnetic "
            "domain engineering for energy storage applications?"
        )
        cleaned = remove_ungrounded_domain_terms(
            query,
            (
                "Compare the entropy paper and the PZO domain-modulation "
                "paper."
            ),
            "Local papers cover materials and energy storage.",
        )
        self.assertNotIn("magnetic", cleaned.casefold())
        self.assertIn("PZO", cleaned)
        self.assertIn("domain engineering", cleaned)

    async def test_each_query_calls_existing_tool_and_results_are_combined(self):
        calls = []

        async def fake_retriever(query: str, top_k: int = 4) -> str:
            calls.append({"query": query, "top_k": top_k})
            if "entropy" in query:
                text = evidence_result(
                    query,
                    "s41467-025-56194-1.pdf",
                    "chunk-1",
                )
            else:
                text = evidence_result(
                    query,
                    "1-s2.0-S2352847824001278-main.pdf",
                    "chunk-2",
                )
            return [{"type": "text", "text": text}]

        base_tool = StructuredTool.from_function(
            coroutine=fake_retriever,
            name="retrieve_paper_evidence",
            description="fake retriever",
        )
        queries = [
            "How does increasing entropy improve antiferroelectric energy storage?",
            "How does domain modulation use phase-field simulation?",
        ]
        retriever = QueryDecompositionRetriever(base_tool, queries)
        result = await retriever.retrieve("ignored model query")

        self.assertEqual([call["query"] for call in calls], queries)
        self.assertEqual(
            json.loads(json.dumps(retriever.trace))[0]["mcp_tool"],
            "retrieve_paper_evidence",
        )
        self.assertEqual(len(retriever.trace), 2)
        self.assertIn("query_count: 2", result)
        self.assertIn("s41467-025-56194-1.pdf", result)
        self.assertIn("1-s2.0-S2352847824001278-main.pdf", result)

        await retriever.retrieve("another outer call")
        self.assertEqual(len(calls), 2, "wrapper must cache, not retry")


if __name__ == "__main__":
    unittest.main()

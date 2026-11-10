import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rag.config import (  # noqa: E402
    DEFAULT_CHROMA_DIR,
    DEFAULT_INDEX_MANIFEST,
    DEFAULT_TOP_K,
    RELEVANCE_THRESHOLD,
)
from rag.pdf_index import (  # noqa: E402
    create_embeddings,
    load_manifest,
    open_vector_store,
    validate_manifest_config,
)


OUTPUT_PATH = (
    ROOT
    / "evaluation"
    / "results"
    / "q16_query_experiments_20261110.json"
)
TARGET_SOURCES = {
    "entropy paper": "s41467-025-56194-1.pdf",
    "PZO domain-modulation paper": "1-s2.0-S2352847824001278-main.pdf",
}
DECOMPOSED_QUERIES = (
    {
        "target_paper": "entropy paper",
        "query": (
            "How is increasing entropy used to design the antiferroelectric "
            "polarization configuration for capacitive energy storage?"
        ),
    },
    {
        "target_paper": "PZO domain-modulation paper",
        "query": (
            "How is antiferroelectric domain modulation studied with "
            "phase-field simulations to improve energy storage performance?"
        ),
    },
)


def compact_text(text: str, limit: int = 500) -> str:
    return re.sub(r"\s+", " ", text).strip()[:limit]


def search(
    store,
    query: str,
    *,
    top_k: int,
    source_filter: str | None,
) -> dict[str, Any]:
    started = time.perf_counter()
    kwargs: dict[str, Any] = {"k": top_k}
    if source_filter:
        kwargs["filter"] = {"source_file": source_filter}
    matches = store.similarity_search_with_relevance_scores(query, **kwargs)
    elapsed = time.perf_counter() - started

    raw_results = []
    for document, score in matches:
        raw_results.append(
            {
                "source_file": document.metadata["source_file"],
                "page_number": document.metadata["page_number"],
                "chunk_id": document.metadata["chunk_id"],
                "relevance_score": round(float(score), 6),
                "score_type": (
                    "chroma_relevance_1_minus_cosine_distance_"
                    "higher_is_better"
                ),
                "passes_threshold": float(score) >= RELEVANCE_THRESHOLD,
                "text_excerpt": compact_text(document.page_content),
            }
        )
    return {
        "query": query,
        "top_k": top_k,
        "source_filter_enabled": source_filter is not None,
        "source_filter": source_filter,
        "raw_results": raw_results,
        "results_passing_threshold": [
            item for item in raw_results if item["passes_threshold"]
        ],
        "execution_seconds": round(elapsed, 6),
    }


def coverage(results: list[dict[str, Any]]) -> dict[str, Any]:
    files = sorted({item["source_file"] for item in results})
    targets_hit = [
        name
        for name, source_file in TARGET_SOURCES.items()
        if source_file in files
    ]
    return {
        "hit_source_files": files,
        "target_papers_hit": targets_hit,
        "targets_hit_count": len(targets_hit),
        "targets_expected_count": len(TARGET_SOURCES),
        "target_coverage": f"{len(targets_hit)}/{len(TARGET_SOURCES)}",
    }


def group_result(queries: list[dict[str, Any]]) -> dict[str, Any]:
    passed = [
        item
        for query_result in queries
        for item in query_result["results_passing_threshold"]
    ]
    unique_passed = {
        item["chunk_id"]: item for item in passed
    }.values()
    passed_list = list(unique_passed)
    return {
        "queries": queries,
        "thresholded_unique_chunks": passed_list,
        "execution_seconds": round(
            sum(item["execution_seconds"] for item in queries),
            6,
        ),
        "coverage": coverage(passed_list),
    }


def threshold_sensitivity(raw_results: list[dict[str, Any]]) -> list[dict]:
    thresholds = (0.25, 0.20, 0.15, 0.10, 0.05, 0.0)
    return [
        {
            "threshold": threshold,
            "passing_chunk_count": sum(
                item["relevance_score"] >= threshold
                for item in raw_results
            ),
            "passing_chunks": [
                {
                    "source_file": item["source_file"],
                    "page_number": item["page_number"],
                    "chunk_id": item["chunk_id"],
                    "relevance_score": item["relevance_score"],
                }
                for item in raw_results
                if item["relevance_score"] >= threshold
            ],
        }
        for threshold in thresholds
    ]


def main() -> None:
    embeddings, dimension = create_embeddings()
    manifest = load_manifest(DEFAULT_INDEX_MANIFEST)
    validate_manifest_config(manifest, dimension)
    store = open_vector_store(embeddings, DEFAULT_CHROMA_DIR)

    original = search(
        store,
        "entropy",
        top_k=DEFAULT_TOP_K,
        source_filter=None,
    )
    complete_semantic = search(
        store,
        (
            "Compare the main design approaches of the entropy-based "
            "antiferroelectric polarization paper and the PZO "
            "antiferroelectric domain-modulation phase-field simulation paper."
        ),
        top_k=DEFAULT_TOP_K,
        source_filter=None,
    )
    decomposed_global_queries = [
        search(
            store,
            item["query"],
            top_k=DEFAULT_TOP_K,
            source_filter=None,
        )
        for item in DECOMPOSED_QUERIES
    ]
    decomposed_filtered_queries = [
        search(
            store,
            item["query"],
            top_k=DEFAULT_TOP_K,
            source_filter=TARGET_SOURCES[item["target_paper"]],
        )
        for item in DECOMPOSED_QUERIES
    ]

    payload = {
        "experiment_id": "q16_query_decomposition_20261110",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "configuration": {
            "embedding_model": manifest["embedding_model"],
            "embedding_dimension": manifest["embedding_dimension"],
            "collection_count": store._collection.count(),
            "top_k": DEFAULT_TOP_K,
            "relevance_threshold": RELEVANCE_THRESHOLD,
            "score_type": (
                "chroma_relevance_1_minus_cosine_distance_"
                "higher_is_better"
            ),
            "production_threshold_changed": False,
            "target_original_text_used_as_query": False,
        },
        "A_original_query": {
            **original,
            "coverage": coverage(original["results_passing_threshold"]),
            "threshold_sensitivity": threshold_sensitivity(
                original["raw_results"]
            ),
        },
        "B_complete_semantic_query": {
            **complete_semantic,
            "coverage": coverage(complete_semantic["results_passing_threshold"]),
        },
        "C_decomposed_global": group_result(decomposed_global_queries),
        "C_decomposed_source_filtered": group_result(
            decomposed_filtered_queries
        ),
        "comparison_note": (
            "C_source_filtered uses source_file filters and must not be "
            "treated as the same retrieval condition as global search."
        ),
    }
    OUTPUT_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    summary = {
        "A_original": payload["A_original_query"]["coverage"]["target_coverage"],
        "B_complete_semantic": payload[
            "B_complete_semantic_query"
        ]["coverage"]["target_coverage"],
        "C_decomposed_global": payload[
            "C_decomposed_global"
        ]["coverage"]["target_coverage"],
        "C_decomposed_source_filtered": payload[
            "C_decomposed_source_filtered"
        ]["coverage"]["target_coverage"],
    }
    print(f"q16 query experiments: {OUTPUT_PATH}")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

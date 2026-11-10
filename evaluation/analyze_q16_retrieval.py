import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rag.config import (
    DEFAULT_CHROMA_DIR,
    DEFAULT_INDEX_MANIFEST,
    RELEVANCE_THRESHOLD,
)
from rag.pdf_index import (
    create_embeddings,
    load_manifest,
    open_vector_store,
    validate_manifest_config,
)
from rag.qa import retrieve_paper_evidence
from evaluation.text_matching import normalize_for_matching


OUTPUT_PATH = (
    ROOT
    / "evaluation"
    / "results"
    / "q16_retrieval_diagnosis_20261110.json"
)
ORIGINAL_QUERY = "entropy"
ORIGINAL_TOP_K = 4
TARGETS = (
    {
        "paper": "entropy paper",
        "source_file": "s41467-025-56194-1.pdf",
        "excerpt": (
            "Design of antiferroelectric polarization conﬁguration for "
            "ultrahigh capacitive energy storage via increasing entropy"
        ),
    },
    {
        "paper": "PZO domain-modulation paper",
        "source_file": "1-s2.0-S2352847824001278-main.pdf",
        "excerpt": (
            "Antiferroelectric domain modulation enhancing energy storage "
            "performance by phase- ﬁeld simulations"
        ),
    },
)


def raw_matches(store, query: str, top_k: int) -> list[dict]:
    matches = store.similarity_search_with_relevance_scores(query, k=top_k)
    return [
        {
            "source_file": document.metadata["source_file"],
            "page_number": document.metadata["page_number"],
            "chunk_id": document.metadata["chunk_id"],
            "relevance_score": round(float(score), 6),
            "passes_threshold": float(score) >= RELEVANCE_THRESHOLD,
            "text_excerpt": re.sub(r"\s+", " ", document.page_content)[:240],
        }
        for document, score in matches
    ]


def locate_targets(store) -> list[dict]:
    stored = store._collection.get(include=["documents", "metadatas"])
    results = []
    for target in TARGETS:
        target_text = normalize_for_matching(target["excerpt"])
        hits = []
        for text, metadata in zip(stored["documents"], stored["metadatas"]):
            if target_text not in normalize_for_matching(text):
                continue
            if metadata["source_file"] != target["source_file"]:
                continue
            hits.append(
                {
                    "source_file": metadata["source_file"],
                    "page_number": metadata["page_number"],
                    "chunk_id": metadata["chunk_id"],
                }
            )
        results.append({**target, "present_in_index": bool(hits), "hits": hits})
    return results


def main() -> None:
    embeddings, dimension = create_embeddings()
    manifest = load_manifest(DEFAULT_INDEX_MANIFEST)
    validate_manifest_config(manifest, dimension)
    store = open_vector_store(embeddings, DEFAULT_CHROMA_DIR)

    raw_original = raw_matches(store, ORIGINAL_QUERY, ORIGINAL_TOP_K)
    thresholded = [
        item for item in raw_original if item["passes_threshold"]
    ]
    targets = locate_targets(store)
    diagnostic_queries = {
        "entropy_antiferroelectric_polarization_configuration": raw_matches(
            store,
            "entropy antiferroelectric polarization configuration",
            6,
        ),
        "antiferroelectric_domain_modulation_phase_field": raw_matches(
            store,
            "antiferroelectric domain modulation phase-field simulations",
            6,
        ),
    }
    current_tool_result = retrieve_paper_evidence(
        ORIGINAL_QUERY,
        top_k=ORIGINAL_TOP_K,
    )
    payload = {
        "diagnosis_id": "q16_retrieval_20261110",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "index": {
            "collection_count": store._collection.count(),
            "embedding_model": manifest["embedding_model"],
            "embedding_dimension": manifest["embedding_dimension"],
            "relevance_threshold": RELEVANCE_THRESHOLD,
            "score_type": (
                "chroma_relevance_1_minus_cosine_distance_higher_is_better"
            ),
        },
        "original_retrieval": {
            "query": ORIGINAL_QUERY,
            "top_k": ORIGINAL_TOP_K,
            "raw_top_k_results": raw_original,
            "results_passing_threshold": thresholded,
            "targeted_papers_hit": sorted(
                {item["source_file"] for item in thresholded}
            ),
            "hit_paper_count": len(
                {item["source_file"] for item in thresholded}
            ),
            "raw_candidate_source_files": sorted(
                {item["source_file"] for item in raw_original}
            ),
            "raw_candidate_paper_count": len(
                {item["source_file"] for item in raw_original}
            ),
            "expected_target_paper_count": len(targets),
            "retrieved_target_paper_count": len(
                {
                    item["source_file"]
                    for item in thresholded
                    if item["source_file"]
                    in {target["source_file"] for target in targets}
                }
            ),
            "current_tool_result": current_tool_result,
        },
        "target_presence_in_index": targets,
        "diagnostic_queries_without_changing_algorithm": diagnostic_queries,
        "diagnosis": {
            "retrieval_miss": True,
            "reason": (
                "The single-term query 'entropy' did not produce any target "
                "evidence above the configured threshold."
            ),
            "target_chunks_missing_from_index": False,
            "source_coverage_failure": True,
            "algorithm_changed": False,
        },
    }
    OUTPUT_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"q16 diagnosis: {OUTPUT_PATH}")
    print(
        json.dumps(
            {
                "original_query": ORIGINAL_QUERY,
                "top_k": ORIGINAL_TOP_K,
                "thresholded_hits": len(thresholded),
                "targets_present": [
                    item["present_in_index"] for item in targets
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

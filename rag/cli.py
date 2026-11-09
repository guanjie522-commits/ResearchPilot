import argparse
from pathlib import Path

from .config import (
    DEFAULT_CHROMA_DIR,
    DEFAULT_INDEX_MANIFEST,
    DEFAULT_PDF_DIR,
    DEFAULT_TOP_K,
)
from .pdf_index import index_pdfs
from .qa import answer_question


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="ResearchPilot independent local PDF RAG"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    ingest = subparsers.add_parser("ingest", help="Parse PDFs and build Chroma index")
    ingest.add_argument("--pdf-dir", type=Path, default=DEFAULT_PDF_DIR)
    ingest.add_argument("--chroma-dir", type=Path, default=DEFAULT_CHROMA_DIR)
    ingest.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_INDEX_MANIFEST,
    )
    ingest.add_argument("--rebuild", action="store_true")

    ask = subparsers.add_parser("ask", help="Retrieve evidence and answer a question")
    ask.add_argument("question")
    ask.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    ask.add_argument("--chroma-dir", type=Path, default=DEFAULT_CHROMA_DIR)
    ask.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_INDEX_MANIFEST,
    )

    status = subparsers.add_parser("status", help="Show persistent index status")
    status.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_INDEX_MANIFEST,
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()

    try:
        if args.command == "ingest":
            result = index_pdfs(
                pdf_dir=args.pdf_dir,
                chroma_dir=args.chroma_dir,
                manifest_path=args.manifest,
                rebuild=args.rebuild,
            )
            print(f"Imported PDFs: {len(result.pdfs)}")
            for pdf in result.pdfs:
                print(f"- {pdf.source_file}: {pdf.page_count} pages")
            print(f"Chunks produced: {len(result.chunks)}")
            print(f"Pages without extractable text: {len(result.pages_without_text)}")
            for source_file, page_number in result.pages_without_text:
                print(f"  - {source_file}, page {page_number}: no extractable text")
            for duplicate in result.duplicate_files:
                print(f"Duplicate PDF skipped: {duplicate}")
            print("Embedding model: qwen3-embedding:0.6b")
            print(f"Embedding dimension: {result.embedding_dimension}")
            print(f"Chroma collection size: {result.collection_count}")
            print(f"Manifest: {args.manifest}")
            return

        if args.command == "status":
            if not args.manifest.exists():
                raise FileNotFoundError(
                    f"No index manifest found at {args.manifest}. Run ingest first."
                )
            print(args.manifest.read_text(encoding="utf-8"))
            return

        result = answer_question(
            args.question,
            top_k=args.top_k,
            chroma_dir=args.chroma_dir,
            manifest_path=args.manifest,
        )
        print("Retrieved chunks:")
        for index, chunk in enumerate(result.chunks, start=1):
            print(
                f"\n[{index}] score={chunk.score:.4f} "
                f"source={chunk.source_file} page={chunk.page_number} "
                f"chunk_id={chunk.chunk_id}"
            )
            print(f"Original excerpt: {chunk.text[:700]}")
        print(f"\nEvidence insufficient: {result.insufficient_evidence}")
        print(f"\nFinal answer:\n{result.answer}")
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        raise SystemExit(f"RAG error: {exc}") from exc


if __name__ == "__main__":
    main()

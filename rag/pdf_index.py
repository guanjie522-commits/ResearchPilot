import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader

from .config import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    COLLECTION_NAME,
    DEFAULT_CHROMA_DIR,
    DEFAULT_INDEX_MANIFEST,
    EMBEDDING_MODEL,
    MAX_PDF_COUNT,
)


@dataclass(frozen=True)
class PageRecord:
    source_file: str
    page_number: int
    text: str
    extraction_status: str


@dataclass(frozen=True)
class PDFRecord:
    source_file: str
    sha256: str
    page_count: int
    pages: list[PageRecord] = field(default_factory=list)


@dataclass
class IngestResult:
    pdfs: list[PDFRecord]
    chunks: list[Document]
    duplicate_files: list[str]
    pages_without_text: list[tuple[str, int]]
    collection_count: int
    embedding_dimension: int


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def discover_pdfs(pdf_dir: Path) -> list[Path]:
    if not pdf_dir.exists():
        raise FileNotFoundError(
            f"PDF directory does not exist: {pdf_dir}. "
            "Create it and place 1-3 authorized paper PDFs there."
        )

    pdfs = sorted(
        path
        for path in pdf_dir.iterdir()
        if path.is_file() and path.suffix.lower() == ".pdf"
    )
    if not pdfs:
        raise FileNotFoundError(
            f"No PDF files found in {pdf_dir}. "
            "Please provide 1-3 real paper PDFs that you are authorized to use."
        )
    if len(pdfs) > MAX_PDF_COUNT:
        raise ValueError(
            f"Found {len(pdfs)} PDFs in {pdf_dir}; this first version accepts at most "
            f"{MAX_PDF_COUNT}. Keep only the papers you want to test."
        )
    return pdfs


def extract_pdf(path: Path) -> PDFRecord:
    reader = PdfReader(str(path))
    if reader.is_encrypted:
        try:
            reader.decrypt("")
        except Exception as exc:
            raise ValueError(f"Encrypted PDF cannot be read: {path.name}") from exc

    pages = []
    for page_index, page in enumerate(reader.pages, start=1):
        try:
            raw_text = page.extract_text() or ""
        except Exception:
            raw_text = ""
        text = raw_text.strip()
        status = "extracted" if text else "no_extractable_text"
        pages.append(
            PageRecord(
                source_file=path.name,
                page_number=page_index,
                text=text,
                extraction_status=status,
            )
        )

    return PDFRecord(
        source_file=path.name,
        sha256=sha256_file(path),
        page_count=len(reader.pages),
        pages=pages,
    )


def build_documents(pdfs: list[PDFRecord]) -> tuple[list[Document], list[tuple[str, int]]]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    documents: list[Document] = []
    pages_without_text: list[tuple[str, int]] = []

    for pdf in pdfs:
        for page in pdf.pages:
            if not page.text:
                pages_without_text.append((page.source_file, page.page_number))
                continue

            page_chunks = splitter.split_text(page.text)
            for chunk_index, text in enumerate(page_chunks):
                clean_text = re.sub(r"[ \t]+", " ", text).strip()
                if not clean_text:
                    continue
                chunk_id = (
                    f"{pdf.sha256[:16]}:p{page.page_number:04d}:"
                    f"c{chunk_index:04d}"
                )
                documents.append(
                    Document(
                        page_content=clean_text,
                        metadata={
                            "source_file": pdf.source_file,
                            "page_number": page.page_number,
                            "chunk_id": chunk_id,
                            "source_sha256": pdf.sha256,
                        },
                    )
                )

    return documents, pages_without_text


def load_manifest(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Index manifest is unreadable: {path}") from exc


def validate_manifest_config(
    manifest: dict[str, Any] | None,
    embedding_dimension: int,
) -> None:
    if manifest is None:
        return

    expected = {
        "embedding_model": EMBEDDING_MODEL,
        "embedding_dimension": embedding_dimension,
        "chunk_size": CHUNK_SIZE,
        "chunk_overlap": CHUNK_OVERLAP,
        "collection_name": COLLECTION_NAME,
    }
    mismatches = {
        key: (manifest.get(key), value)
        for key, value in expected.items()
        if manifest.get(key) != value
    }
    if mismatches:
        raise ValueError(
            "Existing Chroma index configuration does not match the current RAG "
            f"configuration: {mismatches}. Rebuild the index explicitly before querying."
        )


def create_embeddings() -> tuple[OllamaEmbeddings, int]:
    embeddings = OllamaEmbeddings(model=EMBEDDING_MODEL)
    probe_vector = embeddings.embed_query(
        "ResearchPilot embedding configuration validation"
    )
    if not probe_vector:
        raise RuntimeError("Embedding model returned an empty vector.")
    return embeddings, len(probe_vector)


def open_vector_store(
    embeddings: OllamaEmbeddings,
    persist_directory: Path = DEFAULT_CHROMA_DIR,
) -> Chroma:
    return Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=str(persist_directory),
    )


def index_pdfs(
    pdf_dir: Path,
    chroma_dir: Path = DEFAULT_CHROMA_DIR,
    manifest_path: Path = DEFAULT_INDEX_MANIFEST,
    rebuild: bool = False,
) -> IngestResult:
    paths = discover_pdfs(pdf_dir)
    embeddings, dimension = create_embeddings()
    manifest = load_manifest(manifest_path)
    validate_manifest_config(manifest, dimension)

    if rebuild and manifest_path.exists():
        manifest_path.unlink()
        manifest = None

    store = open_vector_store(embeddings, chroma_dir)
    if rebuild:
        store.delete_collection()
        store = open_vector_store(embeddings, chroma_dir)

    pdf_records: list[PDFRecord] = []
    duplicate_files: list[str] = []
    seen_hashes: set[str] = set()
    for path in paths:
        pdf = extract_pdf(path)
        if pdf.sha256 in seen_hashes:
            duplicate_files.append(path.name)
            continue
        seen_hashes.add(pdf.sha256)
        pdf_records.append(pdf)

    documents, pages_without_text = build_documents(pdf_records)
    if not documents:
        raise ValueError(
            "No extractable text was found in the provided PDFs. "
            "This version does not perform OCR."
        )

    previous_files = (manifest or {}).get("files", {})
    for pdf in pdf_records:
        previous = previous_files.get(pdf.source_file)
        if previous and previous.get("sha256") != pdf.sha256:
            old = store.get(where={"source_file": pdf.source_file})
            old_ids = old.get("ids") or []
            if old_ids:
                store.delete(ids=old_ids)

    store.add_texts(
        texts=[document.page_content for document in documents],
        metadatas=[document.metadata for document in documents],
        ids=[str(document.metadata["chunk_id"]) for document in documents],
    )

    files_manifest = dict(previous_files)
    for pdf in pdf_records:
        files_manifest[pdf.source_file] = {
            "sha256": pdf.sha256,
            "page_count": pdf.page_count,
        }
    new_manifest = {
        "embedding_model": EMBEDDING_MODEL,
        "embedding_dimension": dimension,
        "chunk_size": CHUNK_SIZE,
        "chunk_overlap": CHUNK_OVERLAP,
        "collection_name": COLLECTION_NAME,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "files": files_manifest,
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(new_manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return IngestResult(
        pdfs=pdf_records,
        chunks=documents,
        duplicate_files=duplicate_files,
        pages_without_text=pages_without_text,
        collection_count=store._collection.count(),
        embedding_dimension=dimension,
    )

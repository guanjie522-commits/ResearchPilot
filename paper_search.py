import html
import re
import time
from html.parser import HTMLParser
from typing import Any

import requests


CROSSREF_API_URL = "https://api.crossref.org/works"
CROSSREF_TIMEOUT = (5, 20)
CROSSREF_USER_AGENT = "ResearchPilot/0.1"
DEFAULT_MAX_RESULTS = 5
MAX_RESULTS_CAP = 5
ABSTRACT_MAX_LENGTH = 900


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style"}:
            self._skip_depth += 1
        elif tag in {"p", "br", "li", "div"}:
            self.parts.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"} and self._skip_depth:
            self._skip_depth -= 1
        elif tag in {"p", "li", "div"}:
            self.parts.append(" ")

    def handle_data(self, data: str) -> None:
        if not self._skip_depth:
            self.parts.append(data)


def clean_markup(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    parser = _TextExtractor()
    try:
        parser.feed(text)
        parser.close()
        text = " ".join(parser.parts)
    except Exception:
        text = re.sub(r"<[^>]+>", " ", text)
    return " ".join(html.unescape(text).split())


def first_text(value: Any, fallback: str) -> str:
    if isinstance(value, list):
        for item in value:
            text = clean_markup(item)
            if text:
                return text
        return fallback
    text = clean_markup(value)
    return text or fallback


def extract_year(item: dict[str, Any]) -> str:
    for field in (
        "published",
        "published-print",
        "published-online",
        "issued",
        "created",
    ):
        date_parts = (item.get(field) or {}).get("date-parts") or []
        if date_parts and date_parts[0]:
            year = date_parts[0][0]
            if year not in (None, ""):
                return str(year)
    return "Publication year not provided"


def extract_authors(item: dict[str, Any]) -> str:
    authors = []
    for author in item.get("author") or []:
        if not isinstance(author, dict):
            continue
        given = clean_markup(author.get("given"))
        family = clean_markup(author.get("family"))
        name = clean_markup(author.get("name"))
        full_name = " ".join(part for part in (given, family) if part) or name
        if full_name:
            authors.append(full_name)
    return ", ".join(authors) or "Authors not provided"


def extract_abstract(item: dict[str, Any]) -> str:
    abstract = clean_markup(item.get("abstract"))
    if not abstract:
        return "Abstract not available in Crossref metadata."
    if len(abstract) > ABSTRACT_MAX_LENGTH:
        return abstract[:ABSTRACT_MAX_LENGTH].rstrip() + "... [truncated]"
    return abstract


def format_papers(
    query: str,
    items: list[dict[str, Any]],
    max_results: int,
    request_seconds: float,
) -> str:
    papers = []
    seen_dois: set[str] = set()

    for item in items:
        if not isinstance(item, dict) or item.get("type") == "component":
            continue

        title = first_text(item.get("title"), "")
        doi = clean_markup(item.get("DOI"))
        if not title or not doi or doi in seen_dois:
            continue
        seen_dois.add(doi)

        journal = first_text(
            item.get("container-title"),
            "Journal/venue not provided",
        )
        url = clean_markup(item.get("URL")) or f"https://doi.org/{doi}"
        papers.append(
            "\n".join(
                [
                    f"{len(papers) + 1}. Title: {title}",
                    f"   Authors: {extract_authors(item)}",
                    f"   Publication Year: {extract_year(item)}",
                    f"   Journal: {journal}",
                    f"   DOI: {doi}",
                    f"   URL: {url}",
                    f"   Abstract: {extract_abstract(item)}",
                    "   Source: Crossref",
                ]
            )
        )
        if len(papers) >= max_results:
            break

    if not papers:
        return (
            "Crossref request status: 200. Returned papers: 0\n"
            f"Crossref request seconds: {request_seconds:.6f}\n"
            f"No papers found for query: {query}"
        )

    return (
        "Crossref request status: 200. "
        f"Returned papers: {len(papers)}\n"
        f"Crossref request seconds: {request_seconds:.6f}\n"
        f"Query: {query}\n\n"
        + "\n\n".join(papers)
    )


def search_crossref_papers(query: str, max_results: int = DEFAULT_MAX_RESULTS) -> str:
    normalized_query = " ".join(str(query).split())
    if not normalized_query:
        return "Crossref search failed: query must not be empty."

    try:
        requested_results = int(max_results)
    except (TypeError, ValueError):
        requested_results = DEFAULT_MAX_RESULTS
    result_limit = max(1, min(requested_results, MAX_RESULTS_CAP))

    request_started = time.perf_counter()
    try:
        response = requests.get(
            CROSSREF_API_URL,
            params={
                "query.bibliographic": normalized_query,
                "rows": min(max(10, result_limit * 4), 20),
                "select": (
                    "DOI,title,author,published,published-print,"
                    "published-online,issued,created,container-title,"
                    "URL,abstract,type"
                ),
            },
            headers={
                "Accept": "application/json",
                "User-Agent": CROSSREF_USER_AGENT,
            },
            timeout=CROSSREF_TIMEOUT,
        )
        request_seconds = time.perf_counter() - request_started
    except requests.Timeout:
        return "Crossref search failed: request timed out. Please try again later."
    except requests.RequestException as exc:
        return (
            f"Crossref search failed: network error "
            f"({exc.__class__.__name__}). Please try again later."
        )

    if response.status_code == 403:
        return "Crossref search failed: access forbidden (HTTP 403)."
    if response.status_code == 429:
        retry_after = response.headers.get("Retry-After")
        detail = f" Retry after: {retry_after} seconds." if retry_after else ""
        return f"Crossref search rate limit reached (HTTP 429).{detail}"
    if 500 <= response.status_code < 600:
        return (
            "Crossref search failed: service temporarily unavailable "
            f"(HTTP {response.status_code}). Please try again later."
        )
    if response.status_code != 200:
        return f"Crossref search failed: API returned HTTP {response.status_code}."

    try:
        data = response.json()
        items = data["message"].get("items") or []
    except (ValueError, KeyError, TypeError):
        return "Crossref search failed: API returned invalid or unexpected JSON."

    return format_papers(
        normalized_query,
        items,
        result_limit,
        request_seconds,
    )

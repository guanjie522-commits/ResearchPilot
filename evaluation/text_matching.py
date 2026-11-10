import re
import unicodedata
from collections.abc import Iterable


_DASH_TRANSLATION = str.maketrans(
    {
        "\u2010": "-",
        "\u2011": "-",
        "\u2012": "-",
        "\u2013": "-",
        "\u2014": "-",
        "\u2015": "-",
        "\u2212": "-",
    }
)


def normalize_for_matching(text: str) -> str:
    """Conservatively normalize PDF extraction artifacts for term matching."""
    normalized = unicodedata.normalize("NFKC", text or "").casefold()
    normalized = normalized.replace("\u00ad", "")
    normalized = normalized.translate(_DASH_TRANSLATION)

    # Join words broken by a hyphen and line break, but do not join arbitrary
    # adjacent words.
    normalized = re.sub(
        r"(?<=[a-z0-9])-\s*\n\s*(?=[a-z0-9])",
        "",
        normalized,
    )

    # Treat intra-word hyphens as word separators. This lets "phase-field"
    # match "phase field" without allowing fuzzy typo matching.
    normalized = re.sub(r"(?<=[a-z])-(?=[a-z])", " ", normalized)

    # Known PDF extraction split for the q04 term. This is an explicit term
    # equivalence, not a general "remove all spaces" operation.
    normalized = re.sub(r"\bmis\s+fit\b", "misfit", normalized)

    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def contains_term(text: str, term: str) -> bool:
    """Return whether a normalized term occurs on token boundaries."""
    normalized_text = normalize_for_matching(text)
    normalized_term = normalize_for_matching(term)
    if not normalized_term:
        return False

    pattern = re.escape(normalized_term).replace(r"\ ", r"\s+")
    return re.search(
        rf"(?<![a-z0-9]){pattern}(?![a-z0-9])",
        normalized_text,
    ) is not None


def contains_any_term(text: str, terms: Iterable[str]) -> bool:
    return any(contains_term(text, term) for term in terms)


def evaluate_q04_answer(answer: str) -> dict:
    """Check q04 concept coverage without claiming scientific correctness."""
    concept_checks = {
        "misfit_strain": contains_term(answer, "misfit strain"),
        "defect_dipole_doping": contains_any_term(
            answer,
            ("defect dipoles doping", "defect dipole doping"),
        ),
        "film_thickness": contains_term(answer, "film thickness"),
        "does_not_abstain": not re.search(
            r"证据不足|insufficient evidence",
            normalize_for_matching(answer),
        ),
    }
    return {
        "checks": concept_checks,
        "passed": all(concept_checks.values()),
        "status": "pending_human_review",
        "scope": (
            "Checks explicit required-term presence only; it does not establish "
            "scientific correctness."
        ),
    }

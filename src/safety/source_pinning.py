"""
D3 Safety: Source Pinning / Provenance Filtering
Owner: Alia

Filters retrieval results to only approved corpus sources,
preventing answers from citing documents outside the project corpus.
"""

from __future__ import annotations
from typing import Any

# Approved corpus document IDs (from the project's ingested papers)
APPROVED_SOURCES: set[str] = {
    "uae_netzero_2050_strategy",
    "calvin_2023_ipcc",
    "bui_2018_carbon_capture",
    "alam_2020",
    "balcombe_2019",
    "altieri_2015",
    "balsalobre_2017",
    "chu_2016",
    "chen_2013",
    "castellano_2025",
}

# Risk types this filter catches
RISK_TYPES = [
    "out_of_corpus_source",
    "missing_document_id",
    "unknown_source",
]


def filter_to_allowed_sources(
    chunks: list[dict[str, Any]],
    allowed: set[str] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Split chunks into allowed and blocked lists.

    Returns:
        (allowed_chunks, blocked_chunks)
    """
    corpus = allowed if allowed is not None else APPROVED_SOURCES
    allowed_chunks: list[dict[str, Any]] = []
    blocked_chunks: list[dict[str, Any]] = []

    for chunk in chunks:
        doc_id = chunk.get("document_id") or chunk.get("source", "")
        # Match if doc_id starts with any approved source key
        is_approved = any(doc_id.startswith(src) for src in corpus) or doc_id in corpus
        if is_approved:
            allowed_chunks.append(chunk)
        else:
            blocked = dict(chunk)
            blocked["_blocked_reason"] = (
                "missing_document_id" if not doc_id else "out_of_corpus_source"
            )
            blocked_chunks.append(blocked)

    return allowed_chunks, blocked_chunks


def pin_answer_sources(
    answer: str,
    cited_doc_ids: list[str],
    allowed: set[str] | None = None,
) -> dict[str, Any]:
    """
    Check whether all doc_ids cited in an answer are from the approved corpus.

    Returns a dict with:
      - safe (bool)
      - allowed_citations (list)
      - blocked_citations (list)
      - risk_type (str or None)
    """
    corpus = allowed if allowed is not None else APPROVED_SOURCES
    allowed_cites = []
    blocked_cites = []

    for doc_id in cited_doc_ids:
        is_approved = any(doc_id.startswith(src) for src in corpus) or doc_id in corpus
        if is_approved:
            allowed_cites.append(doc_id)
        else:
            blocked_cites.append(doc_id)

    return {
        "safe": len(blocked_cites) == 0,
        "allowed_citations": allowed_cites,
        "blocked_citations": blocked_cites,
        "risk_type": "out_of_corpus_source" if blocked_cites else None,
        "answer_preview": answer[:120],
    }
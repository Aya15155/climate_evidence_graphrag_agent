"""
D3 Safety: Citation Verifier
Owner: Alia

Checks that citations in answers are backed by real page evidence
from the retrieved chunks. Catches hallucinated or unsupported citations.
"""

from __future__ import annotations
from typing import Any


def verify_answer_citations(
    cited_pages: list[str],
    chunks: list[dict[str, Any]],
    strict: bool = False,
) -> dict[str, Any]:
    """
    Verify that cited pages exist in the supporting chunks.

    Args:
        cited_pages: Pages cited in the answer, e.g. ["p. 3", "p. 12"]
        chunks: Retrieved chunks, each with 'page_start', 'page_end', 'snippet'
        strict: If True, page must match exactly. If False, allow ±1 page tolerance.

    Returns dict with:
      - citation_correct (bool)
      - verified_pages (list)
      - unverified_pages (list)
      - citation_status (str): "all_verified", "partial", "none_verified"
      - notes (str)
    """
    verified: list[str] = []
    unverified: list[str] = []

    # Build set of all page numbers from chunks
    chunk_pages: set[int] = set()
    for chunk in chunks:
        p_start = chunk.get("page_start")
        p_end = chunk.get("page_end")
        if p_start is not None:
            chunk_pages.add(int(p_start))
        if p_end is not None:
            chunk_pages.add(int(p_end))
        # Also parse from snippet if pages missing
        snippet = chunk.get("snippet", "")
        if "p." in snippet:
            for part in snippet.split():
                if part.startswith("p."):
                    try:
                        chunk_pages.add(int(part.replace("p.", "").strip(".,;")))
                    except ValueError:
                        pass

    for cite in cited_pages:
        # Parse "p. 12" → 12
        try:
            page_num = int(
                cite.replace("p.", "").replace("page", "").strip(" .,;")
            )
        except ValueError:
            unverified.append(cite)
            continue

        if strict:
            found = page_num in chunk_pages
        else:
            # Allow ±1 page tolerance for PDF extraction noise
            found = any(abs(page_num - cp) <= 1 for cp in chunk_pages)

        if found:
            verified.append(cite)
        else:
            unverified.append(cite)

    total = len(cited_pages)
    if total == 0:
        status = "no_citations"
    elif len(verified) == total:
        status = "all_verified"
    elif len(verified) == 0:
        status = "none_verified"
    else:
        status = "partial"

    return {
        "citation_correct": status == "all_verified",
        "verified_pages": verified,
        "unverified_pages": unverified,
        "citation_status": status,
        "chunk_pages_found": sorted(chunk_pages),
        "notes": (
            f"{len(verified)}/{total} citations verified against chunk provenance."
            + (" Strict mode." if strict else " Tolerance ±1 page.")
        ),
    }


def batch_verify(
    rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Verify citations for a list of answer rows.
    Each row must have: 'cited_pages' (list), 'chunks' (list).
    Returns rows with citation verification fields added.
    """
    results = []
    for row in rows:
        result = verify_answer_citations(
            cited_pages=row.get("cited_pages", []),
            chunks=row.get("chunks", []),
        )
        results.append({**row, **result})
    return results
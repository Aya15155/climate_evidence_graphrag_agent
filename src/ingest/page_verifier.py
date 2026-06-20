"""
Page citation verifier for the Climate Evidence GraphRAG Agent.
Owner: Reem (D3 - Page Citation Verification & Data Quality)

Verifies that cited chunks/pages are grounded in real documents and contain
meaningful evidence text. Produces labelled status rows for audit.
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Optional


STATUS_VALID = "valid"
STATUS_MISSING_DOC = "missing_document"
STATUS_MISSING_PAGE = "missing_page"
STATUS_TEXT_NOT_FOUND = "text_not_found"
STATUS_WEAK_OVERLAP = "weak_overlap"

WEAK_TEXT_THRESHOLD = 200   # chars — below this: weak_overlap
EMPTY_TEXT_THRESHOLD = 50   # chars — below this: text_not_found


def load_metadata(csv_path: str | Path) -> dict[str, dict]:
    """Return {document_id: row_dict} from papers_metadata.csv."""
    meta = {}
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            meta[row["document_id"]] = row
    return meta


def load_chunks(json_path: str | Path) -> dict[str, dict]:
    """Return {chunk_id: chunk_dict} from sample_chunks.json."""
    with open(json_path, encoding="utf-8") as f:
        chunks = json.load(f)
    return {c["chunk_id"]: c for c in chunks}


def _parse_page_number(page_str: str) -> Optional[int]:
    """Extract integer from strings like 'p. 12', '12', 'page 12'."""
    if not page_str:
        return None
    m = re.search(r"\d+", str(page_str))
    return int(m.group()) if m else None


def _try_resolve_doc_id(chunk_id: str, meta: dict[str, dict]) -> Optional[str]:
    """
    For synthetic graph chunks (e.g. 'calvin_2023_chunk_012'), try to match
    the prefix against known document_ids in metadata.
    Returns the first matching document_id or None.
    """
    prefix = re.sub(r"_chunk_\d+$", "", chunk_id)
    for doc_id in meta:
        if doc_id.startswith(prefix):
            return doc_id
    return None


def verify_citation(
    chunk_id: str,
    page_cited_str: str,
    chunks: dict[str, dict],
    meta: dict[str, dict],
) -> dict:
    """
    Verify a single citation and return a result dict with:
        chunk_id, document_id, page_cited, page_start, page_end,
        total_pages, text_length, evidence_overlap_score,
        doc_exists, page_in_range, status, failure_reason
    """
    result = {
        "chunk_id": chunk_id,
        "document_id": None,
        "page_cited": None,
        "page_start": None,
        "page_end": None,
        "total_pages": None,
        "text_length": 0,
        "evidence_overlap_score": 0.0,
        "doc_exists": False,
        "page_in_range": False,
        "status": STATUS_MISSING_DOC,
        "failure_reason": "",
    }

    page_cited = _parse_page_number(page_cited_str)
    result["page_cited"] = page_cited

    # --- 1. Resolve chunk ---
    chunk = chunks.get(chunk_id)

    if chunk:
        doc_id = chunk["document_id"]
        result["document_id"] = doc_id
        result["page_start"] = chunk.get("page_start")
        result["page_end"] = chunk.get("page_end")
        text = chunk.get("text", "").strip()
    else:
        # Synthetic graph chunk — try to resolve document from prefix
        doc_id = _try_resolve_doc_id(chunk_id, meta)
        result["document_id"] = doc_id
        text = ""

    # --- 2. Check document exists in metadata ---
    doc_meta = meta.get(doc_id) if doc_id else None
    if not doc_meta:
        result["status"] = STATUS_MISSING_DOC
        result["failure_reason"] = (
            f"chunk_id '{chunk_id}' not found in sample_chunks and "
            f"document_id could not be resolved to known metadata"
        )
        return result

    result["doc_exists"] = True
    total_pages = int(doc_meta.get("total_pages") or 0)
    result["total_pages"] = total_pages

    # --- 3. Check page is within document range ---
    if page_cited and total_pages > 0 and page_cited > total_pages:
        result["status"] = STATUS_MISSING_PAGE
        result["failure_reason"] = (
            f"cited page {page_cited} exceeds document total pages {total_pages}"
        )
        return result

    result["page_in_range"] = True

    # --- 4. Check text presence ---
    text_len = len(text)
    result["text_length"] = text_len

    if text_len < EMPTY_TEXT_THRESHOLD:
        result["status"] = STATUS_TEXT_NOT_FOUND
        result["failure_reason"] = (
            f"chunk text missing or too short ({text_len} chars); "
            "likely PDF extraction failure or graph-only node with no real chunk"
        )
        return result

    # --- 5. Check text quality (weak overlap) ---
    if text_len < WEAK_TEXT_THRESHOLD:
        score = round(text_len / WEAK_TEXT_THRESHOLD, 3)
        result["evidence_overlap_score"] = score
        result["status"] = STATUS_WEAK_OVERLAP
        result["failure_reason"] = (
            f"text present but short ({text_len} chars); "
            "page exists but evidence confidence is low"
        )
        return result

    # --- 6. Valid ---
    score = min(1.0, round(text_len / 2000, 3))
    result["evidence_overlap_score"] = score
    result["status"] = STATUS_VALID
    result["failure_reason"] = ""
    return result


def verify_graphrag_citations(
    results_csv: str | Path,
    chunks: dict[str, dict],
    meta: dict[str, dict],
) -> list[dict]:
    """
    Expand GraphRAG result rows into per-citation verification rows.
    Each (query, chunk_id, page) triple becomes one row in the output.
    """
    rows = []
    with open(results_csv, newline="", encoding="utf-8") as f:
        for q_idx, row in enumerate(csv.DictReader(f), start=1):
            query = row["query"]
            chunk_ids = [c.strip() for c in row.get("chunk_ids", "").split(";") if c.strip()]
            pages = [p.strip() for p in row.get("citation_pages", "").split(";") if p.strip()]

            for c_idx, chunk_id in enumerate(chunk_ids):
                # Pair each chunk with its corresponding page if available, else use first
                page_str = pages[c_idx] if c_idx < len(pages) else (pages[0] if pages else "")
                result = verify_citation(chunk_id, page_str, chunks, meta)
                result["answer_id"] = f"Q{q_idx:02d}"
                result["query"] = query[:120]
                rows.append(result)
    return rows


def verify_chunk_sample(
    chunks: dict[str, dict],
    meta: dict[str, dict],
    sample_size: int = 150,
) -> list[dict]:
    """
    Verify a random sample of real chunks from sample_chunks.json.
    These should be mostly valid, with weak_overlap for short-text chunks.
    """
    import random
    random.seed(42)
    sample = random.sample(list(chunks.values()), min(sample_size, len(chunks)))
    rows = []
    for chunk in sample:
        page_str = str(chunk.get("page_start", ""))
        result = verify_citation(chunk["chunk_id"], page_str, chunks, meta)
        result["answer_id"] = "SAMPLE"
        result["query"] = "(chunk sample)"
        rows.append(result)
    return rows


OUTPUT_COLUMNS = [
    "answer_id", "query", "chunk_id", "document_id",
    "page_cited", "page_start", "page_end", "total_pages",
    "doc_exists", "page_in_range", "text_length",
    "evidence_overlap_score", "status", "failure_reason",
]


def write_csv(rows: list[dict], output_path: str | Path) -> None:
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    PROJECT_ROOT = Path(__file__).resolve().parents[2]

    meta = load_metadata(PROJECT_ROOT / "data/metadata/papers_metadata.csv")
    chunks = load_chunks(PROJECT_ROOT / "data/sample/sample_chunks.json")

    graphrag_rows = verify_graphrag_citations(
        PROJECT_ROOT / "reports/tables/d3_graph_guided_results.csv",
        chunks,
        meta,
    )
    sample_rows = verify_chunk_sample(chunks, meta, sample_size=150)

    all_rows = graphrag_rows + sample_rows
    out = PROJECT_ROOT / "reports/tables/page_citation_check.csv"
    write_csv(all_rows, out)

    from collections import Counter
    counts = Counter(r["status"] for r in all_rows)
    print(f"Written {len(all_rows)} rows to {out}")
    for status, count in sorted(counts.items()):
        print(f"  {status}: {count}")

"""Build a deterministic, page-grounded D1 retrieval proxy benchmark.

The original auto-generated D1 questions were useful as brainstorming material,
but many labels were not actually anchored to the chunk named in the question.
For D1 evaluation we need a cleaner supervised signal, so this script creates a
page-grounded proxy set where each query is tied to the exact source chunk that
generated it.

Run from the project root:
    python scripts/build_d1_proxy_eval_set.py
"""

from __future__ import annotations

import argparse
import json
import random
import re
from datetime import datetime
from pathlib import Path


TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9_-]+")
STOPWORDS = {
    "about",
    "after",
    "also",
    "among",
    "because",
    "between",
    "climate",
    "document",
    "evidence",
    "from",
    "into",
    "page",
    "paper",
    "results",
    "say",
    "that",
    "their",
    "there",
    "these",
    "this",
    "using",
    "what",
    "which",
    "with",
}


def load_chunks(path: str | Path) -> list[dict]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def choose_keyword(chunk: dict) -> str:
    text_lower = chunk.get("text", "").lower()
    for field in [
        "technologies",
        "climate_risks",
        "topics",
        "sectors",
        "indicators",
        "policies",
        "targets",
        "regions",
        "countries",
    ]:
        values = chunk.get(field) or []
        for value in values:
            if str(value).lower() in text_lower:
                return str(value)

    counts: dict[str, int] = {}
    for token in TOKEN_RE.findall(chunk.get("text", "").lower()):
        if len(token) < 4 or token in STOPWORDS:
            continue
        counts[token] = counts.get(token, 0) + 1
    return max(counts, key=counts.get) if counts else "climate evidence"


def build_proxy_set(
    chunks: list[dict],
    *,
    n_questions: int = 120,
    seed: int = 42,
) -> list[dict]:
    rng = random.Random(seed)

    eligible = [
        chunk
        for chunk in chunks
        if len(chunk.get("text", "")) >= 250 and chunk.get("title") and chunk.get("document_id")
    ]
    rng.shuffle(eligible)

    chosen: list[dict] = []
    seen_docs: set[str] = set()
    for chunk in eligible:
        doc_id = chunk["document_id"]
        if doc_id in seen_docs:
            continue
        chosen.append(chunk)
        seen_docs.add(doc_id)
        if len(chosen) == n_questions:
            break

    if len(chosen) < n_questions:
        raise ValueError(
            f"Requested {n_questions} questions but only found {len(chosen)} eligible unique documents."
        )

    page_index: dict[tuple[str, int], list[str]] = {}
    for chunk in chunks:
        key = (chunk["document_id"], int(chunk["page_start"]))
        page_index.setdefault(key, []).append(chunk["chunk_id"])

    rows: list[dict] = []
    for index, chunk in enumerate(chosen, start=1):
        keyword = choose_keyword(chunk)
        title = chunk["title"]
        page = str(chunk["page_start"])
        relevant_chunk_ids = page_index[(chunk["document_id"], int(chunk["page_start"]))]
        rows.append(
            {
                "question_id": f"Q{index:03d}",
                "question": f'What does page {page} of "{title}" say about {keyword}?',
                "expected_answer": chunk["text"][:450].strip(),
                "question_type": "page_grounded_proxy",
                "source_documents": [chunk["document_id"]],
                "pages": [page],
                "required_entities": [keyword],
                "relevant_chunk_ids": relevant_chunk_ids,
                "evidence": [
                    {
                        "chunk_id": chunk["chunk_id"],
                        "document_id": chunk["document_id"],
                        "title": title,
                        "page_start": chunk["page_start"],
                        "page_end": chunk["page_end"],
                    }
                ],
                "needs_manual_review": True,
                "generation_method": "page_grounded_proxy_from_exact_source_page",
            }
        )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the repaired D1 proxy retrieval set.")
    parser.add_argument("--chunks-path", default="data/sample/sample_chunks.json")
    parser.add_argument("--output-path", default="data/gold/d1_retrieval_eval_set.json")
    parser.add_argument("--report-path", default="data/gold/d1_proxy_eval_set_report.json")
    parser.add_argument("--n-questions", type=int, default=120)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    chunks = load_chunks(args.chunks_path)
    rows = build_proxy_set(chunks, n_questions=args.n_questions, seed=args.seed)

    output_path = Path(args.output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")

    report = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "generation_method": "page_grounded_proxy_from_exact_source_page",
        "source_chunks_path": args.chunks_path,
        "output_path": args.output_path,
        "n_questions": len(rows),
        "seed": args.seed,
        "all_items_need_manual_review": all(row["needs_manual_review"] for row in rows),
        "question_types": sorted({row["question_type"] for row in rows}),
    }
    report_path = Path(args.report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"Saved {len(rows)} repaired D1 proxy questions to {output_path}")
    print(f"Saved proxy-set report to {report_path}")


if __name__ == "__main__":
    main()

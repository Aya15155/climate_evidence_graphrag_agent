"""Build data/sample/sample_chunks.json from metadata when PDFs are unavailable (LFS).

Generates realistic text chunks from the metadata CSV (title, abstract, topics,
etc.) so that the retrieval stack, notebooks, and evaluation pipeline can run
without the actual 70MB PDF corpus.

Run from project root:
    python scripts/build_sample_chunks.py
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.ingest.metadata_loader import load_metadata, split_list_field

METADATA_CSV = PROJECT_ROOT / "data" / "metadata" / "papers_metadata.csv"
OUTPUT_PATH  = PROJECT_ROOT / "data" / "sample" / "sample_chunks.json"

CHUNK_SIZE = 600
PAGES_PER_DOC_DEFAULT = 15


def _synthesize_page_text(rec: dict, page_num: int, total_pages: int, rng: random.Random) -> str:
    """Create a realistic chunk text from metadata fields."""
    title = rec.get("title", "Untitled")
    abstract = rec.get("abstract", "")
    doc_id = rec.get("document_id", "")
    year = rec.get("year", "")
    authors = rec.get("authors", "")
    org = rec.get("organization", "")

    topics = split_list_field(rec.get("topics", ""))
    countries = split_list_field(rec.get("countries", ""))
    regions = split_list_field(rec.get("regions", ""))
    sectors = split_list_field(rec.get("sectors", ""))
    risks = split_list_field(rec.get("climate_risks", ""))
    techs = split_list_field(rec.get("technologies", ""))
    policies = split_list_field(rec.get("policies", ""))

    parts = []

    if page_num == 1:
        parts.append(f"{title}")
        if authors:
            parts.append(f"Authors: {authors[:200]}")
        if org:
            parts.append(f"Published by {org}, {year}.")
        if abstract:
            parts.append(abstract[:500])
        else:
            parts.append(f"This paper examines {title.lower()}.")
    else:
        section_names = [
            "Introduction", "Background", "Literature Review", "Methodology",
            "Data and Methods", "Results", "Analysis", "Discussion",
            "Findings", "Implications", "Policy Recommendations",
            "Conclusions", "Future Work", "References",
        ]
        section = section_names[min(page_num - 1, len(section_names) - 1)]
        parts.append(f"{section}.")

        if abstract and page_num <= 3:
            start = rng.randint(0, max(0, len(abstract) - 200))
            parts.append(abstract[start:start + 200])

        context_phrases = []
        if topics:
            t = rng.choice(topics)
            context_phrases.append(f"In the context of {t}")
        if risks:
            r = rng.choice(risks)
            context_phrases.append(f"addressing climate risk of {r}")
        if sectors:
            s = rng.choice(sectors)
            context_phrases.append(f"with implications for the {s} sector")
        if techs:
            tech = rng.choice(techs)
            context_phrases.append(f"leveraging {tech} technology")
        if policies:
            p = rng.choice(policies)
            context_phrases.append(f"aligned with {p}")
        if countries:
            c = rng.choice(countries)
            context_phrases.append(f"with evidence from {c}")
        if regions:
            reg = rng.choice(regions)
            context_phrases.append(f"in the {reg} region")

        if context_phrases:
            rng.shuffle(context_phrases)
            parts.append(", ".join(context_phrases[:3]) + ".")

        filler = (
            f"This section of {title.lower()} presents evidence and analysis "
            f"relevant to the study's objectives. The findings contribute to "
            f"understanding of climate-related challenges and potential solutions "
            f"discussed in the broader literature."
        )
        parts.append(filler)

    text = " ".join(parts)
    return text[:CHUNK_SIZE] if len(text) > CHUNK_SIZE else text


def main():
    records = load_metadata(METADATA_CSV)
    print(f"Metadata: {len(records)} documents")

    rng = random.Random(42)
    all_chunks = []
    chunk_counter = 0

    for rec in records:
        total_pages = int(rec.get("total_pages") or PAGES_PER_DOC_DEFAULT) or PAGES_PER_DOC_DEFAULT
        n_pages = min(total_pages, 120)

        topics = split_list_field(rec.get("topics", ""))
        countries = split_list_field(rec.get("countries", ""))
        regions = split_list_field(rec.get("regions", ""))
        sectors = split_list_field(rec.get("sectors", ""))
        risks = split_list_field(rec.get("climate_risks", ""))
        techs = split_list_field(rec.get("technologies", ""))
        pols = split_list_field(rec.get("policies", ""))
        targets = split_list_field(rec.get("targets", ""))
        indicators = split_list_field(rec.get("indicators", ""))

        for page_num in range(1, n_pages + 1):
            text = _synthesize_page_text(rec, page_num, n_pages, rng)

            n_sub = max(1, len(text) // (CHUNK_SIZE - 80) + 1)
            step = max(1, CHUNK_SIZE - 80)
            for sub_idx in range(n_sub):
                start = sub_idx * step
                chunk_text = text[start:start + CHUNK_SIZE]
                if not chunk_text.strip():
                    continue

                chunk_counter += 1
                all_chunks.append({
                    "chunk_id": f"chunk_{chunk_counter:06d}",
                    "doc_number": rec.get("doc_number", ""),
                    "document_id": rec["document_id"],
                    "title": rec.get("title", ""),
                    "text": chunk_text,
                    "page_start": page_num,
                    "page_end": page_num,
                    "topics": topics,
                    "countries": countries,
                    "regions": regions,
                    "sectors": sectors,
                    "climate_risks": risks,
                    "technologies": techs,
                    "policies": pols,
                    "targets": targets,
                    "indicators": indicators,
                })

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, ensure_ascii=False)

    n_docs = len(set(c["document_id"] for c in all_chunks))
    print(f"Generated {len(all_chunks):,} chunks from {n_docs} documents")
    print(f"Saved to: {OUTPUT_PATH}")
    print(f"File size: {OUTPUT_PATH.stat().st_size / 1024 / 1024:.1f} MB")


if __name__ == "__main__":
    main()

"""
citation_builder.py — D3 GraphRAG Citation Builder
Climate Evidence GraphRAG Agent | CSAI415


Resolves BlendedChunk objects and GraphHit Finding nodes to page-level
APA-style citation strings.

Design decision: parenthetical APA style (Author, Year, p. N) beats numeric
tags because the LLM can reference them inline without post-processing.
See D3_DESIGN_DOCUMENT.md § D2 for alternatives analysis.

Citation resolution cascade:
  1. Finding.qdrant_chunk_id → chunk metadata → page
  2. Finding doc_id + page → papers_metadata.csv → title + year
  3. Chunk doc_id → papers_metadata.csv → title + year
  4. doc_id slug only → no year, no page (doc-level fallback)
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

LOGGER = logging.getLogger(__name__)


class CitationBuilder:
    """
    Resolves chunk + graph hit metadata to citation strings.

    Attributes:
        chunk_store_path: Path to sample_chunks.json (chunk id → text/doc_id/page)
        metadata_csv_path: Path to papers_metadata.csv (doc_id → title/year/authors)
    """

    def __init__(
        self,
        chunk_store_path: str = "data/sample/sample_chunks.json",
        metadata_csv_path: str = "data/metadata/papers_metadata.csv",
    ):
        self._chunk_store_path = chunk_store_path
        self._metadata_csv_path = metadata_csv_path
        self._chunks: Optional[Dict[str, Dict]] = None
        self._metadata: Optional[Dict[str, Dict]] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build(self, blended_chunks) -> List[Dict[str, Any]]:
        """
        For each BlendedChunk, produce a citation dict:
        {
            "chunk_id": str,
            "doc_id": str,
            "page": int | None,
            "author_year": str,          # "Calvin et al., 2023"
            "citation_string": str,      # "(Calvin et al., 2023, p. 14)"
            "title": str,
        }
        Deduplicates by (doc_id, page).
        """
        seen = set()
        citations = []
        for chunk in blended_chunks:
            doc_id = chunk.doc_id or ""
            page = chunk.page
            key = (doc_id, page)
            if key in seen:
                continue
            seen.add(key)
            citations.append(self._resolve_citation(doc_id, page))
        return citations

    def build_from_hits(self, graph_hits) -> List[Dict[str, Any]]:
        """
        Build citations from GraphHit objects (for Finding-level grounding).
        """
        seen = set()
        citations = []
        for hit in graph_hits:
            doc_id = hit.doc_id or ""
            page = hit.page
            key = (doc_id, page)
            if key in seen:
                continue
            seen.add(key)
            citations.append(self._resolve_citation(doc_id, page))
        return citations

    def format_inline(self, doc_id: str, page: Optional[int] = None) -> str:
        """
        Return a single inline citation string, e.g. '(IPCC, 2023, p. 5)'.
        Used for injecting citations into generated text post-processing.
        """
        cit = self._resolve_citation(doc_id, page)
        return cit["citation_string"]

    # ------------------------------------------------------------------
    # Internal resolution
    # ------------------------------------------------------------------

    def _resolve_citation(self, doc_id: str, page: Optional[int]) -> Dict[str, Any]:
        """
        Resolve one (doc_id, page) pair to a full citation dict.

        Resolution cascade:
        1. Look up doc_id in papers_metadata → title, year, authors
        2. If page is None, try chunk store for page from doc_id
        3. Compose citation string
        """
        meta = self._get_metadata_for_doc(doc_id)
        title = meta.get("title", doc_id)
        year = meta.get("year", "")
        authors = meta.get("authors", "")

        author_year = self._format_author_year(authors, year, doc_id)
        page_str = f", p. {page}" if page is not None else ""
        citation_string = f"({author_year}{page_str})"

        return {
            "chunk_id": "",
            "doc_id": doc_id,
            "page": page,
            "author_year": author_year,
            "citation_string": citation_string,
            "title": title,
        }

    def _format_author_year(self, authors: str, year: Any, doc_id: str) -> str:
        """
        Format author + year for APA citation.
        'Calvin, K., Dasgupta, D., Krinner, G.' → 'Calvin et al., 2023'
        'IPCC' → 'IPCC, 2023'
        No author → slug from doc_id
        """
        year_str = str(int(float(year))) if str(year).strip().replace(".", "").isdigit() else str(year)

        if not authors or authors.strip().lower() in ("", "unknown", "nan"):
            # Extract from doc_id slug (e.g. 'calvin_2023_ipcc...' → 'Calvin, 2023')
            parts = doc_id.split("_")
            if len(parts) >= 2 and parts[1].isdigit() and len(parts[1]) == 4:
                first_author = parts[0].capitalize()
                year_str = parts[1]
                return f"{first_author}, {year_str}"
            return f"{doc_id[:30]}, {year_str}"

        # Parse first author surname
        author_list = [a.strip() for a in re.split(r"[;,]", authors) if a.strip()]
        if not author_list:
            return f"{doc_id[:30]}, {year_str}"

        first_author = author_list[0].split()
        # Handle "Lastname, Firstname" or "Firstname Lastname"
        if "," in author_list[0]:
            surname = author_list[0].split(",")[0].strip()
        else:
            surname = first_author[-1] if first_author else author_list[0]

        if len(author_list) > 1:
            return f"{surname} et al., {year_str}"
        else:
            return f"{surname}, {year_str}"

    def _get_metadata_for_doc(self, doc_id: str) -> Dict[str, Any]:
        """
        Look up doc metadata. Returns empty dict if not found.
        Loads papers_metadata.csv once and caches.
        """
        metadata = self._load_metadata()
        if doc_id in metadata:
            return metadata[doc_id]
        # Try partial match on doc_id prefix (doc_id may be a truncated slug)
        for key in metadata:
            if key.startswith(doc_id[:20]) or doc_id.startswith(key[:20]):
                return metadata[key]
        return {}

    def _load_metadata(self) -> Dict[str, Dict]:
        if self._metadata is not None:
            return self._metadata

        path = self._metadata_csv_path
        if not os.path.exists(path):
            LOGGER.warning("papers_metadata.csv not found at %s; citations will be doc_id only.", path)
            self._metadata = {}
            return self._metadata

        try:
            import pandas as pd
            df = pd.read_csv(path)
            # Normalise column names to lowercase
            df.columns = [c.lower().strip() for c in df.columns]
            # Identify doc_id column
            id_col = next(
                (c for c in df.columns if "doc_id" in c or "document_id" in c or "id" == c),
                df.columns[0],
            )
            df[id_col] = df[id_col].astype(str).str.strip()
            self._metadata = df.set_index(id_col).to_dict(orient="index")
        except Exception as exc:
            LOGGER.warning("Could not load metadata CSV: %s", exc)
            self._metadata = {}

        LOGGER.info("Loaded metadata for %d documents.", len(self._metadata))
        return self._metadata

    def _load_chunks(self) -> Dict[str, Dict]:
        if self._chunks is not None:
            return self._chunks
        path = self._chunk_store_path
        if not os.path.exists(path):
            self._chunks = {}
            return self._chunks
        with open(path, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
        if isinstance(raw, list):
            self._chunks = {c["chunk_id"]: c for c in raw if "chunk_id" in c}
        else:
            self._chunks = raw
        return self._chunks

    # ------------------------------------------------------------------
    # Reporting helpers
    # ------------------------------------------------------------------

    def format_citation_block(self, citations: List[Dict[str, Any]]) -> str:
        """
        Format a numbered reference block for display in notebooks.

        Example:
          [1] (Calvin et al., 2023, p. 14) — IPCC 2023 Synthesis Report
          [2] (Canadell, 2007, p. 5) — Contributions to accelerating CO2 growth
        """
        lines = ["## References"]
        for i, cit in enumerate(citations, 1):
            title = cit.get("title", cit.get("doc_id", ""))[:80]
            lines.append(f"[{i}] {cit['citation_string']} — {title}")
        return "\n".join(lines)

    def build_csv_row(
        self,
        result,  # GraphRAGResult
    ) -> Dict[str, Any]:
        """
        Produce one row for reports/tables/d3_graph_guided_results.csv.
        """
        graph_hit_ids = [
            h.doc_id or "" for h in result.graph_hits
        ]
        chunk_ids = [c.chunk_id for c in result.blended_chunks]
        return {
            "query": result.query,
            "cypher_query": (result.cypher_query or "")[:300].replace("\n", " "),
            "graph_hits": "; ".join(graph_hit_ids[:5]),
            "chunk_ids": "; ".join(chunk_ids[:8]),
            "citation_pages": "; ".join(result.citation_pages[:8]),
            "retrieval_type": result.retrieval_type,
            "answer_quality_notes": result.answer_quality_notes or self._auto_quality_note(result),
        }

    @staticmethod
    def _auto_quality_note(result) -> str:
        """Generate a basic quality note from pipeline metadata."""
        n_graph = len(result.graph_chunks)
        n_hybrid = len(result.hybrid_chunks)
        n_cite = len(result.citation_pages)
        if result.retrieval_type == "empty":
            return "No evidence retrieved; answer likely unsupported."
        if n_graph == 0:
            return f"Graph returned 0 chunks; answer from {n_hybrid} hybrid chunks only."
        if n_cite == 0:
            return "No page citations resolved; answer lacks page-level grounding."
        overlap = len(
            {c.chunk_id for c in result.graph_chunks}
            & {c.chunk_id for c in result.hybrid_chunks}
        )
        overlap_pct = int(100 * overlap / max(n_graph, 1))
        if overlap_pct > 80:
            return (
                f"Graph adds no unique evidence ({overlap_pct}% overlap with hybrid); "
                "consider hybrid_fallback for this query type."
            )
        return (
            f"Graph-guided: {n_graph} graph chunks, {n_hybrid} hybrid chunks, "
            f"{n_cite} page citations resolved. Overlap: {overlap_pct}%."
        )

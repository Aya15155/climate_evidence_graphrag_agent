"""
prompt_builder.py — D3 GraphRAG Prompt Builder
Climate Evidence GraphRAG Agent | CSAI415


Builds the structured two-section prompt used in Stage D of the GraphRAG pipeline.

Design decision: two-section prompt (graph evidence first, hybrid supplementary)
beats a flat context dump because it signals to the LLM which evidence is
structured/high-confidence vs. broad/probabilistic.
See D3_DESIGN_DOCUMENT.md § D1 for alternatives analysis.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class PromptBuilder:
    """
    Constructs the final prompt for answer generation.

    Prompt structure:
    ─────────────────────────────────────────────────────────────────────────
    SYSTEM CONTEXT
    ─────────────────────────────────────────────────────────────────────────
    SECTION 1: GRAPH-GUIDED EVIDENCE
      [Graph path summary]
      [Graph-sourced chunks with confidence and page labels]

    SECTION 2: SUPPLEMENTARY RETRIEVAL EVIDENCE
      [Hybrid-sourced chunks]

    CITATION REFERENCE LIST
      [1] Author, Year, Title, p. N

    INSTRUCTION
      Answer the query. Cite evidence as (Author, Year, p. N). ...
    ─────────────────────────────────────────────────────────────────────────
    """

    SYSTEM_PREAMBLE = (
        "You are a Climate Evidence Research Assistant. "
        "You answer questions about climate policy, risks, technologies, and findings "
        "using only the provided evidence. "
        "You never fabricate citations, page numbers, or statistics. "
        "If the evidence does not support a claim, say so explicitly."
    )

    def build_prompt(
        self,
        query: str,
        graph_hits,           # List[GraphHit]
        blended_chunks,       # List[BlendedChunk]
        citations: List[Dict[str, Any]],
        cypher_query: Optional[str] = None,
    ) -> str:
        """
        Assembles the complete prompt string.

        Args:
            query: The user's original question.
            graph_hits: Ranked GraphHit objects from Stage A (for path summary).
            blended_chunks: BlendedChunk objects from Stage C.
            citations: List of citation dicts from CitationBuilder.
            cypher_query: The Cypher string used (for transparency).

        Returns:
            A single multi-section prompt string.
        """
        sections = [
            self.SYSTEM_PREAMBLE,
            "",
            f"## USER QUERY\n{query}",
            "",
        ]

        # Section 1: Graph-guided evidence
        graph_path_summary = self._build_graph_path_summary(graph_hits)
        graph_section_chunks = [c for c in blended_chunks if c.source_type in ("graph", "both")]

        if graph_section_chunks:
            sections.append("## SECTION 1: GRAPH-GUIDED EVIDENCE (structured, confidence-annotated)")
            if graph_path_summary:
                sections.append(f"**Knowledge graph path:**\n{graph_path_summary}")
            if cypher_query:
                sections.append(
                    f"**Cypher query used:**\n```cypher\n{cypher_query[:600]}\n```"
                )
            sections.append("")
            for i, chunk in enumerate(graph_section_chunks, 1):
                conf_label = self._confidence_label(chunk)
                page_label = f"p. {chunk.page}" if chunk.page else "page unknown"
                sections.append(
                    f"[Graph-{i}] Source: {chunk.doc_id} | {page_label} | {conf_label}\n"
                    f"{chunk.text[:800]}"
                )
            sections.append("")
        else:
            sections.append(
                "## SECTION 1: GRAPH-GUIDED EVIDENCE\n"
                "*(No graph paths found for this query; answer based on Section 2 only.)*"
            )
            sections.append("")

        # Section 2: Supplementary hybrid evidence
        hybrid_section_chunks = [c for c in blended_chunks if c.source_type in ("hybrid", "both")]

        if hybrid_section_chunks:
            sections.append("## SECTION 2: SUPPLEMENTARY RETRIEVAL EVIDENCE (BM25 + dense hybrid)")
            for i, chunk in enumerate(hybrid_section_chunks, 1):
                page_label = f"p. {chunk.page}" if chunk.page else "page unknown"
                sections.append(
                    f"[Hybrid-{i}] Source: {chunk.doc_id} | {page_label}\n"
                    f"{chunk.text[:600]}"
                )
            sections.append("")

        # Citation reference list
        if citations:
            sections.append("## CITATION REFERENCES")
            for ref in citations:
                sections.append(f"  {ref['citation_string']}")
            sections.append("")

        # Instruction
        sections.append(self._build_instruction(bool(graph_section_chunks)))

        return "\n".join(sections)

    def build_fallback_prompt(
        self,
        query: str,
        blended_chunks,
        citations: List[Dict[str, Any]],
    ) -> str:
        """
        Simplified prompt for hybrid-only fallback (when graph returned nothing).
        Used when retrieval_type == 'hybrid_fallback'.
        """
        sections = [
            self.SYSTEM_PREAMBLE,
            "",
            f"## USER QUERY\n{query}",
            "",
            "## EVIDENCE (hybrid retrieval — no graph paths available for this query)",
        ]
        for i, chunk in enumerate(blended_chunks, 1):
            page_label = f"p. {chunk.page}" if chunk.page else "page unknown"
            sections.append(
                f"[{i}] Source: {chunk.doc_id} | {page_label}\n{chunk.text[:700]}"
            )
        sections.append("")
        if citations:
            sections.append("## CITATION REFERENCES")
            for ref in citations:
                sections.append(f"  {ref['citation_string']}")
            sections.append("")
        sections.append(self._build_instruction(False))
        return "\n".join(sections)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_graph_path_summary(self, graph_hits) -> str:
        """
        Produce a human-readable summary of the graph traversal path.

        Example output:
          Template: graphrag_country_policy_target
          Path: UAE → Net Zero by 2050 (Policy) → Triple Renewables by 2030 (Target)
              Source: UAE Net Zero 2050 Strategic Initiative (2021)
        """
        if not graph_hits:
            return ""

        lines = []
        template = graph_hits[0].template if graph_hits else "unknown"
        lines.append(f"Template: {template}")

        for i, hit in enumerate(graph_hits[:5], 1):
            row = hit.row
            path_parts = []

            # Country → Policy → Target path
            if "country" in row:
                path_parts.append(f"{row['country']} (Country)")
            if "policy" in row:
                path_parts.append(f"{row['policy']} (Policy)")
            if "target" in row:
                path_parts.append(f"{row['target']} (Target)")

            # Technology → Risk path
            if "technology" in row:
                path_parts.append(f"{row['technology']} (Technology)")
            if "mitigated_risk" in row:
                path_parts.append(f"{row['mitigated_risk']} (Risk mitigated)")

            # Risk → Sector path
            if "climate_risk" in row:
                path_parts.append(f"{row['climate_risk']} (Risk)")
            if "affected_sector" in row:
                path_parts.append(f"{row['affected_sector']} (Sector)")

            # Region path
            if "region" in row:
                path_parts.append(f"{row['region']} (Region)")

            # Evidence
            source = row.get("source_doc") or row.get("title") or hit.doc_id or ""
            year = row.get("doc_year") or row.get("year") or ""
            page = hit.page
            conf = row.get("confidence") or row.get("mitigation_confidence") or ""

            path_str = " → ".join(path_parts) if path_parts else "(entity path not reconstructed)"
            evidence_str = f"{source} ({year})" if source else ""
            page_str = f", p. {page}" if page else ""
            conf_str = f" [{conf} confidence]" if conf else ""

            lines.append(
                f"  Hit {i}: {path_str}\n"
                f"           Evidence: {evidence_str}{page_str}{conf_str}"
            )

        return "\n".join(lines)

    @staticmethod
    def _confidence_label(chunk) -> str:
        if hasattr(chunk, "graph_score") and chunk.graph_score > 0:
            score = chunk.combined_score
            if score > 0.7:
                return "high confidence"
            elif score > 0.4:
                return "medium confidence"
            else:
                return "low confidence"
        return "retrieved"

    @staticmethod
    def _build_instruction(has_graph_evidence: bool) -> str:
        graph_note = (
            "Prioritise the GRAPH-GUIDED EVIDENCE in Section 1 as it is "
            "structured and confidence-annotated. Use Section 2 for additional context."
            if has_graph_evidence
            else "Use the evidence provided to answer the question."
        )
        return (
            "## INSTRUCTION\n"
            f"{graph_note}\n\n"
            "Answer the query above in 3–5 sentences. "
            "Cite each factual claim using the format (Author/Organisation, Year, p. N) "
            "referencing the CITATION REFERENCES above. "
            "If the evidence does not contain enough information to answer confidently, "
            "state what is known and what is uncertain. "
            "Do not fabricate page numbers, statistics, or citations."
        )

"""
graphrag_executor.py — D3 GraphRAG Pipeline Executor
Climate Evidence GraphRAG Agent | CSAI415


Implements the four-stage GraphRAG pipeline:
  A. Subgraph Selection  (query understanding → entity extraction → Cypher → node ranking)
  B. Graph Expansion     (Finding nodes → supporting chunks → relevance scoring)
  C. Hybrid Blend        (graph evidence + BM25 + dense → MMR re-rank)
  D. Answer Generation   (structured prompt → LLM → page citations)

Design decisions and alternatives are documented in D3_DESIGN_DOCUMENT.md
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

LOGGER = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Alias normalisation (mirrors schema aliases.yaml)
# ---------------------------------------------------------------------------
ENTITY_ALIASES: Dict[str, str] = {
    # Countries → ISO alpha-3
    "uae": "ARE",
    "united arab emirates": "ARE",
    "global": "GLOBAL",
    "saudi arabia": "SAU",
    "ksa": "SAU",
    "egypt": "EGY",
    "jordan": "JOR",
    "germany": "DEU",
    # Technologies
    "solar": "solar_pv",
    "solar power": "solar_pv",
    "wind": "wind_power",
    "wind energy": "wind_power",
    "renewables": "renewable_energy",
    "clean energy": "renewable_energy",
    "green hydrogen": "green_hydrogen",
    "hydrogen": "green_hydrogen",
    "ccs": "carbon_capture_and_storage",
    "carbon capture": "carbon_capture_and_storage",
    "dac": "direct_air_capture",
    # Risks
    "sea level rise": "sea_level_rise",
    "slr": "sea_level_rise",
    "coastal flooding": "coastal_flooding",
    "heat": "heatwaves",
    "extreme heat": "heatwaves",
    "water stress": "water_scarcity",
    "drought": "water_scarcity",
    # Regions
    "mena": "middle_east_and_north_africa",
    "middle east": "middle_east",
    "gcc": "gulf_cooperation_council",
    "gulf": "gulf_cooperation_council",
    # Policies
    "net zero": "net_zero_by_2050",
    "paris agreement": "paris_agreement",
    "cop28": "cop28_uae",
}

# Template → required parameter keys
TEMPLATE_PARAM_MAP: Dict[str, List[str]] = {
    "graphrag_country_policy_target": ["country_id"],
    "graphrag_policy_risk_sector":    ["policy_id"],
    "graphrag_technology_mitigates_risk": ["tech_id"],
    "graphrag_finding_document_grounding": ["risk_id", "sector_id", "country_id", "tech_id",
                                             "confidence_levels"],
    "graphrag_region_climate_risk":   ["region_id"],
}

# Keyword → template routing (fast-path before LLM classification)
KEYWORD_TEMPLATE_HINTS = {
    "policy":      "graphrag_country_policy_target",
    "target":      "graphrag_country_policy_target",
    "commitment":  "graphrag_country_policy_target",
    "ndc":         "graphrag_country_policy_target",
    "net zero":    "graphrag_country_policy_target",
    "technology":  "graphrag_technology_mitigates_risk",
    "mitigate":    "graphrag_technology_mitigates_risk",
    "solar":       "graphrag_technology_mitigates_risk",
    "hydrogen":    "graphrag_technology_mitigates_risk",
    "wind":        "graphrag_technology_mitigates_risk",
    "risk":        "graphrag_finding_document_grounding",
    "flooding":    "graphrag_finding_document_grounding",
    "heatwave":    "graphrag_finding_document_grounding",
    "impact":      "graphrag_finding_document_grounding",
    "sector":      "graphrag_finding_document_grounding",
    "agriculture": "graphrag_finding_document_grounding",
    "region":      "graphrag_region_climate_risk",
    "mena":        "graphrag_region_climate_risk",
    "gulf":        "graphrag_region_climate_risk",
}


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class GraphHit:
    """A single result row from a GRAPHRAG_REASONING Cypher query."""
    template: str
    row: Dict[str, Any]
    doc_id: Optional[str] = None
    page: Optional[int] = None
    chunk_id: Optional[str] = None
    confidence: Optional[str] = None
    text: Optional[str] = None


@dataclass
class BlendedChunk:
    """A chunk after merging graph + hybrid evidence pools."""
    chunk_id: str
    text: str
    doc_id: str
    page: Optional[int]
    source_type: str          # "graph" | "hybrid" | "both"
    combined_score: float
    graph_score: float = 0.0
    hybrid_score: float = 0.0
    graph_path_label: Optional[str] = None   # e.g. "UAE → Net Zero 2050 → Triple Renewables"


@dataclass
class GraphRAGResult:
    """Full output from one GraphRAG pipeline run."""
    query: str
    template_used: Optional[str]
    cypher_query: Optional[str]
    cypher_params: Dict[str, Any]
    graph_hits: List[GraphHit]
    graph_chunks: List[BlendedChunk]
    hybrid_chunks: List[BlendedChunk]
    blended_chunks: List[BlendedChunk]
    answer: str
    citation_pages: List[str]
    retrieval_type: str       # "graph_guided" | "hybrid_fallback" | "graph_only" | "empty"
    latency_sec: float
    answer_quality_notes: str = ""


# ---------------------------------------------------------------------------
# Helper: slugify (mirrors neo4j_builder.slugify)
# ---------------------------------------------------------------------------

def slugify(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_") or "unknown"


def normalise_entity(name: str) -> str:
    """Resolve alias and slugify an entity name for Cypher parameter use."""
    lowered = name.strip().lower()
    resolved = ENTITY_ALIASES.get(lowered, lowered)
    return slugify(resolved) if resolved == lowered else resolved


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


# ---------------------------------------------------------------------------
# Stage A — Subgraph Selection
# ---------------------------------------------------------------------------

class SubgraphSelector:
    """
    Stage A: Query understanding → entity extraction → Cypher selection → node ranking.

    Design decision: LLM-based classification beats keyword routing for paraphrased queries.
    Fallback to keyword routing avoids an API call for simple, keyword-rich queries.
    See D3_DESIGN_DOCUMENT.md § A1–A4 for alternatives analysis.
    """

    def __init__(
        self,
        neo4j_driver,
        llm_classify: bool = True,
        gemini_api_key: Optional[str] = None,
        cypher_timeout_sec: int = 10,
    ):
        self.driver = neo4j_driver
        self.llm_classify = llm_classify
        self.gemini_api_key = gemini_api_key or os.getenv("GEMINI_API_KEY", "")
        self.cypher_timeout_sec = cypher_timeout_sec

        try:
            from src.graph.cypher_queries import GRAPHRAG_REASONING
        except ModuleNotFoundError:
            from graph.cypher_queries import GRAPHRAG_REASONING
        self._templates = GRAPHRAG_REASONING

    # ------------------------------------------------------------------
    # A1: Intent classification
    # ------------------------------------------------------------------

    def classify_intent(self, query: str) -> Tuple[Optional[str], Dict[str, Any]]:
        """
        Return (template_name, params_dict).
        Falls back gracefully: LLM → keyword hints → graphrag_finding_document_grounding.

        Why LLM-first: handles paraphrased entity names and multi-entity queries.
        Fallback to keywords: avoids latency for obvious queries.
        """
        if self.llm_classify and self.gemini_api_key:
            try:
                return self._classify_with_llm(query)
            except Exception as exc:
                LOGGER.warning("LLM classification failed (%s); using keyword routing.", exc)

        return self._classify_with_keywords(query)

    def _classify_with_llm(self, query: str) -> Tuple[Optional[str], Dict[str, Any]]:
        """Ask Gemini to classify the query and extract entity IDs."""
        import requests

        system_prompt = """You are a query classifier for a Climate Evidence Knowledge Graph.
Given a user query, return JSON only (no markdown) with:
  {
    "template": one of [
      "graphrag_country_policy_target",
      "graphrag_policy_risk_sector",
      "graphrag_technology_mitigates_risk",
      "graphrag_finding_document_grounding",
      "graphrag_region_climate_risk"
    ],
    "params": {
      "country_id": null or ISO alpha-3 like "ARE",
      "policy_id": null or slug like "paris_agreement",
      "tech_id": null or slug like "solar_pv",
      "risk_id": null or slug like "heatwaves",
      "sector_id": null or slug like "agriculture",
      "region_id": null or slug like "middle_east",
      "confidence_levels": null or list like ["high", "medium"]
    }
  }

Template selection rules:
- country_policy_target: query mentions a specific country + policy/targets/commitments
- policy_risk_sector: query asks about a policy and what risks/sectors it covers
- technology_mitigates_risk: query asks what a technology does to reduce a risk
- finding_document_grounding: query asks for evidence/findings about a risk/sector/country
- region_climate_risk: query asks about risks or policies in a geographic region

Normalise entity names to slugs (lowercase, underscores). Use ISO alpha-3 for countries."""

        payload = {
            "contents": [
                {"role": "user", "parts": [{"text": f"{system_prompt}\n\nQuery: {query}"}]}
            ],
            "generationConfig": {"temperature": 0.0, "maxOutputTokens": 256},
        }
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"gemini-2.5-flash:generateContent?key={self.gemini_api_key}"
        )
        resp = requests.post(url, json=payload, timeout=15)
        resp.raise_for_status()
        raw_text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
        # Strip markdown fences if present
        raw_text = re.sub(r"```(?:json)?", "", raw_text).strip()
        parsed = json.loads(raw_text)
        template = parsed.get("template")
        params = {k: v for k, v in parsed.get("params", {}).items() if v is not None}
        return template, params

    def _classify_with_keywords(self, query: str) -> Tuple[Optional[str], Dict[str, Any]]:
        """Keyword-based fallback classifier with basic entity extraction."""
        q_lower = query.lower()
        template = None
        for kw, tmpl in KEYWORD_TEMPLATE_HINTS.items():
            if kw in q_lower:
                template = tmpl
                break
        if template is None:
            template = "graphrag_finding_document_grounding"  # safe default

        params: Dict[str, Any] = {}
        # Country extraction
        for alias, iso in ENTITY_ALIASES.items():
            if len(iso) == 3 and iso.isupper() and alias in q_lower:
                params["country_id"] = iso
                break
        # Technology extraction
        for alias, slug in ENTITY_ALIASES.items():
            if alias in q_lower and "solar" in slug or "hydrogen" in slug or "wind" in slug or "carbon" in slug:
                if alias in q_lower:
                    params["tech_id"] = slug
                    break
        # Risk extraction
        for alias, slug in ENTITY_ALIASES.items():
            if "flood" in alias or "heat" in alias or "drought" in alias or "sea" in alias:
                if alias in q_lower:
                    params["risk_id"] = slug
                    break
        return template, params

    # ------------------------------------------------------------------
    # A3: Cypher generation and execution
    # ------------------------------------------------------------------

    def run_cypher(
        self,
        template: str,
        params: Dict[str, Any],
    ) -> Tuple[str, List[GraphHit]]:
        """
        Generate parameterised Cypher from template and execute against Neo4j.

        Why parameterised templates over LLM-generated Cypher:
        - Zero injection risk
        - Deterministic structure
        - Testable independently of graph content
        """
        if template not in self._templates:
            LOGGER.warning("Unknown template %r; defaulting to finding_document_grounding", template)
            template = "graphrag_finding_document_grounding"

        cypher = self._templates[template]

        # Fill any missing optional params with None so Cypher OPTIONAL MATCH works
        all_params: Dict[str, Any] = {
            "country_id": None,
            "policy_id": None,
            "tech_id": None,
            "risk_id": None,
            "sector_id": None,
            "region_id": None,
            "confidence_levels": None,
        }
        all_params.update(params)

        hits: List[GraphHit] = []
        try:
            with self.driver.session() as session:
                result = session.run(
                    cypher,
                    **all_params,
                    timeout=self.cypher_timeout_sec,
                )
                for record in result:
                    row = dict(record)
                    hit = GraphHit(
                        template=template,
                        row=row,
                        doc_id=row.get("doc_id"),
                        page=row.get("page") or row.get("evidence_page"),
                        chunk_id=row.get("qdrant_chunk_id"),
                        confidence=row.get("confidence"),
                        text=row.get("evidence_text") or row.get("finding"),
                    )
                    hits.append(hit)
        except Exception as exc:
            LOGGER.error("Cypher execution failed for template %r: %s", template, exc)

        return cypher, hits

    # ------------------------------------------------------------------
    # A4: Node ranking
    # ------------------------------------------------------------------

    def rank_graph_hits(
        self,
        hits: List[GraphHit],
        query: str,
        top_k: int = 5,
    ) -> List[GraphHit]:
        """
        Score hits by BM25 relevance of their text to the query + confidence_rank.

        Why hybrid score over confidence alone:
        A high-confidence finding about coastal flooding is irrelevant for a query
        about renewable energy targets. Relevance must be primary; confidence secondary.
        """
        if not hits:
            return []

        from rank_bm25 import BM25Okapi

        texts = [h.text or "" for h in hits]
        tokenised = [t.lower().split() for t in texts]
        query_tokens = query.lower().split()

        try:
            bm25 = BM25Okapi(tokenised)
            bm25_scores = bm25.get_scores(query_tokens)
        except Exception:
            bm25_scores = np.zeros(len(hits))

        confidence_map = {"low": 1, "medium": 2, "high": 3, "very_high": 4}
        scored = []
        for i, hit in enumerate(hits):
            conf_score = confidence_map.get(str(hit.confidence or "medium").lower(), 2)
            combined = float(bm25_scores[i]) + 0.5 * conf_score
            scored.append((combined, hit))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [h for _, h in scored[:top_k]]


# ---------------------------------------------------------------------------
# Stage B — Graph Expansion
# ---------------------------------------------------------------------------

class GraphExpander:
    """
    Stage B: Expand ranked Finding nodes to full text chunks.

    Design decisions:
    - Max 1 expansion hop (prevents combinatorial explosion)
    - Max 8 graph chunks (prevents context pollution)
    - Cosine similarity gate at 0.25 (removes off-topic expansions)

    See D3_DESIGN_DOCUMENT.md § B1–B3 for alternatives analysis.
    """

    def __init__(
        self,
        chunk_store_path: str = "data/sample/sample_chunks.json",
        cosine_threshold: float = 0.25,
        max_graph_chunks: int = 8,
        dense_retriever=None,
    ):
        self.cosine_threshold = cosine_threshold
        self.max_graph_chunks = max_graph_chunks
        self.dense_retriever = dense_retriever
        self._chunks: Optional[Dict[str, Dict]] = None
        self._chunk_store_path = chunk_store_path

    def _load_chunks(self) -> Dict[str, Dict]:
        if self._chunks is not None:
            return self._chunks
        path = self._chunk_store_path
        if not os.path.exists(path):
            LOGGER.warning("Chunk store not found at %s; graph expansion will return empty.", path)
            self._chunks = {}
            return self._chunks
        with open(path, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
        if isinstance(raw, list):
            self._chunks = {c["chunk_id"]: c for c in raw if "chunk_id" in c}
        elif isinstance(raw, dict):
            self._chunks = raw
        else:
            self._chunks = {}
        LOGGER.info("Loaded %d chunks from %s", len(self._chunks), path)
        return self._chunks

    def expand(
        self,
        hits: List[GraphHit],
        query: str,
    ) -> List[BlendedChunk]:
        """
        For each GraphHit, look up chunk_id or (doc_id, page) in chunk store.
        Score each retrieved chunk vs. query. Filter by cosine_threshold.
        Return top max_graph_chunks as BlendedChunk objects.

        Why: Finding.text is 1–3 sentences. The LLM needs full chunk context.
        Without expansion, answers are unsupported by PDF-level evidence.
        """
        chunks = self._load_chunks()
        query_emb = self._embed(query)
        results: List[Tuple[float, BlendedChunk]] = []
        seen_ids = set()

        for hit in hits:
            candidate_chunks = self._resolve_hit_to_chunks(hit, chunks)
            for chunk in candidate_chunks:
                cid = chunk.get("chunk_id", "")
                if cid in seen_ids:
                    continue
                seen_ids.add(cid)

                text = chunk.get("text", "") or chunk.get("content", "")
                if not text:
                    continue

                # Score relevance vs. query
                chunk_emb = self._embed(text[:512])
                sim = cosine_similarity(query_emb, chunk_emb)
                if sim < self.cosine_threshold:
                    LOGGER.debug("Dropping graph chunk %s (sim=%.3f < threshold)", cid, sim)
                    continue

                blended = BlendedChunk(
                    chunk_id=cid,
                    text=text,
                    doc_id=chunk.get("doc_id", hit.doc_id or ""),
                    page=chunk.get("page") or hit.page,
                    source_type="graph",
                    combined_score=sim,
                    graph_score=sim,
                )
                results.append((sim, blended))

        results.sort(key=lambda x: x[0], reverse=True)
        return [bc for _, bc in results[: self.max_graph_chunks]]

    def _resolve_hit_to_chunks(
        self,
        hit: GraphHit,
        chunks: Dict[str, Dict],
    ) -> List[Dict]:
        """
        Resolution cascade:
        1. Direct chunk_id lookup (from Finding.qdrant_chunk_id)
        2. (doc_id, page) lookup — scan chunks with matching doc_id and page
        3. doc_id only — take first 3 chunks from that document
        """
        # 1. Direct chunk_id
        if hit.chunk_id and hit.chunk_id in chunks:
            return [chunks[hit.chunk_id]]

        # 2. doc_id + page
        if hit.doc_id and hit.page is not None:
            page_matches = [
                c for c in chunks.values()
                if c.get("doc_id") == hit.doc_id and c.get("page") == hit.page
            ]
            if page_matches:
                return page_matches[:3]

        # 3. doc_id only
        if hit.doc_id:
            doc_matches = [
                c for c in chunks.values()
                if c.get("doc_id") == hit.doc_id
            ]
            return doc_matches[:3]

        return []

    def _embed(self, text: str) -> np.ndarray:
        """Embed text using dense_retriever if available, else TF-IDF hash fallback."""
        if self.dense_retriever is not None:
            try:
                return self.dense_retriever.embed([text])[0]
            except Exception:
                pass
        # Deterministic fallback: character n-gram hash (low quality but consistent)
        vec = np.zeros(128)
        for i, ch in enumerate(text[:256]):
            vec[ord(ch) % 128] += 1.0
        norm = np.linalg.norm(vec)
        return vec / norm if norm > 0 else vec


# ---------------------------------------------------------------------------
# Stage C — Hybrid Blend
# ---------------------------------------------------------------------------

class HybridBlender:
    """
    Stage C: Merge graph-guided chunks + BM25 + dense retrieval chunks.

    Uses weighted score normalisation (not RRF) because graph confidence_rank
    is an ordinal quality signal that RRF would discard.

    MMR re-ranking after merge ensures the final context is diverse.

    See D3_DESIGN_DOCUMENT.md § C1–C2 for alternatives analysis.
    """

    def __init__(
        self,
        hybrid_retriever,
        graph_weight: float = 0.4,
        hybrid_weight: float = 0.6,
        mmr_lambda: float = 0.7,
        top_k: int = 10,
        dense_retriever=None,
    ):
        self.hybrid_retriever = hybrid_retriever
        self.graph_weight = graph_weight
        self.hybrid_weight = hybrid_weight
        self.mmr_lambda = mmr_lambda
        self.top_k = top_k
        self.dense_retriever = dense_retriever

    def blend(
        self,
        query: str,
        graph_chunks: List[BlendedChunk],
        k_hybrid: int = 8,
    ) -> Tuple[List[BlendedChunk], List[BlendedChunk]]:
        """
        Returns (blended_chunks, hybrid_only_chunks).

        Why parallel execution (not sequential):
        Graph hits fail ~30% of the time on edge-case queries.
        Running hybrid independently ensures we always have fallback evidence.
        """
        # Run hybrid retrieval independently
        raw_hybrid = self.hybrid_retriever.search(query, k=k_hybrid)
        hybrid_chunks = self._wrap_hybrid_chunks(raw_hybrid)

        # Normalise scores for merging
        graph_scores = [c.graph_score for c in graph_chunks]
        hybrid_scores = [c.hybrid_score for c in hybrid_chunks]

        graph_norm = self._minmax(graph_scores)
        hybrid_norm = self._minmax(hybrid_scores)

        for i, c in enumerate(graph_chunks):
            c.combined_score = self.graph_weight * graph_norm[i]
        for i, c in enumerate(hybrid_chunks):
            c.combined_score = self.hybrid_weight * hybrid_norm[i]

        # Merge pools, deduplicate by chunk_id
        pool: Dict[str, BlendedChunk] = {}
        for c in graph_chunks:
            pool[c.chunk_id] = c
        for c in hybrid_chunks:
            if c.chunk_id in pool:
                existing = pool[c.chunk_id]
                existing.combined_score += c.combined_score
                existing.source_type = "both"
                existing.hybrid_score = c.hybrid_score
            else:
                pool[c.chunk_id] = c

        # MMR re-rank
        blended = self._mmr_rerank(query, list(pool.values()), k=self.top_k)
        return blended, hybrid_chunks

    def _wrap_hybrid_chunks(self, raw_results: List[Dict]) -> List[BlendedChunk]:
        out = []
        for r in raw_results:
            out.append(BlendedChunk(
                chunk_id=r.get("chunk_id", ""),
                text=r.get("text", "") or r.get("content", ""),
                doc_id=r.get("doc_id", ""),
                page=r.get("page"),
                source_type="hybrid",
                combined_score=float(r.get("fused_score", r.get("rrf_score", 0.0))),
                hybrid_score=float(r.get("fused_score", r.get("rrf_score", 0.0))),
            ))
        return out

    @staticmethod
    def _minmax(values: List[float]) -> List[float]:
        if not values:
            return []
        arr = np.array(values, dtype=float)
        mn, mx = arr.min(), arr.max()
        if mx == mn:
            return [1.0] * len(values)
        return list((arr - mn) / (mx - mn))

    def _mmr_rerank(
        self,
        query: str,
        candidates: List[BlendedChunk],
        k: int = 10,
    ) -> List[BlendedChunk]:
        """
        Maximal Marginal Relevance re-ranking.
        Penalises chunks too similar to already-selected chunks.
        lambda_param=0.7 → favour relevance over diversity.

        Why MMR over simple score sort:
        Without MMR, the top-10 blended chunks often contain near-duplicates
        from the same document page, wasting context window budget.
        """
        if not candidates:
            return []

        lam = self.mmr_lambda
        selected: List[BlendedChunk] = []
        remaining = list(candidates)

        while remaining and len(selected) < k:
            if not selected:
                # First pick: highest combined score
                best = max(remaining, key=lambda c: c.combined_score)
            else:
                # MMR score: λ·relevance - (1-λ)·max_similarity_to_selected
                def mmr_score(c: BlendedChunk) -> float:
                    rel = c.combined_score
                    sim_to_selected = max(
                        self._text_overlap(c.text, s.text) for s in selected
                    )
                    return lam * rel - (1 - lam) * sim_to_selected

                best = max(remaining, key=mmr_score)

            selected.append(best)
            remaining.remove(best)

        return selected

    @staticmethod
    def _text_overlap(a: str, b: str) -> float:
        """Jaccard similarity on word sets — fast approximate deduplication."""
        sa = set(a.lower().split())
        sb = set(b.lower().split())
        if not sa or not sb:
            return 0.0
        return len(sa & sb) / len(sa | sb)


# ---------------------------------------------------------------------------
# Stage D — Answer Generation (delegated to PromptBuilder + citation_builder)
# ---------------------------------------------------------------------------

class AnswerGenerator:
    """
    Stage D: Build structured prompt, call Gemini, inject citations.

    The PromptBuilder produces the two-section context block.
    The CitationBuilder resolves chunk metadata to page citations.
    Gemini 2.5 Flash generates the answer with citation references embedded.
    """

    def __init__(
        self,
        prompt_builder,
        citation_builder,
        gemini_api_key: Optional[str] = None,
        model: str = "gemini-2.5-flash",
        max_tokens: int = 1024,
    ):
        self.prompt_builder = prompt_builder
        self.citation_builder = citation_builder
        self.gemini_api_key = gemini_api_key or os.getenv("GEMINI_API_KEY", "")
        self.model = model
        self.max_tokens = max_tokens

    def generate(
        self,
        query: str,
        graph_hits: List[GraphHit],
        blended_chunks: List[BlendedChunk],
        cypher_query: Optional[str] = None,
    ) -> Tuple[str, List[str]]:
        """
        Returns (answer_text, citation_pages_list).
        """
        citations = self.citation_builder.build(blended_chunks)
        prompt = self.prompt_builder.build_prompt(
            query=query,
            graph_hits=graph_hits,
            blended_chunks=blended_chunks,
            citations=citations,
            cypher_query=cypher_query,
        )

        if not self.gemini_api_key:
            LOGGER.warning("No GEMINI_API_KEY found; returning prompt as mock answer.")
            return f"[MOCK — no API key]\n\n{prompt[:500]}", [c["citation_string"] for c in citations]

        answer = self._call_gemini(prompt)
        citation_strings = [c["citation_string"] for c in citations]
        return answer, citation_strings

    def _call_gemini(self, prompt: str) -> str:
        import requests

        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": self.max_tokens,
            },
        }
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent?key={self.gemini_api_key}"
        )
        resp = requests.post(url, json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json()["candidates"][0]["content"]["parts"][0]["text"]


# ---------------------------------------------------------------------------
# Main Orchestrator
# ---------------------------------------------------------------------------

class GraphRAGExecutor:
    """
    Orchestrates all four GraphRAG pipeline stages.

    Usage:
        executor = GraphRAGExecutor.from_config(config_path="configs/config.yaml")
        result = executor.run("What renewable energy targets has the UAE committed to?")
        print(result.answer)
        print(result.citation_pages)
    """

    def __init__(
        self,
        subgraph_selector: SubgraphSelector,
        graph_expander: GraphExpander,
        hybrid_blender: HybridBlender,
        answer_generator: AnswerGenerator,
        fallback_to_hybrid: bool = True,
        min_graph_hits_for_graph_path: int = 1,
    ):
        self.selector = subgraph_selector
        self.expander = graph_expander
        self.blender = hybrid_blender
        self.generator = answer_generator
        self.fallback_to_hybrid = fallback_to_hybrid
        self.min_graph_hits = min_graph_hits_for_graph_path

    def run(self, query: str) -> GraphRAGResult:
        """Execute the full 4-stage pipeline for a single query."""
        t0 = time.perf_counter()
        LOGGER.info("[GraphRAG] Query: %r", query)

        # ── Stage A: Subgraph Selection ──────────────────────────────────
        template, params = self.selector.classify_intent(query)
        LOGGER.info("[A] Template=%r  Params=%r", template, params)

        cypher_str: Optional[str] = None
        graph_hits: List[GraphHit] = []

        if template:
            cypher_str, graph_hits = self.selector.run_cypher(template, params)
            graph_hits = self.selector.rank_graph_hits(graph_hits, query)
            LOGGER.info("[A] Graph hits after ranking: %d", len(graph_hits))

        # ── Stage B: Graph Expansion ─────────────────────────────────────
        graph_chunks: List[BlendedChunk] = []
        if len(graph_hits) >= self.min_graph_hits:
            graph_chunks = self.expander.expand(graph_hits, query)
            LOGGER.info("[B] Graph chunks after expansion: %d", len(graph_chunks))
        else:
            LOGGER.info("[B] Insufficient graph hits; skipping expansion.")

        # ── Stage C: Hybrid Blend ─────────────────────────────────────────
        blended_chunks, hybrid_chunks = self.blender.blend(
            query=query,
            graph_chunks=graph_chunks,
        )
        LOGGER.info("[C] Blended chunks: %d", len(blended_chunks))

        # Determine retrieval type for reporting
        has_graph = len(graph_chunks) > 0
        has_hybrid = len(hybrid_chunks) > 0
        if has_graph and has_hybrid:
            retrieval_type = "graph_guided"
        elif has_graph and not has_hybrid:
            retrieval_type = "graph_only"
        elif has_hybrid and not has_graph:
            retrieval_type = "hybrid_fallback"
        else:
            retrieval_type = "empty"

        # ── Stage D: Answer Generation ────────────────────────────────────
        answer, citation_pages = self.generator.generate(
            query=query,
            graph_hits=graph_hits,
            blended_chunks=blended_chunks,
            cypher_query=cypher_str,
        )
        LOGGER.info("[D] Answer generated (%d chars), citations: %d",
                    len(answer), len(citation_pages))

        latency = time.perf_counter() - t0
        return GraphRAGResult(
            query=query,
            template_used=template,
            cypher_query=cypher_str,
            cypher_params=params,
            graph_hits=graph_hits,
            graph_chunks=graph_chunks,
            hybrid_chunks=hybrid_chunks,
            blended_chunks=blended_chunks,
            answer=answer,
            citation_pages=citation_pages,
            retrieval_type=retrieval_type,
            latency_sec=round(latency, 3),
        )

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def from_config(cls, config_path: str = "configs/config.yaml") -> "GraphRAGExecutor":
        """
        Build GraphRAGExecutor from config.yaml.
        Requires NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD env vars or config values.
        """
        import yaml

        with open(config_path, "r") as fh:
            cfg = yaml.safe_load(fh)

        neo4j_cfg = cfg.get("neo4j", {})
        uri = os.getenv("NEO4J_URI", neo4j_cfg.get("uri", "bolt://localhost:7687"))
        user = os.getenv("NEO4J_USER", neo4j_cfg.get("user", "neo4j"))
        pwd = os.getenv("NEO4J_PASSWORD", neo4j_cfg.get("password", "climate123"))

        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(uri, auth=(user, pwd))

        gr_cfg = cfg.get("graphrag", {})

        # Import existing D2 components
        try:
            from src.retrieval.bm25_retriever import BM25Retriever
            from src.retrieval.dense_retriever import DenseRetriever
            from src.retrieval.hybrid_retriever import HybridRetriever
        except ModuleNotFoundError:
            from retrieval.bm25_retriever import BM25Retriever
            from retrieval.dense_retriever import DenseRetriever
            from retrieval.hybrid_retriever import HybridRetriever

        chunk_store = cfg.get("retrieval", {}).get("chunks_path", "data/sample/sample_chunks.json")
        with open(chunk_store, "r") as fh:
            chunks = json.load(fh)

        bm25 = BM25Retriever(chunks)
        dense = DenseRetriever(
            embeddings_path=cfg.get("retrieval", {}).get("dense_cache",
                                                         "data/embeddings/chunks_tfidf_lsa.npy"),
            chunks=chunks,
        )
        hybrid = HybridRetriever(bm25, dense, normalization="rrf")

        try:
            from src.rag.prompt_builder import PromptBuilder
            from src.rag.citation_builder import CitationBuilder
        except ModuleNotFoundError:
            from rag.prompt_builder import PromptBuilder
            from rag.citation_builder import CitationBuilder

        gemini_key = os.getenv("GEMINI_API_KEY", "")

        selector = SubgraphSelector(
            neo4j_driver=driver,
            llm_classify=True,
            gemini_api_key=gemini_key,
            cypher_timeout_sec=gr_cfg.get("cypher_timeout_sec", 10),
        )
        expander = GraphExpander(
            chunk_store_path=chunk_store,
            cosine_threshold=gr_cfg.get("cosine_threshold", 0.25),
            max_graph_chunks=gr_cfg.get("max_graph_chunks", 8),
            dense_retriever=dense,
        )
        blender = HybridBlender(
            hybrid_retriever=hybrid,
            graph_weight=gr_cfg.get("graph_weight", 0.4),
            hybrid_weight=gr_cfg.get("hybrid_weight", 0.6),
            mmr_lambda=gr_cfg.get("mmr_lambda", 0.7),
            top_k=gr_cfg.get("max_graph_chunks", 8) + gr_cfg.get("max_hybrid_chunks", 8),
            dense_retriever=dense,
        )
        prompt_builder = PromptBuilder()
        citation_builder = CitationBuilder(chunk_store_path=chunk_store)
        generator = AnswerGenerator(
            prompt_builder=prompt_builder,
            citation_builder=citation_builder,
            gemini_api_key=gemini_key,
        )

        return cls(
            subgraph_selector=selector,
            graph_expander=expander,
            hybrid_blender=blender,
            answer_generator=generator,
            fallback_to_hybrid=gr_cfg.get("fallback_to_hybrid", True),
        )

# member3_d3_graphrag_executor_section.md

## D3 — GraphRAG Executor: Cypher Subgraph, Chunk Expansion, Answer Citations

**Owner:** Rana
**Code:** `src/rag/graphrag_executor.py`, `src/rag/prompt_builder.py`, `src/rag/citation_builder.py`, `src/graph/cypher_queries.py`
**Notebook:** `notebooks/D3_03_Rana_graphrag_executor.ipynb` (full implementation), `notebooks/D3_graphrag_eval_safety.ipynb` → "Rana block" (cross-team summary)
**Evidence table:** `reports/tables/d3_graph_guided_results.csv`

---

### 1. What this implements

A 4-stage GraphRAG pipeline, orchestrated by `GraphRAGExecutor`:

| Stage | Class | Job |
|---|---|---|
| A — Subgraph Selection | `SubgraphSelector` | query → entity extraction (alias-resolved) → Cypher template → node ranking |
| B — Graph Expansion | `GraphExpander` | graph nodes → supporting chunks/documents, cosine-thresholded |
| C — Hybrid Blend | `HybridBlender` | graph evidence + BM25 + dense → MMR re-rank into one chunk list |
| D — Answer Generation | `PromptBuilder` + `AnswerGenerator` + `CitationBuilder` | structured two-section prompt → LLM → page citations |

**Design decision — parallel lanes, not a waterfall.** The graph path (A–B) and the hybrid path (BM25 + dense) run independently and merge at Stage C. A Stage A failure (no Cypher hits) doesn't blank the answer — it just means Stage C receives hybrid evidence only, and `retrieval_type` is set to `hybrid_fallback`. Full alternatives analysis is in `D3_DESIGN_DOCUMENT.md`.

### 2. What the graph adds beyond vector search

- **Structured multi-hop paths** — e.g. `Country -[:HAS_POLICY]-> Policy -[:SETS_TARGET]-> Target`. Vector search returns chunks that *mention* a country and a target; only the graph knows which target belongs to which policy.
- **Confidence- and page-annotated edges** — `MITIGATES`, `IMPACTS`, `OCCURS_IN` carry `confidence`/`evidence_page` properties set at ingestion, giving page-level grounding before any chunk similarity search runs.
- **Precision on named-entity questions** — `ENTITY_ALIASES` resolves natural-language entities ("UAE", "sea level rise") to exact graph IDs, anchoring the answer to the *correct* entity rather than the most similar-sounding text.

### 3. When fallback to hybrid retrieval is safer

1. No entity extracted from the query (LLM classifier / keyword router returns all-null params).
2. Entity not in the alias table or not present as a node in the corpus graph (e.g. "Pacific Islands").
3. Cypher expansion is too broad — an unfiltered query returns 50+ rows that collapse into near-duplicate chunks from the same 2–3 documents.
4. The query is methodological, not entity-based (e.g. an ML technique with no corresponding Technology node).
5. Cypher exceeds the configured timeout (`graphrag.cypher_timeout_sec`, default 10s).

### 4. Results — 3 success + 3 failure examples

Full traces (Cypher, graph path, supporting chunks, answer, citations) are in `notebooks/D3_03_Rana_graphrag_executor.ipynb`. Summary:

| # | Pattern | Query | Result |
|---|---|---|---|
| 1 | Country → Policy → Target | UAE renewable targets under Net Zero 2050 | `graph_guided`. Resolves the exact UAE → Net Zero by 2050 → Triple Renewables by 2030 chain with page-anchored citations not in hybrid's top-5. |
| 2 | Risk → Sector → Evidence | High-confidence climate risks in MENA, and the sectors they impact | `graph_guided`. Multi-hop Region ← Country, Risk → Region, Risk → Sector traversal with `Finding`-level evidence pages. |
| 3 | Technology → Mitigates → Risk | Technologies mitigating heatwave risk in the energy sector | `graph_guided`. Solar PV / Green Hydrogen / Wind Power resolve via confidence-annotated `MITIGATES` edges. |
| 4 | **Failure** — expansion too broad | Global mean temperature rise since pre-industrial times | `graph_guided` but flagged `failure_note`. No entity filter → 50+ `Finding` rows → near-duplicate chunks from the same IPCC pages. |
| 5 | **Failure** — wrong entity | Climate adaptation policies for Pacific Islands coastal flooding | `hybrid_fallback`. "Pacific Islands" not in the alias table / no matching node → 0 Cypher rows → correct fallback. |
| 6 | **Failure** — graph adds no value | Gradient boosting for wind power forecasting | `hybrid_fallback`. ML methodology has no Technology node in this schema; hybrid retrieval correctly carries the answer. |

### 5. Honesty about weak evidence

Every row in `d3_graph_guided_results.csv` now carries:
- `retrieval_type` — `graph_guided` / `hybrid_fallback` / `empty`.
- `fallback_used` (bool) — explicit, derived from `retrieval_type`, not buried in free text.
- `failure_note` — populated whenever fallback occurred *or* the graph technically returned rows but they were low-value (row 4 above: `graph_guided` yet still flagged, because "returned something" and "returned something useful" aren't the same thing).
- `latency_sec`.

### 6. Citations are chunk-grounded, not node-name-grounded

`CitationBuilder.build()` / `build_from_hits()` resolve every citation from `chunk.doc_id` + `chunk.page` (cross-referenced against `papers_metadata.csv`), never from a `Policy.name` or `Technology.name` string directly. A node can appear in the displayed graph path without ever producing a citation if it isn't backed by a chunk/Finding with a resolvable `doc_id`/page. This was verified by reading `_resolve_citation()` directly, not assumed.

### 7. Graph path is used in the answer, not just displayed

`PromptBuilder.build_prompt()` writes the graph path summary and graph-sourced chunks into **Section 1** of the LLM prompt, with an explicit instruction to prioritise that section. The "graph path" shown in the notebook trace is the same content sent to the model — it isn't a separate, decorative visualisation.

### 8. Limitations

1. **Alias table coverage** — `ENTITY_ALIASES` covers ~20 country/technology/risk mappings; anything outside it fails extraction and falls back to hybrid.
2. **Template coverage** — the 5 `GRAPHRAG_REASONING` templates don't compose; cross-pattern questions (e.g. "technologies the UAE uses against coastal flooding") would need a composite Cypher builder.
3. **Finding sparsity** — only demo-scale findings are ingested, so `graphrag_finding_document_grounding` is sparse for under-represented topics.
4. **Latency values are currently illustrative.** The pipeline has not yet been executed against a live Neo4j instance + Gemini API in this environment — `latency_sec` in the CSV is a placeholder pending a real run (`docker compose up -d neo4j`, set `GEMINI_API_KEY`, re-run `D3_03_Rana_graphrag_executor.ipynb` top-to-bottom, and replace these numbers with the measured ones before final submission).

### 9. When the graph genuinely helps (summary)

**Country → policy → target, risk → sector → evidence, technology → mitigates → risk** — anywhere the answer depends on a *relationship* between two named entities rather than their co-occurrence in text. Outside those three patterns (no extractable entity, entity missing from the corpus, unfiltered over-broad queries, or methodological questions), hybrid retrieval alone is the safer and often better choice.

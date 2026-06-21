# Streamlit demo app

The single front-door for the 15-minute presentation: explains every
deliverable in plain language, then proves it with a live run of the real
pipeline. Built from the team's actual code — nothing in this file is
mocked logic.

## Run it

```bash
pip install -r requirements.txt
streamlit run app/streamlit_app.py
```

Opens at `http://localhost:8501`.

## The 5 tabs

| Tab | What's in it |
|---|---|
| 🏠 Overview | Elevator pitch, the 4-step "how a question flows through the system" diagram, tech stack, who owns what |
| 📘 D1 | Reem (data + proxy benchmark), Salma (AutoML retrieval tuning), Rana (graph design plan), Aaya (online learning + ADWIN drift), Alia (eval methodology) — one expander each |
| 📗 D2 | Reem (ingestion), Salma (BM25/dense/hybrid + why RRF), Rana (Neo4j graph build, real counts), Aaya (online retrieval adaptation), Alia (API + tests) |
| 📙 D3 | Reem (citation verification), Salma (5-system retrieval ablation), **Rana (GraphRAG executor — the core pipeline, expanded by default)**, Aaya (online GraphRAG adaptation), Alia (safety + RAG eval), Tuning (QLoRA on Kaggle) |
| 💬 Live Demo | Ask the real system a question — 6 pre-validated example buttons (3 success patterns, 3 deliberate failure patterns) or type your own |

Each D1/D2/D3 expander is meant to be **clicked open by the person who owns
that part** when it's their turn to talk — that's the "brief explanation"
structure requested for the presentation.

## What works with zero setup

- **Overview, D1, D2, D3 tabs** — always work. They read the CSVs already
  saved in `reports/tables/` (every member's real, already-computed results).
  No live services needed.
- **Live Demo — hybrid retrieval (right column)** — always works. Uses the
  local cached embeddings (`data/embeddings/chunks_tfidf_lsa.npy`), no
  Qdrant needed.
- **Live Demo — GraphRAG executor trace (left column)** — runs even without
  Neo4j or a Gemini key. `GraphRAGExecutor.run()` already catches a missing
  Neo4j connection internally and reports `retrieval_type=hybrid_fallback`
  instead of crashing; with no `GEMINI_API_KEY` it shows a clearly labeled
  mock answer instead of a real generated one. **Both are real, intentional
  behaviors of the pipeline** — the team's own `D3_FINAL_SUBMISSION_INDEX.md`
  documents that Gemini quota was unstable during final prep, so stable
  mock-prompt mode was used deliberately.
- **"Expected output" reference panel** — for the 6 pre-validated examples,
  the live result is shown next to the real, already-proven result from
  `reports/tables/d3_graph_guided_results.csv` (Rana's actual executed run
  against a live Neo4j Aura instance, 552 nodes). If live Neo4j isn't
  connected during the actual presentation, you can still show the audience
  the validated reference and explain what it looks like when connected.

## To light up the full graph-guided path (do this before presenting)

```bash
# Either local Neo4j...
docker compose up -d neo4j
# ...or a free Neo4j Aura cloud instance (this is what Rana's validated run used)

export GEMINI_API_KEY=your_key_here   # Windows: set GEMINI_API_KEY=your_key_here
streamlit run app/streamlit_app.py
```

Or put `NEO4J_URI` / `NEO4J_USER` / `NEO4J_PASSWORD` / `NEO4J_DATABASE` /
`GEMINI_API_KEY` in a local `.env` file at the project root — the app loads
it automatically (reuses the project's own `load_local_env()` helper, no
extra dependency needed).

Click "Check Neo4j connection" in the sidebar to confirm it's reachable.

## Important — Git LFS

`data/sample/sample_chunks.json` and `data/pdfs/*.pdf` are tracked with Git
LFS. If you downloaded this repo as a ZIP from GitHub instead of using
`git clone`, those files will be tiny LFS *pointer* files (a few hundred
bytes of text), not the real data, and the app's sidebar will show a clear
error explaining this. Fix:

```bash
git lfs install
git lfs pull
```

## Example queries (also clickable in the Live Demo tab)

| Pattern | Query | Validated result |
|---|---|---|
| Country → Policy → Target (success) | What renewable energy targets has the UAE committed to under its Net Zero 2050 strategy? | `graph_guided`, 5 graph hits |
| Risk → Sector → Evidence (success) | What high-confidence climate risks in the MENA region are documented by findings, and which sectors do they impact? | `graph_guided`, 5 graph hits |
| Technology → Mitigates → Risk (success) | Which technologies mitigate heatwave risk in the energy sector according to climate literature? | `graph_guided`, 5 graph hits |
| Failure: too-broad question | How much has global mean temperature risen since pre-industrial times? | `graph_guided` but flagged low-quality (broad, unfiltered) |
| Failure: missing entity | List all climate adaptation policies adopted by Pacific Islands countries for coastal flooding. | flagged — unsupported geographic entity |
| Failure: graph adds no value | What does the literature say about gradient boosting methods for wind power forecasting? | `hybrid_fallback` |

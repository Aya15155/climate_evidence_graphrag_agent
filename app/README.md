# Streamlit demo app

A single front-door demo that wraps the team's real pipeline (hybrid retrieval
+ GraphRAG executor) in one screen, plus a tab showing every member's already
-computed real results. Built for the 15-minute presentation.

## Run it

```bash
pip install -r requirements.txt
streamlit run app/streamlit_app.py
```

Opens at `http://localhost:8501`.

## What works with zero setup

- **Tab 2 "Team Evidence"** — always works. Reads the CSVs already saved in
  `reports/tables/` (Salma's ablation, Alia's safety + RAG eval, Rana's graph
  counts and graph-guided results). No live services needed.
- **Tab 1 "Ask a Question" — hybrid retrieval (right column)** — always works.
  Uses the local cached embeddings (`data/embeddings/chunks_tfidf_lsa.npy`),
  no Qdrant needed.
- **Tab 1 — GraphRAG executor trace (left column)** — runs even without Neo4j
  or a Gemini key. `GraphRAGExecutor.run()` already catches a missing Neo4j
  connection internally and reports `retrieval_type=hybrid_fallback` instead
  of crashing; with no `GEMINI_API_KEY` it shows a clearly labeled `[MOCK]`
  answer instead of a real generated one. **Both are real, intentional
  behaviors of the pipeline, not bugs in the app** — see
  `STUDY_GUIDE_Rana_D3.md` section 3.5 for why.

## To light up the full graph-guided path (do this before presenting)

```bash
docker compose up -d neo4j
export GEMINI_API_KEY=your_key_here   # Windows: set GEMINI_API_KEY=your_key_here
streamlit run app/streamlit_app.py
```

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

## Example queries (also clickable in the sidebar)

| Pattern | Query |
|---|---|
| Country → Policy → Target | What renewable energy targets has the UAE committed to under its Net Zero 2050 strategy? |
| Risk → Sector → Evidence | What high-confidence climate risks in the MENA region are documented by findings, and which sectors do they impact? |
| Technology → Mitigates → Risk | Which technologies mitigate heatwave risk in the energy sector according to climate literature? |
| Failure: missing entity | List all climate adaptation policies adopted by Pacific Islands countries for coastal flooding. |
| Failure: graph adds no value | What does the literature say about gradient boosting methods for wind power forecasting? |

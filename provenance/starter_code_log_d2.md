# D2 Starter-Code Provenance Log

Use this file to answer: where each starter file/code idea came from and what each member changed. D2 must be transparent because the doctor questioned unclear starter-code origin in D1.

## Notebook evidence

| Notebook/component | Owner | Source | What was changed by member | How verified |
|---|---|---|---|---|
| `notebooks/D2_01_Reem_ingestion_data_quality.ipynb` | Reem | Starter template provided in repo; code completed with AI assistance and local data inspection | Added working ingestion evidence: PDF count, page count, chunk count, metadata audit, page-map examples, quality issues table, summary CSV | Ran all cells; verified real outputs: 300 PDFs, 7588 pages, 57939 chunks; saved `reports/tables/d2_ingestion_summary.csv` |
| `notebooks/D2_02_Salma_retrieval_comparison.ipynb` | Salma | D1 retrieval work extended with member-directed design discussion on fusion/evaluation | Implemented BM25, TF-IDF/LSA dense, hybrid min-max, hybrid RRF, metadata filtering demo, top-k examples, Hit@5/NDCG@5/MRR/p95 latency table | Ran all cells; saved `reports/tables/d2_search_metrics.csv`; top-k examples show page provenance |
| `notebooks/D2_03_Rana_graph_build_cypher.ipynb` | Rana | Graph schema and Neo4j builder scaffold extended with climate-specific graph design | Added graph counts, useful Cypher queries, Finding evidence nodes/relationships, graph reasoning notes, exported graph evidence | Ran all cells; saved `reports/tables/d2_graph_counts.csv`; Cypher outputs visible in notebook |
| `notebooks/D2_04_Aaya_online_retrieval_adaptation.ipynb` | Aaya | D1 River classifier and FeedbackAdapter connected to D2 retrieval baseline | Added static vs topic-gated vs adaptive retrieval routing, feedback-triggered updates, phase metrics, behavior-change example, honest interpretation | Ran all cells; saved `reports/tables/d2_online_vs_static.csv`, `d2_online_adaptation_summary.csv`, and update evidence CSVs |
| `notebooks/D2_05_Alia_api_tests_integration.ipynb` | Alia | FastAPI/TestClient integration built from repo API scaffold | Verified `/search`, API response shape, provenance fields, pytest output, Docker/README setup notes | Ran all cells; `/search` response and pytest evidence visible; pytest now passes 4 tests |

## Support code

| File/component | Owner | Source | What was changed by member | How verified |
|---|---|---|---|---|
| `src/ingest/pdf_loader.py` | Reem | Starter file provided in repo with improvement comments | Added robust page extraction handling and clean failure behavior for corrupted/scanned PDFs | Ingestion notebook ran on corpus without pipeline crash |
| `src/retrieval/hybrid_retriever.py` | Salma | D1 retrieval baseline extended for D2 | Supports BM25+dense fusion using min-max or RRF and returns top-k chunks with provenance fields | Retrieval notebook compared four systems and saved metrics table |
| `src/graph/neo4j_builder.py` | Rana | Graph builder scaffold extended for D2 graph evidence | Supports constraints, document ingestion, Finding nodes, evidence edges, and graph integrity counts | Rana notebook exported node/relationship counts and Cypher query evidence |
| `src/learning/feedback_adapter.py` | Aaya | D1 lightweight adapter extended for D2 online retrieval routing | Maintains per-topic BM25/dense weights and updates them from feedback reasons | Aaya notebook produced feedback update evidence and online-vs-static table |
| `src/api/main.py` | Alia | FastAPI scaffold completed for D2 `/search` | Replaced placeholder `/search` with lazy-loaded BM25 + TF-IDF/LSA dense hybrid search and provenance formatting | `pytest tests -q` passes 4 tests; `/search` returns non-empty results with document/page provenance |

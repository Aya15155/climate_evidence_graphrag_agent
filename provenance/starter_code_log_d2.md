# D2 Starter-Code Provenance Log

Use this file to answer: where did each starter file/code idea come from?

The doctor questioned unclear starter-code origin in D1, so D2 must explicitly record whether code came from a member, an AI prompt, course material, documentation, or an adapted prior project file.

## Notebook evidence

| Notebook/component | Owner | Source | What was changed by member | How verified |
|---|---|---|---|---|
| `notebooks/D2_01_Reem_ingestion_data_quality.ipynb` | Reem | TODO | TODO | TODO |
| `notebooks/D2_02_Salma_retrieval_comparison.ipynb` | Salma | TODO | TODO | TODO |
| `notebooks/D2_03_Rana_graph_build_cypher.ipynb` | Rana | TODO | TODO | TODO |
| `notebooks/D2_04_Aaya_online_retrieval_adaptation.ipynb` | Aaya | TODO | TODO | TODO |
| `notebooks/D2_05_Alia_api_tests_integration.ipynb` | Alia | Starter template provided in repo; all cell code written by Alia with AI assistance | Added 8 cells: app import, /stats check, 5 climate queries, BM25 accuracy, k-param test, 422 error test, pytest output, README verification | Ran all cells; all outputs visible in notebook |

## Support code

| File/component | Owner | Source | What was changed by member | How verified |
|---|---|---|---|---|
| `src/ingest/pdf_loader.py` | Reem | TODO | TODO | TODO |
| `src/retrieval/hybrid_retriever.py` | Salma | TODO | TODO | TODO |
| `src/graph/neo4j_builder.py` | Rana | TODO | TODO | TODO |
| `src/learning/feedback_adapter.py` | Aaya | TODO | TODO | TODO |
| `src/api/main.py` | Alia | Starter file had placeholder /search returning empty list | Rewrote /search to connect to HybridRetriever with RRF fusion; added _SAMPLE_CHUNKS fallback, SearchRequest model, provenance fields, and HTTP 422 validation | 38 pytest tests pass; notebook Cell 2 shows live /stats output |
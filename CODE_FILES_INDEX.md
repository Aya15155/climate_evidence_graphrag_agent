# Code Files Index - D1/D2 Scope

This repo keeps D1 completed artifacts and D2 working files only. D2 evidence is notebook-first.

## Core project files

- `README.md`
- `requirements.txt`
- `docker-compose.yml`
- `.env.example`
- `.gitattributes`
- `.gitignore`

## D1 completed artifacts

- `D1_README.md`
- `D1_SUBMISSION_CHECKLIST.md`
- `D1_Technical_Report_2_Pages.docx`
- `D1_Technical_Report_2_Pages.pdf`
- `configs/run_card_d1.yaml`
- `scripts/build_d1_proxy_eval_set.py`
- `src/retrieval/automl_tuner.py`
- `src/learning/river_topic_classifier.py`
- `src/learning/drift_detector.py`
- `reports/tables/d1_baseline_vs_automl_metrics.csv`
- `reports/tables/d1_automl_trials.csv`
- `reports/figures/prequential_accuracy_plot.png`

## D2 notebooks - primary deliverables

- `notebooks/D2_retrieval_graph_build.ipynb` - final integrated notebook
- `notebooks/D2_01_Reem_ingestion_data_quality.ipynb`
- `notebooks/D2_02_Salma_retrieval_comparison.ipynb`
- `notebooks/D2_03_Rana_graph_build_cypher.ipynb`
- `notebooks/D2_04_Aaya_online_retrieval_adaptation.ipynb`
- `notebooks/D2_05_Alia_api_tests_integration.ipynb`
- `notebooks/README_D2_NOTEBOOKS.md`

## D2 support modules

These `.py` files are backend code imported by the notebooks. They are not substitutes for executed notebook evidence.

### Ingestion - Reem
- `src/ingest/pdf_loader.py`
- `src/ingest/chunker.py`
- `src/ingest/metadata_loader.py`
- `src/ingest/mongo_store.py`
- `src/ingest/qdrant_store.py`
- `src/ingest/run_ingest.py`
- `reports/tables/d2_ingestion_summary.csv`

### Retrieval - Salma
- `src/retrieval/bm25_retriever.py`
- `src/retrieval/dense_retriever.py`
- `src/retrieval/hybrid_retriever.py`
- `src/retrieval/fusion.py`
- `src/evaluation/retrieval_metrics.py`
- `reports/tables/d2_search_metrics.csv`

### Graph - Rana
- `src/graph/neo4j_builder.py`
- `src/graph/cypher_queries.py`
- `src/graph/graph_schema.md`
- `reports/tables/d2_graph_counts.csv`

### Online/adaptation - Aaya
- `src/learning/feedback_adapter.py`
- `src/learning/river_topic_classifier.py`
- `reports/tables/d2_online_vs_static.csv`

### API/tests/integration - Alia
- `src/api/main.py`
- `tests/test_api.py`
- `tests/test_search.py`
- `deliverables/D2/README_D2.md`

## D2 evidence folders

- `deliverables/D2/D2_ACCEPTANCE_CHECKLIST.md`
- `deliverables/D2/member_evidence/`
- `provenance/starter_code_log_d2.md`

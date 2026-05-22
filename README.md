# Climate Evidence GraphRAG Agent - D1 Clean Base + D2 Notebook-First Repo

This repository is cleaned to focus on **D1 completed evidence** and **D2 Retrieval Stack & Graph Build** work.

D1 has already been submitted. The D1 artifacts are kept here as the repaired baseline for D2.

## Current scope

- **D1 completed:** AutoML Track A, River online learner, ADWIN, prequential plot, run card, and final report.
- **D2 in progress:** ingestion, MongoDB/Qdrant storage, BM25+dense hybrid retrieval, Neo4j graph build, `/search` API, metrics, and notebook evidence.

## Important rule from D1 feedback

Each member must commit their own technical work from their own GitHub account. The AI chat logs must show real steering: asking why, comparing options, debugging, verifying outputs, and explaining decisions.

## Main D1 files

| Purpose | File |
|---|---|
| D1 final report | `D1_Technical_Report_2_Pages.docx` |
| D1 report PDF copy | `D1_Technical_Report_2_Pages.pdf` |
| D1 run card | `configs/run_card_d1.yaml` |
| D1 AutoML script | `src/retrieval/automl_tuner.py` |
| D1 River learner | `src/learning/river_topic_classifier.py` |
| D1 metrics | `reports/tables/d1_baseline_vs_automl_metrics.csv` |
| D1 prequential plot | `reports/figures/prequential_accuracy_plot.png` |

## Notebook-first D2 submission rule

The doctor specifically asked for Jupyter notebooks for the next deliverables. Therefore, D2 should be submitted as executed notebooks with visible outputs.

Main integrated notebook:

```text
notebooks/D2_retrieval_graph_build.ipynb
```

Member notebooks:

| Member | Notebook | Main proof |
|---|---|---|
| Reem | `notebooks/D2_01_Reem_ingestion_data_quality.ipynb` | ingestion, metadata, chunk/page provenance |
| Salma | `notebooks/D2_02_Salma_retrieval_comparison.ipynb` | BM25 vs dense vs hybrid metrics |
| Rana | `notebooks/D2_03_Rana_graph_build_cypher.ipynb` | graph schema, counts, Cypher evidence |
| Aaya | `notebooks/D2_04_Aaya_online_retrieval_adaptation.ipynb` | online learner compared with static retrieval |
| Alia | `notebooks/D2_05_Alia_api_tests_integration.ipynb` | `/search`, tests, reproducible run steps |

The `.py` files in `src/` are backend implementation modules only. They support the notebooks, but they do not replace notebook evidence.

## Main D2 evidence files

| Purpose | File |
|---|---|
| D2 integrated notebook | `notebooks/D2_retrieval_graph_build.ipynb` |
| D2 notebook map | `notebooks/README_D2_NOTEBOOKS.md` |
| D2 checklist | `deliverables/D2/D2_ACCEPTANCE_CHECKLIST.md` |
| D2 run card | `configs/d2_run_card.yaml` |
| D2 eval queries | `data/eval/d2_eval_queries.csv` |
| D2 starter-code provenance | `provenance/starter_code_log_d2.md` |
| D2 ingestion table | `reports/tables/d2_ingestion_summary.csv` |
| D2 search metrics | `reports/tables/d2_search_metrics.csv` |
| D2 graph counts | `reports/tables/d2_graph_counts.csv` |
| D2 online-vs-static comparison | `reports/tables/d2_online_vs_static.csv` |

## D2 member ownership - edit your notebook and assigned modules

| Member | Owns for D2 | Notebook | Main folders/files to edit |
|---|---|---|---|
| Reem | Ingestion, metadata, page maps, data quality | `notebooks/D2_01_Reem_ingestion_data_quality.ipynb` | `src/ingest/`, `data/metadata/`, `reports/tables/d2_ingestion_summary.csv` |
| Salma | BM25, dense, hybrid retrieval, retrieval metrics | `notebooks/D2_02_Salma_retrieval_comparison.ipynb` | `src/retrieval/`, `src/evaluation/retrieval_metrics.py`, `reports/tables/d2_search_metrics.csv` |
| Rana | Neo4j climate graph, Cypher queries, graph evidence | `notebooks/D2_03_Rana_graph_build_cypher.ipynb` | `src/graph/`, `docs/diagrams/`, `reports/tables/d2_graph_counts.csv` |
| Aaya | River/ADWIN connection to retrieval, online-vs-static comparison | `notebooks/D2_04_Aaya_online_retrieval_adaptation.ipynb` | `src/learning/`, `reports/tables/d2_online_vs_static.csv` |
| Alia | FastAPI `/search`, tests, integration README | `notebooks/D2_05_Alia_api_tests_integration.ipynb` | `src/api/`, `tests/`, `deliverables/D2/README_D2.md` |

## D2 depth requirement

D2 should not only show that the code runs. It must compare systems:

1. BM25-only retrieval
2. Dense-only retrieval
3. Hybrid retrieval
4. Static hybrid vs topic-gated/adaptive hybrid, if feasible
5. Graph-supported search examples using Neo4j Cypher

Minimum metrics:

- Recall@5
- NDCG@5 or MRR
- p95 latency
- top-k examples with document/page provenance

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install -r requirements.txt
```

If using the stores for D2:

```powershell
docker compose up -d
```

## Run D1 reproduction

```powershell
python scripts/build_d1_proxy_eval_set.py
python src/retrieval/automl_tuner.py --n-trials 30
python src/learning/river_topic_classifier.py
```

## D2 work starts here

Open and complete the notebooks in `notebooks/`. Do not leave TODO placeholders in the final D2 submission.

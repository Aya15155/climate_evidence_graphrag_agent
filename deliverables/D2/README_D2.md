# D2 - Retrieval Stack & Graph Build

This folder is the D2 submission workspace inside the repo.

## Notebook is the main deliverable

The doctor asked for Jupyter notebooks for the next deliverables. The `.py` files are backend/support code only. They must be imported or called from notebooks that show actual outputs, comparisons, metrics, and reflection.

Main integrated notebook:

```text
notebooks/D2_retrieval_graph_build.ipynb
```

Member notebooks:

| Member | Notebook | Evidence expected |
|---|---|---|
| Reem | `notebooks/D2_01_Reem_ingestion_data_quality.ipynb` | corpus count, chunk count, metadata/page provenance |
| Salma | `notebooks/D2_02_Salma_retrieval_comparison.ipynb` | BM25 vs dense vs hybrid metrics |
| Rana | `notebooks/D2_03_Rana_graph_build_cypher.ipynb` | graph counts and Cypher outputs |
| Aaya | `notebooks/D2_04_Aaya_online_retrieval_adaptation.ipynb` | static vs adaptive retrieval comparison |
| Alia | `notebooks/D2_05_Alia_api_tests_integration.ipynb` | `/search` response and tests |

A good D2 notebook section should answer:

1. What did this member implement?
2. Why was this design selected?
3. What comparison or metric proves it works?
4. What failed or remains limited?

## Required D2 outputs

- Executed notebooks under `notebooks/` with visible outputs.
- Ingestion summary: `reports/tables/d2_ingestion_summary.csv`
- Retrieval metrics: `reports/tables/d2_search_metrics.csv`
- Graph counts and Cypher evidence: `reports/tables/d2_graph_counts.csv`
- Online-vs-static comparison: `reports/tables/d2_online_vs_static.csv`
- Starter-code provenance: `provenance/starter_code_log_d2.md`

## Who edits what

| Member | D2 area | Edit these first |
|---|---|---|
| Reem | Ingestion/data quality | `notebooks/D2_01_Reem_ingestion_data_quality.ipynb`, `src/ingest/`, `data/metadata/`, `reports/tables/d2_ingestion_summary.csv`, `member_evidence/Reem_D2_evidence.md` |
| Salma | Retrieval | `notebooks/D2_02_Salma_retrieval_comparison.ipynb`, `src/retrieval/`, `reports/tables/d2_search_metrics.csv`, `member_evidence/Salma_D2_evidence.md` |
| Rana | Graph | `notebooks/D2_03_Rana_graph_build_cypher.ipynb`, `src/graph/`, `reports/tables/d2_graph_counts.csv`, `member_evidence/Rana_D2_evidence.md` |
| Aaya | Online learner connected to retrieval | `notebooks/D2_04_Aaya_online_retrieval_adaptation.ipynb`, `src/learning/`, `reports/tables/d2_online_vs_static.csv`, `member_evidence/Aaya_D2_evidence.md` |
| Alia | API/tests/integration | `notebooks/D2_05_Alia_api_tests_integration.ipynb`, `src/api/`, `tests/`, `member_evidence/Alia_D2_evidence.md` |

Each member must commit their own changes and keep their own complete AI chat log.

# D1 Submission Checklist

## Required by the brief

| Brief requirement | Current artifact | Status |
|---|---|---|
| Choose AutoML Track A or B | Track A implemented in `src/retrieval/automl_tuner.py` | Ready |
| Search over k, metric, SVD dim, normalization, hybrid weight | Implemented and recorded in `configs/run_card_d1.yaml` | Ready |
| River online learner | `src/learning/river_topic_classifier.py` | Ready |
| ADWIN drift handling | `src/learning/drift_detector.py` | Ready |
| Prequential metrics plot | `reports/figures/prequential_accuracy_plot.png` | Ready |
| Baseline vs AutoML Recall@5 / NDCG@5 | `reports/tables/d1_baseline_vs_automl_metrics.csv` | Ready |
| p95 latency | Included in metrics CSV and report | Ready |
| Max 2-page report | `D1_Technical_Report_2_Pages.docx` | Ready |
| Runnable script + YAML/JSON winning run card | `src/retrieval/automl_tuner.py` + `configs/run_card_d1.yaml` | Ready |


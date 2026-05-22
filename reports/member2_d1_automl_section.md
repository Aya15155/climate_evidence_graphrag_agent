# Member 2 D1 Section — AutoML Retrieval Optimisation

## Implemented track

I implemented **Track A: supervised auto-tuned kNN retrieval** using Optuna.

The repaired D1 retriever combines:

- BM25 lexical retrieval
- TF-IDF features reduced with TruncatedSVD
- kNN retrieval over the SVD representation
- hybrid lexical/dense fusion

## Search space

| Parameter | Values |
|---|---|
| `k` | 5, 10, 15, 20 |
| `metric` | cosine, euclidean, manhattan |
| `svd_dim` | 50, 100, 200, 300 |
| `normalization` | none, minmax, zscore |
| `hybrid_weight` | float in [0.0, 1.0] |

The objective was:

```text
NDCG@5 + 0.25 * Recall@5 - 0.0005 * p95_latency_ms
```

## Evaluation design

- Input corpus: 49,541 chunks
- Retrieval benchmark: 120 page-grounded proxy questions
- Split: 84 train / 36 held-out test questions
- Evaluation unit: page-level evidence
- Search budget: 30 Optuna trials

## Results on held-out test split

| System | Recall@5 | NDCG@5 | MRR | p95 latency |
|---|---:|---:|---:|---:|
| Baseline | 0.667 | 0.522 | 0.493 | 674.5 ms |
| AutoML tuned | 0.833 | 0.682 | 0.645 | 676.2 ms |

## Winning configuration

```yaml
k: 20
metric: cosine
svd_dim: 300
normalization: minmax
hybrid_weight: 0.8152445172912974
```

The winning configuration improves both Recall@5 and NDCG@5 while keeping latency almost unchanged.

## Reproducibility

- runnable script: `src/retrieval/automl_tuner.py`
- run card: `configs/run_card_d1.yaml`
- baseline-vs-tuned table: `reports/tables/d1_baseline_vs_automl_metrics.csv`
- trial log: `reports/tables/d1_automl_trials.csv`


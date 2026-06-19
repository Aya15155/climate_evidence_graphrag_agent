# D2 Retrieval Stack — Salma

## Summary

I built the BM25 + dense + hybrid retrieval stack for the Climate Evidence GraphRAG Agent, with a comparison table showing Hit@5, NDCG@5, MRR, and p95 latency across four retrieval methods.

## Design Decisions

### Score Normalisation: Why RRF over Min-Max

BM25 and dense retrievers produce scores in incompatible scales (BM25: 0–30+, dense cosine: 0–1). I compared three fusion strategies:

1. **Min-max normalisation** — simple but fragile; one outlier compresses all other scores near zero.
2. **Z-score normalisation** — more outlier-robust but produces negatives, distorting weighted sums.
3. **Reciprocal Rank Fusion (RRF)** — only uses rank position, completely scale-invariant, no tuning needed.

I chose RRF (k=60, Cormack et al. 2009) as the default because it is the safest when BM25 and dense scores have different scales, which they always do.

### Dense Backend: TF-IDF+LSA Fallback

The primary dense backend is sentence-transformers (BAAI/bge-small-en-v1.5, 384-dim). When torch/sentence-transformers are unavailable, `NumpyDenseRetriever` falls back to TF-IDF + TruncatedSVD (8k features, 128-dim LSA). This ensures the retrieval stack works on any machine without GPU requirements.

## Results (Document-Level Relevance)

| Method | Hit@5 | NDCG@5 | MRR | p95 Latency (ms) |
|---|---|---|---|---|
| BM25 | 1.00 | 0.685 | 0.578 | 690 |
| Dense | 0.60 | 0.320 | 0.198 | 46 |
| Hybrid (min-max) | 0.80 | 0.549 | 0.453 | 938 |
| Hybrid (RRF) | 0.90 | 0.640 | 0.558 | 798 |

### Key observations

- BM25 achieves perfect Hit@5 because climate papers contain distinctive terminology that exact matching captures well.
- Dense-only fails on 4/10 queries because TF-IDF+LSA conflates semantically similar but distinct documents.
- Hybrid RRF recovers most of BM25's hits while improving ranking quality (NDCG) through semantic signal.
- Metadata filtering (topics, regions, sectors) is demonstrated with the Africa region filter on DQ009.

## Files Owned

- `src/retrieval/bm25_retriever.py` — BM25 retriever
- `src/retrieval/dense_retriever.py` — NumpyDenseRetriever with TF-IDF+LSA fallback
- `src/retrieval/hybrid_retriever.py` — Hybrid fusion with RRF/min-max
- `src/retrieval/fusion.py` — Score normalisation and RRF implementation
- `notebooks/D2_02_Salma_retrieval_comparison.ipynb` — Full comparison notebook
- `reports/tables/d2_search_metrics.csv` — Per-query metrics
- `reports/tables/d2_search_metrics_summary.csv` — Summary table

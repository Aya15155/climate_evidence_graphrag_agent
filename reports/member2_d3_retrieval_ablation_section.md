# D3 Retrieval Ablation — Salma

## Summary

This section presents a fair retrieval ablation comparing five systems on the same 10-query gold evaluation set used across D1–D4. All systems operate on the same 49,541-chunk corpus from 300 climate documents, with document-level relevance as the primary evaluation criterion.

## Systems Compared

| System | Description |
|---|---|
| BM25-only | Okapi BM25 lexical retrieval (rank-bm25) |
| Dense-only | TF-IDF + TruncatedSVD (128-dim LSA), cosine similarity |
| Hybrid RRF | BM25 + Dense fused via Reciprocal Rank Fusion (k=60) |
| Topic-gated | River topic classifier filters dense component before RRF fusion |
| Graph-guided | Metadata entity expansion: seed hybrid results → extract topics/risks/sectors → expand candidate pool → re-rank |

## Results

| System | Hit@5 | NDCG@5 | MRR | Precision@5 | p95 Latency (ms) |
|---|---|---|---|---|---|
| bm25_only | 0.60 | 0.600 | 0.600 | 0.60 | 195.87 |
| dense_only | 0.90 | 0.876 | 0.850 | 0.80 | 24.76 |
| hybrid_rrf | 0.90 | 0.803 | 0.775 | 0.70 | 250.08 |
| topic_gated | 0.60 | 0.577 | 0.600 | 0.52 | 263.80 |
| graph_guided | 0.70 | 0.645 | 0.625 | 0.56 | 315.23 |

## Key Findings

### When dense-only outperforms
Dense TF-IDF+LSA achieves the highest NDCG@5 (0.876) because it captures semantic similarity across the metadata-enriched chunk text. It also has the lowest latency (24.76ms p95) since it avoids BM25's O(n) term scoring.

### When hybrid RRF helps
Hybrid RRF matches dense on Hit@5 (0.90) and adds lexical anchoring for factual queries with specific terminology (e.g., DQ006 on Germany's CO2 emissions). Its NDCG@5 (0.803) is slightly lower than dense-only because BM25's contribution dilutes the semantic signal on some queries.

### When graph-guided retrieval fails
Graph-guided (Hit@5=0.70) performs worse than hybrid RRF because metadata entity expansion introduces noise — generic entities like "policy and governance" overlap with many documents, pushing relevant results out of the top-5. It also adds ~65ms latency over hybrid RRF.

### When topic-gated hurts
Topic-gated (Hit@5=0.60) is the weakest hybrid variant. The River classifier, trained on simulated queries, often mispredicts topics for the real evaluation queries, restricting dense search to the wrong subset of chunks.

### Latency trade-off
Graph-guided adds ~65ms over hybrid RRF (315 vs 250ms p95). Dense-only is 10x faster than any hybrid variant. For latency-sensitive applications, dense-only is the best choice; for quality-first applications, hybrid RRF offers the best balance.

## Limitations

1. **Small evaluation set**: 10 queries is insufficient for statistical significance.
2. **Graph proxy**: Metadata co-occurrence approximates Neo4j traversal but cannot capture multi-hop reasoning.
3. **Topic classifier**: Trained on simulated data; real user queries may produce different predictions.
4. **Dense backend**: TF-IDF+LSA is weaker than sentence-transformer embeddings.

## Evidence Artifacts

- Notebook: `notebooks/D3_02_Salma_retrieval_ablation.ipynb`
- Per-query results: `reports/tables/d3_retrieval_ablation.csv`
- Summary: `reports/tables/d3_retrieval_ablation_summary.csv`
- Quality vs latency plot: `reports/figures/d3_quality_vs_latency.png`
- Source: `src/evaluation/retrieval_metrics.py`

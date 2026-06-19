# D4 Final Retrieval Performance — Salma

## Summary

This section reports the final retrieval latency and quality of the integrated system, including an LRU caching analysis. Results are compared against D2 and D3 baselines to show consistency and improvement across deliverables.

## Test Configuration

| Parameter | Value |
|---|---|
| System | Hybrid RRF (BM25 + TF-IDF/LSA dense, RRF fusion k=60) |
| Corpus | 49,541 chunks from 300 climate documents |
| Dense backend | TF-IDF + TruncatedSVD (8k features, 128-dim, cached .npy) |
| Cache | LRU in-memory, max 128 entries, query-level caching |
| Queries | 10 gold evaluation queries (same across D2–D4) |
| Repeats | 20 per query for latency measurement |
| Hardware | Windows 11 laptop, CPU-only, no GPU |

## Results

### Quality (unchanged across cache/no-cache)

| Metric | Value |
|---|---|
| Hit@5 (doc-level) | 0.90 |
| NDCG@5 (doc-level) | 0.8032 |
| Recall@5 | 0.1372 |

### Latency

| Scenario | p95 Latency (ms) | Mean Latency (ms) |
|---|---|---|
| No cache | 139.39 | 99.10 |
| LRU cache (overall) | 8.67 | 5.09 |

### Cache Impact

- **Speedup**: 22.2x median across queries
- **Quality change**: None (deterministic, same results returned)
- Cache is most effective for repeated queries in demo scenarios

## Cross-Deliverable Comparison

| Deliverable | System | NDCG@5 | p95 (ms) | Notes |
|---|---|---|---|---|
| D3 | hybrid_rrf | 0.803 | 250.08 | Ablation, 10 repeats |
| D3 | dense_only | 0.876 | 24.76 | Best quality in ablation |
| D3 | graph_guided | 0.645 | 315.23 | Entity expansion overhead |
| D4 | hybrid_rrf (no cache) | 0.803 | 139.39 | 20 repeats, consistent |
| D4 | hybrid_rrf (cached) | 0.803 | 8.67 | LRU cache, 22.2x speedup |

## Honest Limitations

1. **TF-IDF+LSA dense backend**: Chosen for hardware compatibility (no GPU, <200MB RAM). Sentence-transformer embeddings would improve quality but require ~1GB RAM.

2. **Linear corpus scaling**: Both BM25 (rank-bm25) and numpy dense are O(n). At 3,000 documents, BM25 p95 would be ~6-7s. Qdrant HNSW would reduce dense to O(log n).

3. **Cache effectiveness is scenario-dependent**: Very effective for demos with pre-scripted questions; much lower hit rate with diverse real users.

4. **Machine-specific numbers**: Latency depends on hardware, OS load, and whether the .npy file is OS-cached. Results are not reproducible on different machines without specifying hardware.

5. **No GPU acceleration**: All retrieval is CPU-only. This is realistic for deployment but slower than GPU-accelerated alternatives.

## Evidence Artifacts

- Notebook: `notebooks/D4_02_Salma_retrieval_latency.ipynb`
- Per-query latency: `reports/tables/d4_retrieval_latency.csv`
- Summary: `reports/tables/d4_retrieval_latency_summary.csv`
- Quality vs latency plot: `reports/figures/d4_latency_quality.png`
- Source: `src/evaluation/latency.py`

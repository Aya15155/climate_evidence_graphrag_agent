# ------------------------------------------------------------
# Improvement comments for this starter file:
# - Improvement: replace placeholder scoring with evaluated BM25/Qdrant results on the 30-question gold set.
# - Improvement: add country, sector, policy, risk, and technology filters to support climate-specific search.
# ------------------------------------------------------------
from .fusion import fuse_results

class HybridRetriever:
    def __init__(self, bm25_retriever, dense_retriever, bm25_weight: float = 0.5):
        self.bm25 = bm25_retriever
        self.dense = dense_retriever
        self.bm25_weight = bm25_weight

    def search(self, query: str, k: int = 5, filters: dict | None = None):
        bm25_results = self.bm25.search(query, k=20)
        dense_results = self.dense.search(query, k=20, filters=filters) if self.dense else []
        return fuse_results(bm25_results, dense_results, bm25_weight=self.bm25_weight, top_k=k)

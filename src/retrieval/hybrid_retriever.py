from .fusion import fuse_results, rrf_fuse_results


class HybridRetriever:
    """Combines BM25 and dense retrieval via weighted-sum or RRF fusion.

    normalization="rrf"   → Reciprocal Rank Fusion (recommended for production)
    normalization="minmax" → min-max normalised weighted sum (good for ablation)
    """

    def __init__(
        self,
        bm25_retriever,
        dense_retriever,
        bm25_weight: float = 0.5,
        normalization: str = "rrf",
    ):
        self.bm25 = bm25_retriever
        self.dense = dense_retriever
        self.bm25_weight = bm25_weight
        self.normalization = normalization

    def search(self, query: str, k: int = 5, filters: dict | None = None):
        bm25_results = self.bm25.search(query, k=20)
        dense_results = (
            self.dense.search(query, k=20, filters=filters)
            if self.dense else []
        )
        if self.normalization == "rrf":
            return rrf_fuse_results(bm25_results, dense_results, top_k=k)
        return fuse_results(
            bm25_results,
            dense_results,
            bm25_weight=self.bm25_weight,
            normalization=self.normalization,
            top_k=k,
        )

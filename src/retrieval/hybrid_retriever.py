from .fusion import fuse_results, rrf_fuse_results


class HybridRetriever:
    """Combines BM25 (lexical) and dense (semantic) retrieval.

    Why hybrid beats either alone on climate literature:
    - BM25 catches exact matches: country names, chemical formulas, acronyms
    - Dense catches paraphrases: "warming" ↔ "temperature increase"
    - Fusion merges both ranked lists so neither signal is lost

    normalization="rrf"    → Reciprocal Rank Fusion (default, recommended)
    normalization="minmax" → min-max normalised weighted sum (for ablation)
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
        # Fetch a deeper candidate pool before fusion.
        #
        # D3 exact-chunk evaluation is stricter than document-level retrieval:
        # the relevant evidence may be outside a shallow top-20 list even when
        # the correct document is found.  Use k-aware overfetching so callers
        # can request larger reranking pools without changing this class again.
        candidate_k = max(20, min(max(k * 3, k), 200))

        bm25_results = self.bm25.search(query, k=candidate_k)
        dense_results = (
            self.dense.search(query, k=candidate_k, filters=filters)
            if self.dense else []
        )
        # Filters only apply to dense — BM25 has no metadata index.
        # RRF then re-ranks the merged pool by position, not raw score.
        if self.normalization == "rrf":
            return rrf_fuse_results(bm25_results, dense_results, top_k=k)
        return fuse_results(
            bm25_results,
            dense_results,
            bm25_weight=self.bm25_weight,
            normalization=self.normalization,
            top_k=k,
        )

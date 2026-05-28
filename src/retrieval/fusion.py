import numpy as np


def minmax_normalize(scores):
    """Map scores to [0, 1].  Fragile to outliers — one extreme BM25 score
    compresses all others near zero, hurting the weighted sum."""
    scores = np.array(scores, dtype=float)
    if scores.max() == scores.min():
        return np.ones_like(scores)
    return (scores - scores.min()) / (scores.max() - scores.min())


def zscore_normalize(scores):
    """Shift scores to zero mean / unit variance.  More outlier-robust than
    min-max but can produce negatives, which distort the weighted sum."""
    scores = np.array(scores, dtype=float)
    std = scores.std()
    if std == 0:
        return np.zeros_like(scores)
    return (scores - scores.mean()) / std


def normalize_scores(results, method="minmax"):
    if not results:
        return []
    scores = [float(r.get("score", 0.0)) for r in results]
    if method == "minmax":
        normalized = minmax_normalize(scores)
    elif method == "zscore":
        normalized = zscore_normalize(scores)
    else:
        normalized = np.array(scores, dtype=float)
    out = []
    for idx, r in enumerate(results):
        nr = dict(r)
        nr["norm_score"] = float(normalized[idx])
        out.append(nr)
    return out


def fuse_results(
    bm25_results,
    dense_results,
    bm25_weight=0.5,
    normalization="minmax",
    top_k=5,
):
    """Weighted-sum fusion after score normalisation.

    BM25 scores are unbounded (0–30+) while dense cosine scores live in [0, 1].
    Normalisation brings them to the same scale before combining, but both
    min-max and z-score are query-dependent — the same document can get a
    different normalised score depending on what else is in the result list.
    Use rrf_fuse_results for production; keep this for ablation comparisons.
    """
    if normalization == "rrf":
        # Shortcut: if caller passes normalization='rrf', delegate to RRF
        return rrf_fuse_results(bm25_results, dense_results, top_k=top_k)

    fused = {}
    dense_weight = 1.0 - bm25_weight

    for r in normalize_scores(dense_results, normalization):
        cid = r["chunk_id"]
        fused[cid] = dict(r, fused_score=dense_weight * r["norm_score"])

    for r in normalize_scores(bm25_results, normalization):
        cid = r["chunk_id"]
        if cid not in fused:
            fused[cid] = dict(r, fused_score=0.0)
        fused[cid]["fused_score"] += bm25_weight * r["norm_score"]

    return sorted(fused.values(), key=lambda x: x["fused_score"], reverse=True)[:top_k]


def rrf_fuse_results(
    bm25_results,
    dense_results,
    k: int = 60,
    top_k: int = 5,
):
    """Reciprocal Rank Fusion — the recommended fusion method.

    score(doc) = Σ  1 / (k + rank(doc))
                retrievers

    Why RRF is safest when BM25 and dense scores have different scales:
    - It only uses rank position, not score magnitude
    - BM25 returning score=22 and dense returning score=0.71 for the same
      document doesn't matter — both contribute equally via their rank
    - k=60 is the standard constant from Cormack et al. 2009; it dampens
      the advantage of top-ranked documents without needing any tuning
    """
    scores: dict[str, dict] = {}

    for rank, r in enumerate(bm25_results):
        cid = r["chunk_id"]
        scores.setdefault(cid, dict(r, rrf_score=0.0))
        scores[cid]["rrf_score"] += 1.0 / (k + rank + 1)

    for rank, r in enumerate(dense_results):
        cid = r["chunk_id"]
        scores.setdefault(cid, dict(r, rrf_score=0.0))
        scores[cid]["rrf_score"] += 1.0 / (k + rank + 1)

    results = sorted(scores.values(), key=lambda x: x["rrf_score"], reverse=True)[:top_k]
    for r in results:
        # Alias so downstream code can always read "fused_score"
        r["fused_score"] = r["rrf_score"]
    return results

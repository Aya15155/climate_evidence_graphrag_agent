# ------------------------------------------------------------
# Improvement comments for this starter file:
# - Improvement: replace placeholder scoring with evaluated BM25/Qdrant results on the 30-question gold set.
# - Improvement: add country, sector, policy, risk, and technology filters to support climate-specific search.
# ------------------------------------------------------------

import numpy as np


def minmax_normalize(scores):

    scores = np.array(scores)

    if scores.max() == scores.min():
        return np.ones_like(scores)

    return (
        scores - scores.min()
    ) / (
        scores.max() - scores.min()
    )


def zscore_normalize(scores):

    scores = np.array(scores)

    std = scores.std()

    if std == 0:
        return np.zeros_like(scores)

    return (
        scores - scores.mean()
    ) / std


def normalize_scores(results, method="minmax"):

    if not results:
        return []

    scores = [
        float(r.get("score", 0.0))
        for r in results
    ]

    if method == "minmax":
        normalized = minmax_normalize(scores)

    elif method == "zscore":
        normalized = zscore_normalize(scores)

    else:
        normalized = scores

    out = []

    for idx, r in enumerate(results):

        nr = dict(r)

        nr["norm_score"] = float(
            normalized[idx]
        )

        out.append(nr)

    return out


def fuse_results(
    bm25_results,
    dense_results,
    bm25_weight=0.5,
    normalization="minmax",
    top_k=5,
):

    fused = {}

    dense_weight = 1.0 - bm25_weight

    for r in normalize_scores(
        dense_results,
        normalization,
    ):

        cid = r["chunk_id"]

        fused[cid] = dict(
            r,
            fused_score=
            dense_weight * r["norm_score"]
        )

    for r in normalize_scores(
        bm25_results,
        normalization,
    ):

        cid = r["chunk_id"]

        if cid not in fused:

            fused[cid] = dict(
                r,
                fused_score=0.0
            )

        fused[cid]["fused_score"] += (
            bm25_weight * r["norm_score"]
        )

    return sorted(
        fused.values(),
        key=lambda x: x["fused_score"],
        reverse=True
    )[:top_k]
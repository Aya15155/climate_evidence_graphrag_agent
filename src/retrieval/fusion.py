# ------------------------------------------------------------
# Improvement comments for this starter file:
# - Improvement: replace placeholder scoring with evaluated BM25/Qdrant results on the 30-question gold set.
# - Improvement: add country, sector, policy, risk, and technology filters to support climate-specific search.
# ------------------------------------------------------------
def normalize_scores(results):
    if not results:
        return []
    scores = [float(r.get("score", 0.0)) for r in results]
    lo, hi = min(scores), max(scores)
    denom = hi - lo if hi != lo else 1.0
    out = []
    for r in results:
        nr = dict(r)
        nr["norm_score"] = (float(r.get("score", 0.0)) - lo) / denom
        out.append(nr)
    return out


def fuse_results(bm25_results, dense_results, bm25_weight=0.5, top_k=5):
    fused = {}
    for r in normalize_scores(dense_results):
        cid = r["chunk_id"]
        fused[cid] = dict(r, fused_score=(1 - bm25_weight) * r["norm_score"])
    for r in normalize_scores(bm25_results):
        cid = r["chunk_id"]
        if cid not in fused:
            fused[cid] = dict(r, fused_score=0.0)
        fused[cid]["fused_score"] += bm25_weight * r["norm_score"]
    return sorted(fused.values(), key=lambda x: x["fused_score"], reverse=True)[:top_k]

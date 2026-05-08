# ------------------------------------------------------------
# Improvement comments for this starter file:
# - Improvement: use the same 30 gold Q/A examples across D1, D2, D3, and D4 for fair comparison.
# - Improvement: report Recall@5, NDCG@5, MRR, faithfulness, answer relevance, hallucinated citations, and p95 latency.
# ------------------------------------------------------------
def recall_at_k(retrieved_ids: list[str], relevant_ids: list[str], k: int = 5) -> float:
    if not relevant_ids:
        return 0.0
    return len(set(retrieved_ids[:k]) & set(relevant_ids)) / len(set(relevant_ids))


def dcg(relevances: list[int]) -> float:
    import math
    return sum(rel / math.log2(i + 2) for i, rel in enumerate(relevances))


def ndcg_at_k(retrieved_ids: list[str], relevant_ids: list[str], k: int = 5) -> float:
    rels = [1 if rid in set(relevant_ids) else 0 for rid in retrieved_ids[:k]]
    ideal = sorted(rels, reverse=True)
    denom = dcg(ideal)
    return dcg(rels) / denom if denom else 0.0

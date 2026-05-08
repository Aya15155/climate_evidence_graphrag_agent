# ------------------------------------------------------------
# Improvement comments for this starter file:
# - Improvement: use the same 30 gold Q/A examples across D1, D2, D3, and D4 for fair comparison.
# - Improvement: report Recall@5, NDCG@5, MRR, faithfulness, answer relevance, hallucinated citations, and p95 latency.
# ------------------------------------------------------------
def run_ablation(query_set, systems: dict):
    """Run vector-only, BM25-only, hybrid, graph-guided, and full system comparisons."""
    results = []
    for name, system in systems.items():
        for q in query_set:
            # system should expose system.ask(question) or system.search(question)
            results.append({"system": name, "question": q.get("question"), "status": "TODO"})
    return results

# ------------------------------------------------------------
# Improvement comments for this starter file:
# - Improvement: use the same 30 gold Q/A examples across D1, D2, D3, and D4 for fair comparison.
# - Improvement: report Recall@5, NDCG@5, MRR, faithfulness, answer relevance, hallucinated citations, and p95 latency.
# ------------------------------------------------------------
def faithfulness_placeholder(answer: str, contexts: list[str]) -> float:
    """Replace with RAGAS or an LLM judge later."""
    if not answer or not contexts:
        return 0.0
    return 0.5


def answer_relevance_placeholder(question: str, answer: str) -> float:
    if not question or not answer:
        return 0.0
    return 0.5

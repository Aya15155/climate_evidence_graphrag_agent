# ------------------------------------------------------------
# Improvement comments for this starter file:
# - Improvement: use the same 30 gold Q/A examples across D1, D2, D3, and D4 for fair comparison.
# - Improvement: report Recall@5, NDCG@5, MRR, faithfulness, answer relevance, hallucinated citations, and p95 latency.
# ------------------------------------------------------------

import math
import numpy as np


def recall_at_k(
    retrieved_ids: list[str],
    relevant_ids: list[str],
    k: int = 5
) -> float:

    if not relevant_ids:
        return 0.0

    return len(
        set(retrieved_ids[:k])
        & set(relevant_ids)
    ) / len(set(relevant_ids))


def dcg(
    relevances: list[int]
) -> float:

    return sum(
        rel / math.log2(i + 2)
        for i, rel in enumerate(relevances)
    )


def ndcg_at_k(
    retrieved_ids: list[str],
    relevant_ids: list[str],
    k: int = 5
) -> float:

    rels = [
        1 if rid in set(relevant_ids)
        else 0
        for rid in retrieved_ids[:k]
    ]

    ideal = sorted(
        rels,
        reverse=True
    )

    denom = dcg(ideal)

    return (
        dcg(rels) / denom
        if denom else 0.0
    )


def mean_reciprocal_rank(
    all_results
) -> float:

    rr_scores = []

    for (
        retrieved_docs,
        relevant_docs
    ) in all_results:

        rank = 0

        for idx, doc_id in enumerate(
            retrieved_docs
        ):

            if doc_id in relevant_docs:

                rank = idx + 1
                break

        rr_scores.append(
            1 / rank if rank > 0 else 0
        )

    return float(
        np.mean(rr_scores)
    )


def p95_latency(
    latencies: list[float]
) -> float:

    return float(
        np.percentile(latencies, 95)
    )


# ------------------------------------------------------------
# Placeholder metrics for future D2/D3/D4 evaluation
# ------------------------------------------------------------

def faithfulness_placeholder(
    answer: str,
    contexts: list[str]
) -> float:
    """
    Future integration:
    - RAGAS
    - DeepEval
    - LLM-as-a-judge
    """

    if not answer or not contexts:
        return 0.0

    return 0.5


def answer_relevance_placeholder(
    question: str,
    answer: str
) -> float:

    if not question or not answer:
        return 0.0

    return 0.5


def hallucinated_citation_rate_placeholder(
    citations: list[str],
    retrieved_docs: list[str]
) -> float:
    """
    Placeholder hallucination metric.
    """

    if not citations:
        return 0.0

    hallucinated = 0

    for c in citations:

        if c not in retrieved_docs:
            hallucinated += 1

    return hallucinated / len(citations)
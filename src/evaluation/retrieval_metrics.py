from __future__ import annotations

import math
import re

import numpy as np


# ── Core retrieval metrics (D2/D3/D4) ──────────────────────────


def recall_at_k(retrieved_ids: list[str], relevant_ids: list[str], k: int = 5) -> float:
    if not relevant_ids:
        return 0.0
    return len(set(retrieved_ids[:k]) & set(relevant_ids)) / len(set(relevant_ids))


def dcg(relevances: list[int]) -> float:
    return sum(rel / math.log2(i + 2) for i, rel in enumerate(relevances))


def ndcg_at_k(retrieved_ids: list[str], relevant_ids: list[str], k: int = 5) -> float:
    rel_set = set(relevant_ids)
    rels = [1 if rid in rel_set else 0 for rid in retrieved_ids[:k]]
    ideal = sorted(rels, reverse=True)
    denom = dcg(ideal)
    return dcg(rels) / denom if denom else 0.0


def mean_reciprocal_rank(all_results) -> float:
    rr_scores = []
    for retrieved_docs, relevant_docs in all_results:
        rank = 0
        relevant_set = set(relevant_docs) if not isinstance(relevant_docs, set) else relevant_docs
        for idx, doc_id in enumerate(retrieved_docs):
            if doc_id in relevant_set:
                rank = idx + 1
                break
        rr_scores.append(1 / rank if rank > 0 else 0)
    return float(np.mean(rr_scores))


def p95_latency(latencies: list[float]) -> float:
    return float(np.percentile(latencies, 95))


# ── RAG quality metrics (D3/D4) ────────────────────────────────


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def faithfulness_score(answer: str, contexts: list[str]) -> float:
    """Token-overlap faithfulness: fraction of answer tokens grounded in contexts.

    Measures whether the answer's content can be traced back to the retrieved
    evidence.  A score of 1.0 means every answer token appears in at least one
    context; 0.0 means no overlap at all.
    """
    if not answer or not contexts:
        return 0.0
    answer_tokens = _tokenize(answer)
    if not answer_tokens:
        return 0.0
    context_tokens = set()
    for ctx in contexts:
        context_tokens.update(_tokenize(ctx))
    grounded = sum(1 for t in answer_tokens if t in context_tokens)
    return grounded / len(answer_tokens)


def answer_relevance_score(question: str, answer: str) -> float:
    """Token-overlap relevance: fraction of question tokens addressed by the answer."""
    if not question or not answer:
        return 0.0
    q_tokens = set(_tokenize(question))
    a_tokens = set(_tokenize(answer))
    if not q_tokens:
        return 0.0
    return len(q_tokens & a_tokens) / len(q_tokens)


def hallucinated_citation_rate(
    citations: list[str],
    retrieved_docs: list[str],
) -> float:
    """Fraction of cited document IDs not present in the retrieved set."""
    if not citations:
        return 0.0
    retrieved_set = set(retrieved_docs)
    hallucinated = sum(1 for c in citations if c not in retrieved_set)
    return hallucinated / len(citations)


def context_precision(
    retrieved_ids: list[str],
    relevant_ids: list[str],
    k: int = 5,
) -> float:
    """Precision at k: fraction of top-k retrieved docs that are relevant."""
    if not retrieved_ids:
        return 0.0
    rel_set = set(relevant_ids)
    top_k = retrieved_ids[:k]
    return sum(1 for rid in top_k if rid in rel_set) / len(top_k)


def run_ablation_evaluation(
    systems: dict[str, callable],
    queries: list[dict],
    k: int = 5,
    n_repeats: int = 10,
) -> list[dict]:
    """Run a standard retrieval ablation across multiple systems and queries.

    Each system is a callable(query_text, filters) -> list[dict with chunk_id].
    Each query dict has: query, doc_ids (relevant chunk IDs), filters (optional).
    Returns one row per (query, system) with all metrics.
    """
    import time

    rows = []
    for qrow in queries:
        query_text = qrow["query"]
        doc_rel = qrow.get("doc_ids", [])
        filters = qrow.get("filters")
        qid = qrow.get("query_id", "")

        for sname, sfn in systems.items():
            sfn(query_text, filters)
            lats = []
            for _ in range(n_repeats):
                t0 = time.perf_counter()
                res = sfn(query_text, filters)
                lats.append((time.perf_counter() - t0) * 1000)

            rids = [r["chunk_id"] for r in res]
            doc_rel_set = set(doc_rel)

            rows.append({
                "query_id": qid,
                "system": sname,
                "hit_at_5": 1.0 if any(rid in doc_rel_set for rid in rids[:k]) else 0.0,
                "recall_at_5": recall_at_k(rids, doc_rel, k=k),
                "ndcg_at_5": ndcg_at_k(rids, doc_rel, k=k),
                "precision_at_5": context_precision(rids, doc_rel, k=k),
                "p95_latency_ms": p95_latency(lats),
                "mean_latency_ms": float(np.mean(lats)),
            })
    return rows
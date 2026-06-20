"""
D3 Evaluation: RAG Metrics - Faithfulness & Answer Relevance
Owner: Alia

Simple keyword-overlap scoring for faithfulness and answer relevance.
No GPU or external API needed — works on sample chunks.
"""

from __future__ import annotations
import re
import time
from typing import Any


def _tokenize(text: str) -> set[str]:
    """Lowercase word tokens, strip punctuation."""
    return set(re.findall(r"\b[a-z]{3,}\b", text.lower()))


def faithfulness_score(answer: str, chunks: list[dict[str, Any]]) -> float:
    """
    Proportion of answer content words that appear in the supporting chunks.
    Score: 0.0 (hallucinated) → 1.0 (fully grounded).
    """
    answer_tokens = _tokenize(answer)
    if not answer_tokens:
        return 0.0

    corpus_tokens: set[str] = set()
    for chunk in chunks:
        corpus_tokens |= _tokenize(chunk.get("snippet", "") + " " + chunk.get("text", ""))

    overlap = answer_tokens & corpus_tokens
    return round(len(overlap) / len(answer_tokens), 4)


def answer_relevance_score(answer: str, question: str) -> float:
    """
    Proportion of question keywords found in the answer.
    Score: 0.0 (irrelevant) → 1.0 (fully relevant).
    """
    q_tokens = _tokenize(question)
    if not q_tokens:
        return 0.0
    a_tokens = _tokenize(answer)
    overlap = q_tokens & a_tokens
    return round(len(overlap) / len(q_tokens), 4)


def evaluate_row(
    question: str,
    answer: str,
    chunks: list[dict[str, Any]],
    cited_pages: list[str],
    question_id: str = "",
    method: str = "hybrid",
) -> dict[str, Any]:
    """
    Full evaluation for one Q&A row.
    Returns faithfulness, answer_relevance, citation_correct, latency_ms.
    """
    t0 = time.perf_counter()
    faith = faithfulness_score(answer, chunks)
    relevance = answer_relevance_score(answer, question)
    latency_ms = round((time.perf_counter() - t0) * 1000, 2)

    # Check citation correctness (at least one cited page)
    citation_correct = len(cited_pages) > 0

    return {
        "question_id": question_id,
        "method": method,
        "faithfulness": faith,
        "answer_relevance": relevance,
        "citation_correct": citation_correct,
        "latency_ms": latency_ms,
        "p95_group": "fast" if latency_ms < 500 else "slow",
        "evaluator_notes": (
            f"faith={faith:.2f}, relevance={relevance:.2f}, "
            f"cited={len(cited_pages)} pages"
        ),
    }


def compute_p95_latency(latencies: list[float]) -> float:
    """Return 95th percentile latency from a list of ms values."""
    if not latencies:
        return 0.0
    sorted_lat = sorted(latencies)
    idx = int(len(sorted_lat) * 0.95)
    return round(sorted_lat[min(idx, len(sorted_lat) - 1)], 2)
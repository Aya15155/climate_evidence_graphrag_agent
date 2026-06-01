"""Simple feedback adapter for later retrieval adaptation.

For D1 this is intentionally lightweight. It does not replace the retrieval
stack. It only shows how explicit user feedback could later adjust hybrid
retrieval weights per query topic.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class FeedbackUpdate:
    topic: str
    helpful: bool
    reason: str
    bm25_weight: float
    dense_weight: float
    n_feedback: int


class FeedbackAdapter:
    """Adapt BM25/dense retrieval weights from user feedback.

    The Climate Evidence GraphRAG system uses hybrid retrieval. In the future,
    once the topic classifier predicts a query topic, this adapter can keep a
    small per-topic memory of whether results were helpful.

    Simple D1 rule:
    - If feedback says keyword matching was too narrow/irrelevant, reduce BM25
      and rely more on dense semantic retrieval.
    - If feedback says the answer missed exact policy names/citations, increase
      BM25 to favor lexical matches.
    """

    def __init__(
        self,
        default_bm25_weight: float = 0.50,
        step: float = 0.05,
        min_weight: float = 0.10,
        max_weight: float = 0.90,
    ):
        self.default_bm25_weight = default_bm25_weight
        self.step = step
        self.min_weight = min_weight
        self.max_weight = max_weight
        self.topic_priors = {"policy_governance": 0.65, "uae_cop28": 0.65, "mitigation": 0.55, "adaptation": 0.50, "climate_science": 0.40, "technology_innovation": 0.40, "global": default_bm25_weight,}

        self.topic_weights: Dict[str, float] = defaultdict(lambda: default_bm25_weight)

        for topic, weight in self.topic_priors.items():
            self.topic_weights[topic] = weight
        self.feedback_counts: Dict[str, int] = defaultdict(int)
        
    def get_weights(self, query_topic: Optional[str] = None) -> dict[str, float]:
        """Return the current hybrid weights for a topic."""

        topic = query_topic or "global"
        bm25_weight = self.topic_weights[topic]

        return {
            "bm25_weight": round(bm25_weight, 4),
            "dense_weight": round(1.0 - bm25_weight, 4),
        }

    def get_bm25_weight(self, query_topic: Optional[str] = None) -> float:
        """Return only the BM25 weight for the retriever."""
        return self.get_weights(query_topic)["bm25_weight"]
    


    def update(
        self,
        helpful: bool,
        query_topic: Optional[str] = None,
        reason: str = "generic",
    ) -> FeedbackUpdate:
        """Update retrieval weights after user feedback.

        Parameters
        ----------
        helpful:
            True if the retrieved answer was useful, False otherwise.

        query_topic:
            Optional topic predicted by the River online classifier.

        reason:
            Optional feedback reason, for example:
            - keyword_mismatch
            - too_broad
            - missed_exact_policy
            - missed_citation
            - needs_source_name
            - generic
        """

        topic = query_topic or "global"
        current = self.topic_weights[topic]
        self.feedback_counts[topic] += 1

        if helpful:
            # Keep stable when users are satisfied.
            new_weight = current

        elif reason in {"missed_exact_policy", "missed_citation", "needs_source_name"}:
            # User likely needed exact terms, document titles, policies, or page evidence.
            new_weight = current + self.step

        else:
            # Default: reduce lexical weight and let dense retrieval help more.
            new_weight = current - self.step

        new_weight = max(self.min_weight, min(self.max_weight, new_weight))
        self.topic_weights[topic] = new_weight

        return FeedbackUpdate(
            topic=topic,
            helpful=helpful,
            reason=reason,
            bm25_weight=round(new_weight, 4),
            dense_weight=round(1.0 - new_weight, 4),
            n_feedback=self.feedback_counts[topic],
        )
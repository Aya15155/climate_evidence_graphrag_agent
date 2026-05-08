# ------------------------------------------------------------
# Improvement comments for this starter file:
# - Improvement: log prequential accuracy and ADWIN drift alerts for the D1 report plot.
# - Improvement: connect feedback labels to hybrid weight adaptation after the first working retrieval baseline.
# ------------------------------------------------------------
class FeedbackAdapter:
    """Adapt hybrid retrieval weight from helpful/not-helpful feedback.

    Placeholder rule: increase dense weight when users dislike lexical-heavy results.
    Replace with a proper River learner after feedback data is collected.
    """
    def __init__(self, bm25_weight: float = 0.5):
        self.bm25_weight = bm25_weight

    def update(self, helpful: bool, query_topic: str | None = None) -> float:
        if helpful:
            return self.bm25_weight
        self.bm25_weight = max(0.1, min(0.9, self.bm25_weight - 0.05))
        return self.bm25_weight

# ------------------------------------------------------------
# Improvement comments for this starter file:
# - Improvement: log prequential accuracy and ADWIN drift alerts for the D1 report plot.
# - Improvement: connect feedback labels to hybrid weight adaptation after the first working retrieval baseline.
# ------------------------------------------------------------
class ADWINDriftDetector:
    def __init__(self, delta: float = 0.002):
        from river import drift
        self.detector = drift.ADWIN(delta=delta)

    def update(self, correct: bool) -> bool:
        self.detector.update(int(correct))
        return bool(self.detector.drift_detected)

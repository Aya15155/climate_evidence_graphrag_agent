# ------------------------------------------------------------
# Improvement comments for this starter file:
# - Improvement: use the same 30 gold Q/A examples across D1, D2, D3, and D4 for fair comparison.
# - Improvement: report Recall@5, NDCG@5, MRR, faithfulness, answer relevance, hallucinated citations, and p95 latency.
# ------------------------------------------------------------
import time
from statistics import quantiles

class LatencyTimer:
    def __init__(self):
        self.times_ms = []

    def measure(self, fn, *args, **kwargs):
        start = time.perf_counter()
        result = fn(*args, **kwargs)
        self.times_ms.append((time.perf_counter() - start) * 1000)
        return result

    def p95(self) -> float:
        if not self.times_ms:
            return 0.0
        if len(self.times_ms) < 2:
            return self.times_ms[0]
        return quantiles(self.times_ms, n=20)[-1]

from __future__ import annotations

import time
from collections import OrderedDict
from statistics import quantiles
from typing import Any, Callable


class LatencyTimer:
    """Collect wall-clock latency samples for a callable."""

    def __init__(self):
        self.times_ms: list[float] = []

    def measure(self, fn: Callable, *args, **kwargs) -> Any:
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

    def mean(self) -> float:
        return sum(self.times_ms) / len(self.times_ms) if self.times_ms else 0.0

    def median(self) -> float:
        if not self.times_ms:
            return 0.0
        s = sorted(self.times_ms)
        n = len(s)
        return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2

    def summary(self) -> dict[str, float]:
        import numpy as np
        if not self.times_ms:
            return {"n": 0, "mean_ms": 0, "median_ms": 0, "p95_ms": 0, "min_ms": 0, "max_ms": 0}
        arr = self.times_ms
        return {
            "n": len(arr),
            "mean_ms": round(float(np.mean(arr)), 2),
            "median_ms": round(self.median(), 2),
            "p95_ms": round(self.p95(), 2),
            "min_ms": round(min(arr), 2),
            "max_ms": round(max(arr), 2),
        }


class LRUSearchCache:
    """LRU cache for search results, measuring cache hit/miss latency separately."""

    def __init__(self, maxsize: int = 128):
        self._cache: OrderedDict[str, list[dict]] = OrderedDict()
        self._maxsize = maxsize
        self.hit_timer = LatencyTimer()
        self.miss_timer = LatencyTimer()

    def search(self, search_fn: Callable, query: str, **kwargs) -> list[dict]:
        cache_key = f"{query}|{sorted(kwargs.items())}"
        if cache_key in self._cache:
            start = time.perf_counter()
            result = self._cache[cache_key]
            self._cache.move_to_end(cache_key)
            self.hit_timer.times_ms.append((time.perf_counter() - start) * 1000)
            return result
        start = time.perf_counter()
        result = search_fn(query, **kwargs)
        self.miss_timer.times_ms.append((time.perf_counter() - start) * 1000)
        self._cache[cache_key] = result
        if len(self._cache) > self._maxsize:
            self._cache.popitem(last=False)
        return result

    @property
    def hits(self) -> int:
        return len(self.hit_timer.times_ms)

    @property
    def misses(self) -> int:
        return len(self.miss_timer.times_ms)

    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total else 0.0

    def summary(self) -> dict[str, Any]:
        return {
            "cache_hits": self.hits,
            "cache_misses": self.misses,
            "hit_rate": round(self.hit_rate(), 4),
            "hit_p95_ms": round(self.hit_timer.p95(), 4),
            "miss_p95_ms": round(self.miss_timer.p95(), 2),
        }


def run_latency_benchmark(
    search_fn: Callable,
    queries: list[str],
    n_repeats: int = 10,
    use_cache: bool = False,
    cache_maxsize: int = 128,
    **search_kwargs,
) -> dict[str, Any]:
    """Run a latency benchmark over a list of queries.

    Returns summary dict with p95, mean, median, and cache stats if enabled.
    """
    timer = LatencyTimer()
    cache = LRUSearchCache(maxsize=cache_maxsize) if use_cache else None

    for _ in range(n_repeats):
        for query in queries:
            if cache:
                cache.search(search_fn, query, **search_kwargs)
            else:
                timer.measure(search_fn, query, **search_kwargs)

    if cache:
        all_times = cache.hit_timer.times_ms + cache.miss_timer.times_ms
        timer.times_ms = all_times
        return {**timer.summary(), **cache.summary()}
    return timer.summary()

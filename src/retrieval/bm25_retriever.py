# ------------------------------------------------------------
# Improvement comments for this starter file:
# - Improvement: replace placeholder scoring with evaluated BM25/Qdrant results on the 30-question gold set.
# - Improvement: add country, sector, policy, risk, and technology filters to support climate-specific search.
# ------------------------------------------------------------
from typing import List, Dict

class BM25Retriever:
    def __init__(self, chunks: List[Dict]):
        self.chunks = chunks
        tokenized = [c["text"].lower().split() for c in chunks]
        try:
            from rank_bm25 import BM25Okapi
            self.index = BM25Okapi(tokenized)
        except Exception:
            self.index = None

    def search(self, query: str, k: int = 5) -> List[Dict]:
        if not self.chunks:
            return []
        if self.index is None:
            q = set(query.lower().split())
            scored = [(sum(1 for w in c["text"].lower().split() if w in q), c) for c in self.chunks]
        else:
            scores = self.index.get_scores(query.lower().split())
            scored = list(zip(scores, self.chunks))
        return [dict(c, score=float(s), retriever="bm25") for s, c in sorted(scored, key=lambda x: x[0], reverse=True)[:k]]

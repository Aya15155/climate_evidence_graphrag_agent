from typing import List, Dict


class BM25Retriever:
    """Lexical retriever using Okapi BM25 (rank-bm25 library).

    BM25 rewards exact term matches and penalises very long documents,
    making it strong for keyword-heavy climate queries (e.g. species names,
    country names, policy acronyms) where dense models may miss exact terms.
    """

    def __init__(self, chunks: List[Dict]):
        self.chunks = chunks
        # Lowercase split is sufficient for BM25; stemming adds noise on
        # technical climate vocabulary (e.g. "CO2" != "co2" stemmed forms).
        tokenized = [c["text"].lower().split() for c in chunks]
        try:
            from rank_bm25 import BM25Okapi
            self.index = BM25Okapi(tokenized)
        except Exception:
            # rank_bm25 not installed — fall back to raw term-overlap count
            self.index = None

    def search(self, query: str, k: int = 5) -> List[Dict]:
        if not self.chunks:
            return []
        if self.index is None:
            # Fallback: count how many query words appear in each chunk
            q = set(query.lower().split())
            scored = [(sum(1 for w in c["text"].lower().split() if w in q), c)
                      for c in self.chunks]
        else:
            scores = self.index.get_scores(query.lower().split())
            scored = list(zip(scores, self.chunks))
        return [
            dict(c, score=float(s), retriever="bm25")
            for s, c in sorted(scored, key=lambda x: x[0], reverse=True)[:k]
        ]

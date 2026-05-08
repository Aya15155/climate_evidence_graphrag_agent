# ------------------------------------------------------------
# Improvement comments for this starter file:
# - Improvement: replace placeholder scoring with evaluated BM25/Qdrant results on the 30-question gold set.
# - Improvement: add country, sector, policy, risk, and technology filters to support climate-specific search.
# ------------------------------------------------------------
class DenseRetriever:
    """Qdrant dense search wrapper. Add filters for country, sector, policy, risk, etc."""
    def __init__(self, qdrant_client=None, embedder=None, collection: str = "climate_chunks"):
        self.qdrant_client = qdrant_client
        self.embedder = embedder
        self.collection = collection

    def search(self, query: str, k: int = 5, filters: dict | None = None):
        if self.qdrant_client is None or self.embedder is None:
            return []
        vector = self.embedder.encode([query])[0]
        # TODO: convert filters to Qdrant Filter conditions.
        hits = self.qdrant_client.search(self.collection, query_vector=vector, limit=k)
        return [dict(hit.payload, score=hit.score, retriever="dense") for hit in hits]

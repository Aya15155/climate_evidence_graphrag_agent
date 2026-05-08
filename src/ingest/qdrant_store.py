# ------------------------------------------------------------
# Improvement comments for this starter file:
# - Improvement: add stronger PDF error handling for scanned PDFs, encrypted PDFs, and missing page text.
# - Improvement: preserve page_start/page_end and climate metadata in every chunk for citation reliability.
# ------------------------------------------------------------
from typing import Iterable, List

class QdrantStore:
    def __init__(self, url: str = "http://localhost:6333", collection: str = "climate_chunks", vector_size: int = 384):
        from qdrant_client import QdrantClient
        from qdrant_client.models import Distance, VectorParams
        self.collection = collection
        self.client = QdrantClient(url=url)
        collections = [c.name for c in self.client.get_collections().collections]
        if collection not in collections:
            self.client.create_collection(collection, vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE))

    def upsert(self, chunks: Iterable, embeddings: List[List[float]]) -> None:
        from qdrant_client.models import PointStruct
        points = []
        for i, (chunk, vector) in enumerate(zip(chunks, embeddings)):
            points.append(PointStruct(
                id=i,
                vector=vector,
                payload=chunk.__dict__,
            ))
        if points:
            self.client.upsert(collection_name=self.collection, points=points)

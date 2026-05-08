# ------------------------------------------------------------
# Improvement comments for this starter file:
# - Improvement: add stronger PDF error handling for scanned PDFs, encrypted PDFs, and missing page text.
# - Improvement: preserve page_start/page_end and climate metadata in every chunk for citation reliability.
# ------------------------------------------------------------
from typing import Iterable, Dict

class MongoStore:
    """MongoDB wrapper for document metadata, chunks, provenance, and run cards."""
    def __init__(self, uri: str = "mongodb://localhost:27017", database: str = "climate_agent"):
        from pymongo import MongoClient
        self.client = MongoClient(uri)
        self.db = self.client[database]

    def upsert_document(self, metadata: Dict) -> None:
        self.db.documents.update_one(
            {"document_id": metadata["document_id"]},
            {"$set": metadata},
            upsert=True,
        )

    def upsert_chunks(self, chunks: Iterable) -> None:
        for chunk in chunks:
            self.db.chunks.update_one(
                {"chunk_id": chunk.chunk_id},
                {"$set": chunk.__dict__},
                upsert=True,
            )

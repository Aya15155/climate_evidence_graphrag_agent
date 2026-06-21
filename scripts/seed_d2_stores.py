"""Seed or verify D2 stores for MongoDB and Qdrant.

Usage examples
--------------
Dry-run input verification only:
    python scripts/seed_d2_stores.py --dry-run

Seed local Docker stores after `docker compose up -d mongodb qdrant`:
    python scripts/seed_d2_stores.py --stores mongo qdrant --max-chunks 5000

This script is intentionally safe for D2: dry-run is available for machines where
Docker is unavailable, while real seeding works when MongoDB/Qdrant are running.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CHUNKS = ROOT / "data" / "sample" / "sample_chunks.json"
DEFAULT_METADATA = ROOT / "data" / "metadata" / "papers_metadata.csv"
DEFAULT_EMBEDDINGS = ROOT / "data" / "embeddings" / "chunks_tfidf_lsa.npy"


def load_inputs(chunks_path: Path, metadata_path: Path, embeddings_path: Path):
    if not chunks_path.exists():
        raise FileNotFoundError(f"Missing chunks file: {chunks_path}")
    if not metadata_path.exists():
        raise FileNotFoundError(f"Missing metadata CSV: {metadata_path}")
    if not embeddings_path.exists():
        raise FileNotFoundError(f"Missing embedding matrix: {embeddings_path}")

    chunks: list[dict[str, Any]] = json.loads(chunks_path.read_text(encoding="utf-8"))
    for i, chunk in enumerate(chunks):
        chunk.setdefault("chunk_id", f"chunk_{i:06d}")
    metadata = pd.read_csv(metadata_path)
    embeddings = np.load(embeddings_path, mmap_mode="r")

    if len(chunks) != embeddings.shape[0]:
        raise ValueError(
            f"Chunk/embedding row mismatch: {len(chunks)} chunks vs {embeddings.shape[0]} embeddings"
        )
    return chunks, metadata, embeddings


def seed_mongo(chunks: list[dict[str, Any]], metadata: pd.DataFrame, max_chunks: int, uri: str):
    from pymongo import MongoClient

    client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    client.admin.command("ping")
    db = client["climate_agent"]

    records = metadata.to_dict(orient="records")
    for record in records:
        doc_id = record.get("document_id") or record.get("doc_id")
        if doc_id:
            db.documents.update_one({"document_id": doc_id}, {"$set": record}, upsert=True)

    selected = chunks[:max_chunks] if max_chunks else chunks
    for chunk in selected:
        db.chunks.update_one({"chunk_id": chunk["chunk_id"]}, {"$set": chunk}, upsert=True)

    return {"documents": len(records), "chunks": len(selected)}


def seed_qdrant(chunks: list[dict[str, Any]], embeddings, max_chunks: int, url: str, collection: str):
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, PointStruct, VectorParams

    client = QdrantClient(url=url, timeout=30)
    vector_size = int(embeddings.shape[1])
    existing = [c.name for c in client.get_collections().collections]
    if collection not in existing:
        client.create_collection(
            collection_name=collection,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )

    n = min(max_chunks, len(chunks)) if max_chunks else len(chunks)
    batch_size = 256
    for start in range(0, n, batch_size):
        end = min(start + batch_size, n)
        points = []
        for idx in range(start, end):
            payload = dict(chunks[idx])
            payload["row_index"] = idx
            points.append(
                PointStruct(
                    id=idx,
                    vector=embeddings[idx].astype(float).tolist(),
                    payload=payload,
                )
            )
        client.upsert(collection_name=collection, points=points)

    return {"collection": collection, "vector_size": vector_size, "points": n}


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed/verify D2 MongoDB and Qdrant stores.")
    parser.add_argument("--chunks", type=Path, default=DEFAULT_CHUNKS)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    parser.add_argument("--embeddings", type=Path, default=DEFAULT_EMBEDDINGS)
    parser.add_argument("--dry-run", action="store_true", help="Verify inputs only; do not contact stores.")
    parser.add_argument("--stores", nargs="*", choices=["mongo", "qdrant"], default=["mongo", "qdrant"])
    parser.add_argument("--max-chunks", type=int, default=5000, help="0 means seed all chunks.")
    parser.add_argument("--mongo-uri", default="mongodb://localhost:27017")
    parser.add_argument("--qdrant-url", default="http://localhost:6333")
    parser.add_argument("--qdrant-collection", default="climate_chunks")
    args = parser.parse_args()

    chunks, metadata, embeddings = load_inputs(args.chunks, args.metadata, args.embeddings)
    print("D2 store seed input check")
    print("-------------------------")
    print(f"chunks     : {len(chunks)} from {args.chunks}")
    print(f"metadata   : {len(metadata)} rows from {args.metadata}")
    print(f"embeddings : shape={embeddings.shape} from {args.embeddings}")
    print(f"max_chunks : {args.max_chunks or 'all'}")

    if args.dry_run:
        print("DRY RUN OK: inputs are consistent; no stores contacted.")
        return

    if "mongo" in args.stores:
        result = seed_mongo(chunks, metadata, args.max_chunks, args.mongo_uri)
        print("Mongo seeded:", result)

    if "qdrant" in args.stores:
        result = seed_qdrant(chunks, embeddings, args.max_chunks, args.qdrant_url, args.qdrant_collection)
        print("Qdrant seeded:", result)


if __name__ == "__main__":
    main()

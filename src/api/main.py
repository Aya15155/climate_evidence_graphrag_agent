"""FastAPI entrypoint for the D1/D2 repo scope.

D2 requires a working `/search` hybrid endpoint. This module lazily loads the
local D2 chunk corpus, BM25 index, and cached TF-IDF+LSA dense matrix on the
first search request. `/ask` remains lightweight until D3 GraphRAG.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from src.retrieval.bm25_retriever import BM25Retriever
from src.retrieval.dense_retriever import NumpyDenseRetriever
from src.retrieval.hybrid_retriever import HybridRetriever


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CHUNKS_PATH = PROJECT_ROOT / "data" / "sample" / "sample_chunks.json"
EMBED_CACHE = PROJECT_ROOT / "data" / "embeddings" / "chunks_tfidf_lsa.npy"

app = FastAPI(title="Climate Evidence GraphRAG Agent")


class AskRequest(BaseModel):
    question: str


class SearchRequest(BaseModel):
    question: str
    top_k: int = Field(default=5, ge=1, le=20)
    filters: dict[str, list[str]] | None = None


class FeedbackRequest(BaseModel):
    question: str
    helpful: bool
    comment: str | None = None


@lru_cache(maxsize=1)
def get_hybrid_retriever() -> HybridRetriever:
    """Load the D2 hybrid retriever once and reuse it across requests."""
    if not CHUNKS_PATH.exists():
        raise FileNotFoundError(f"Missing D2 chunks file: {CHUNKS_PATH}")

    with CHUNKS_PATH.open("r", encoding="utf-8") as f:
        chunks: list[dict[str, Any]] = json.load(f)

    # Ensure stable chunk IDs for older/generated chunk files.
    for i, chunk in enumerate(chunks):
        chunk.setdefault("chunk_id", f"chunk_{i:06d}")

    bm25 = BM25Retriever(chunks)
    if EMBED_CACHE.exists():
        dense = NumpyDenseRetriever.load(chunks, str(EMBED_CACHE))
    else:
        # Deterministic fallback; slower on first run but keeps /search usable.
        dense = NumpyDenseRetriever(chunks)

    return HybridRetriever(
        bm25_retriever=bm25,
        dense_retriever=dense,
        bm25_weight=0.5,
        normalization="rrf",
    )


def format_search_result(result: dict[str, Any], rank: int) -> dict[str, Any]:
    """Return only D2 API fields needed for citation/provenance checking."""
    page_start = result.get("page_start") or result.get("page")
    page_end = result.get("page_end") or page_start
    score = result.get("rrf_score", result.get("fused_score", result.get("score", 0.0)))
    text = result.get("text") or result.get("snippet") or ""
    return {
        "rank": rank,
        "chunk_id": result.get("chunk_id") or result.get("id"),
        "document_id": result.get("document_id") or result.get("doc_id"),
        "title": result.get("title"),
        "source": result.get("source") or result.get("pdf_path") or result.get("url"),
        "page_start": page_start,
        "page_end": page_end,
        "score": float(score or 0.0),
        "retriever": result.get("retriever", "hybrid_rrf"),
        "topics": result.get("topics", []),
        "countries": result.get("countries", []),
        "regions": result.get("regions", []),
        "sectors": result.get("sectors", []),
        "snippet": text[:500],
    }


@app.get("/stats")
def stats():
    return {
        "project": "Climate Evidence GraphRAG Agent",
        "status": "D1 complete; D2 retrieval/API available",
        "chunks_path": str(CHUNKS_PATH.relative_to(PROJECT_ROOT)),
        "dense_cache_exists": EMBED_CACHE.exists(),
    }


@app.post("/ingest")
def ingest():
    return {"message": "Run python -m src.ingest.run_ingest after adding PDFs and metadata."}


@app.post("/search")
def search(req: SearchRequest):
    """Hybrid BM25+dense search with document/page provenance for D2."""
    try:
        retriever = get_hybrid_retriever()
        results = retriever.search(req.question, k=req.top_k, filters=req.filters)
    except Exception as exc:  # pragma: no cover - defensive API guard
        raise HTTPException(status_code=503, detail=f"Search backend unavailable: {exc}") from exc

    return {
        "query": req.question,
        "top_k": req.top_k,
        "filters": req.filters,
        "retriever": "BM25 + TF-IDF/LSA dense hybrid using Reciprocal Rank Fusion",
        "results": [format_search_result(r, i) for i, r in enumerate(results, start=1)],
    }


@app.post("/ask")
def ask(req: AskRequest):
    return {
        "question": req.question,
        "answer": "D2 scope exposes retrieval through /search; answer generation is D3 GraphRAG scope.",
        "citations": [],
    }


@app.post("/feedback")
def feedback(req: FeedbackRequest):
    return {
        "message": "Feedback accepted for later River/adaptive retrieval logging.",
        "helpful": req.helpful,
        "comment": req.comment,
    }

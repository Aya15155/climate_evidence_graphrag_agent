"""FastAPI entrypoint for the D1/D2 repo scope.

D2 connects `/search` to the hybrid retrieval stack (BM25 + dense via RRF fusion)
and returns document/page provenance with every result.
`/ask` remains a lightweight placeholder until the GraphRAG stage (D3).
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

log = logging.getLogger(__name__)

app = FastAPI(title="Climate Evidence GraphRAG Agent")

# ---------------------------------------------------------------------------
# Fallback sample chunks — used when MongoDB is unavailable or empty.
# ---------------------------------------------------------------------------
_SAMPLE_CHUNKS: list[dict] = [
    {"chunk_id": "sample_p1_c0", "document_id": "ipcc_ar6_wg1_2021",
     "text": "Global surface temperature has increased faster since 1970 than in any other 50-year period over at least the last 2000 years. Human influence has warmed the climate at an unprecedented rate.",
     "start_page": 1, "end_page": 1, "source": "IPCC AR6 WG1 (2021)"},
    {"chunk_id": "sample_p2_c0", "document_id": "ipcc_ar6_wg1_2021",
     "text": "Global mean sea level increased by 0.20 m between 1901 and 2018. The average rate of sea level rise was 1.3 mm/yr between 1901 and 1971, increasing to 3.7 mm/yr between 2006 and 2018.",
     "start_page": 2, "end_page": 2, "source": "IPCC AR6 WG1 (2021)"},
    {"chunk_id": "sample_p3_c0", "document_id": "friedlingstein_2020_global_carbon_budget",
     "text": "Global CO2 emissions from fossil fuels and industry reached 36.4 GtCO2 in 2019. Land-use change contributed an additional 6.0 GtCO2, bringing total anthropogenic CO2 emissions to 42.4 GtCO2.",
     "start_page": 3, "end_page": 3, "source": "Global Carbon Budget 2020 (Friedlingstein et al.)"},
    {"chunk_id": "sample_p4_c0", "document_id": "werf_2010_global_fire_emissions",
     "text": "Deforestation and fire emissions in tropical regions account for approximately 2.0 GtC per year, representing a major component of the global carbon budget that is highly variable between years.",
     "start_page": 8, "end_page": 8, "source": "Global Fire Emissions Database (van der Werf et al., 2010)"},
    {"chunk_id": "sample_p5_c0", "document_id": "bui_2018_carbon_capture_storage",
     "text": "Carbon capture and storage (CCS) is considered one of the key mitigation strategies to limit warming to 1.5 C. Post-combustion capture imposes an energy penalty of 15-25% on the host power plant.",
     "start_page": 9, "end_page": 9, "source": "Carbon Capture and Storage: The Way Forward (Bui et al., 2018)"},
    {"chunk_id": "sample_p6_c0", "document_id": "tabari_2020_climate_change_flood",
     "text": "Climate change intensifies the hydrological cycle, increasing both flood frequency and drought severity. Precipitation extremes are projected to increase by 10-30% under 2 C warming scenarios.",
     "start_page": 6, "end_page": 6, "source": "Climate Change Impact on Floods (Tabari, 2020)"},
    {"chunk_id": "sample_p7_c0", "document_id": "fuzzi_2015_particulate_matter",
     "text": "Particulate matter (PM2.5) air pollution is responsible for approximately 7 million premature deaths per year globally. Climate change is expected to worsen air quality in many regions through increased wildfire smoke.",
     "start_page": 71, "end_page": 71, "source": "Particulate Matter Air Quality and Climate (Fuzzi et al., 2015)"},
    {"chunk_id": "sample_p8_c0", "document_id": "bakhtiarifard_2025_sustainable_ai",
     "text": "Training large deep learning models can emit over 280 tonnes of CO2 equivalent — five times the lifetime emissions of an average car. Sustainable AI requires energy-efficient hardware and renewable power.",
     "start_page": 14, "end_page": 14, "source": "Climate and Resource Awareness for Sustainable AI (Bakhtiarifard et al., 2025)"},
]


def _build_retriever(chunks: list[dict]):
    from src.retrieval.bm25_retriever import BM25Retriever
    from src.retrieval.dense_retriever import NumpyDenseRetriever
    from src.retrieval.hybrid_retriever import HybridRetriever
    return HybridRetriever(BM25Retriever(chunks), NumpyDenseRetriever(chunks), normalization="rrf")


def _load_chunks_from_mongo() -> list[dict]:
    try:
        from pymongo import MongoClient
        client = MongoClient("mongodb://localhost:27017", serverSelectionTimeoutMS=1000)
        client.admin.command("ping")
        docs = list(client["climate_agent"].chunks.find({}, {"_id": 0}, limit=2000))
        return docs if docs else []
    except Exception:
        return []


def _get_chunks() -> list[dict]:
    live = _load_chunks_from_mongo()
    return live if live else _SAMPLE_CHUNKS


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class SearchRequest(BaseModel):
    query: str
    k: int = 5
    filters: dict | None = None

class AskRequest(BaseModel):
    question: str

class FeedbackRequest(BaseModel):
    question: str
    helpful: bool
    comment: str | None = None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/stats")
def stats():
    chunks = _get_chunks()
    source = "mongodb" if _load_chunks_from_mongo() else "sample"
    return {"project": "Climate Evidence GraphRAG Agent", "status": "D2 in progress",
            "chunk_source": source, "chunk_count": len(chunks)}

@app.post("/ingest")
def ingest():
    return {"message": "Run python -m src.ingest.run_ingest after adding PDFs and metadata."}

@app.post("/search")
def search(req: SearchRequest):
    if not req.query or not req.query.strip():
        raise HTTPException(status_code=422, detail="query must not be empty")

    chunks = _get_chunks()
    retriever = _build_retriever(chunks)
    raw = retriever.search(req.query.strip(), k=req.k, filters=req.filters)

    results = []
    for r in raw:
        results.append({
            "chunk_id": r.get("chunk_id", ""),
            "document_id": r.get("document_id", ""),
            "source": r.get("source", r.get("document_id", "")),
            "page_start": r.get("start_page", None),
            "page_end": r.get("end_page", None),
            "score": round(float(r.get("fused_score", r.get("rrf_score", r.get("score", 0.0)))), 6),
            "snippet": r.get("text", "")[:300],
        })

    source = "mongodb" if _load_chunks_from_mongo() else "sample"
    return {"query": req.query, "k": req.k, "results": results,
            "chunk_source": source, "total_chunks_searched": len(chunks)}

@app.post("/ask")
def ask(req: AskRequest):
    return {"question": req.question,
            "answer": "D2 scope keeps /ask as a placeholder; use /search for retrieval evidence.",
            "citations": []}

@app.post("/feedback")
def feedback(req: FeedbackRequest):
    return {"message": "D2 TODO: connect feedback to River/adaptive retrieval.", "helpful": req.helpful}
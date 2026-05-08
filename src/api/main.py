# ------------------------------------------------------------
# Improvement comments for this starter file:
# - Improvement: replace demo responses with real calls into ingestion, retrieval, GraphRAG, feedback, and stats services.
# - Improvement: validate request/response schemas and return clear error messages for demo robustness.
# ------------------------------------------------------------
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Climate Evidence GraphRAG Agent")

class AskRequest(BaseModel):
    question: str

class FeedbackRequest(BaseModel):
    question: str
    helpful: bool
    comment: str | None = None

@app.get("/stats")
def stats():
    return {"project": "Climate Evidence GraphRAG Agent", "status": "starter", "graph": "climate evidence knowledge graph"}

@app.post("/ingest")
def ingest():
    return {"message": "Run python -m src.ingest.run_ingest after adding PDFs and metadata."}

@app.post("/search")
def search(req: AskRequest):
    return {"query": req.question, "results": [], "note": "Connect HybridRetriever here."}

@app.post("/ask")
def ask(req: AskRequest):
    return {"question": req.question, "answer": "Connect ClimateGraphRAGExecutor here.", "citations": []}

@app.post("/feedback")
def feedback(req: FeedbackRequest):
    return {"message": "Feedback recorded placeholder", "helpful": req.helpful}

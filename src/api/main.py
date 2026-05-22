"""FastAPI entrypoint for the D1/D2 repo scope.

D2 should connect `/search` to the hybrid retrieval stack and return document/page
provenance. `/ask` remains a lightweight placeholder until the later GraphRAG stage.
"""
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
    return {"project": "Climate Evidence GraphRAG Agent", "status": "D1 complete; D2 in progress"}

@app.post("/ingest")
def ingest():
    return {"message": "Run python -m src.ingest.run_ingest after adding PDFs and metadata."}

@app.post("/search")
def search(req: AskRequest):
    return {"query": req.question, "results": [], "note": "D2 TODO: connect BM25+dense hybrid retrieval here."}

@app.post("/ask")
def ask(req: AskRequest):
    return {"question": req.question, "answer": "D2 scope keeps /ask as a placeholder; use /search for retrieval evidence.", "citations": []}

@app.post("/feedback")
def feedback(req: FeedbackRequest):
    return {"message": "D2 TODO: connect feedback to River/adaptive retrieval.", "helpful": req.helpful}

from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)


def test_stats():
    r = client.get("/stats")
    assert r.status_code == 200
    body = r.json()
    assert body["project"] == "Climate Evidence GraphRAG Agent"
    assert "chunks_path" in body


def test_search_returns_provenance():
    r = client.post("/search", json={"question": "renewable energy emissions", "top_k": 3})
    assert r.status_code == 200
    body = r.json()
    assert body["query"] == "renewable energy emissions"
    assert body["results"]
    first = body["results"][0]
    for field in ["chunk_id", "document_id", "page_start", "page_end", "snippet", "score"]:
        assert field in first
    assert first["snippet"]


def test_ask_is_d3_placeholder_only():
    r = client.post("/ask", json={"question": "Which policies address renewable energy?"})
    assert r.status_code == 200
    assert "answer" in r.json()

"""
D2 API smoke tests — Alia

Tests the FastAPI endpoints using TestClient (no live server needed).
MongoDB is not required — the API falls back to built-in sample chunks.

Run:  pytest tests/test_api.py -v
"""
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# /stats
# ---------------------------------------------------------------------------

def test_stats_returns_200():
    r = client.get("/stats")
    assert r.status_code == 200

def test_stats_has_project_field():
    r = client.get("/stats")
    assert r.json()["project"] == "Climate Evidence GraphRAG Agent"

def test_stats_has_chunk_count():
    r = client.get("/stats")
    assert r.json()["chunk_count"] > 0


# ---------------------------------------------------------------------------
# /search
# ---------------------------------------------------------------------------

def test_search_returns_200():
    r = client.post("/search", json={"query": "What causes global warming?"})
    assert r.status_code == 200

def test_search_response_has_required_keys():
    r = client.post("/search", json={"query": "climate change temperature"})
    for key in ("query", "k", "results", "chunk_source", "total_chunks_searched"):
        assert key in r.json()

def test_search_results_is_a_list():
    r = client.post("/search", json={"query": "carbon emissions"})
    assert isinstance(r.json()["results"], list)

def test_search_returns_results_for_climate_query():
    r = client.post("/search", json={"query": "CO2 emissions fossil fuel"})
    assert len(r.json()["results"]) > 0

def test_search_result_has_provenance_fields():
    r = client.post("/search", json={"query": "sea level rise"})
    result = r.json()["results"][0]
    for field in ("chunk_id", "document_id", "source", "page_start", "page_end", "score", "snippet"):
        assert field in result

def test_search_result_chunk_id_is_nonempty_string():
    r = client.post("/search", json={"query": "deforestation fire"})
    assert len(r.json()["results"][0]["chunk_id"]) > 0

def test_search_result_score_is_numeric():
    r = client.post("/search", json={"query": "climate mitigation"})
    for result in r.json()["results"]:
        assert isinstance(result["score"], (int, float))

def test_search_result_snippet_is_nonempty():
    r = client.post("/search", json={"query": "temperature increase"})
    for result in r.json()["results"]:
        assert len(result["snippet"]) > 0

def test_search_k_limits_results():
    r = client.post("/search", json={"query": "climate", "k": 2})
    assert len(r.json()["results"]) <= 2

def test_search_k_defaults_to_5():
    r = client.post("/search", json={"query": "climate change"})
    assert r.json()["k"] == 5

def test_search_query_echoed_in_response():
    query = "What is carbon capture and storage?"
    r = client.post("/search", json={"query": query})
    assert r.json()["query"] == query

def test_search_empty_query_returns_422():
    r = client.post("/search", json={"query": ""})
    assert r.status_code == 422

def test_search_missing_query_returns_422():
    r = client.post("/search", json={})
    assert r.status_code == 422

def test_search_total_chunks_searched_is_positive():
    r = client.post("/search", json={"query": "climate"})
    assert r.json()["total_chunks_searched"] > 0


# ---------------------------------------------------------------------------
# /ask and /feedback
# ---------------------------------------------------------------------------

def test_ask_returns_200():
    r = client.post("/ask", json={"question": "Which policies address renewable energy?"})
    assert r.status_code == 200

def test_ask_has_answer_field():
    r = client.post("/ask", json={"question": "What is the greenhouse effect?"})
    assert "answer" in r.json()

def test_feedback_returns_200():
    r = client.post("/feedback", json={"question": "Is CCS effective?", "helpful": True})
    assert r.status_code == 200

def test_feedback_echoes_helpful_flag():
    r = client.post("/feedback", json={"question": "test", "helpful": False})
    assert r.json()["helpful"] is False
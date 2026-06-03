from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)


def test_search_top_k_shape():
    r = client.post("/search", json={"question": "climate finance adaptation", "top_k": 2})
    assert r.status_code == 200
    body = r.json()
    assert body["top_k"] == 2
    assert len(body["results"]) == 2
    assert all("page_start" in item and "document_id" in item for item in body["results"])

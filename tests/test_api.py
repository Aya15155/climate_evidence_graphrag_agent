# ------------------------------------------------------------
# Improvement comments for this starter file:
# - Improvement: keep this starter file small, tested, and connected to the final integrated pipeline.
# ------------------------------------------------------------
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)

def test_stats():
    r = client.get('/stats')
    assert r.status_code == 200
    assert r.json()['project'] == 'Climate Evidence GraphRAG Agent'

def test_ask_placeholder():
    r = client.post('/ask', json={'question': 'Which policies address renewable energy?'})
    assert r.status_code == 200
    assert 'answer' in r.json()

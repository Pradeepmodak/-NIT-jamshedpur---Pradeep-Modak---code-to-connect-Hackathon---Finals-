"""
Tests for API endpoints.
"""
from fastapi.testclient import TestClient
from engine.api.app import app

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_analyze_empty():
    response = client.post("/analyze", json={"text": ""})
    assert response.status_code == 422
    
def test_analyze_valid():
    response = client.post("/analyze", json={"text": "Apple announces new iPhone."})
    assert response.status_code == 200
    res_list = response.json()
    assert len(res_list) > 0
    assert res_list[0]["ticker"] == "AAPL"

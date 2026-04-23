from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_tracker_returns_200():
    response = client.get("/api/signals/tracker")
    assert response.status_code == 200


def test_tracker_shape():
    response = client.get("/api/signals/tracker")
    data = response.json()
    assert len(data) == 15
    first = data[0]
    assert "date" in first
    assert "market" in first
    assert "recommendation" in first
    assert "outcome" in first
    assert "edge" in first
    assert "modelProbability" in first

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_model_health_returns_200():
    response = client.get("/api/model/health")
    assert response.status_code == 200


def test_model_health_shape():
    response = client.get("/api/model/health")
    data = response.json()
    assert data["overallStatus"] == "Warning"
    assert len(data["features"]) == 8
    assert len(data["driftWarnings"]) == 1

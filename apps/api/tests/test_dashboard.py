from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_get_dashboard_returns_opportunities():
    response = client.get("/api/dashboard")
    assert response.status_code == 200
    data = response.json()
    assert data["opportunities"]["passing"] == 2

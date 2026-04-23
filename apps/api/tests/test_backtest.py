from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_backtest_summary_returns_200():
    response = client.get("/api/backtest/summary")
    assert response.status_code == 200


def test_backtest_summary_shape():
    response = client.get("/api/backtest/summary")
    data = response.json()
    assert data["totalTrades"] == 84
    assert len(data["rows"]) == 6
    assert len(data["equityCurve"]) == 30

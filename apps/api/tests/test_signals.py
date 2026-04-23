from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_get_signals_returns_three_items():
    response = client.get("/api/signals")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3


def test_get_signal_detail_eur_usd():
    response = client.get("/api/signals/EUR-USD/1.0850")
    assert response.status_code == 200
    data = response.json()
    assert data["recommendation"] == "Take"


def test_get_signal_detail_not_found():
    response = client.get("/api/signals/EUR-USD/9.9999")
    assert response.status_code == 404

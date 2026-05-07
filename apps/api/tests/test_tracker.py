from decimal import Decimal
from unittest.mock import patch

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def _mock_signals() -> list[dict]:
    return [
        {
            "signal_id": "eurusd__2026-05-06",
            "s3_key": "eurusd",
            "date": "2026-05-06",
            "score": Decimal("0.70"),
            "signal_valid": True,
            "direction": "bullish",
            "strike_candidate": "1.0880",
            "timing_slot": "14:00",
            "trend_bias": "bullish",
            "timing_risk": "low",
            "reasoning": "[]",
        },
        {
            "signal_id": "gbpusd__2026-05-05",
            "s3_key": "gbpusd",
            "date": "2026-05-05",
            "score": Decimal("0.52"),
            "signal_valid": False,
            "direction": "none",
            "strike_candidate": "1.2680",
            "timing_slot": "11:00",
            "trend_bias": "neutral",
            "timing_risk": "low",
            "reasoning": "[]",
        },
    ]


def test_tracker_returns_200():
    with patch("routers.tracker.get_latest_signals", return_value=_mock_signals()):
        response = client.get("/api/signals/tracker")
    assert response.status_code == 200


def test_tracker_shape():
    with patch("routers.tracker.get_latest_signals", return_value=_mock_signals()):
        response = client.get("/api/signals/tracker")
    data = response.json()
    assert len(data) == 2
    first = data[0]
    assert "date" in first
    assert "market" in first
    assert "recommendation" in first
    assert "outcome" in first
    assert "edge" in first
    assert "modelProbability" in first


def test_tracker_sorted_by_date_descending():
    with patch("routers.tracker.get_latest_signals", return_value=_mock_signals()):
        response = client.get("/api/signals/tracker")
    data = response.json()
    dates = [r["date"] for r in data]
    assert dates == sorted(dates, reverse=True)


def test_tracker_recommendation_and_edge():
    with patch("routers.tracker.get_latest_signals", return_value=_mock_signals()):
        response = client.get("/api/signals/tracker")
    data = response.json()
    # First record: score=0.70, signal_valid=True, direction=bullish → Take
    assert data[0]["recommendation"] == "Take"
    assert data[0]["modelProbability"] == 0.70
    assert data[0]["edge"] == round(0.70 * 2 - 1, 4)
    assert data[0]["outcome"] == "Pending"
    assert data[0]["actionTaken"] is None


def test_tracker_empty_when_no_signals():
    with patch("routers.tracker.get_latest_signals", return_value=[]):
        response = client.get("/api/signals/tracker")
    assert response.status_code == 200
    assert response.json() == []

from unittest.mock import patch
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

_SIGNALS = [
    {"s3_key": "EURUSD", "date": "2026-05-07", "signal_id": "EURUSD__2026-05-07",
     "score": "0.71", "signal_valid": True, "direction": "buy",
     "strike_candidate": "1.0850", "timing_slot": "12:00", "timing_risk": "moderate",
     "trend_bias": "bullish", "reasoning": "[]"},
    {"s3_key": "GBPUSD", "date": "2026-05-07", "signal_id": "GBPUSD__2026-05-07",
     "score": "0.68", "signal_valid": True, "direction": "buy",
     "strike_candidate": "1.2650", "timing_slot": "12:00", "timing_risk": "low",
     "trend_bias": "neutral", "reasoning": "[]"},
]

_REGISTRY = {
    "version": "20260507T144919",
    "trained_at": "2026-05-07T14:49:19+00:00",
    "win_rate": "0.86",
    "status": "active",
}


def test_get_dashboard_returns_opportunities():
    with patch("routers.dashboard.get_latest_signals", return_value=_SIGNALS), \
         patch("routers.dashboard.get_active_model", return_value=_REGISTRY):
        response = client.get("/api/dashboard")
    assert response.status_code == 200
    data = response.json()
    assert data["opportunities"]["passing"] == 2

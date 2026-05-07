# apps/api/tests/routers/test_dashboard_router.py
from __future__ import annotations
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from main import app

SIGNALS = [
    {"s3_key": "EURUSD", "date": "2026-05-07", "signal_id": "EURUSD__2026-05-07",
     "score": "0.71", "signal_valid": True, "direction": "buy",
     "strike_candidate": "1.0850", "timing_slot": "12:00", "timing_risk": "moderate",
     "trend_bias": "bullish", "reasoning": "[]"},
    {"s3_key": "GBPUSD", "date": "2026-05-07", "signal_id": "GBPUSD__2026-05-07",
     "score": "0.58", "signal_valid": True, "direction": "buy",
     "strike_candidate": "1.2650", "timing_slot": "12:00", "timing_risk": "low",
     "trend_bias": "neutral", "reasoning": "[]"},
    {"s3_key": "USDJPY", "date": "2026-05-07", "signal_id": "USDJPY__2026-05-07",
     "score": "0.40", "signal_valid": False, "direction": "none",
     "strike_candidate": "150.00", "timing_slot": "09:30", "timing_risk": "low",
     "trend_bias": "bearish", "reasoning": "[]"},
]

REGISTRY = {
    "version": "20260507T144919",
    "trained_at": "2026-05-07T14:49:19+00:00",
    "win_rate": "0.86",
    "status": "active",
}


@pytest.fixture(autouse=True)
def env(monkeypatch):
    monkeypatch.setenv("LIVEWELL_ENV", "test")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")


def test_dashboard_counts():
    with patch("routers.dashboard.get_latest_signals", return_value=SIGNALS), \
         patch("routers.dashboard.get_active_model", return_value=REGISTRY):
        client = TestClient(app)
        resp = client.get("/api/dashboard")
    assert resp.status_code == 200
    data = resp.json()
    assert data["opportunities"]["total"] == 3
    assert data["opportunities"]["passing"] == 1   # EURUSD score >= 0.65
    assert data["opportunities"]["review"] == 1    # GBPUSD score 0.55–0.65


def test_dashboard_top_candidates_ordered_by_score():
    with patch("routers.dashboard.get_latest_signals", return_value=SIGNALS), \
         patch("routers.dashboard.get_active_model", return_value=REGISTRY):
        client = TestClient(app)
        resp = client.get("/api/dashboard")
    assert resp.status_code == 200
    data = resp.json()
    candidates = data["topCandidates"]
    instruments = [c["instrument"] for c in candidates]
    assert instruments[0] == "EUR/USD"
    assert instruments[1] == "GBP/USD"
    assert instruments[2] == "USD/JPY"

# apps/api/tests/routers/test_signals_router.py
from __future__ import annotations
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from main import app

DYNAMO_SIGNAL = {
    "signal_id": "EURUSD__2026-05-07",
    "s3_key": "EURUSD",
    "date": "2026-05-07",
    "strike_candidate": "1.0850",
    "timing_slot": "12:00",
    "timing_risk": "moderate",
    "signal_valid": True,
    "direction": "buy",
    "trend_bias": "bullish",
    "reasoning": "[]",
    "score": "0.71",
    "model_version": "20260507T144919",
}


@pytest.fixture(autouse=True)
def env(monkeypatch):
    monkeypatch.setenv("LIVEWELL_ENV", "test")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")


def test_get_signals_returns_list():
    with patch("routers.signals.get_latest_signals", return_value=[DYNAMO_SIGNAL]):
        client = TestClient(app)
        resp = client.get("/api/signals")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["instrument"] == "EUR/USD"
    assert data[0]["status"] == "Open"


def test_get_signals_empty_returns_empty_list():
    with patch("routers.signals.get_latest_signals", return_value=[]):
        client = TestClient(app)
        resp = client.get("/api/signals")
    assert resp.status_code == 200
    assert resp.json() == []


def test_get_signal_detail_found():
    with patch("routers.signals.get_latest_signals", return_value=[DYNAMO_SIGNAL]), \
         patch("routers.signals.get_signal", return_value=DYNAMO_SIGNAL):
        client = TestClient(app)
        resp = client.get("/api/signals/EUR-USD/1.0850")
    assert resp.status_code == 200
    data = resp.json()
    assert data["recommendation"] == "Take"
    assert data["confidence"] == "High"
    assert data["noTradeFlag"] is False


def test_get_signal_detail_not_found():
    with patch("routers.signals.get_latest_signals", return_value=[DYNAMO_SIGNAL]), \
         patch("routers.signals.get_signal", return_value=None):
        client = TestClient(app)
        resp = client.get("/api/signals/EUR-USD/9.9999")
    assert resp.status_code == 404


GOLD_SIGNAL = {
    "signal_id": "XAUUSD__2026-05-07",
    "s3_key": "XAUUSD",
    "date": "2026-05-07",
    "strike_candidate": "2300.00",
    "timing_slot": "12:00",
    "timing_risk": "low",
    "signal_valid": True,
    "direction": "buy",
    "trend_bias": "bullish",
    "reasoning": "[]",
    "score": "0.68",
    "model_version": "20260507T144919",
}


def test_get_signal_detail_gold_slug_resolves_to_xauusd():
    """URL slug 'Gold' must resolve to s3_key 'XAUUSD', not 'GOLD'."""
    captured = {}

    def mock_get_signal(s3_key: str, date: str):
        captured["s3_key"] = s3_key
        return GOLD_SIGNAL

    with patch("routers.signals.get_latest_signals", return_value=[GOLD_SIGNAL]), \
         patch("routers.signals.get_signal", side_effect=mock_get_signal):
        client = TestClient(app)
        resp = client.get("/api/signals/Gold/2300.00")
    assert resp.status_code == 200
    assert captured["s3_key"] == "XAUUSD"
    assert resp.json()["instrument"] == "Gold"

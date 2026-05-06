from __future__ import annotations
import os
from unittest.mock import patch
import pytest


@pytest.fixture(autouse=True)
def env(monkeypatch):
    monkeypatch.setenv("LIVEWELL_BUCKET", "test-bucket")
    monkeypatch.setenv("LIVEWELL_ENV", "test")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")


MOCK_SIGNAL_ROW = {
    "date": "2026-05-05",
    "ema_20": 1.08,
    "ema_50": 1.07,
    "rsi_14": 55.0,
    "macd": 0.001,
    "macd_signal": 0.0009,
    "macd_hist": 0.0001,
    "atr_14": 0.005,
    "trend_bias": "bullish",
    "session_quality": "high",
    "strike_candidate": "1.0850",
    "signal_valid": True,
    "direction": "buy",
    "reasoning": "{}",
    "timing_slot": "buy_bullish",
    "timing_risk": "moderate",
}


def test_run_instrument_returns_signal_record():
    import pandas as pd
    mock_df = pd.DataFrame([MOCK_SIGNAL_ROW])

    with patch("livewell.pipeline.runner.run_ingestion") as mock_ingest, \
         patch("livewell.pipeline.runner.run_features") as mock_features, \
         patch("livewell.pipeline.runner.run_signals") as mock_signals, \
         patch("livewell.pipeline.runner._read_latest_signal", return_value=MOCK_SIGNAL_ROW):

        mock_ingest.return_value = {"succeeded": ["EURUSD"], "failed": []}
        mock_features.return_value = {"succeeded": ["EURUSD"], "failed": []}
        mock_signals.return_value = {"succeeded": ["EURUSD"], "failed": []}

        from livewell.pipeline.runner import run_instrument
        result = run_instrument("EURUSD", "run-123")

    assert result["signal_id"] == "EURUSD__2026-05-05"
    assert result["s3_key"] == "EURUSD"
    assert result["run_id"] == "run-123"
    assert result["direction"] == "buy"
    assert result["score"] is None
    assert result["model_version"] is None
    assert "created_at" in result


def test_run_instrument_propagates_exception():
    with patch("livewell.pipeline.runner.run_ingestion", side_effect=RuntimeError("yfinance down")):
        from livewell.pipeline.runner import run_instrument
        with pytest.raises(RuntimeError, match="yfinance down"):
            run_instrument("EURUSD", "run-456")

from __future__ import annotations
import io
from unittest.mock import patch, MagicMock
import numpy as np
import pandas as pd
import pytest


@pytest.fixture(autouse=True)
def env(monkeypatch):
    monkeypatch.setenv("LIVEWELL_BUCKET", "test-bucket")
    monkeypatch.setenv("LIVEWELL_ENV", "test")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")


def _synthetic_df(n: int = 60) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    return pd.DataFrame({
        "signal_id": [f"EURUSD__2026-01-{i+1:02d}" for i in range(n)],
        "s3_key": ["EURUSD"] * n,
        "date": pd.date_range("2026-01-01", periods=n, freq="D"),
        "ema_20": rng.uniform(1.05, 1.15, n),
        "ema_50": rng.uniform(1.04, 1.14, n),
        "rsi_14": rng.uniform(30, 70, n),
        "macd": rng.uniform(-0.002, 0.002, n),
        "macd_signal": rng.uniform(-0.002, 0.002, n),
        "macd_hist": rng.uniform(-0.001, 0.001, n),
        "atr_14": rng.uniform(0.003, 0.01, n),
        "session_quality": rng.choice(["high", "medium", "low"], n),
        "direction": rng.choice(["buy", "sell", "none"], n),
        "signal_valid": rng.choice([True, False], n),
        "outcome": rng.integers(0, 2, n),
    })


def test_train_produces_model_with_predict_proba(tmp_path):
    df = _synthetic_df()
    with patch("livewell.models.train._load_labeled_data", return_value=df), \
         patch("livewell.models.train._upload_artifact") as mock_upload, \
         patch("livewell.models.train.register_model") as mock_register:
        from livewell.models.train import run_training
        model, metrics = run_training()
    assert hasattr(model, "predict_proba")
    proba = model.predict_proba([[1.0, 55.0, 0.0001, 0.005, 2, 1, 1, 1.08, 1.07, 0.001, 0.0009, 0]])
    assert proba.shape == (1, 2)


def test_train_calls_register_model(tmp_path):
    df = _synthetic_df()
    with patch("livewell.models.train._load_labeled_data", return_value=df), \
         patch("livewell.models.train._upload_artifact", return_value="models/rf_tuned/vTEST.joblib"), \
         patch("livewell.models.train.register_model") as mock_register:
        from livewell.models.train import run_training
        run_training()
    mock_register.assert_called_once()
    call_kwargs = mock_register.call_args.kwargs
    assert call_kwargs["model_name"] == "rf_tuned"
    assert "version" in call_kwargs
    assert "win_rate" in call_kwargs
    assert "ev" in call_kwargs


def test_train_metrics_are_reasonable(tmp_path):
    df = _synthetic_df(n=120)
    with patch("livewell.models.train._load_labeled_data", return_value=df), \
         patch("livewell.models.train._upload_artifact"), \
         patch("livewell.models.train.register_model"):
        from livewell.models.train import run_training
        _, metrics = run_training()
    assert 0.0 <= metrics["win_rate"] <= 1.0
    assert isinstance(metrics["brier_score"], float)
    assert isinstance(metrics["ev"], float)

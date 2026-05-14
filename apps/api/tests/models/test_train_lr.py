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
        "label": rng.integers(0, 2, n),
    })


def test_run_lr_training_returns_model_and_metrics():
    df = _synthetic_df()
    with patch("livewell.models.train_lr._load_labeled_data", return_value=df), \
         patch("livewell.models.train_lr._upload_lr_artifact", return_value="models/lr_baseline/vTEST.joblib"), \
         patch("livewell.models.train_lr.register_model"):
        from livewell.models.train_lr import run_lr_training
        model, metrics, coef_df = run_lr_training()
    assert hasattr(model, "predict_proba")
    assert {"win_rate", "brier_score", "ev"}.issubset(metrics.keys())
    assert isinstance(coef_df, pd.DataFrame)


def test_coef_df_has_all_feature_names():
    from livewell.models.features import FEATURE_NAMES
    df = _synthetic_df()
    with patch("livewell.models.train_lr._load_labeled_data", return_value=df), \
         patch("livewell.models.train_lr._upload_lr_artifact", return_value="models/lr_baseline/vTEST.joblib"), \
         patch("livewell.models.train_lr.register_model"):
        from livewell.models.train_lr import run_lr_training
        _, _, coef_df = run_lr_training()
    assert set(coef_df["feature"].tolist()) == set(FEATURE_NAMES)


def test_model_registered_as_lr_baseline():
    df = _synthetic_df()
    with patch("livewell.models.train_lr._load_labeled_data", return_value=df), \
         patch("livewell.models.train_lr._upload_lr_artifact", return_value="models/lr_baseline/vTEST.joblib"), \
         patch("livewell.models.train_lr.register_model") as mock_register:
        from livewell.models.train_lr import run_lr_training
        run_lr_training()
    mock_register.assert_called_once()
    kwargs = mock_register.call_args.kwargs
    assert kwargs["model_name"] == "lr_baseline"
    assert "version" in kwargs
    assert "win_rate" in kwargs
    assert "ev" in kwargs


def test_walk_forward_produces_multiple_folds():
    rng = np.random.default_rng(0)
    n = 540
    df = pd.DataFrame({
        "signal_id": [f"EURUSD__2026-01-{i}" for i in range(n)],
        "s3_key": ["EURUSD"] * n,
        "date": pd.date_range("2025-01-01", periods=n, freq="D"),
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
        "label": rng.integers(0, 2, n),
    })
    with patch("livewell.models.train_lr._load_labeled_data", return_value=df), \
         patch("livewell.models.train_lr._upload_lr_artifact", return_value="models/lr_baseline/vTEST.joblib"), \
         patch("livewell.models.train_lr.register_model"):
        from livewell.models.train_lr import run_lr_training
        _, metrics, _ = run_lr_training()
    from livewell.models.train import _walk_forward_split
    folds = list(_walk_forward_split(df))
    assert len(folds) >= 6
    assert {"win_rate", "brier_score", "ev"}.issubset(metrics.keys())

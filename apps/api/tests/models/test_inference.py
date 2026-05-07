from __future__ import annotations
import os
import pickle
import tempfile
from unittest.mock import patch, MagicMock
import pytest
import numpy as np


@pytest.fixture(autouse=True)
def env(monkeypatch):
    monkeypatch.setenv("LIVEWELL_BUCKET", "test-bucket")
    monkeypatch.setenv("LIVEWELL_ENV", "test")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")


RECORD = {
    "ema_20": "1.08",
    "ema_50": "1.07",
    "rsi_14": "55.0",
    "macd": "0.001",
    "macd_signal": "0.0009",
    "macd_hist": "0.0001",
    "atr_14": "0.005",
    "session_quality": "high",
    "direction": "buy",
    "signal_valid": True,
    "score": None,
    "model_version": None,
}

ACTIVE_MODEL = {
    "version": "20260506T142000",
    "s3_path": "models/rf_tuned/v20260506T142000.joblib",
    "features": [
        "ema_ratio", "rsi_14", "macd_hist", "atr_14",
        "session_quality_enc", "direction_enc", "signal_valid_enc",
        "ema_20", "ema_50", "macd", "macd_signal", "instrument_enc",
    ],
}


class FakeModel:
    """Pickleable fake model for testing."""
    def predict_proba(self, X):
        return np.array([[0.266, 0.734]])


def _make_mock_model():
    """Return a mock sklearn-like model that returns prob_itm=0.734."""
    model = MagicMock()
    model.predict_proba.return_value = np.array([[0.266, 0.734]])
    return model


def test_score_is_set_on_returned_record(tmp_path, monkeypatch):
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    mock_model = _make_mock_model()
    with patch("livewell.models.inference.get_active_model", return_value=ACTIVE_MODEL), \
         patch("livewell.models.inference._load_model", return_value=mock_model):
        from livewell.models.inference import score_signal
        result = score_signal(dict(RECORD), "EURUSD")
    assert abs(result["score"] - 0.734) < 1e-6
    assert result["model_version"] == "20260506T142000"


def test_original_record_fields_preserved(tmp_path, monkeypatch):
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    mock_model = _make_mock_model()
    with patch("livewell.models.inference.get_active_model", return_value=ACTIVE_MODEL), \
         patch("livewell.models.inference._load_model", return_value=mock_model):
        from livewell.models.inference import score_signal
        result = score_signal(dict(RECORD), "EURUSD")
    assert result["ema_20"] == "1.08"
    assert result["direction"] == "buy"


def test_raises_when_no_active_model(tmp_path, monkeypatch):
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    with patch("livewell.models.inference.get_active_model",
               side_effect=RuntimeError("no active model found for rf_tuned")):
        from livewell.models.inference import score_signal
        with pytest.raises(RuntimeError, match="no active model found"):
            score_signal(dict(RECORD), "EURUSD")


def test_s3_download_called_on_cache_miss(tmp_path, monkeypatch):
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    mock_model = _make_mock_model()
    with patch("livewell.models.inference.get_active_model", return_value=ACTIVE_MODEL), \
         patch("livewell.models.inference._download_model", return_value=mock_model) as mock_dl:
        from livewell.models.inference import score_signal
        score_signal(dict(RECORD), "EURUSD")
    mock_dl.assert_called_once()


def test_s3_download_not_called_on_cache_hit(tmp_path, monkeypatch):
    import joblib
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    mock_model = FakeModel()
    # Pre-populate the /tmp cache file
    cache_path = tmp_path / "livewell_model_20260506T142000.joblib"
    joblib.dump(mock_model, str(cache_path))

    with patch("livewell.models.inference.get_active_model", return_value=ACTIVE_MODEL), \
         patch("livewell.models.inference._download_model") as mock_dl:
        from livewell.models.inference import score_signal
        score_signal(dict(RECORD), "EURUSD")
    mock_dl.assert_not_called()

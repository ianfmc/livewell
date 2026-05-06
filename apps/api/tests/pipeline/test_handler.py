from __future__ import annotations
from unittest.mock import call, patch, MagicMock
import pytest


@pytest.fixture(autouse=True)
def env(monkeypatch):
    monkeypatch.setenv("LIVEWELL_BUCKET", "test-bucket")
    monkeypatch.setenv("LIVEWELL_ENV", "test")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")


def _make_signal(s3_key: str) -> dict:
    return {
        "signal_id": f"{s3_key}__2026-05-05",
        "s3_key": s3_key,
        "run_id": "run-1",
        "direction": "buy",
        "signal_valid": True,
        "score": None,
        "model_version": None,
        "created_at": "2026-05-05T00:05:00Z",
    }


def test_all_succeed_status_is_completed():
    with patch("livewell.pipeline.handler.run_instrument", side_effect=lambda s, r, **kw: _make_signal(s)), \
         patch("livewell.pipeline.handler.create_run"), \
         patch("livewell.pipeline.handler.update_run") as mock_update, \
         patch("livewell.pipeline.handler.put_signal"):
        from livewell.pipeline.handler import handler
        result = handler({}, None)

    assert result["status"] == "completed"
    status_call = mock_update.call_args
    assert status_call.kwargs["status"] == "completed"
    assert status_call.kwargs["errors"] == []


def test_partial_failure_status_is_completed_with_errors():
    instruments_seen = []

    def side_effect(s3_key, run_id, **kwargs):
        instruments_seen.append(s3_key)
        if s3_key == "EURUSD":
            raise RuntimeError("yfinance down")
        return _make_signal(s3_key)

    with patch("livewell.pipeline.handler.run_instrument", side_effect=side_effect), \
         patch("livewell.pipeline.handler.create_run"), \
         patch("livewell.pipeline.handler.update_run") as mock_update, \
         patch("livewell.pipeline.handler.put_signal") as mock_put:
        from livewell.pipeline.handler import handler
        result = handler({}, None)

    assert result["status"] == "completed_with_errors"
    status_call = mock_update.call_args
    assert status_call.kwargs["status"] == "completed_with_errors"
    assert len(status_call.kwargs["errors"]) == 1
    assert status_call.kwargs["errors"][0]["s3_key"] == "EURUSD"
    # put_signal called for every instrument except the failing one
    assert mock_put.call_count == len(instruments_seen) - 1


def test_all_fail_status_is_failed():
    with patch("livewell.pipeline.handler.run_instrument", side_effect=RuntimeError("network error")), \
         patch("livewell.pipeline.handler.create_run"), \
         patch("livewell.pipeline.handler.update_run") as mock_update, \
         patch("livewell.pipeline.handler.put_signal"):
        from livewell.pipeline.handler import handler
        result = handler({}, None)

    assert result["status"] == "failed"
    assert mock_update.call_args.kwargs["status"] == "failed"


def test_put_signal_called_per_success():
    successes = 0

    def side_effect(s3_key, run_id, **kwargs):
        nonlocal successes
        if s3_key in ("EURUSD", "GBPUSD"):
            raise RuntimeError("fail")
        successes += 1
        return _make_signal(s3_key)

    with patch("livewell.pipeline.handler.run_instrument", side_effect=side_effect), \
         patch("livewell.pipeline.handler.create_run"), \
         patch("livewell.pipeline.handler.update_run"), \
         patch("livewell.pipeline.handler.put_signal") as mock_put:
        from livewell.pipeline.handler import handler
        handler({}, None)

    assert mock_put.call_count == successes

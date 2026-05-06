from __future__ import annotations
import json
from unittest.mock import patch, MagicMock
import pytest

from livewell.pipeline.handler import handler


@pytest.fixture(autouse=True)
def env(monkeypatch):
    monkeypatch.setenv("LIVEWELL_BUCKET", "test-bucket")
    monkeypatch.setenv("LIVEWELL_ENV", "test")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")
    monkeypatch.setenv("AWS_LAMBDA_FUNCTION_NAME", "livewell-pipeline-fn-test")


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


# ── Coordinator tests ─────────────────────────────────────────────────────────

def test_coordinator_creates_run_record():
    mock_lambda = MagicMock()
    mock_lambda.invoke.return_value = {"StatusCode": 202}
    with patch("livewell.pipeline.handler.create_run") as mock_create, \
         patch("livewell.pipeline.handler.update_run"), \
         patch("livewell.pipeline.handler._lambda_client", mock_lambda):
        handler({}, None)
    mock_create.assert_called_once()
    run_id, started_at = mock_create.call_args.args
    assert isinstance(run_id, str) and len(run_id) == 36  # uuid4
    assert "T" in started_at and started_at.endswith("+00:00")


def test_coordinator_invokes_one_worker_per_instrument():
    from livewell.ingestion.constants import INSTRUMENTS
    mock_lambda = MagicMock()
    mock_lambda.invoke.return_value = {"StatusCode": 202}
    with patch("livewell.pipeline.handler.create_run"), \
         patch("livewell.pipeline.handler.update_run"), \
         patch("livewell.pipeline.handler._lambda_client", mock_lambda):
        handler({}, None)
    assert mock_lambda.invoke.call_count == len(INSTRUMENTS)


def test_coordinator_passes_s3_key_and_run_id_to_workers():
    mock_lambda = MagicMock()
    mock_lambda.invoke.return_value = {"StatusCode": 202}
    with patch("livewell.pipeline.handler.create_run") as mock_create, \
         patch("livewell.pipeline.handler.update_run"), \
         patch("livewell.pipeline.handler._lambda_client", mock_lambda):
        handler({}, None)
    run_id = mock_create.call_args.args[0]
    first_call_payload = json.loads(
        mock_lambda.invoke.call_args_list[0].kwargs["Payload"]
    )
    assert first_call_payload["run_id"] == run_id
    assert "s3_key" in first_call_payload
    assert first_call_payload["backfill"] is False


def test_coordinator_passes_backfill_flag():
    mock_lambda = MagicMock()
    mock_lambda.invoke.return_value = {"StatusCode": 202}
    with patch("livewell.pipeline.handler.create_run"), \
         patch("livewell.pipeline.handler.update_run"), \
         patch("livewell.pipeline.handler._lambda_client", mock_lambda):
        handler({"backfill": True}, None)
    payload = json.loads(
        mock_lambda.invoke.call_args_list[0].kwargs["Payload"]
    )
    assert payload["backfill"] is True


def test_coordinator_returns_running_status():
    mock_lambda = MagicMock()
    mock_lambda.invoke.return_value = {"StatusCode": 202}
    with patch("livewell.pipeline.handler.create_run"), \
         patch("livewell.pipeline.handler.update_run"), \
         patch("livewell.pipeline.handler._lambda_client", mock_lambda):
        result = handler({}, None)
    assert result["status"] == "dispatched"
    assert "run_id" in result


def test_coordinator_continues_and_records_partial_dispatch_failure():
    from livewell.ingestion.constants import INSTRUMENTS

    call_count = 0
    def invoke_side_effect(**kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RuntimeError("throttled")
        return {"StatusCode": 202}

    mock_lambda = MagicMock()
    mock_lambda.invoke.side_effect = invoke_side_effect
    with patch("livewell.pipeline.handler.create_run"), \
         patch("livewell.pipeline.handler.update_run") as mock_update, \
         patch("livewell.pipeline.handler._lambda_client", mock_lambda):
        result = handler({}, None)

    # All instruments attempted despite first failure
    assert mock_lambda.invoke.call_count == len(INSTRUMENTS)
    # Status reflects partial failure
    assert result["status"] == "dispatch_partial"
    # update_run called with the failed instrument in errors
    update_call = mock_update.call_args
    assert len(update_call.kwargs["errors"]) == 1
    assert update_call.kwargs["status"] == "dispatch_partial"


# ── Worker tests ──────────────────────────────────────────────────────────────

def test_worker_calls_run_instrument_and_puts_signal():
    signal = _make_signal("EURUSD")
    with patch("livewell.pipeline.handler.run_instrument", return_value=signal) as mock_run, \
         patch("livewell.pipeline.handler.put_signal") as mock_put:
        handler({"s3_key": "EURUSD", "run_id": "run-1", "backfill": False}, None)
    mock_run.assert_called_once_with("EURUSD", "run-1", backfill=False)
    mock_put.assert_called_once_with(signal)


def test_worker_raises_on_run_instrument_failure():
    with patch("livewell.pipeline.handler.run_instrument", side_effect=RuntimeError("yfinance down")), \
         patch("livewell.pipeline.handler.put_signal") as mock_put:
        with pytest.raises(RuntimeError, match="yfinance down"):
            handler({"s3_key": "EURUSD", "run_id": "run-1", "backfill": False}, None)
    mock_put.assert_not_called()


def test_worker_returns_signal_id():
    signal = _make_signal("GBPUSD")
    with patch("livewell.pipeline.handler.run_instrument", return_value=signal), \
         patch("livewell.pipeline.handler.put_signal"):
        result = handler({"s3_key": "GBPUSD", "run_id": "run-1", "backfill": False}, None)
    assert result["signal_id"] == signal["signal_id"]
    assert result["s3_key"] == "GBPUSD"

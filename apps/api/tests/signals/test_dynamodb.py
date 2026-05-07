# apps/api/tests/signals/test_dynamodb.py
from __future__ import annotations
import os
from unittest.mock import MagicMock, patch
import pytest


@pytest.fixture(autouse=True)
def env(monkeypatch):
    monkeypatch.setenv("LIVEWELL_ENV", "test")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")


SIGNAL_A = {
    "signal_id": "EURUSD__2026-05-07",
    "s3_key": "EURUSD",
    "date": "2026-05-07",
    "score": "0.71",
}

SIGNAL_B = {
    "signal_id": "EURUSD__2026-05-06",
    "s3_key": "EURUSD",
    "date": "2026-05-06",
    "score": "0.60",
}

SIGNAL_C = {
    "signal_id": "GBPUSD__2026-05-07",
    "s3_key": "GBPUSD",
    "date": "2026-05-07",
    "score": "0.55",
}


def _mock_table(items):
    table = MagicMock()
    table.scan.return_value = {"Items": items}
    return table


def test_get_latest_signals_returns_most_recent_per_instrument():
    with patch("livewell.signals.dynamodb._table", return_value=_mock_table([SIGNAL_A, SIGNAL_B, SIGNAL_C])):
        from livewell.signals.dynamodb import get_latest_signals
        result = get_latest_signals()
    signal_ids = {r["signal_id"] for r in result}
    assert "EURUSD__2026-05-07" in signal_ids
    assert "GBPUSD__2026-05-07" in signal_ids
    assert "EURUSD__2026-05-06" not in signal_ids


def test_get_latest_signals_empty_table():
    with patch("livewell.signals.dynamodb._table", return_value=_mock_table([])):
        from livewell.signals.dynamodb import get_latest_signals
        result = get_latest_signals()
    assert result == []


def test_get_signal_returns_matching_record():
    table = MagicMock()
    table.get_item.return_value = {"Item": SIGNAL_A}
    with patch("livewell.signals.dynamodb._table", return_value=table):
        from livewell.signals.dynamodb import get_signal
        result = get_signal("EURUSD", "2026-05-07")
    assert result is not None
    assert result["signal_id"] == "EURUSD__2026-05-07"


def test_get_signal_returns_none_when_not_found():
    table = MagicMock()
    table.get_item.return_value = {}  # no "Item" key → not found
    with patch("livewell.signals.dynamodb._table", return_value=table):
        from livewell.signals.dynamodb import get_signal
        result = get_signal("EURUSD", "2026-01-01")
    assert result is None


def test_get_latest_signals_returns_empty_on_client_error():
    from botocore.exceptions import ClientError
    table = MagicMock()
    table.scan.side_effect = ClientError(
        {"Error": {"Code": "InternalServerError", "Message": "test"}}, "Scan"
    )
    with patch("livewell.signals.dynamodb._table", return_value=table):
        from livewell.signals.dynamodb import get_latest_signals
        result = get_latest_signals()
    assert result == []


def test_get_signal_returns_none_on_client_error():
    from botocore.exceptions import ClientError
    table = MagicMock()
    table.get_item.side_effect = ClientError(
        {"Error": {"Code": "InternalServerError", "Message": "test"}}, "GetItem"
    )
    with patch("livewell.signals.dynamodb._table", return_value=table):
        from livewell.signals.dynamodb import get_signal
        result = get_signal("EURUSD", "2026-05-07")
    assert result is None

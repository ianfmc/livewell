# apps/api/tests/signals/test_dynamodb.py
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def env(monkeypatch):
    monkeypatch.setenv("LIVEWELL_ENV", "test")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")


SIGNAL_EURUSD = {
    "signal_id": "EURUSD__2026-05-07",
    "s3_key": "EURUSD",
    "date": "2026-05-07",
    "score": "0.71",
}

SIGNAL_GBPUSD = {
    "signal_id": "GBPUSD__2026-05-07",
    "s3_key": "GBPUSD",
    "date": "2026-05-07",
    "score": "0.55",
}


def _query_table(latest_by_key):
    """Build a mock table whose .query returns the latest item for the queried s3_key.

    `latest_by_key` maps s3_key -> item (the instrument's latest). The mock reads
    the s3_key out of the KeyConditionExpression the production code builds with
    Key("s3_key").eq(s3_key), returning {"Items": [item]} or {"Items": []}.
    """
    table = MagicMock()

    def _query(**kwargs):
        cond = kwargs.get("KeyConditionExpression")
        # boto3 Equals condition: values are (Attr, value); grab the s3_key value.
        values = getattr(cond, "_values", ())
        s3_key = values[1] if len(values) > 1 else None
        item = latest_by_key.get(s3_key)
        return {"Items": [item] if item is not None else []}

    table.query.side_effect = _query
    return table


def test_get_latest_signals_returns_most_recent_per_instrument():
    table = _query_table({"EURUSD": SIGNAL_EURUSD, "GBPUSD": SIGNAL_GBPUSD})
    with patch("livewell.signals.dynamodb._table", return_value=table):
        from livewell.signals.dynamodb import get_latest_signals

        result = get_latest_signals()
    signal_ids = {r["signal_id"] for r in result}
    assert "EURUSD__2026-05-07" in signal_ids
    assert "GBPUSD__2026-05-07" in signal_ids


def test_get_latest_signals_skips_instruments_with_no_signals():
    # Only EURUSD has a signal; the other 18 instruments return empty.
    table = _query_table({"EURUSD": SIGNAL_EURUSD})
    with patch("livewell.signals.dynamodb._table", return_value=table):
        from livewell.signals.dynamodb import get_latest_signals

        result = get_latest_signals()
    assert len(result) == 1
    assert result[0]["signal_id"] == "EURUSD__2026-05-07"


def test_get_latest_signals_empty_table():
    table = _query_table({})
    with patch("livewell.signals.dynamodb._table", return_value=table):
        from livewell.signals.dynamodb import get_latest_signals

        result = get_latest_signals()
    assert result == []


def test_get_latest_signal_single_instrument():
    table = _query_table({"EURUSD": SIGNAL_EURUSD})
    with patch("livewell.signals.dynamodb._table", return_value=table):
        from livewell.signals.dynamodb import get_latest_signal

        result = get_latest_signal("EURUSD")
    assert result is not None
    assert result["signal_id"] == "EURUSD__2026-05-07"


def test_get_latest_signal_returns_none_when_absent():
    table = _query_table({})  # no signal for the queried instrument
    with patch("livewell.signals.dynamodb._table", return_value=table):
        from livewell.signals.dynamodb import get_latest_signal

        result = get_latest_signal("EURUSD")
    assert result is None


def test_get_signal_returns_matching_record():
    table = MagicMock()
    table.get_item.return_value = {"Item": SIGNAL_EURUSD}
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
    table.query.side_effect = ClientError({"Error": {"Code": "InternalServerError", "Message": "test"}}, "Query")
    with patch("livewell.signals.dynamodb._table", return_value=table):
        from livewell.signals.dynamodb import get_latest_signals

        result = get_latest_signals()
    assert result == []


def test_get_latest_signal_returns_none_on_client_error():
    from botocore.exceptions import ClientError

    table = MagicMock()
    table.query.side_effect = ClientError({"Error": {"Code": "InternalServerError", "Message": "test"}}, "Query")
    with patch("livewell.signals.dynamodb._table", return_value=table):
        from livewell.signals.dynamodb import get_latest_signal

        result = get_latest_signal("EURUSD")
    assert result is None


def test_get_signal_returns_none_on_client_error():
    from botocore.exceptions import ClientError

    table = MagicMock()
    table.get_item.side_effect = ClientError({"Error": {"Code": "InternalServerError", "Message": "test"}}, "GetItem")
    with patch("livewell.signals.dynamodb._table", return_value=table):
        from livewell.signals.dynamodb import get_signal

        result = get_signal("EURUSD", "2026-05-07")
    assert result is None

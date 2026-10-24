# apps/api/tests/tracking/test_tracking_dynamodb.py
from __future__ import annotations

import boto3
import pytest
from moto import mock_aws

TABLE_TRADES = "livewell-trades-test"


@pytest.fixture(autouse=True)
def aws_env(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")
    monkeypatch.setenv("LIVEWELL_ENV", "test")


@pytest.fixture()
def trades_table():
    with mock_aws():
        ddb = boto3.resource("dynamodb", region_name="us-east-1")
        ddb.create_table(
            TableName=TABLE_TRADES,
            KeySchema=[{"AttributeName": "trade_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "trade_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        yield


def _seed(**overrides):
    rec = {
        "trade_id": "t1",
        "s3_key": "EURUSD",
        "direction": "buy",
        "strike": "1.1000",
        "expiry_time": "2026-05-05T20:00:00Z",
        "status": "open",
    }
    rec.update(overrides)
    return rec


def test_create_and_list_trades(trades_table):
    from livewell.tracking.dynamodb import create_trade, list_trades

    create_trade(_seed(trade_id="a"))
    create_trade(_seed(trade_id="b", status="won"))
    all_trades = list_trades()
    assert {t["trade_id"] for t in all_trades} == {"a", "b"}
    open_only = list_trades(status="open")
    assert [t["trade_id"] for t in open_only] == ["a"]


def test_get_open_trades_due_filters_by_expiry(trades_table):
    from livewell.tracking.dynamodb import create_trade, get_open_trades_due

    create_trade(_seed(trade_id="past", expiry_time="2026-05-05T12:00:00Z"))
    create_trade(_seed(trade_id="future", expiry_time="2026-05-05T23:00:00Z"))
    create_trade(_seed(trade_id="done", status="won", expiry_time="2026-05-05T12:00:00Z"))

    due = get_open_trades_due(as_of="2026-05-05T20:00:00Z")
    ids = {t["trade_id"] for t in due}
    # 'past' is open and expired; 'future' not yet due; 'done' not open
    assert ids == {"past"}


def test_patch_trade_sets_outcome(trades_table):
    from livewell.tracking.dynamodb import create_trade, list_trades, patch_trade

    create_trade(_seed(trade_id="p"))
    patch_trade(
        trade_id="p",
        status="lost",
        outcome_price="1.0950",
        outcome_source="auto",
        resolved_at="2026-05-05T21:00:00Z",
    )
    rec = next(t for t in list_trades() if t["trade_id"] == "p")
    assert rec["status"] == "lost"
    assert rec["outcome_price"] == "1.0950"
    assert rec["outcome_source"] == "auto"
    assert rec["resolved_at"] == "2026-05-05T21:00:00Z"


def test_patch_trade_without_price_omits_field(trades_table):
    from livewell.tracking.dynamodb import create_trade, list_trades, patch_trade

    create_trade(_seed(trade_id="np"))
    patch_trade(
        trade_id="np",
        status="won",
        outcome_price=None,
        outcome_source="manual",
        resolved_at="2026-05-05T21:00:00Z",
    )
    rec = next(t for t in list_trades() if t["trade_id"] == "np")
    assert rec["status"] == "won"
    assert "outcome_price" not in rec

from __future__ import annotations
import io
import os
import boto3
import pandas as pd
import pytest
from moto import mock_aws
from decimal import Decimal

TABLE_SIGNALS = "livewell-signals-test"
BUCKET = "test-bucket"
YEARS = [2026]


@pytest.fixture(autouse=True)
def aws_env(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")
    monkeypatch.setenv("LIVEWELL_ENV", "test")
    monkeypatch.setenv("LIVEWELL_BUCKET", BUCKET)


def _make_parquet(rows: list[dict]) -> bytes:
    df = pd.DataFrame(rows)
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
    buf = io.BytesIO()
    df.to_parquet(buf, index=False)
    return buf.getvalue()


def _signal_rows(direction="call", n=2):
    return [
        {
            "date": f"2026-01-0{i+1}",
            "ema_20": 1.08, "ema_50": 1.07, "rsi_14": 55.0,
            "macd": 0.001, "macd_signal": 0.0009, "macd_hist": 0.0001,
            "atr_14": 0.005, "trend_bias": "bullish",
            "session_quality": "high", "strike_candidate": 1.085,
            "signal_valid": True, "direction": direction,
            "reasoning": "{}", "timing_slot": "slot1", "timing_risk": "low",
        }
        for i in range(n)
    ]


@pytest.fixture()
def aws_resources():
    with mock_aws():
        ddb = boto3.resource("dynamodb", region_name="us-east-1")
        ddb.create_table(
            TableName=TABLE_SIGNALS,
            KeySchema=[{"AttributeName": "signal_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "signal_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket=BUCKET)
        yield ddb, s3


def _put_parquet(s3, s3_key: str, rows: list[dict], year: int = 2026):
    data = _make_parquet(rows)
    s3.put_object(Bucket=BUCKET, Key=f"signals/{s3_key}/1d/{year}.parquet", Body=data)


def test_writes_records_for_directional_rows(aws_resources):
    ddb, s3 = aws_resources
    _put_parquet(s3, "EURUSD", _signal_rows("call", n=2))
    from livewell.pipeline.replay import replay_signals
    result = replay_signals(instruments=["EURUSD"], env="test", bucket=BUCKET)
    assert result["written"] == 2
    assert result["skipped"] == 0
    assert result["failed"] == []
    table = ddb.Table(TABLE_SIGNALS)
    item = table.get_item(Key={"signal_id": "EURUSD__2026-01-01"})["Item"]
    assert item["direction"] == "call"
    assert item["run_id"] == "replay"
    assert item["score"] is None
    assert item["model_version"] is None


def test_skips_rows_with_direction_none(aws_resources):
    ddb, s3 = aws_resources
    rows = _signal_rows("call", n=1) + [
        {**_signal_rows("call", n=1)[0], "date": "2026-01-02", "direction": "none"}
    ]
    _put_parquet(s3, "EURUSD", rows)
    from livewell.pipeline.replay import replay_signals
    result = replay_signals(instruments=["EURUSD"], env="test", bucket=BUCKET)
    assert result["written"] == 1
    assert result["skipped"] == 0


def test_normalises_buy_sell_direction(aws_resources):
    ddb, s3 = aws_resources
    rows = _signal_rows("buy", n=1) + [
        {**_signal_rows("sell", n=1)[0], "date": "2026-01-02", "direction": "sell"}
    ]
    _put_parquet(s3, "EURUSD", rows)
    from livewell.pipeline.replay import replay_signals
    replay_signals(instruments=["EURUSD"], env="test", bucket=BUCKET)
    table = ddb.Table(TABLE_SIGNALS)
    assert table.get_item(Key={"signal_id": "EURUSD__2026-01-01"})["Item"]["direction"] == "call"
    assert table.get_item(Key={"signal_id": "EURUSD__2026-01-02"})["Item"]["direction"] == "put"


def test_skips_existing_signal_ids(aws_resources):
    ddb, s3 = aws_resources
    _put_parquet(s3, "EURUSD", _signal_rows("call", n=2))
    table = ddb.Table(TABLE_SIGNALS)
    table.put_item(Item={"signal_id": "EURUSD__2026-01-01", "run_id": "live"})
    from livewell.pipeline.replay import replay_signals
    result = replay_signals(instruments=["EURUSD"], env="test", bucket=BUCKET)
    assert result["written"] == 1
    assert result["skipped"] == 1
    # Existing record not overwritten
    assert table.get_item(Key={"signal_id": "EURUSD__2026-01-01"})["Item"]["run_id"] == "live"


def test_returns_correct_counts(aws_resources):
    ddb, s3 = aws_resources
    _put_parquet(s3, "EURUSD", _signal_rows("call", n=3))
    table = ddb.Table(TABLE_SIGNALS)
    table.put_item(Item={"signal_id": "EURUSD__2026-01-01", "run_id": "live"})
    from livewell.pipeline.replay import replay_signals
    result = replay_signals(instruments=["EURUSD"], env="test", bucket=BUCKET)
    assert result["written"] == 2
    assert result["skipped"] == 1


def test_dry_run_writes_nothing(aws_resources):
    ddb, s3 = aws_resources
    _put_parquet(s3, "EURUSD", _signal_rows("call", n=2))
    from livewell.pipeline.replay import replay_signals
    result = replay_signals(instruments=["EURUSD"], env="test", bucket=BUCKET, dry_run=True)
    assert result["written"] == 2
    assert result["skipped"] == 0
    table = ddb.Table(TABLE_SIGNALS)
    assert table.scan(Select="COUNT")["Count"] == 0


def test_empty_parquet_produces_no_writes(aws_resources):
    ddb, s3 = aws_resources
    _put_parquet(s3, "EURUSD", [])
    from livewell.pipeline.replay import replay_signals
    result = replay_signals(instruments=["EURUSD"], env="test", bucket=BUCKET)
    assert result["written"] == 0
    assert result["skipped"] == 0


def test_missing_parquet_year_is_skipped(aws_resources):
    ddb, s3 = aws_resources
    # Only put 2025, not 2026 — 2026 key missing → should be skipped, not crash
    _put_parquet(s3, "EURUSD", _signal_rows("call", n=1), year=2025)
    from livewell.pipeline.replay import replay_signals
    result = replay_signals(instruments=["EURUSD"], env="test", bucket=BUCKET)
    assert result["written"] == 1
    assert result["failed"] == []

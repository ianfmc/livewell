from __future__ import annotations
import os
import boto3
import pytest
from moto import mock_aws

TABLE_RUNS = "livewell-model-runs-test"
TABLE_SIGNALS = "livewell-signals-test"


@pytest.fixture(autouse=True)
def aws_env(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")
    monkeypatch.setenv("LIVEWELL_ENV", "test")


@pytest.fixture()
def tables():
    with mock_aws():
        ddb = boto3.resource("dynamodb", region_name="us-east-1")
        ddb.create_table(
            TableName=TABLE_RUNS,
            KeySchema=[
                {"AttributeName": "run_id", "KeyType": "HASH"},
                {"AttributeName": "started_at", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "run_id", "AttributeType": "S"},
                {"AttributeName": "started_at", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        ddb.create_table(
            TableName=TABLE_SIGNALS,
            KeySchema=[{"AttributeName": "signal_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "signal_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        yield ddb


def test_create_run_writes_running_status(tables):
    from livewell.pipeline.dynamodb import create_run
    create_run("run-1", "2026-05-05T00:00:00Z")
    item = tables.Table(TABLE_RUNS).get_item(
        Key={"run_id": "run-1", "started_at": "2026-05-05T00:00:00Z"}
    )["Item"]
    assert item["status"] == "running"
    assert item["instruments"] == []
    assert item["errors"] == []


def test_update_run_writes_final_status(tables):
    from livewell.pipeline.dynamodb import create_run, update_run
    create_run("run-2", "2026-05-05T00:00:00Z")
    update_run(
        run_id="run-2",
        started_at="2026-05-05T00:00:00Z",
        status="completed",
        instruments=["EURUSD", "GBPUSD"],
        errors=[],
        completed_at="2026-05-05T00:05:00Z",
    )
    item = tables.Table(TABLE_RUNS).get_item(
        Key={"run_id": "run-2", "started_at": "2026-05-05T00:00:00Z"}
    )["Item"]
    assert item["status"] == "completed"
    assert item["instruments"] == ["EURUSD", "GBPUSD"]
    assert item["completed_at"] == "2026-05-05T00:05:00Z"


def test_put_signal_writes_record(tables):
    from livewell.pipeline.dynamodb import put_signal
    record = {
        "signal_id": "EURUSD__2026-05-05",
        "s3_key": "EURUSD",
        "run_id": "run-1",
        "date": "2026-05-05",
        "direction": "buy",
        "signal_valid": True,
        "score": None,
        "model_version": None,
        "created_at": "2026-05-05T00:05:00Z",
        "ema_20": "1.08",
        "ema_50": "1.07",
        "rsi_14": "55.0",
        "strike_candidate": "1.0850",
        "timing_slot": "buy_bullish",
        "timing_risk": "moderate",
    }
    put_signal(record)
    item = tables.Table(TABLE_SIGNALS).get_item(
        Key={"signal_id": "EURUSD__2026-05-05"}
    )["Item"]
    assert item["direction"] == "buy"
    assert item["run_id"] == "run-1"

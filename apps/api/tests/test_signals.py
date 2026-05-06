from __future__ import annotations
import os
import boto3
import pytest
from moto import mock_aws
from fastapi.testclient import TestClient


TABLE_SIGNALS = "livewell-signals-test"


@pytest.fixture(autouse=True)
def aws_env(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")
    monkeypatch.setenv("LIVEWELL_ENV", "test")


@pytest.fixture()
def signals_table():
    with mock_aws():
        ddb = boto3.resource("dynamodb", region_name="us-east-1")
        table = ddb.create_table(
            TableName=TABLE_SIGNALS,
            KeySchema=[{"AttributeName": "signal_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "signal_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        table.put_item(Item={
            "signal_id": "EURUSD__2026-05-05",
            "s3_key": "EURUSD",
            "run_id": "run-1",
            "date": "2026-05-05",
            "direction": "buy",
            "signal_valid": True,
            "strike_candidate": "1.0850",
            "timing_slot": "buy_bullish",
            "score": None,
            "model_version": None,
            "created_at": "2026-05-05T00:05:00Z",
        })
        table.put_item(Item={
            "signal_id": "GBPUSD__2026-05-05",
            "s3_key": "GBPUSD",
            "run_id": "run-1",
            "date": "2026-05-05",
            "direction": "none",
            "signal_valid": False,
            "strike_candidate": "",
            "timing_slot": "unscheduled",
            "score": None,
            "model_version": None,
            "created_at": "2026-05-05T00:05:00Z",
        })
        yield table


def test_get_signals_returns_dynamodb_records(signals_table):
    from main import app
    client = TestClient(app)
    response = client.get("/api/signals")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    signal_ids = {d["signalId"] for d in data}
    assert "EURUSD__2026-05-05" in signal_ids


def test_get_signals_returns_empty_list_when_no_data():
    with mock_aws():
        ddb = boto3.resource("dynamodb", region_name="us-east-1")
        ddb.create_table(
            TableName=TABLE_SIGNALS,
            KeySchema=[{"AttributeName": "signal_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "signal_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        from main import app
        client = TestClient(app)
        response = client.get("/api/signals")
        assert response.status_code == 200
        assert response.json() == []


def test_get_signals_returns_empty_list_when_env_not_set(monkeypatch):
    monkeypatch.delenv("LIVEWELL_ENV", raising=False)
    from main import app
    client = TestClient(app)
    response = client.get("/api/signals")
    assert response.status_code == 200
    assert response.json() == []


def test_signal_valid_false_maps_to_invalid_status(signals_table):
    from main import app
    client = TestClient(app)
    response = client.get("/api/signals")
    assert response.status_code == 200
    data = response.json()
    gbpusd = next(d for d in data if d["signalId"] == "GBPUSD__2026-05-05")
    assert gbpusd["status"] == "Invalid"


def test_get_signal_detail_eur_usd():
    from main import app
    client = TestClient(app)
    response = client.get("/api/signals/EUR-USD/1.0850")
    assert response.status_code == 200
    data = response.json()
    assert data["recommendation"] == "Take"


def test_get_signal_detail_not_found():
    from main import app
    client = TestClient(app)
    response = client.get("/api/signals/EUR-USD/9.9999")
    assert response.status_code == 404

from __future__ import annotations
import json
import os
import unittest.mock

import pytest
from fastapi.testclient import TestClient
from moto import mock_aws

from main import app

client = TestClient(app)

_MOCK_SUMMARY = {
    "totalTrades": 84,
    "winRate": 0.61,
    "avgEdge": 0.14,
    "maxDrawdown": -0.09,
    "equityCurve": [
        {"date": "2026-03-01", "value": 1000},
        {"date": "2026-03-03", "value": 1018},
        {"date": "2026-03-05", "value": 1009},
        {"date": "2026-03-07", "value": 1031},
        {"date": "2026-03-10", "value": 1024},
        {"date": "2026-03-12", "value": 1047},
        {"date": "2026-03-14", "value": 1039},
        {"date": "2026-03-17", "value": 1062},
        {"date": "2026-03-19", "value": 1055},
        {"date": "2026-03-21", "value": 1078},
        {"date": "2026-03-24", "value": 1070},
        {"date": "2026-03-26", "value": 1093},
        {"date": "2026-03-28", "value": 1085},
        {"date": "2026-03-31", "value": 1108},
        {"date": "2026-04-02", "value": 1099},
        {"date": "2026-04-04", "value": 1122},
        {"date": "2026-04-07", "value": 1113},
        {"date": "2026-04-09", "value": 1136},
        {"date": "2026-04-11", "value": 1128},
        {"date": "2026-04-14", "value": 1151},
        {"date": "2026-04-16", "value": 1143},
        {"date": "2026-04-18", "value": 1134},
        {"date": "2026-04-19", "value": 1157},
        {"date": "2026-04-20", "value": 1149},
        {"date": "2026-04-21", "value": 1172},
        {"date": "2026-04-22", "value": 1163},
        {"date": "2026-04-23", "value": 1186},
        {"date": "2026-04-24", "value": 1177},
        {"date": "2026-04-25", "value": 1200},
        {"date": "2026-04-26", "value": 1191},
    ],
    "rows": [
        {"market": "EUR/USD", "regime": "Bullish", "expiryWindow": "2-hour", "trades": 18, "winRate": 0.67, "avgEdge": 0.18, "netReturn": 0.21},
        {"market": "EUR/USD", "regime": "Bearish", "expiryWindow": "2-hour", "trades": 12, "winRate": 0.58, "avgEdge": 0.11, "netReturn": 0.09},
        {"market": "GBP/USD", "regime": "Bullish", "expiryWindow": "Daily",  "trades": 15, "winRate": 0.60, "avgEdge": 0.14, "netReturn": 0.12},
        {"market": "GBP/USD", "regime": "Bearish", "expiryWindow": "Daily",  "trades": 11, "winRate": 0.55, "avgEdge": 0.09, "netReturn": 0.06},
        {"market": "USD/JPY", "regime": "Bullish", "expiryWindow": "2-hour", "trades": 16, "winRate": 0.63, "avgEdge": 0.15, "netReturn": 0.14},
        {"market": "USD/JPY", "regime": "Bearish", "expiryWindow": "Daily",  "trades": 12, "winRate": 0.50, "avgEdge": 0.08, "netReturn": 0.02},
    ],
}

_BUCKET = "test-livewell-bucket"


@pytest.fixture()
def s3_with_summary(monkeypatch):
    """Spin up a moto S3 bucket pre-loaded with a valid summary.json."""
    monkeypatch.setenv("LIVEWELL_BUCKET", _BUCKET)
    with mock_aws():
        import boto3
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket=_BUCKET)
        s3.put_object(
            Bucket=_BUCKET,
            Key="backtest/summary.json",
            Body=json.dumps(_MOCK_SUMMARY),
        )
        yield


def test_backtest_summary_returns_200(s3_with_summary):
    response = client.get("/api/backtest/summary")
    assert response.status_code == 200


def test_backtest_summary_shape(s3_with_summary):
    response = client.get("/api/backtest/summary")
    data = response.json()
    assert data["totalTrades"] == 84
    assert len(data["rows"]) == 6
    assert len(data["equityCurve"]) == 30


def test_backtest_summary_no_bucket(monkeypatch):
    monkeypatch.delenv("LIVEWELL_BUCKET", raising=False)
    response = client.get("/api/backtest/summary")
    assert response.status_code == 500
    assert "LIVEWELL_BUCKET" in response.json()["detail"]


def test_backtest_summary_missing_key(monkeypatch):
    monkeypatch.setenv("LIVEWELL_BUCKET", _BUCKET)
    with mock_aws():
        import boto3
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket=_BUCKET)
        # do NOT put the summary object — key is absent
        response = client.get("/api/backtest/summary")
        assert response.status_code == 404
        assert "not been run" in response.json()["detail"]


def test_backtest_summary_signal_valid_split(monkeypatch):
    monkeypatch.setenv("LIVEWELL_BUCKET", _BUCKET)
    summary_with_split = {**_MOCK_SUMMARY, "signalValidSplit": {
        "valid": {"trades": 60, "winRate": 0.68},
        "invalid": {"trades": 24, "winRate": 0.42},
    }}
    with mock_aws():
        import boto3
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket=_BUCKET)
        s3.put_object(
            Bucket=_BUCKET,
            Key="backtest/summary.json",
            Body=json.dumps(summary_with_split),
        )
        response = client.get("/api/backtest/summary")
    assert response.status_code == 200
    split = response.json()["signalValidSplit"]
    assert split["valid"]["trades"] == 60
    assert split["invalid"]["winRate"] == pytest.approx(0.42)

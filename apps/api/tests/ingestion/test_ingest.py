import os
from datetime import date, timedelta
from unittest.mock import patch, MagicMock

import boto3
import pandas as pd
import pytest
from moto import mock_aws

from livewell.ingestion.ingest import fetch_ohlcv, merge_and_dedup, run_ingestion
from livewell.ingestion.constants import INSTRUMENTS


def make_ohlcv(dates: list[str]) -> pd.DataFrame:
    n = len(dates)
    return pd.DataFrame({
        "date":   pd.to_datetime(dates),
        "open":   [1.0] * n,
        "high":   [1.1] * n,
        "low":    [0.9] * n,
        "close":  [1.05] * n,
        "volume": [1000.0] * n,
    })


BUCKET = "test-livewell"


@pytest.fixture()
def s3_bucket():
    with mock_aws():
        boto3.client("s3", region_name="us-east-1").create_bucket(Bucket=BUCKET)
        yield


# --- fetch_ohlcv ---

def test_fetch_ohlcv_returns_dataframe():
    mock_ticker = MagicMock()
    mock_ticker.history.return_value = pd.DataFrame({
        "Open": [1.0], "High": [1.1], "Low": [0.9], "Close": [1.05], "Volume": [1000.0]
    }, index=pd.to_datetime(["2026-04-22"]))
    with patch("livewell.ingestion.ingest.yf.Ticker", return_value=mock_ticker):
        df = fetch_ohlcv("EURUSD=X", interval="1d", lookback_days=7)
    assert list(df.columns) == ["date", "open", "high", "low", "close", "volume"]
    assert len(df) == 1


def test_fetch_ohlcv_returns_none_on_empty():
    mock_ticker = MagicMock()
    mock_ticker.history.return_value = pd.DataFrame()
    with patch("livewell.ingestion.ingest.yf.Ticker", return_value=mock_ticker):
        result = fetch_ohlcv("EURUSD=X", interval="1d", lookback_days=7)
    assert result is None


def test_fetch_ohlcv_schema():
    mock_ticker = MagicMock()
    mock_ticker.history.return_value = pd.DataFrame({
        "Open": [1.0], "High": [1.1], "Low": [0.9], "Close": [1.05], "Volume": [1000.0]
    }, index=pd.to_datetime(["2026-04-22"]))
    with patch("livewell.ingestion.ingest.yf.Ticker", return_value=mock_ticker):
        df = fetch_ohlcv("EURUSD=X", interval="1d", lookback_days=7)
    assert list(df.columns) == ["date", "open", "high", "low", "close", "volume"]
    for col in ["open", "high", "low", "close", "volume"]:
        assert df[col].dtype == float, f"{col} should be float, got {df[col].dtype}"


# --- merge_and_dedup ---

def test_merge_and_dedup_appends_new_rows():
    existing = make_ohlcv(["2026-04-20", "2026-04-21"])
    new = make_ohlcv(["2026-04-21", "2026-04-22"])
    result = merge_and_dedup(existing, new)
    assert len(result) == 3
    assert list(result["date"].dt.strftime("%Y-%m-%d")) == ["2026-04-20", "2026-04-21", "2026-04-22"]


def test_merge_and_dedup_idempotent():
    existing = make_ohlcv(["2026-04-20", "2026-04-21"])
    result = merge_and_dedup(existing, existing)
    assert len(result) == 2


def test_merge_and_dedup_with_no_existing():
    new = make_ohlcv(["2026-04-21", "2026-04-22"])
    result = merge_and_dedup(None, new)
    assert len(result) == 2


# --- run_ingestion ---

def test_run_ingestion_writes_to_s3(s3_bucket):
    mock_ticker = MagicMock()
    mock_ticker.history.return_value = pd.DataFrame({
        "Open": [1.0], "High": [1.1], "Low": [0.9], "Close": [1.05], "Volume": [1000.0]
    }, index=pd.to_datetime(["2026-04-22"]))

    with patch("livewell.ingestion.ingest.yf.Ticker", return_value=mock_ticker):
        with patch("livewell.ingestion.ingest.run_features"):
            with patch.dict("os.environ", {"LIVEWELL_BUCKET": BUCKET}):
                result = run_ingestion(instruments=["EURUSD"])

    assert result["succeeded"] == ["EURUSD"]
    assert result["failed"] == []


def test_run_ingestion_isolates_failures(s3_bucket):
    def ticker_side_effect(ticker_symbol):
        mock = MagicMock()
        if ticker_symbol == "GBPUSD=X":
            mock.history.side_effect = RuntimeError("network error")
        else:
            mock.history.return_value = pd.DataFrame({
                "Open": [1.0], "High": [1.1], "Low": [0.9], "Close": [1.05], "Volume": [1000.0]
            }, index=pd.to_datetime(["2026-04-22"]))
        return mock

    with patch("livewell.ingestion.ingest.yf.Ticker", side_effect=ticker_side_effect):
        with patch("livewell.ingestion.ingest.run_features"):
            with patch.dict("os.environ", {"LIVEWELL_BUCKET": BUCKET}):
                result = run_ingestion(instruments=["EURUSD", "GBPUSD"])

    assert "EURUSD" in result["succeeded"]
    assert "GBPUSD" in result["failed"]


def test_run_ingestion_backfill_uses_longer_lookback(s3_bucket):
    call_kwargs = {}

    def ticker_side_effect(ticker_symbol):
        mock = MagicMock()
        def history_capture(**kwargs):
            call_kwargs.update(kwargs)
            return pd.DataFrame({
                "Open": [1.0], "High": [1.1], "Low": [0.9], "Close": [1.05], "Volume": [1000.0]
            }, index=pd.to_datetime(["2026-04-22"]))
        mock.history.side_effect = history_capture
        return mock

    with patch("livewell.ingestion.ingest.yf.Ticker", side_effect=ticker_side_effect):
        with patch("livewell.ingestion.ingest.run_features"):
            with patch.dict("os.environ", {"LIVEWELL_BUCKET": BUCKET}):
                run_ingestion(instruments=["EURUSD"], backfill=True)

    start = call_kwargs.get("start")
    end = call_kwargs.get("end")
    assert start is not None and end is not None
    delta = end - start
    assert delta.days >= 365 * 2 - 5  # at least ~2 years lookback


def test_ingestion_triggers_features(s3_bucket):
    mock_ticker = MagicMock()
    mock_ticker.history.return_value = pd.DataFrame({
        "Open": [1.0], "High": [1.1], "Low": [0.9], "Close": [1.05], "Volume": [1000.0]
    }, index=pd.to_datetime(["2026-04-22"]))

    with patch("livewell.ingestion.ingest.yf.Ticker", return_value=mock_ticker):
        with patch("livewell.ingestion.ingest.run_features") as mock_run_features:
            with patch.dict("os.environ", {"LIVEWELL_BUCKET": BUCKET}):
                run_ingestion(instruments=["EURUSD"])

    mock_run_features.assert_called_once_with(instruments=["EURUSD"])

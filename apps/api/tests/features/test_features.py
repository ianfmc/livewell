import numpy as np
from unittest.mock import patch
import boto3
import pandas as pd
import pytest
from moto import mock_aws

from livewell.features.constants import FEATURE_COLUMNS, PRICES_PREFIX, FEATURES_PREFIX, COLUMN_RENAMES


def test_feature_columns():
    assert FEATURE_COLUMNS == ["date", "ema_20", "ema_50", "rsi_14", "macd", "macd_hist", "macd_signal", "atr_14"]


def test_prefixes():
    assert PRICES_PREFIX == "prices"
    assert FEATURES_PREFIX == "features"


def test_column_renames_maps_all_indicators():
    expected_targets = {"ema_20", "ema_50", "rsi_14", "macd", "macd_hist", "macd_signal", "atr_14"}
    assert set(COLUMN_RENAMES.values()) == expected_targets


from livewell.features.features import _compute_indicators


def make_price_df(n: int = 60) -> pd.DataFrame:
    """Generate n rows of synthetic OHLCV with a gentle uptrend."""
    dates = pd.date_range("2025-01-01", periods=n, freq="D")
    close = [1.0 + i * 0.001 for i in range(n)]
    return pd.DataFrame({
        "date":   dates,
        "open":   [c - 0.0005 for c in close],
        "high":   [c + 0.002  for c in close],
        "low":    [c - 0.002  for c in close],
        "close":  close,
        "volume": [1000.0] * n,
    })


def test_compute_indicators_returns_expected_columns():
    df = make_price_df(60)
    result = _compute_indicators(df)
    assert list(result.columns) == ["date", "ema_20", "ema_50", "rsi_14", "macd", "macd_hist", "macd_signal", "atr_14"]


def test_ema_20_known_value():
    df = make_price_df(60)
    result = _compute_indicators(df)
    last_ema = result["ema_20"].iloc[-1]
    last_close = df["close"].iloc[-1]
    assert not np.isnan(last_ema)
    assert abs(last_ema - last_close) < 0.01


def test_ema_50_requires_50_rows():
    df = make_price_df(60)
    result = _compute_indicators(df)
    assert result["ema_50"].iloc[:49].isna().all()
    assert not np.isnan(result["ema_50"].iloc[-1])


def test_rsi_14_bounded():
    df = make_price_df(60)
    result = _compute_indicators(df)
    valid = result["rsi_14"].dropna()
    assert (valid >= 0).all() and (valid <= 100).all()


def test_macd_columns_present_and_converge():
    df = make_price_df(60)
    result = _compute_indicators(df)
    for col in ["macd", "macd_hist", "macd_signal"]:
        assert not np.isnan(result[col].iloc[-1]), f"{col} is NaN at end"


def test_atr_14_positive():
    df = make_price_df(60)
    result = _compute_indicators(df)
    valid = result["atr_14"].dropna()
    assert (valid > 0).all()


from livewell.features.features import run_features
from livewell.ingestion.s3 import write_parquet as write_prices


BUCKET = "test-livewell"


@pytest.fixture()
def s3_bucket():
    with mock_aws():
        boto3.client("s3", region_name="us-east-1").create_bucket(Bucket=BUCKET)
        yield


def make_price_parquet(bucket: str, s3_key: str, interval: str, year: int, n: int = 60):
    """Write synthetic price Parquet to mocked S3."""
    dates = pd.date_range(f"{year}-01-01", periods=n, freq="D")
    close = [1.0 + i * 0.001 for i in range(n)]
    df = pd.DataFrame({
        "date":   dates,
        "open":   [c - 0.0005 for c in close],
        "high":   [c + 0.002  for c in close],
        "low":    [c - 0.002  for c in close],
        "close":  close,
        "volume": [1000.0] * n,
    })
    key = f"prices/{s3_key}/{interval}/{year}.parquet"
    write_prices(df, bucket, key)


def test_run_features_writes_to_s3(s3_bucket):
    make_price_parquet(BUCKET, "EURUSD", "1d", 2026, n=60)

    with patch.dict("os.environ", {"LIVEWELL_BUCKET": BUCKET}):
        result = run_features(instruments=["EURUSD"], intervals=["1d"])

    assert result["succeeded"] == ["EURUSD"]
    assert result["failed"] == []

    s3 = boto3.client("s3", region_name="us-east-1")
    resp = s3.list_objects_v2(Bucket=BUCKET, Prefix="features/EURUSD/1d/")
    keys = [obj["Key"] for obj in resp.get("Contents", [])]
    assert any("2026.parquet" in k for k in keys)


def test_run_features_output_schema(s3_bucket):
    make_price_parquet(BUCKET, "EURUSD", "1d", 2026, n=60)

    with patch.dict("os.environ", {"LIVEWELL_BUCKET": BUCKET}):
        run_features(instruments=["EURUSD"], intervals=["1d"])

    from livewell.ingestion.s3 import read_parquet
    df = read_parquet(BUCKET, "features/EURUSD/1d/2026.parquet")
    assert df is not None
    assert list(df.columns) == ["date", "ema_20", "ema_50", "rsi_14", "macd", "macd_hist", "macd_signal", "atr_14"]


def test_run_features_isolates_failures(s3_bucket):
    make_price_parquet(BUCKET, "EURUSD", "1d", 2026, n=60)

    original_features_one = __import__(
        "livewell.features.features", fromlist=["_features_one"]
    )._features_one

    def failing_features_one(instrument, interval, bucket):
        if instrument["s3_key"] == "GBPUSD":
            raise RuntimeError("simulated failure")
        return original_features_one(instrument, interval, bucket)

    with patch("livewell.features.features._features_one", side_effect=failing_features_one):
        with patch.dict("os.environ", {"LIVEWELL_BUCKET": BUCKET}):
            result = run_features(instruments=["EURUSD", "GBPUSD"], intervals=["1d"])

    assert "EURUSD" in result["succeeded"]
    assert "GBPUSD" in result["failed"]

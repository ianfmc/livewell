import json

import pandas as pd
from livewell.signals.constants import SIGNAL_COLUMNS
from livewell.signals.signals import _apply_pipeline, _session_quality


def test_signal_columns_defined():
    expected = [
        "date", "ema_20", "ema_50", "rsi_14",
        "macd", "macd_signal", "macd_hist", "atr_14",
        "trend_bias", "session_quality", "strike_candidate",
        "signal_valid", "direction", "reasoning",
    ]
    assert SIGNAL_COLUMNS == expected


def test_session_filter_low_quality():
    # EUR/USD row at 03:00 UTC → Asian session → low
    ts = pd.Timestamp("2026-01-15 03:00:00", tz="UTC")
    assert _session_quality("EURUSD", ts) == "low"


def test_session_filter_high_quality_london():
    ts = pd.Timestamp("2026-01-15 09:00:00", tz="UTC")
    assert _session_quality("EURUSD", ts) == "high"


def test_session_filter_jpy_asian_high():
    # USD/JPY Asian session (03:00 UTC) → high
    ts = pd.Timestamp("2026-01-15 03:00:00", tz="UTC")
    assert _session_quality("USDJPY", ts) == "high"


def test_session_filter_equity_ny_high():
    # US500 at 14:00 UTC → NY hours → high
    ts = pd.Timestamp("2026-01-15 14:00:00", tz="UTC")
    assert _session_quality("US500", ts) == "high"


def test_session_filter_equity_off_hours_low():
    # US500 at 03:00 UTC → low
    ts = pd.Timestamp("2026-01-15 03:00:00", tz="UTC")
    assert _session_quality("US500", ts) == "low"


def _bullish_row(rsi=55.0, close=1.1000, atr=0.0015, hour=9):
    return {
        "date": pd.Timestamp(f"2026-01-15 {hour:02d}:00:00", tz="UTC"),
        "ema_20": 1.1010, "ema_50": 1.1000,
        "rsi_14": rsi, "macd": 0.0005, "macd_signal": 0.0003, "macd_hist": 0.0002,
        "atr_14": atr, "close": close,
    }


def _bearish_row(rsi=45.0, close=1.1000, atr=0.0015, hour=9):
    return {
        "date": pd.Timestamp(f"2026-01-15 {hour:02d}:00:00", tz="UTC"),
        "ema_20": 1.0990, "ema_50": 1.1000,
        "rsi_14": rsi, "macd": -0.0005, "macd_signal": -0.0003, "macd_hist": -0.0002,
        "atr_14": atr, "close": close,
    }


def test_bullish_setup_valid():
    row = _bullish_row()
    result = _apply_pipeline("EURUSD", row)
    assert result["signal_valid"] is True
    assert result["direction"] == "buy"
    assert result["trend_bias"] == "bullish"


def test_bearish_setup_valid():
    row = _bearish_row()
    result = _apply_pipeline("EURUSD", row)
    assert result["signal_valid"] is True
    assert result["direction"] == "sell"
    assert result["trend_bias"] == "bearish"


def test_neutral_trend_invalid():
    row = _bullish_row()
    row["ema_20"] = row["ema_50"] = 1.1000  # equal → neutral
    result = _apply_pipeline("EURUSD", row)
    assert result["signal_valid"] is False
    assert result["direction"] == "none"
    assert result["trend_bias"] == "neutral"


def test_overextension_invalidates_signal():
    row = _bullish_row(rsi=80.0)  # rsi > 75 = overbought
    result = _apply_pipeline("EURUSD", row)
    assert result["signal_valid"] is False


def test_low_atr_invalidates_signal():
    row = _bullish_row(atr=0.0005)  # below MIN_ATR_THRESHOLD["EURUSD"]=0.0010
    result = _apply_pipeline("EURUSD", row)
    assert result["signal_valid"] is False


def test_strike_candidate_bullish():
    row = _bullish_row(close=1.1000, atr=0.0020)
    result = _apply_pipeline("EURUSD", row)
    # 1.1000 + 0.0020 * 0.5 = 1.1010, rounded to 4 dp
    assert result["strike_candidate"] == round(1.1000 + 0.0020 * 0.5, 4)


def test_strike_candidate_bearish():
    row = _bearish_row(close=1.1000, atr=0.0020)
    result = _apply_pipeline("EURUSD", row)
    assert result["strike_candidate"] == round(1.1000 - 0.0020 * 0.5, 4)


def test_reasoning_completeness():
    # A bearish row invalidated by overextension should mention the failing condition
    row = _bearish_row(rsi=20.0)  # rsi < 25 = oversold, should fail stage 3
    result = _apply_pipeline("EURUSD", row)
    reasons = json.loads(result["reasoning"])
    assert isinstance(reasons, list)
    assert any("oversold" in r.lower() or "overextension" in r.lower() for r in reasons)


import boto3
import pytest
from moto import mock_aws
from unittest.mock import patch
from livewell.signals.signals import run_signals
from livewell.ingestion.s3 import write_parquet as _write

BUCKET = "test-livewell"


@pytest.fixture()
def s3_bucket():
    with mock_aws():
        boto3.client("s3", region_name="us-east-1").create_bucket(Bucket=BUCKET)
        yield


def _write_feature_parquet(bucket, s3_key, interval, year, n=60):
    """Write minimal feature Parquet (all columns, gentle bullish trend)."""
    dates = pd.date_range(f"{year}-01-02", periods=n, freq="B")
    # Force all timestamps to London-open UTC hour (09:00) for high session quality
    dates = pd.DatetimeIndex([d.replace(hour=9) for d in dates]).tz_localize("UTC")
    base = 1.1000
    ema_20 = [base + i * 0.0001 for i in range(n)]
    ema_50 = [base - 0.005 + i * 0.00005 for i in range(n)]
    df = pd.DataFrame({
        "date":        dates,
        "ema_20":      ema_20,
        "ema_50":      ema_50,
        "rsi_14":      [55.0] * n,
        "macd":        [0.0005] * n,
        "macd_signal": [0.0003] * n,
        "macd_hist":   [0.0002] * n,
        "atr_14":      [0.0015] * n,
    })
    key = f"features/{s3_key}/{interval}/{year}.parquet"
    _write(df, bucket, key)


def _write_price_parquet(bucket, s3_key, interval, year, n=60):
    """Write minimal price Parquet (date + close columns)."""
    dates = pd.date_range(f"{year}-01-02", periods=n, freq="B")
    dates = pd.DatetimeIndex([d.replace(hour=9) for d in dates]).tz_localize("UTC")
    df = pd.DataFrame({
        "date":  dates,
        "open":  [1.0990] * n,
        "high":  [1.1020] * n,
        "low":   [1.0980] * n,
        "close": [1.1000] * n,
        "volume":[1000.0] * n,
    })
    key = f"prices/{s3_key}/{interval}/{year}.parquet"
    _write(df, bucket, key)


def test_run_signals_writes_to_s3(s3_bucket):
    _write_feature_parquet(BUCKET, "EURUSD", "1d", 2026)
    _write_price_parquet(BUCKET, "EURUSD", "1d", 2026)

    with patch.dict("os.environ", {"LIVEWELL_BUCKET": BUCKET}):
        result = run_signals(instruments=["EURUSD"], intervals=["1d"])

    assert result["succeeded"] == ["EURUSD"]
    assert result["failed"] == []

    s3 = boto3.client("s3", region_name="us-east-1")
    resp = s3.list_objects_v2(Bucket=BUCKET, Prefix="signals/EURUSD/1d/")
    keys = [obj["Key"] for obj in resp.get("Contents", [])]
    assert any("2026.parquet" in k for k in keys)


def test_run_signals_output_schema(s3_bucket):
    _write_feature_parquet(BUCKET, "EURUSD", "1d", 2026)
    _write_price_parquet(BUCKET, "EURUSD", "1d", 2026)

    with patch.dict("os.environ", {"LIVEWELL_BUCKET": BUCKET}):
        run_signals(instruments=["EURUSD"], intervals=["1d"])

    from livewell.ingestion.s3 import read_parquet
    df = read_parquet(BUCKET, "signals/EURUSD/1d/2026.parquet")
    assert df is not None
    assert list(df.columns) == [
        "date", "ema_20", "ema_50", "rsi_14",
        "macd", "macd_signal", "macd_hist", "atr_14",
        "trend_bias", "session_quality", "strike_candidate",
        "signal_valid", "direction", "reasoning",
    ]


def test_run_signals_idempotent(s3_bucket):
    _write_feature_parquet(BUCKET, "EURUSD", "1d", 2026)
    _write_price_parquet(BUCKET, "EURUSD", "1d", 2026)

    with patch.dict("os.environ", {"LIVEWELL_BUCKET": BUCKET}):
        run_signals(instruments=["EURUSD"], intervals=["1d"])
        run_signals(instruments=["EURUSD"], intervals=["1d"])

    from livewell.ingestion.s3 import read_parquet
    df = read_parquet(BUCKET, "signals/EURUSD/1d/2026.parquet")
    assert df is not None
    assert not df.duplicated(subset=["date"]).any()


def test_run_signals_isolates_failures(s3_bucket):
    _write_feature_parquet(BUCKET, "EURUSD", "1d", 2026)
    _write_price_parquet(BUCKET, "EURUSD", "1d", 2026)
    # GBPUSD: write features but NO prices → inner join → empty → error
    _write_feature_parquet(BUCKET, "GBPUSD", "1d", 2026)

    with patch.dict("os.environ", {"LIVEWELL_BUCKET": BUCKET}):
        result = run_signals(instruments=["EURUSD", "GBPUSD"], intervals=["1d"])

    assert "EURUSD" in result["succeeded"]
    assert "GBPUSD" in result["failed"]


def test_multi_year_continuity(s3_bucket):
    _write_feature_parquet(BUCKET, "EURUSD", "1d", 2025, n=60)
    _write_feature_parquet(BUCKET, "EURUSD", "1d", 2026, n=60)
    _write_price_parquet(BUCKET, "EURUSD", "1d", 2025, n=60)
    _write_price_parquet(BUCKET, "EURUSD", "1d", 2026, n=60)

    with patch.dict("os.environ", {"LIVEWELL_BUCKET": BUCKET}):
        run_signals(instruments=["EURUSD"], intervals=["1d"])

    from livewell.ingestion.s3 import read_parquet
    df_2025 = read_parquet(BUCKET, "signals/EURUSD/1d/2025.parquet")
    df_2026 = read_parquet(BUCKET, "signals/EURUSD/1d/2026.parquet")
    assert df_2025 is not None and len(df_2025) > 0
    assert df_2026 is not None and len(df_2026) > 0
    # No NaN bleed: trend_bias column has no nulls in valid rows
    for df in [df_2025, df_2026]:
        assert df["trend_bias"].notna().all()

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

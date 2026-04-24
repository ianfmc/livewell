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

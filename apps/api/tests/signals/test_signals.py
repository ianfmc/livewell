import pandas as pd
from livewell.signals.constants import SIGNAL_COLUMNS
from livewell.signals.signals import _session_quality


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

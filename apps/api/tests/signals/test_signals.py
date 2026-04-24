from livewell.signals.constants import SIGNAL_COLUMNS


def test_signal_columns_defined():
    expected = [
        "date", "ema_20", "ema_50", "rsi_14",
        "macd", "macd_signal", "macd_hist", "atr_14",
        "trend_bias", "session_quality", "strike_candidate",
        "signal_valid", "direction", "reasoning",
    ]
    assert SIGNAL_COLUMNS == expected

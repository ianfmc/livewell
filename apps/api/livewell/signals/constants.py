"""Thresholds, session windows, pip precision, and output column list for signal generation."""

SIGNALS_PREFIX = "signals"

SIGNAL_COLUMNS = [
    "date", "ema_20", "ema_50", "rsi_14",
    "macd", "macd_signal", "macd_hist", "atr_14",
    "trend_bias", "session_quality", "strike_candidate",
    "signal_valid", "direction", "reasoning",
]

RSI_BULLISH_MIN = 50
RSI_BEARISH_MAX = 50
RSI_OVERBOUGHT = 75
RSI_OVERSOLD = 25
ATR_FEASIBILITY_MULTIPLIER = 0.5

PIP_PRECISION = {
    # Existing
    "EURUSD": 4,
    "GBPUSD": 4,
    "USDJPY": 2,
    "XAUUSD": 1,
    "US500":  0,
    # New — Futures
    "CL":    2,
    "NG":    3,
    "NQ":    0,
    "RTY":   0,
    "YM":    0,
    "NKD":   0,
    # New — Forex
    "AUDUSD": 4,
    "AUDJPY": 2,
    "EURJPY": 2,
    "EURGBP": 4,
    "GBPJPY": 2,
    "USDCAD": 4,
    "USDCHF": 4,
    "USDMXN": 4,
}

MIN_ATR_THRESHOLD = {
    # Existing
    "EURUSD": 0.0010,
    "GBPUSD": 0.0010,
    "USDJPY": 0.10,
    "XAUUSD": 1.0,
    "US500":  5.0,
    # New — Futures
    "CL":    0.40,
    "NG":    0.070,
    "NQ":    20.0,
    "RTY":   15.0,
    "YM":    25.0,
    "NKD":   50.0,
    # New — Forex
    "AUDUSD": 0.0012,
    "AUDJPY": 0.15,
    "EURJPY": 0.18,
    "EURGBP": 0.0008,
    "GBPJPY": 0.20,
    "USDCAD": 0.0011,
    "USDCHF": 0.0009,
    "USDMXN": 0.035,
}

# Session windows: list of (start_hour_utc, end_hour_utc, quality)
# Hours are UTC. end_hour < start_hour means the window crosses midnight.
_FOREX_MAJOR_SESSIONS = [
    (12, 16, "high"),    # London/NY overlap
    (7,  12, "high"),    # London open
    (16, 21, "medium"),  # NY afternoon
    (21, 23, "low"),
    (23,  7, "low"),     # Asian (low for non-JPY majors)
]

_JPY_SESSIONS = [
    (12, 16, "high"),
    (7,  12, "high"),
    (16, 21, "medium"),
    (21, 23, "low"),
    (23,  7, "high"),    # Tokyo session = high for JPY pairs
]

_EQUITY_SESSIONS = [
    (12, 21, "high"),    # NY hours
    # all other hours = low
]

_COMMODITY_SESSIONS = [
    (8,  12, "high"),    # Early NY morning ramp-up
    (12, 21, "high"),    # NYMEX primary session
    (21, 23, "low"),
    (23,  8, "medium"),  # Overnight continuous contract
]

_ASIAN_EQUITY_SESSIONS = [
    (23,  7, "high"),    # Tokyo session (08:00–15:00 JST = 23:00–07:00 UTC)
    (7,  12, "medium"),  # European overlap
    (12, 21, "low"),     # NY hours (illiquid for Nikkei)
    (21, 23, "low"),
]

_EMERGING_SESSIONS = [
    (12, 16, "high"),    # London/NY overlap
    (7,  12, "medium"),  # London session
    (16, 21, "high"),    # NY afternoon (MXN markets active)
    (21, 23, "low"),
    (23,  7, "low"),
]

SESSION_CONFIG = {
    # Existing
    "EURUSD": _FOREX_MAJOR_SESSIONS,
    "GBPUSD": _FOREX_MAJOR_SESSIONS,
    "USDJPY": _JPY_SESSIONS,
    "XAUUSD": _EQUITY_SESSIONS,
    "US500":  _EQUITY_SESSIONS,
    # New — Futures
    "CL":    _COMMODITY_SESSIONS,
    "NG":    _COMMODITY_SESSIONS,
    "NQ":    _EQUITY_SESSIONS,
    "RTY":   _EQUITY_SESSIONS,
    "YM":    _EQUITY_SESSIONS,
    "NKD":   _ASIAN_EQUITY_SESSIONS,
    # New — Forex
    "AUDUSD": _FOREX_MAJOR_SESSIONS,
    "AUDJPY": _JPY_SESSIONS,
    "EURJPY": _JPY_SESSIONS,
    "EURGBP": _FOREX_MAJOR_SESSIONS,
    "GBPJPY": _JPY_SESSIONS,
    "USDCAD": _FOREX_MAJOR_SESSIONS,
    "USDCHF": _FOREX_MAJOR_SESSIONS,
    "USDMXN": _EMERGING_SESSIONS,
}

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
    "EURUSD": 4,
    "GBPUSD": 4,
    "USDJPY": 2,
    "XAUUSD": 1,
    "US500":  0,
}

MIN_ATR_THRESHOLD = {
    "EURUSD": 0.0010,
    "GBPUSD": 0.0010,
    "USDJPY": 0.10,
    "XAUUSD": 1.0,
    "US500":  5.0,
}

# Session windows: list of (start_hour_utc, end_hour_utc, quality)
# Hours are UTC. end_hour wraps at 24 (i.e., 23->07 crosses midnight).
_STANDARD_SESSIONS = [
    (12, 16, "high"),   # London/NY overlap
    (7,  12, "high"),   # London open
    (16, 21, "medium"), # NY afternoon
    (21, 23, "low"),    # Off-hours
    # 23-07 (crosses midnight): Asian session = low
]

_JPY_SESSIONS = [
    (12, 16, "high"),
    (7,  12, "high"),
    (16, 21, "medium"),
    (21, 23, "low"),
    # 23-07: Asian session = high for JPY
]

_EQUITY_SESSIONS = [
    (12, 21, "high"),   # NY hours
    # all other hours = low
]

SESSION_CONFIG = {
    "EURUSD": _STANDARD_SESSIONS,
    "GBPUSD": _STANDARD_SESSIONS,
    "USDJPY": _JPY_SESSIONS,
    "XAUUSD": _EQUITY_SESSIONS,
    "US500":  _EQUITY_SESSIONS,
}

"""Instrument list, yfinance tickers, S3 layout, and interval config."""

INSTRUMENTS = [
    {"name": "EUR/USD", "ticker": "EURUSD=X", "s3_key": "EURUSD"},
    {"name": "GBP/USD", "ticker": "GBPUSD=X", "s3_key": "GBPUSD"},
    {"name": "USD/JPY", "ticker": "USDJPY=X", "s3_key": "USDJPY"},
    {"name": "Gold",    "ticker": "GC=F",      "s3_key": "XAUUSD"},
    {"name": "US 500",  "ticker": "^GSPC",     "s3_key": "US500"},
]

INTERVALS = {
    "1d": {"lookback_days": 7,  "backfill_years": 2},
    "1h": {"lookback_days": 30, "backfill_years": 2},
}

S3_PREFIX = "prices"

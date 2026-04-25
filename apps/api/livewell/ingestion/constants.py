"""Instrument list, yfinance tickers, S3 layout, and interval config."""

INSTRUMENTS = [
    # Existing
    {"name": "EUR/USD",      "ticker": "EURUSD=X", "s3_key": "EURUSD"},
    {"name": "GBP/USD",      "ticker": "GBPUSD=X", "s3_key": "GBPUSD"},
    {"name": "USD/JPY",      "ticker": "USDJPY=X", "s3_key": "USDJPY"},
    {"name": "Gold",         "ticker": "GC=F",     "s3_key": "XAUUSD"},
    {"name": "US 500",       "ticker": "^GSPC",    "s3_key": "US500"},
    # New — Futures
    {"name": "Crude Oil",    "ticker": "CL=F",     "s3_key": "CL"},
    {"name": "Natural Gas",  "ticker": "NG=F",     "s3_key": "NG"},
    {"name": "NASDAQ 100",   "ticker": "NQ=F",     "s3_key": "NQ"},
    {"name": "Russell 2000", "ticker": "RTY=F",    "s3_key": "RTY"},
    {"name": "Dow Jones",    "ticker": "YM=F",     "s3_key": "YM"},
    {"name": "Nikkei 225",   "ticker": "NKD=F",    "s3_key": "NKD"},
    # New — Forex
    {"name": "AUD/USD",      "ticker": "AUDUSD=X", "s3_key": "AUDUSD"},
    {"name": "AUD/JPY",      "ticker": "AUDJPY=X", "s3_key": "AUDJPY"},
    {"name": "EUR/JPY",      "ticker": "EURJPY=X", "s3_key": "EURJPY"},
    {"name": "EUR/GBP",      "ticker": "EURGBP=X", "s3_key": "EURGBP"},
    {"name": "GBP/JPY",      "ticker": "GBPJPY=X", "s3_key": "GBPJPY"},
    {"name": "USD/CAD",      "ticker": "USDCAD=X", "s3_key": "USDCAD"},
    {"name": "USD/CHF",      "ticker": "USDCHF=X", "s3_key": "USDCHF"},
    {"name": "USD/MXN",      "ticker": "USDMXN=X", "s3_key": "USDMXN"},
]

INTERVALS = {
    "1d": {"lookback_days": 7,  "backfill_years": 7},
    "1h": {"lookback_days": 30, "backfill_years": 2},
}

S3_PREFIX = "prices"

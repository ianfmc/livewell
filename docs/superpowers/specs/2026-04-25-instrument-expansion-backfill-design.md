# Instrument Expansion + Historical Backfill Design

**Date:** 2026-04-25
**Status:** Approved
**Scope:** Expand livewell from 5 to 19 instruments, backfill price/feature/signal data to 2019, backfill NADEX settlement data to 2019, and re-run Phase 2 notebooks with the expanded dataset.

---

## Context

Phase 2 baseline ML produced poor results (13.9% rules-only win rate, 29.5% model top-50%) primarily due to data volume: only 441 labeled rows spanning Mar–Dec 2025. Expanding to all 19 NADEX instruments with 7 years of history is expected to produce 3,000–10,000+ labeled rows, giving the walk-forward model enough data to produce stable, meaningful results.

---

## Sub-project A: Instrument Expansion + Backfill

### Files Modified

| File | Change |
|---|---|
| `apps/api/livewell/ingestion/constants.py` | Expand `INSTRUMENTS` from 5 to 19; increase `1d` `backfill_years` from 2 to 7 |
| `apps/api/livewell/signals/constants.py` | Add session definitions for new asset classes; add all 14 new instruments to `PIP_PRECISION`, `MIN_ATR_THRESHOLD`, `SESSION_CONFIG` |
| `notebooks/livewell-nadex/configs/s3.yaml` | Change `start_date` from `2025-03-01` to `2019-01-01` |

### No code changes required for the backfill run itself — the existing CLI handles all 19 instruments automatically once `INSTRUMENTS` is expanded.

---

### `INSTRUMENTS` expansion

Full 19-instrument list with yfinance tickers and s3_keys:

```python
INSTRUMENTS = [
    # Existing 5
    {"name": "EUR/USD",        "ticker": "EURUSD=X", "s3_key": "EURUSD"},
    {"name": "GBP/USD",        "ticker": "GBPUSD=X", "s3_key": "GBPUSD"},
    {"name": "USD/JPY",        "ticker": "USDJPY=X", "s3_key": "USDJPY"},
    {"name": "Gold",           "ticker": "GC=F",      "s3_key": "XAUUSD"},
    {"name": "US 500",         "ticker": "^GSPC",     "s3_key": "US500"},
    # New — Futures
    {"name": "Crude Oil",      "ticker": "CL=F",      "s3_key": "CL"},
    {"name": "Natural Gas",    "ticker": "NG=F",      "s3_key": "NG"},
    {"name": "NASDAQ 100",     "ticker": "NQ=F",      "s3_key": "NQ"},
    {"name": "Russell 2000",   "ticker": "RTY=F",     "s3_key": "RTY"},
    {"name": "Dow Jones",      "ticker": "YM=F",      "s3_key": "YM"},
    {"name": "Nikkei 225",     "ticker": "NKD=F",     "s3_key": "NKD"},
    # New — Forex
    {"name": "AUD/USD",        "ticker": "AUDUSD=X",  "s3_key": "AUDUSD"},
    {"name": "AUD/JPY",        "ticker": "AUDJPY=X",  "s3_key": "AUDJPY"},
    {"name": "EUR/JPY",        "ticker": "EURJPY=X",  "s3_key": "EURJPY"},
    {"name": "EUR/GBP",        "ticker": "EURGBP=X",  "s3_key": "EURGBP"},
    {"name": "GBP/JPY",        "ticker": "GBPJPY=X",  "s3_key": "GBPJPY"},
    {"name": "USD/CAD",        "ticker": "USDCAD=X",  "s3_key": "USDCAD"},
    {"name": "USD/CHF",        "ticker": "USDCHF=X",  "s3_key": "USDCHF"},
    {"name": "USD/MXN",        "ticker": "USDMXN=X",  "s3_key": "USDMXN"},
]
```

`backfill_years` for `1d` changes from 2 to 7. `1h` stays at 2 years.

---

### `signals/constants.py` expansion

#### New session window definitions

```python
_FOREX_MAJOR_SESSIONS = [
    (12, 16, "high"),    # London/NY overlap
    (7,  12, "high"),    # London open
    (16, 21, "medium"),  # NY afternoon
    (21, 23, "low"),
    (23,  7, "low"),     # Asian (low for non-JPY majors)
]

_COMMODITY_SESSIONS = [
    (8,  12, "high"),    # Early NY morning ramp-up
    (12, 21, "high"),    # NYMEX primary session
    (21, 23, "low"),
    (23,  8, "medium"),  # Overnight continuous contract
]

_ASIAN_EQUITY_SESSIONS = [
    (23,  7, "high"),    # Tokyo session (08:00–15:00 JST)
    (7,  12, "medium"),  # European overlap
    (12, 21, "low"),     # NY hours (illiquid for JPY equity)
    (21, 23, "low"),
]

_EMERGING_SESSIONS = [
    (12, 16, "high"),    # London/NY overlap
    (7,  12, "medium"),  # London session
    (16, 21, "high"),    # NY afternoon (MXN markets active)
    (21, 23, "low"),
    (23,  7, "low"),
]
```

Rename existing `_STANDARD_SESSIONS` → `_FOREX_MAJOR_SESSIONS` (same values, clearer name). Update the existing `SESSION_CONFIG` entries for `EURUSD` and `GBPUSD` to reference `_FOREX_MAJOR_SESSIONS` instead of `_STANDARD_SESSIONS`. `_JPY_SESSIONS` and `_EQUITY_SESSIONS` are unchanged.

#### `PIP_PRECISION` additions

```python
PIP_PRECISION = {
    # Existing
    "EURUSD": 4, "GBPUSD": 4, "USDJPY": 2, "XAUUSD": 1, "US500": 0,
    # New futures
    "CL": 2, "NG": 3, "NQ": 0, "RTY": 0, "YM": 0, "NKD": 0,
    # New forex
    "AUDUSD": 4, "AUDJPY": 2, "EURJPY": 2, "EURGBP": 4,
    "GBPJPY": 2, "USDCAD": 4, "USDCHF": 4, "USDMXN": 4,
}
```

#### `MIN_ATR_THRESHOLD` additions

```python
MIN_ATR_THRESHOLD = {
    # Existing
    "EURUSD": 0.0010, "GBPUSD": 0.0010, "USDJPY": 0.10,
    "XAUUSD": 1.0,    "US500":  5.0,
    # New futures
    "CL": 0.40, "NG": 0.070, "NQ": 20.0,
    "RTY": 15.0, "YM": 25.0, "NKD": 50.0,
    # New forex
    "AUDUSD": 0.0012, "AUDJPY": 0.15, "EURJPY": 0.18,
    "EURGBP": 0.0008, "GBPJPY": 0.20, "USDCAD": 0.0011,
    "USDCHF": 0.0009, "USDMXN": 0.035,
}
```

#### `SESSION_CONFIG` additions

```python
SESSION_CONFIG = {
    # Existing (rename _STANDARD_SESSIONS refs to _FOREX_MAJOR_SESSIONS)
    "EURUSD": _FOREX_MAJOR_SESSIONS,
    "GBPUSD": _FOREX_MAJOR_SESSIONS,
    "USDJPY": _JPY_SESSIONS,
    "XAUUSD": _EQUITY_SESSIONS,
    "US500":  _EQUITY_SESSIONS,
    # New futures
    "CL":  _COMMODITY_SESSIONS,
    "NG":  _COMMODITY_SESSIONS,
    "NQ":  _EQUITY_SESSIONS,
    "RTY": _EQUITY_SESSIONS,
    "YM":  _EQUITY_SESSIONS,
    "NKD": _ASIAN_EQUITY_SESSIONS,
    # New forex
    "AUDUSD": _FOREX_MAJOR_SESSIONS,
    "AUDJPY": _JPY_SESSIONS,
    "EURJPY": _JPY_SESSIONS,
    "EURGBP": _FOREX_MAJOR_SESSIONS,
    "GBPJPY": _JPY_SESSIONS,
    "USDCAD": _FOREX_MAJOR_SESSIONS,
    "USDCHF": _FOREX_MAJOR_SESSIONS,
    "USDMXN": _EMERGING_SESSIONS,
}
```

---

### Backfill run sequence

After code changes are committed:

1. Run `run_ingestion` — downloads 7 years of daily price data for all 19 instruments to S3
2. Run `run_features` — computes EMA/RSI/MACD/ATR features for all instruments
3. `run_signals` is triggered automatically at the end of `run_features` (existing wiring)
4. Run `nadex-historical` notebook with `start_date: 2019-01-01` — populates settlement CSVs for full history

Steps 1–3 are CLI operations. Step 4 is a one-time notebook run.

---

## Sub-project B: Phase 2 Re-run

### Files Modified

| File | Change |
|---|---|
| `notebooks/livewell-nadex/notebooks/phase2/01_label_construction.ipynb` | Expand `S3_KEY_TO_TICKER` to all 19 instruments |

### Notebooks 02–04: no code changes. Re-run as-is.

---

### `S3_KEY_TO_TICKER` expansion

```python
S3_KEY_TO_TICKER = {
    # Existing 5
    "EURUSD":  "EURUSD=X",
    "GBPUSD":  "GBPUSD=X",
    "USDJPY":  "USDJPY=X",
    "XAUUSD":  "GC=F",
    "US500":   "ES=F",
    # New futures
    "CL":      "CL=F",
    "NG":      "NG=F",
    "NQ":      "NQ=F",
    "RTY":     "RTY=F",
    "YM":      "YM=F",
    "NKD":     "NKD=F",
    # New forex
    "AUDUSD":  "AUDUSD=X",
    "AUDJPY":  "AUDJPY=X",
    "EURJPY":  "EURJPY=X",
    "EURGBP":  "EURGBP=X",
    "GBPJPY":  "GBPJPY=X",
    "USDCAD":  "USDCAD=X",
    "USDCHF":  "USDCHF=X",
    "USDMXN":  "USDMXN=X",
}
```

Note: `US500` maps to `ES=F` (E-mini S&P futures), not `^GSPC`, because NADEX settlement uses futures tickers not index tickers.

---

### Walk-forward fold configuration

Keep `train_months=6`, `test_months=1` unchanged. With 7 years of data (2019–2025), this produces approximately 66 folds — excellent statistical confidence for validation.

---

## What Does NOT Change

- `nadex-recommendation` notebook — untouched
- `nadex-backtesting` notebook — untouched
- `1h` interval backfill depth — stays at 2 years
- Signal pipeline logic — no new features or rule changes
- Phase 3 (random forest) — not started until Phase 2 re-run confirms improvement

---

## Expected Outcome

| Metric | Before | After |
|---|---|---|
| Instruments | 5 | 19 |
| Settlement history | Mar–Dec 2025 | 2019–2025 |
| Labeled rows (Phase 2) | 441 | ~5,000–10,000 |
| Walk-forward folds | 4 | ~66 |
| Fold stability | High variance | Stable |

# Instrument Expansion + Historical Backfill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expand livewell from 5 to 19 instruments, backfill 7 years of price/feature/signal data, backfill NADEX settlement history to 2019, and re-run Phase 2 notebooks with the expanded labeled dataset.

**Architecture:** Two sequential sub-projects. Sub-project A: update `INSTRUMENTS` and `signals/constants.py` for all 19 instruments, update the nadex-historical config, then run the full backfill pipeline (ingest → features → signals → settlement). Sub-project B: update `S3_KEY_TO_TICKER` in notebook 01 and re-run all four Phase 2 notebooks. Sub-project B cannot start until the Sub-project A backfill run completes.

**Tech Stack:** Python 3.12, pandas, boto3, yfinance, pytest, Jupyter (livewell-api kernel).

---

## File Structure

**Sub-project A — Modified:**
- `apps/api/livewell/ingestion/constants.py` — expand `INSTRUMENTS` to 19, increase `1d` `backfill_years` to 7
- `apps/api/livewell/signals/constants.py` — add 4 new session window defs, add 14 new instruments to all three per-instrument dicts
- `apps/api/tests/signals/test_signals.py` — add session tests for new asset classes
- `notebooks/livewell-nadex/configs/s3.yaml` — change `start_date` to `2019-01-01`

**Sub-project B — Modified:**
- `notebooks/livewell-nadex/notebooks/phase2/01_label_construction.ipynb` — expand `S3_KEY_TO_TICKER` to 19 instruments

---

## Task 1: Expand `INSTRUMENTS` and backfill depth in `ingestion/constants.py`

**Files:**
- Modify: `apps/api/livewell/ingestion/constants.py`

- [ ] **Step 1: Replace `constants.py` content**

Replace the entire file with:

```python
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
```

- [ ] **Step 2: Verify tests still pass**

```bash
cd apps/api && uv run pytest tests/ -v --ignore=tests/signals
```

Expected: all tests pass. (Signal tests are covered in Task 3.)

- [ ] **Step 3: Commit**

```bash
git add apps/api/livewell/ingestion/constants.py
git commit -m "feat: expand INSTRUMENTS to 19 and backfill_years to 7"
```

---

## Task 2: Expand `signals/constants.py` with new session defs and per-instrument values

**Files:**
- Modify: `apps/api/livewell/signals/constants.py`

- [ ] **Step 1: Replace `signals/constants.py` content**

Replace the entire file with:

```python
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
```

- [ ] **Step 2: Run existing signal tests to verify nothing broke**

```bash
cd apps/api && uv run pytest tests/signals/test_signals.py -v
```

Expected: all 19 tests pass. (The rename of `_STANDARD_SESSIONS` → `_FOREX_MAJOR_SESSIONS` keeps the same values so existing tests still pass.)

---

## Task 3: Add signal tests for new session configurations

**Files:**
- Modify: `apps/api/tests/signals/test_signals.py`

- [ ] **Step 1: Add tests for new session configs**

Append to `apps/api/tests/signals/test_signals.py`:

```python
def test_session_commodity_nymex_high():
    # CL at 14:00 UTC → NYMEX primary session → high
    ts = pd.Timestamp("2026-01-15 14:00:00", tz="UTC")
    assert _session_quality("CL", ts) == "high"


def test_session_commodity_early_morning_high():
    # CL at 09:00 UTC → early NY morning ramp-up → high
    ts = pd.Timestamp("2026-01-15 09:00:00", tz="UTC")
    assert _session_quality("CL", ts) == "high"


def test_session_commodity_overnight_medium():
    # NG at 02:00 UTC → overnight continuous → medium
    ts = pd.Timestamp("2026-01-15 02:00:00", tz="UTC")
    assert _session_quality("NG", ts) == "medium"


def test_session_asian_equity_tokyo_high():
    # NKD at 01:00 UTC → Tokyo session → high
    ts = pd.Timestamp("2026-01-15 01:00:00", tz="UTC")
    assert _session_quality("NKD", ts) == "high"


def test_session_asian_equity_ny_low():
    # NKD at 15:00 UTC → NY hours → low
    ts = pd.Timestamp("2026-01-15 15:00:00", tz="UTC")
    assert _session_quality("NKD", ts) == "low"


def test_session_emerging_ny_afternoon_high():
    # USDMXN at 18:00 UTC → NY afternoon → high
    ts = pd.Timestamp("2026-01-15 18:00:00", tz="UTC")
    assert _session_quality("USDMXN", ts) == "high"


def test_session_jpy_cross_asian_high():
    # GBPJPY at 02:00 UTC → Tokyo session → high
    ts = pd.Timestamp("2026-01-15 02:00:00", tz="UTC")
    assert _session_quality("GBPJPY", ts) == "high"


def test_session_forex_major_audusd_london_high():
    # AUDUSD at 09:00 UTC → London open → high
    ts = pd.Timestamp("2026-01-15 09:00:00", tz="UTC")
    assert _session_quality("AUDUSD", ts) == "high"


def test_session_forex_major_audusd_asian_low():
    # AUDUSD at 02:00 UTC → Asian session → low
    ts = pd.Timestamp("2026-01-15 02:00:00", tz="UTC")
    assert _session_quality("AUDUSD", ts) == "low"


def test_pipeline_new_futures_instrument_bullish():
    # NQ behaves like an equity — uses _EQUITY_SESSIONS and PIP_PRECISION=0
    row = {
        "date": pd.Timestamp("2026-01-15 15:00:00", tz="UTC"),
        "ema_20": 21010.0, "ema_50": 21000.0,
        "rsi_14": 55.0,
        "macd": 5.0, "macd_signal": 3.0, "macd_hist": 2.0,
        "atr_14": 25.0,
        "close": 21005.0,
    }
    result = _apply_pipeline("NQ", row)
    assert result["signal_valid"] is True
    assert result["direction"] == "buy"
    assert result["strike_candidate"] == round(21005.0 + 25.0 * 0.5, 0)


def test_pipeline_new_futures_instrument_low_atr():
    # NQ with ATR below MIN_ATR_THRESHOLD (20.0) → signal_valid=False
    row = {
        "date": pd.Timestamp("2026-01-15 15:00:00", tz="UTC"),
        "ema_20": 21010.0, "ema_50": 21000.0,
        "rsi_14": 55.0,
        "macd": 5.0, "macd_signal": 3.0, "macd_hist": 2.0,
        "atr_14": 10.0,
        "close": 21005.0,
    }
    result = _apply_pipeline("NQ", row)
    assert result["signal_valid"] is False
    assert "atr" in result["reasoning"].lower()


def test_pipeline_crude_oil_pip_precision():
    # CL uses pip_precision=2 → strike rounded to 2 decimal places
    row = {
        "date": pd.Timestamp("2026-01-15 15:00:00", tz="UTC"),
        "ema_20": 75.10, "ema_50": 75.00,
        "rsi_14": 55.0,
        "macd": 0.05, "macd_signal": 0.03, "macd_hist": 0.02,
        "atr_14": 0.50,
        "close": 75.05,
    }
    result = _apply_pipeline("CL", row)
    assert result["signal_valid"] is True
    assert result["strike_candidate"] == round(75.05 + 0.50 * 0.5, 2)
```

- [ ] **Step 2: Run all signal tests**

```bash
cd apps/api && uv run pytest tests/signals/test_signals.py -v
```

Expected: all 31 tests pass.

- [ ] **Step 3: Commit**

```bash
git add apps/api/livewell/signals/constants.py apps/api/tests/signals/test_signals.py
git commit -m "feat: expand signals constants to 19 instruments with new session configs"
```

---

## Task 4: Update nadex-historical config to backfill from 2019

**Files:**
- Modify: `notebooks/livewell-nadex/configs/s3.yaml`

- [ ] **Step 1: Update `start_date`**

In `notebooks/livewell-nadex/configs/s3.yaml`, change line:
```yaml
  start_date: 2025-03-01  # YYYY-MM-DD format
```
to:
```yaml
  start_date: 2019-01-01  # YYYY-MM-DD format
```

- [ ] **Step 2: Commit**

```bash
git add notebooks/livewell-nadex/configs/s3.yaml
git commit -m "feat: set nadex-historical start_date to 2019-01-01 for full backfill"
```

---

## Task 5: Run the backfill pipeline

This task is a human-run operation. No code changes. Run each step and confirm it completes without errors before proceeding.

- [ ] **Step 1: Run NADEX settlement backfill**

Open `notebooks/livewell-nadex/notebooks/nadex-historical.ipynb` in Jupyter (livewell-api kernel). Restart & Run All.

Expected output: ~1,500+ CSV files processed (covering 2019–2025), uploaded to `s3://nadex-daily-results/historical/`. The manifest will skip any already-processed files. Runtime: 20–60 minutes depending on network.

- [ ] **Step 2: Run livewell ingestion backfill**

```bash
cd apps/api && uv run python -m livewell.ingestion.cli --interval 1d
```

Expected: downloads ~7 years of daily OHLCV data for all 19 instruments to S3. Prints one line per instrument. Runtime: 5–15 minutes.

- [ ] **Step 3: Run feature generation (triggers signals automatically)**

```bash
cd apps/api && uv run python -m livewell.features.cli --interval 1d
```

Expected: computes EMA/RSI/MACD/ATR features for all 19 instruments and writes feature Parquets to S3, then calls `run_signals()` which writes signal Parquets. Prints per-instrument progress. Runtime: 5–10 minutes.

- [ ] **Step 4: Spot-check S3 output**

```bash
cd apps/api && uv run python -c "
import boto3, os
s3 = boto3.client('s3')
bucket = '715853571313-livewell'
for prefix in ['prices/CL/1d', 'signals/NQ/1d', 'signals/AUDUSD/1d']:
    r = s3.list_objects_v2(Bucket=bucket, Prefix=prefix + '/')
    keys = [o['Key'] for o in r.get('Contents', [])]
    print(f'{prefix}: {len(keys)} files — {keys[:3]}')
"
```

Expected: each prefix shows multiple Parquet files covering multiple years.

---

## Task 6: Update `S3_KEY_TO_TICKER` in notebook 01 and re-run Phase 2

**Files:**
- Modify: `notebooks/livewell-nadex/notebooks/phase2/01_label_construction.ipynb` cell `cell-01`

- [ ] **Step 1: Replace cell-01 content**

Replace the entire source of cell `cell-01` with:

```python
import os
import sys
import boto3
import pandas as pd

# Allow importing from apps/api
sys.path.insert(0, os.path.abspath("../../../../apps/api"))

from livewell.ingestion.s3 import read_parquet, write_parquet
from livewell.ingestion.constants import INSTRUMENTS, INTERVALS

os.environ["LIVEWELL_BUCKET"] = "715853571313-livewell"

BUCKET = os.environ["LIVEWELL_BUCKET"]
SETTLEMENT_BUCKET = "nadex-daily-results"
SETTLEMENT_PREFIX = "historical"

SIGNALS_PREFIX = "signals"
PRICES_PREFIX = "prices"
OUTPUT_PATH = "../../../data/phase2/labeled_signals.parquet"
INTERVAL = "1d"

# Maps livewell s3_key → NADEX ticker symbol used in settlement CSV
S3_KEY_TO_TICKER = {
    # Existing
    "EURUSD":  "EURUSD=X",
    "GBPUSD":  "GBPUSD=X",
    "USDJPY":  "USDJPY=X",
    "XAUUSD":  "GC=F",
    "US500":   "ES=F",
    # New — Futures
    "CL":      "CL=F",
    "NG":      "NG=F",
    "NQ":      "NQ=F",
    "RTY":     "RTY=F",
    "YM":      "YM=F",
    "NKD":     "NKD=F",
    # New — Forex
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

- [ ] **Step 2: Run notebook 01**

```bash
jupyter nbconvert --to notebook --execute --inplace \
  --ExecutePreprocessor.kernel_name=livewell-api \
  notebooks/livewell-nadex/notebooks/phase2/01_label_construction.ipynb
```

Expected Cell 3 output (approximate):
```
Settlement data loaded: ~400,000+ rows, 2019-01-02 to 2025-12-19
EURUSD: ~1800 rows, ~1400 labeled, ~400 NaN
GBPUSD: ~1800 rows, ~1400 labeled, ~400 NaN
...
Total rows: ~35,000+
Labeled (direction != none): ~5,000–10,000
Label distribution:
1.0    ~3000–6000
0.0    ~2000–4000
```

- [ ] **Step 3: Run notebook 02**

```bash
jupyter nbconvert --to notebook --execute --inplace \
  --ExecutePreprocessor.kernel_name=livewell-api \
  notebooks/livewell-nadex/notebooks/phase2/02_feature_prep.ipynb
```

Expected Cell 3 output: ~66 folds, each showing both train and test rows. Total rows after dropping direction=none: ~5,000–10,000.

- [ ] **Step 4: Run notebook 03**

```bash
jupyter nbconvert --to notebook --execute --inplace \
  --ExecutePreprocessor.kernel_name=livewell-api \
  notebooks/livewell-nadex/notebooks/phase2/03_walk_forward_validation.ipynb
```

Expected: ~66 folds of predictions, `prob_itm` range covering 0.0–1.0. No errors.

- [ ] **Step 5: Run notebook 04**

```bash
jupyter nbconvert --to notebook --execute --inplace \
  --ExecutePreprocessor.kernel_name=livewell-api \
  notebooks/livewell-nadex/notebooks/phase2/04_calibration_analysis.ipynb
```

Expected: win rates and EV metrics printed per fold. Model win rate should be materially higher than the 29.5% seen with 441 rows.

- [ ] **Step 6: Commit all notebooks with saved output**

```bash
git add \
  notebooks/livewell-nadex/notebooks/phase2/01_label_construction.ipynb \
  notebooks/livewell-nadex/notebooks/phase2/02_feature_prep.ipynb \
  notebooks/livewell-nadex/notebooks/phase2/03_walk_forward_validation.ipynb \
  notebooks/livewell-nadex/notebooks/phase2/04_calibration_analysis.ipynb
git commit -m "feat: re-run Phase 2 notebooks with 19-instrument 7-year dataset"
```

---

## Self-Review

### Spec coverage

| Spec requirement | Covered in |
|---|---|
| Expand `INSTRUMENTS` to 19 | Task 1 |
| `1d` `backfill_years` → 7 | Task 1 |
| `_FOREX_MAJOR_SESSIONS` rename + 4 new session defs | Task 2 |
| All 14 new instruments in `PIP_PRECISION` | Task 2 |
| All 14 new instruments in `MIN_ATR_THRESHOLD` | Task 2 |
| All 14 new instruments in `SESSION_CONFIG` | Task 2 |
| Tests for new session configs + pipeline behavior | Task 3 |
| `nadex-historical` `start_date` → 2019-01-01 | Task 4 |
| Settlement backfill run | Task 5 Step 1 |
| Ingestion backfill run | Task 5 Step 2 |
| Feature + signal backfill run | Task 5 Step 3 |
| `S3_KEY_TO_TICKER` expanded to 19 | Task 6 Step 1 |
| Phase 2 notebooks 01–04 re-run | Task 6 Steps 2–5 |
| No changes to 1h backfill depth | Task 1 (1h stays 2 years) |
| No changes to notebooks 02–04 code | Task 6 (only re-runs them) |

### Placeholder scan

No TBDs or incomplete steps.

### Type consistency

- `s3_key` values in Task 1 (`CL`, `NG`, `NQ`, etc.) match keys used in Task 2 (`PIP_PRECISION`, `MIN_ATR_THRESHOLD`, `SESSION_CONFIG`) and Task 6 (`S3_KEY_TO_TICKER`). ✓
- `_apply_pipeline("NQ", row)` in Task 3 tests uses `PIP_PRECISION["NQ"] = 0` and `MIN_ATR_THRESHOLD["NQ"] = 20.0` — consistent with Task 2. ✓
- `_apply_pipeline("CL", row)` in Task 3 uses `PIP_PRECISION["CL"] = 2` — consistent with Task 2. ✓

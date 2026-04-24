# Design: Sub-project 1B — Feature Generation

**Date:** 2026-04-24
**Status:** Approved
**Scope:** Read OHLCV Parquet from S3, compute 5 technical indicators per instrument+interval, write feature tables back to S3 as Parquet. Triggered automatically by ingestion.

---

## Context

Sub-project 1A delivers clean OHLCV price data in S3. Sub-project 1B transforms that raw price data into technical features — the inputs required before any signal logic or ML scoring can begin. This sub-project closes the gap between raw prices and actionable indicators.

---

## Approach

A new `livewell/features/` package following the same structure as `livewell/ingestion/`. Uses `pandas-ta` for indicator computation (pure Python, correct Wilder smoothing, predictable column names). Entry point is `run_features()` — a standalone callable that ingestion triggers at the end of `run_ingestion()`. Per-instrument error isolation. Idempotent re-runs.

---

## Architecture

### Indicators

| Indicator | pandas-ta call | Raw column name | Renamed to |
|---|---|---|---|
| EMA-20 | `df.ta.ema(length=20)` | `EMA_20` | `ema_20` |
| EMA-50 | `df.ta.ema(length=50)` | `EMA_50` | `ema_50` |
| RSI-14 | `df.ta.rsi(length=14)` | `RSI_14` | `rsi_14` |
| MACD | `df.ta.macd(fast=12, slow=26, signal=9)` | `MACD_12_26_9`, `MACDh_12_26_9`, `MACDs_12_26_9` | `macd`, `macd_hist`, `macd_signal` |
| ATR-14 | `df.ta.atr(length=14)` | `ATRr_14` | `atr_14` |

`features.py` renames all columns from pandas-ta's default names to the lowercase snake_case names above before writing to Parquet.

### S3 Layout

```
s3://{LIVEWELL_BUCKET}/features/{INSTRUMENT}/{INTERVAL}/{YEAR}.parquet

# Examples
s3://livewell-data/features/EURUSD/1d/2026.parquet
s3://livewell-data/features/EURUSD/1h/2026.parquet
s3://livewell-data/features/GBPUSD/1d/2025.parquet
```

Each Parquet file covers one calendar year per instrument per interval. Columns: `date`, `ema_20`, `ema_50`, `rsi_14`, `macd`, `macd_signal`, `macd_hist`, `atr_14` — all float64 except `date`.

### Files

| File | Purpose |
|---|---|
| `apps/api/livewell/features/__init__.py` | Package marker |
| `apps/api/livewell/features/constants.py` | Indicator config (parameters, output column names) |
| `apps/api/livewell/features/features.py` | Core compute + read/write logic |
| `apps/api/tests/features/__init__.py` | Package marker |
| `apps/api/tests/features/test_features.py` | Unit tests (known-value indicator tests + moto S3) |

### Modified Files

| File | Change |
|---|---|
| `apps/api/pyproject.toml` | Add `pandas-ta` runtime dependency |
| `apps/api/livewell/ingestion/ingest.py` | Call `run_features()` at end of `run_ingestion()` |
| `apps/web/current_step_plan.md` | Update to Sub-project 1C on completion |

### Config

| Var | Purpose | Default |
|---|---|---|
| `LIVEWELL_BUCKET` | S3 bucket name | required |

---

## Data Flow

### Per instrument+interval

1. List all year keys under `prices/{INSTRUMENT}/{INTERVAL}/` and read all Parquet files
2. Concatenate into a single DataFrame, sort by `date`, dedup — full history needed for accurate indicator warmup (EMA-50 needs ≥50 rows, ATR-14 needs ≥14)
3. Compute all 5 indicators in one pass using pandas-ta; rows with insufficient history produce NaN (kept in output)
4. Split results by calendar year
5. For each year, read existing `features/` Parquet (if any), merge+dedup on `date`, write back to S3

### Integration with ingestion

`run_ingestion()` calls `run_features(instruments=instruments)` at the end, after all price data is written. Feature failures are logged but do not affect `run_ingestion()`'s return value — ingestion succeeded/failed reflects price data only.

```python
# apps/api/livewell/ingestion/ingest.py (addition)
from livewell.features.features import run_features

def run_ingestion(instruments=None, backfill=False):
    ...  # existing logic
    run_features(instruments=instruments)
    return {"succeeded": succeeded, "failed": failed}
```

### Error isolation

Each instrument is processed in a try/except block. A failed instrument logs the error and continues. `run_features()` returns `{"succeeded": [...], "failed": [...]}`.

---

## Interface

```python
def run_features(
    instruments: list[str] | None = None,
    intervals: list[str] | None = None,
) -> dict:
    """
    Compute technical indicators for all instruments and intervals.

    Args:
        instruments: list of s3_key values (e.g. ["EURUSD"]). Defaults to all.
        intervals: list of interval strings (e.g. ["1d"]). Defaults to all.

    Returns:
        {"succeeded": [...], "failed": [...]}
    """
```

---

## Testing

Tests use `pytest`, `moto` for S3 mocking, and hand-crafted DataFrames with known expected values.

| Test | What it verifies |
|---|---|
| `test_compute_features_returns_expected_columns` | All 7 output columns present |
| `test_ema_20_known_value` | EMA-20 matches manually calculated value on simple price series |
| `test_rsi_14_known_value` | RSI-14 matches known value |
| `test_macd_known_value` | macd, macd_signal, macd_hist columns present and non-NaN after warmup |
| `test_atr_14_known_value` | ATR-14 matches known value using OHLC series |
| `test_run_features_writes_to_s3` | Parquet written to correct S3 key with correct schema |
| `test_run_features_isolates_failures` | One instrument error doesn't block others |
| `test_ingestion_triggers_features` | `run_ingestion()` calls `run_features()` with correct instruments arg |

---

## Out of Scope

- Signal generation from features — Sub-project 1C
- Additional indicators beyond the 5 listed — follow-on
- Feature validation / drift detection — Phase 5
- AWS Lambda deployment — Phase 4

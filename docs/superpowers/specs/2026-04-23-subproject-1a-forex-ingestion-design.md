# Design: Sub-project 1A — Forex Data Ingestion

**Date:** 2026-04-23
**Status:** Approved
**Scope:** Fetch daily (1d) and hourly (1h) OHLCV for 5 instruments via yfinance and store as Parquet files in S3. Runs locally or in AWS Lambda without code changes.

---

## Context

Phase 1 of the roadmap requires a reliable historical price dataset before feature generation, signal logic, or ML can begin. This sub-project delivers that foundation: clean, deduplicated OHLCV data in S3 Parquet format, fetched daily via yfinance.

NADEX contract outcomes (did the underlying finish above/below the strike?) will be derived from the underlying close price rather than scraping NADEX directly — deferring NADEX scraping to Sub-project 1C when market-implied probability calculations require contract prices.

**Planned follow-on:** Expand instrument list to the full set of NADEX-available pairs and indices. The design makes this a one-line change in the constants module.

---

## Approach

Single Python module (`ingest.py`) in the existing `apps/api/livewell/` domain package. Environment-driven config (no hardcoded paths or bucket names). Per-instrument error isolation. Idempotent — re-running any day produces the same result.

---

## Architecture

### Instruments

| Display name | yfinance ticker | S3 key prefix |
|---|---|---|
| EUR/USD | `EURUSD=X` | `EURUSD` |
| GBP/USD | `GBPUSD=X` | `GBPUSD` |
| USD/JPY | `USDJPY=X` | `USDJPY` |
| Gold | `GC=F` | `XAUUSD` |
| US 500 | `^GSPC` | `US500` |

### S3 layout

```
s3://{LIVEWELL_BUCKET}/prices/{INSTRUMENT}/{INTERVAL}/{YEAR}.parquet

# Examples
s3://livewell-data/prices/EURUSD/1d/2026.parquet
s3://livewell-data/prices/EURUSD/1h/2026.parquet
s3://livewell-data/prices/GBPUSD/1d/2025.parquet
```

Each Parquet file covers one calendar year per instrument per interval. Columns: `date` (date for 1d, datetime for 1h), `open`, `high`, `low`, `close`, `volume` — all float64 except `date`.

### Files

| File | Purpose |
|---|---|
| `apps/api/livewell/ingestion/__init__.py` | Package marker |
| `apps/api/livewell/ingestion/constants.py` | Instrument list, interval config, S3 prefix |
| `apps/api/livewell/ingestion/ingest.py` | Core fetch + merge + write logic |
| `apps/api/livewell/ingestion/s3.py` | S3 read/write helpers (read Parquet, write Parquet) |
| `apps/api/tests/ingestion/test_ingest.py` | Unit tests (mocked yfinance + moto S3) |

### Config

All configuration via environment variables:

| Var | Purpose | Default |
|---|---|---|
| `LIVEWELL_BUCKET` | S3 bucket name | required |
| `AWS_REGION` | AWS region | `us-east-1` |

---

## Data Flow

### First run (backfill)

1. Detect no existing Parquet in S3 for this instrument+interval
2. Fetch full history: 2 years for `1d`, 2 years for `1h` (yfinance limit for hourly)
3. Write to S3 split by year (e.g. 2025.parquet, 2026.parquet)

### Subsequent runs (incremental)

1. Fetch last 7 days for `1d`; last 30 days for `1h`
2. Read existing Parquet(s) from S3 for affected year(s)
3. Concatenate new rows with existing, dedup on `date`, sort ascending
4. Write back to S3

### Error isolation

Each instrument is processed independently in a try/except block. A failed instrument logs the error (instrument name, interval, exception) and continues. After all instruments, a summary is logged: N succeeded, M failed. Failed instruments can be rerun by passing instrument names as arguments.

---

## Lambda Readiness

The entry point is `run_ingestion(instruments=None, backfill=False)` — a plain function with no constructor arguments beyond env vars. Lambda handler:

```python
# apps/api/lambda_function.py (future)
from livewell.ingestion.ingest import run_ingestion

def handler(event, context):
    run_ingestion()
```

No logic changes needed to move from local to Lambda. EventBridge triggers this once daily after market close (approx. 17:15 ET).

---

## Testing

Tests use `pytest`, `moto` for S3 mocking, and `unittest.mock.patch` for yfinance.

| Test | What it verifies |
|---|---|
| `test_fresh_run` | No existing S3 file → creates new Parquet with correct schema |
| `test_incremental_append` | Existing file → new rows appended, old rows preserved |
| `test_idempotent_rerun` | Running twice same day → no duplicate rows |
| `test_instrument_failure_isolation` | One yfinance failure → others still complete, error logged |
| `test_backfill_flag` | `backfill=True` → fetches 2-year history regardless of existing data |
| `test_schema` | Output Parquet has correct column names and dtypes |

---

## Out of Scope

- AWS Lambda deployment and EventBridge scheduling — Phase 4
- Feature generation from the price data — Sub-project 1B
- NADEX contract price scraping — Sub-project 1C
- Expanding to the full NADEX instrument list — follow-on to 1A
- Data quality alerts or monitoring — Phase 5

# Sub-project 1B — Feature Generation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Read OHLCV Parquet from S3, compute EMA-20, EMA-50, RSI-14, MACD, and ATR-14 per instrument+interval using pandas-ta, and write feature tables back to S3 as year-partitioned Parquet files.

**Architecture:** A `livewell/features/` package with three focused files: `constants.py` (indicator config + column rename map), `features.py` (read all price history, compute indicators, write by year). Entry point is `run_features()` — callable standalone or triggered from `run_ingestion()`. Per-instrument error isolation. Idempotent re-runs.

**Tech Stack:** Python 3.12, pandas-ta, pandas, pyarrow, boto3, moto (tests), pytest, uv.

---

## File Map

**Created:**
- `apps/api/livewell/features/__init__.py` — package marker
- `apps/api/livewell/features/constants.py` — indicator params + pandas-ta raw→snake_case column rename map
- `apps/api/livewell/features/features.py` — `run_features()`, `_compute_indicators()`, `_features_one()`
- `apps/api/tests/features/__init__.py` — package marker
- `apps/api/tests/features/test_features.py` — unit tests (known-value indicators + moto S3)

**Modified:**
- `apps/api/pyproject.toml` — add `pandas-ta` runtime dependency
- `apps/api/livewell/ingestion/ingest.py` — call `run_features()` at end of `run_ingestion()`
- `apps/api/tests/ingestion/test_ingest.py` — add `test_ingestion_triggers_features`
- `apps/web/current_step_plan.md` — update to Sub-project 1C on completion

---

## Task 1: Add pandas-ta dependency

**Files:**
- Modify: `apps/api/pyproject.toml`

- [ ] **Step 1: Add pandas-ta**

```bash
cd apps/api && uv add pandas-ta
```

Expected output: uv resolves and installs pandas-ta, updates `pyproject.toml` and `uv.lock`.

- [ ] **Step 2: Verify installation**

```bash
cd apps/api && uv run python -c "import pandas_ta; print('ok')"
```

Expected: `ok`

- [ ] **Step 3: Run existing tests to confirm no regressions**

```bash
cd apps/api && uv run pytest -q
```

Expected: 30 tests pass.

- [ ] **Step 4: Commit**

```bash
git add apps/api/pyproject.toml apps/api/uv.lock
git commit -m "chore: add pandas-ta dependency"
```

---

## Task 2: Constants module

**Files:**
- Create: `apps/api/livewell/features/__init__.py`
- Create: `apps/api/livewell/features/constants.py`
- Create: `apps/api/tests/features/__init__.py`

- [ ] **Step 1: Write the failing test**

Create `apps/api/tests/features/__init__.py` (empty file).

Create `apps/api/tests/features/test_features.py`:

```python
import numpy as np
from unittest.mock import patch
import boto3
import pandas as pd
import pytest
from moto import mock_aws

from livewell.features.constants import FEATURE_COLUMNS, PRICES_PREFIX, FEATURES_PREFIX, COLUMN_RENAMES


def test_feature_columns():
    assert FEATURE_COLUMNS == ["date", "ema_20", "ema_50", "rsi_14", "macd", "macd_hist", "macd_signal", "atr_14"]


def test_prefixes():
    assert PRICES_PREFIX == "prices"
    assert FEATURES_PREFIX == "features"


def test_column_renames_maps_all_indicators():
    expected_targets = {"ema_20", "ema_50", "rsi_14", "macd", "macd_hist", "macd_signal", "atr_14"}
    assert set(COLUMN_RENAMES.values()) == expected_targets
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd apps/api && uv run pytest tests/features/test_features.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'livewell.features'`

- [ ] **Step 3: Create the package and constants**

Create `apps/api/livewell/features/__init__.py`:
```python
"""Technical indicator feature generation from OHLCV to S3."""
```

Create `apps/api/livewell/features/constants.py`:
```python
"""Indicator config and pandas-ta column rename map."""

PRICES_PREFIX = "prices"
FEATURES_PREFIX = "features"

FEATURE_COLUMNS = ["date", "ema_20", "ema_50", "rsi_14", "macd", "macd_hist", "macd_signal", "atr_14"]

# pandas-ta default names → our snake_case names
COLUMN_RENAMES = {
    "EMA_20":       "ema_20",
    "EMA_50":       "ema_50",
    "RSI_14":       "rsi_14",
    "MACD_12_26_9": "macd",
    "MACDh_12_26_9":"macd_hist",
    "MACDs_12_26_9":"macd_signal",
    "ATRr_14":      "atr_14",
}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd apps/api && uv run pytest tests/features/test_features.py::test_feature_columns tests/features/test_features.py::test_prefixes tests/features/test_features.py::test_column_renames_maps_all_indicators -v
```

Expected: 3 tests pass.

- [ ] **Step 5: Commit**

```bash
git add apps/api/livewell/features/ apps/api/tests/features/
git commit -m "feat: add features constants module"
```

---

## Task 3: Core feature computation

**Files:**
- Create: `apps/api/livewell/features/features.py`
- Extend: `apps/api/tests/features/test_features.py`

- [ ] **Step 1: Write the failing tests**

Append to `apps/api/tests/features/test_features.py`:

```python
import numpy as np
from livewell.features.features import _compute_indicators


def make_price_df(n: int = 60) -> pd.DataFrame:
    """Generate n rows of synthetic OHLCV with a gentle uptrend."""
    dates = pd.date_range("2025-01-01", periods=n, freq="D")
    close = [1.0 + i * 0.001 for i in range(n)]
    return pd.DataFrame({
        "date":   dates,
        "open":   [c - 0.0005 for c in close],
        "high":   [c + 0.002  for c in close],
        "low":    [c - 0.002  for c in close],
        "close":  close,
        "volume": [1000.0] * n,
    })


def test_compute_indicators_returns_expected_columns():
    df = make_price_df(60)
    result = _compute_indicators(df)
    assert list(result.columns) == ["date", "ema_20", "ema_50", "rsi_14", "macd", "macd_hist", "macd_signal", "atr_14"]


def test_ema_20_known_value():
    df = make_price_df(60)
    result = _compute_indicators(df)
    # After 60 rows the EMA-20 should be non-NaN and close to the recent close
    last_ema = result["ema_20"].iloc[-1]
    last_close = df["close"].iloc[-1]
    assert not np.isnan(last_ema)
    assert abs(last_ema - last_close) < 0.01  # EMA tracks price closely on a smooth series


def test_ema_50_requires_50_rows():
    df = make_price_df(60)
    result = _compute_indicators(df)
    # First 49 rows must be NaN for EMA-50
    assert result["ema_50"].iloc[:49].isna().all()
    assert not np.isnan(result["ema_50"].iloc[-1])


def test_rsi_14_bounded():
    df = make_price_df(60)
    result = _compute_indicators(df)
    valid = result["rsi_14"].dropna()
    assert (valid >= 0).all() and (valid <= 100).all()


def test_macd_columns_present_and_converge():
    df = make_price_df(60)
    result = _compute_indicators(df)
    # All three MACD columns must be present and non-NaN at the end
    for col in ["macd", "macd_hist", "macd_signal"]:
        assert not np.isnan(result[col].iloc[-1]), f"{col} is NaN at end"


def test_atr_14_positive():
    df = make_price_df(60)
    result = _compute_indicators(df)
    valid = result["atr_14"].dropna()
    assert (valid > 0).all()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd apps/api && uv run pytest tests/features/ -v -k "compute_indicators or ema or rsi or macd or atr"
```

Expected: FAIL — `ImportError: cannot import name '_compute_indicators' from 'livewell.features.features'`

- [ ] **Step 3: Implement features.py**

Create `apps/api/livewell/features/features.py`:

```python
"""Core feature generation: read OHLCV from S3, compute indicators, write features to S3."""
from __future__ import annotations

import logging
import os

import boto3
import pandas as pd
import pandas_ta as ta

from livewell.ingestion.constants import INSTRUMENTS, INTERVALS
from livewell.ingestion.s3 import read_parquet, write_parquet
from livewell.features.constants import COLUMN_RENAMES, FEATURE_COLUMNS, FEATURES_PREFIX, PRICES_PREFIX

logger = logging.getLogger(__name__)


def _compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Compute all 5 indicators on a full-history OHLCV DataFrame. Returns feature DataFrame."""
    prices = df.copy()
    prices = prices.sort_values("date").reset_index(drop=True)

    prices.ta.ema(length=20, append=True)
    prices.ta.ema(length=50, append=True)
    prices.ta.rsi(length=14, append=True)
    prices.ta.macd(fast=12, slow=26, signal=9, append=True)
    prices.ta.atr(length=14, append=True)

    prices = prices.rename(columns=COLUMN_RENAMES)
    return prices[FEATURE_COLUMNS]


def _features_one(instrument: dict, interval: str, bucket: str) -> None:
    """Read all price years for one instrument+interval, compute features, write by year."""
    s3_key = instrument["s3_key"]

    # List all available price year keys for this instrument+interval
    s3 = boto3.client("s3")
    prefix = f"{PRICES_PREFIX}/{s3_key}/{interval}/"
    resp = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
    objects = resp.get("Contents", [])
    if not objects:
        logger.warning("no price files found for %s/%s", s3_key, interval)
        return

    # Read and concatenate all years
    frames = []
    for obj in objects:
        df = read_parquet(bucket, obj["Key"])
        if df is not None:
            frames.append(df)
    if not frames:
        return

    full_history = pd.concat(frames, ignore_index=True)
    full_history = full_history.drop_duplicates(subset=["date"]).sort_values("date").reset_index(drop=True)

    # Compute indicators on full history (needed for correct warmup)
    features = _compute_indicators(full_history)

    # Write back split by year
    for year, group in features.groupby(features["date"].dt.year):
        key = f"{FEATURES_PREFIX}/{s3_key}/{interval}/{int(year)}.parquet"
        existing = read_parquet(bucket, key)
        if existing is not None:
            combined = pd.concat([existing, group], ignore_index=True)
            combined["date"] = pd.to_datetime(combined["date"])
            group = combined.drop_duplicates(subset=["date"]).sort_values("date").reset_index(drop=True)
        write_parquet(group, bucket, key)
        logger.info("%s/%s/%s features: %d rows", s3_key, interval, year, len(group))


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
    bucket = os.environ["LIVEWELL_BUCKET"]
    targets = (
        [i for i in INSTRUMENTS if i["s3_key"] in instruments]
        if instruments
        else INSTRUMENTS
    )
    target_intervals = intervals if intervals else list(INTERVALS.keys())

    failed_pairs: list[tuple[str, str]] = []

    for instrument in targets:
        for interval in target_intervals:
            try:
                _features_one(instrument, interval, bucket)
            except Exception as exc:
                logger.error(
                    "failed to compute features %s/%s: %s",
                    instrument["s3_key"], interval, exc,
                )
                failed_pairs.append((instrument["s3_key"], interval))

    failed = list({s3_key for s3_key, _ in failed_pairs})
    succeeded = [i["s3_key"] for i in targets if i["s3_key"] not in failed]

    logger.info("features complete — succeeded: %s, failed: %s", succeeded, failed)
    return {"succeeded": succeeded, "failed": failed}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd apps/api && uv run pytest tests/features/ -v -k "compute_indicators or ema or rsi or macd or atr"
```

Expected: 6 tests pass.

- [ ] **Step 5: Commit**

```bash
git add apps/api/livewell/features/features.py apps/api/tests/features/test_features.py
git commit -m "feat: add core feature computation with pandas-ta"
```

---

## Task 4: S3 read/write and run_features tests

**Files:**
- Extend: `apps/api/tests/features/test_features.py`

- [ ] **Step 1: Write the failing tests**

Append to `apps/api/tests/features/test_features.py`:

```python
import boto3
from moto import mock_aws
from livewell.features.features import run_features
from livewell.ingestion.s3 import write_parquet as write_prices


BUCKET = "test-livewell"


@pytest.fixture()
def s3_bucket():
    with mock_aws():
        boto3.client("s3", region_name="us-east-1").create_bucket(Bucket=BUCKET)
        yield


def make_price_parquet(bucket: str, s3_key: str, interval: str, year: int, n: int = 60):
    """Write synthetic price Parquet to mocked S3."""
    dates = pd.date_range(f"{year}-01-01", periods=n, freq="D")
    close = [1.0 + i * 0.001 for i in range(n)]
    df = pd.DataFrame({
        "date":   dates,
        "open":   [c - 0.0005 for c in close],
        "high":   [c + 0.002  for c in close],
        "low":    [c - 0.002  for c in close],
        "close":  close,
        "volume": [1000.0] * n,
    })
    key = f"prices/{s3_key}/{interval}/{year}.parquet"
    write_prices(df, bucket, key)


def test_run_features_writes_to_s3(s3_bucket):
    make_price_parquet(BUCKET, "EURUSD", "1d", 2026, n=60)

    with patch.dict("os.environ", {"LIVEWELL_BUCKET": BUCKET}):
        result = run_features(instruments=["EURUSD"], intervals=["1d"])

    assert result["succeeded"] == ["EURUSD"]
    assert result["failed"] == []

    # Verify the feature file was written to S3
    s3 = boto3.client("s3", region_name="us-east-1")
    resp = s3.list_objects_v2(Bucket=BUCKET, Prefix="features/EURUSD/1d/")
    keys = [obj["Key"] for obj in resp.get("Contents", [])]
    assert any("2026.parquet" in k for k in keys)


def test_run_features_output_schema(s3_bucket):
    make_price_parquet(BUCKET, "EURUSD", "1d", 2026, n=60)

    with patch.dict("os.environ", {"LIVEWELL_BUCKET": BUCKET}):
        run_features(instruments=["EURUSD"], intervals=["1d"])

    from livewell.ingestion.s3 import read_parquet
    df = read_parquet(BUCKET, "features/EURUSD/1d/2026.parquet")
    assert df is not None
    assert list(df.columns) == ["date", "ema_20", "ema_50", "rsi_14", "macd", "macd_hist", "macd_signal", "atr_14"]


def test_run_features_isolates_failures(s3_bucket):
    # EURUSD has prices; GBPUSD has no prices — _features_one will return early (no failure)
    # To test isolation, we patch _features_one to raise for GBPUSD
    make_price_parquet(BUCKET, "EURUSD", "1d", 2026, n=60)

    original_features_one = __import__(
        "livewell.features.features", fromlist=["_features_one"]
    )._features_one

    def failing_features_one(instrument, interval, bucket):
        if instrument["s3_key"] == "GBPUSD":
            raise RuntimeError("simulated failure")
        return original_features_one(instrument, interval, bucket)

    with patch("livewell.features.features._features_one", side_effect=failing_features_one):
        with patch.dict("os.environ", {"LIVEWELL_BUCKET": BUCKET}):
            result = run_features(instruments=["EURUSD", "GBPUSD"], intervals=["1d"])

    assert "EURUSD" in result["succeeded"]
    assert "GBPUSD" in result["failed"]
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd apps/api && uv run pytest tests/features/ -v -k "s3 or schema or isolates"
```

Expected: FAIL — `ImportError: cannot import name 'run_features'` or similar (test references not yet fully wired).

- [ ] **Step 3: Run tests to verify they pass**

```bash
cd apps/api && uv run pytest tests/features/ -v
```

Expected: all tests in `tests/features/` pass (3 constants + 6 compute + 3 S3 = 12 tests).

- [ ] **Step 4: Commit**

```bash
git add apps/api/tests/features/test_features.py
git commit -m "feat: add S3 read/write and run_features tests"
```

---

## Task 5: Wire ingestion → features + update step plan

**Files:**
- Modify: `apps/api/livewell/ingestion/ingest.py`
- Modify: `apps/api/tests/ingestion/test_ingest.py`
- Modify: `apps/web/current_step_plan.md`

- [ ] **Step 1: Write the failing test**

Append to `apps/api/tests/ingestion/test_ingest.py`:

```python
def test_ingestion_triggers_features(s3_bucket):
    mock_ticker = MagicMock()
    mock_ticker.history.return_value = pd.DataFrame({
        "Open": [1.0], "High": [1.1], "Low": [0.9], "Close": [1.05], "Volume": [1000.0]
    }, index=pd.to_datetime(["2026-04-22"]))

    with patch("livewell.ingestion.ingest.yf.Ticker", return_value=mock_ticker):
        with patch("livewell.ingestion.ingest.run_features") as mock_run_features:
            with patch.dict("os.environ", {"LIVEWELL_BUCKET": BUCKET}):
                run_ingestion(instruments=["EURUSD"])

    mock_run_features.assert_called_once_with(instruments=["EURUSD"])
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd apps/api && uv run pytest tests/ingestion/test_ingest.py::test_ingestion_triggers_features -v
```

Expected: FAIL — `AssertionError: Expected call not found` (run_features not yet called from run_ingestion).

- [ ] **Step 3: Wire run_features into run_ingestion**

In `apps/api/livewell/ingestion/ingest.py`, add the import after the existing imports:

```python
from livewell.features.features import run_features
```

And at the end of `run_ingestion()`, just before the `return` statement, add:

```python
    try:
        run_features(instruments=instruments)
    except Exception as exc:
        logger.error("feature generation failed: %s", exc)

    logger.info("ingestion complete — succeeded: %s, failed: %s", succeeded, failed)
    return {"succeeded": succeeded, "failed": failed}
```

The full updated `run_ingestion` function should look like:

```python
def run_ingestion(
    instruments: list[str] | None = None,
    backfill: bool = False,
) -> dict:
    """
    Run ingestion for all instruments and intervals.

    Args:
        instruments: list of s3_key values to process (e.g. ["EURUSD", "GBPUSD"]).
                     Defaults to all instruments in constants.INSTRUMENTS.
        backfill: if True, fetch full 2-year history regardless of existing data.

    Returns:
        {"succeeded": [...], "failed": [...]}
    """
    bucket = os.environ["LIVEWELL_BUCKET"]
    targets = (
        [i for i in INSTRUMENTS if i["s3_key"] in instruments]
        if instruments
        else INSTRUMENTS
    )

    failed_pairs: list[tuple[str, str]] = []

    for instrument in targets:
        for interval in INTERVALS:
            try:
                _ingest_one(instrument, interval, bucket, backfill)
            except Exception as exc:
                logger.error(
                    "failed to ingest %s/%s: %s",
                    instrument["s3_key"], interval, exc,
                )
                failed_pairs.append((instrument["s3_key"], interval))

    failed = list({s3_key for s3_key, _ in failed_pairs})
    succeeded = [i["s3_key"] for i in targets if i["s3_key"] not in failed]

    try:
        run_features(instruments=instruments)
    except Exception as exc:
        logger.error("feature generation failed: %s", exc)

    logger.info("ingestion complete — succeeded: %s, failed: %s", succeeded, failed)
    return {"succeeded": succeeded, "failed": failed}
```

- [ ] **Step 4: Run the new test to verify it passes**

```bash
cd apps/api && uv run pytest tests/ingestion/test_ingest.py::test_ingestion_triggers_features -v
```

Expected: PASS.

- [ ] **Step 5: Run the full test suite**

```bash
cd apps/api && uv run pytest -q
```

Expected: all tests pass (30 existing + 12 features + 1 ingestion trigger = 43 tests).

- [ ] **Step 6: Update current_step_plan.md**

Replace the contents of `apps/web/current_step_plan.md` with:

```markdown
# Current Step: Sub-project 1C — NADEX Strike Feasibility

**Sub-project 1B status:** Complete
- Reads all available OHLCV Parquet years from S3 per instrument+interval
- Computes EMA-20, EMA-50, RSI-14, MACD (line/signal/hist), ATR-14 via pandas-ta
- Writes feature tables to `features/{INSTRUMENT}/{INTERVAL}/{YEAR}.parquet`
- Idempotent re-runs; per-instrument error isolation
- Triggered automatically by `run_ingestion()` at end of each price update
- 12 tests: constants, known-value indicator tests, S3 write, schema, error isolation

**Sub-project 1A status:** Complete
- yfinance ingestion for 5 instruments: EUR/USD, GBP/USD, USD/JPY, Gold, US 500
- Daily (1d) and hourly (1h) OHLCV stored as Parquet in S3
- Per-instrument error isolation; idempotent re-runs
- Backfill mode fetches 2-year history; incremental mode fetches last 7d (1d) / 30d (1h)
- CLI: `uv run python -m livewell.ingestion.cli [--instruments ...] [--backfill]`
- Lambda-ready: `run_ingestion()` callable from thin handler, config via env vars

**Phase 1D status:** Complete
- Vite proxy: `/api/*` forwarded to `localhost:8000`
- MSW gated behind `VITE_USE_MOCKS=true` (off by default in dev; on for tests)
- 3 new FastAPI routes with hardcoded stubs
- CORS expanded to cover ports 5173–5175 + 4173
- 65 frontend tests passing, 14 backend tests passing

---

## Next: Sub-project 1C — NADEX Strike Feasibility

- Derive NADEX contract outcomes from underlying close prices
- Compute strike feasibility scores per instrument
- Filter signals by feasibility before presenting to trader
```

- [ ] **Step 7: Commit**

```bash
git add apps/api/livewell/ingestion/ingest.py apps/api/tests/ingestion/test_ingest.py apps/web/current_step_plan.md
git commit -m "feat: wire ingestion → features; update step plan to 1C"
```

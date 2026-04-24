# Sub-project 1A — Forex Data Ingestion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fetch daily (1d) and hourly (1h) OHLCV for 5 instruments via yfinance and store as deduplicated, idempotent Parquet files in S3.

**Architecture:** A `livewell/ingestion/` module with three focused files: `constants.py` (instrument list + interval config), `s3.py` (S3 read/write helpers), and `ingest.py` (fetch + merge + write logic). Entry point is `run_ingestion()` — a plain function callable locally or from a Lambda handler. Per-instrument error isolation ensures one failure doesn't block others.

**Tech Stack:** Python 3.12, yfinance, pandas, pyarrow, boto3, moto (tests), pytest, uv (dependency management).

---

## File Map

**Created:**
- `apps/api/livewell/ingestion/__init__.py` — package marker
- `apps/api/livewell/ingestion/constants.py` — instrument list, yfinance tickers, S3 prefixes, interval config
- `apps/api/livewell/ingestion/s3.py` — read Parquet from S3, write Parquet to S3
- `apps/api/livewell/ingestion/ingest.py` — `run_ingestion()`, `fetch_ohlcv()`, `merge_and_dedup()`
- `apps/api/tests/ingestion/__init__.py` — package marker
- `apps/api/tests/ingestion/test_ingest.py` — unit tests (mocked yfinance + moto S3)

**Modified:**
- `apps/api/pyproject.toml` — add yfinance, pandas, pyarrow, boto3, moto dependencies

---

## Task 1: Add dependencies

**Files:**
- Modify: `apps/api/pyproject.toml`

- [ ] **Step 1: Add runtime dependencies**

```bash
cd apps/api && uv add yfinance pandas pyarrow boto3
```

Expected output: uv resolves and installs packages, updates `pyproject.toml` and `uv.lock`.

- [ ] **Step 2: Add dev dependencies**

```bash
cd apps/api && uv add --dev moto[s3]
```

Expected output: moto added to `[dependency-groups] dev`.

- [ ] **Step 3: Verify installation**

```bash
cd apps/api && uv run python -c "import yfinance, pandas, pyarrow, boto3, moto; print('all ok')"
```

Expected: `all ok`

- [ ] **Step 4: Run existing tests to confirm no regressions**

```bash
cd apps/api && uv run pytest -q
```

Expected: all existing tests pass (14 tests).

- [ ] **Step 5: Commit**

```bash
git add apps/api/pyproject.toml apps/api/uv.lock
git commit -m "chore: add yfinance, pandas, pyarrow, boto3, moto dependencies"
```

---

## Task 2: Constants module

**Files:**
- Create: `apps/api/livewell/ingestion/__init__.py`
- Create: `apps/api/livewell/ingestion/constants.py`

- [ ] **Step 1: Write the failing test**

Create `apps/api/tests/ingestion/__init__.py` (empty) and `apps/api/tests/ingestion/test_constants.py`:

```python
from livewell.ingestion.constants import INSTRUMENTS, INTERVALS, S3_PREFIX


def test_instruments_count():
    assert len(INSTRUMENTS) == 5


def test_instruments_have_required_keys():
    for inst in INSTRUMENTS:
        assert "name" in inst
        assert "ticker" in inst
        assert "s3_key" in inst


def test_intervals():
    assert set(INTERVALS.keys()) == {"1d", "1h"}
    assert INTERVALS["1d"]["lookback_days"] == 7
    assert INTERVALS["1h"]["lookback_days"] == 30
    assert INTERVALS["1d"]["backfill_years"] == 2
    assert INTERVALS["1h"]["backfill_years"] == 2


def test_s3_prefix():
    assert S3_PREFIX == "prices"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd apps/api && uv run pytest tests/ingestion/test_constants.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'livewell.ingestion'`

- [ ] **Step 3: Create the package and constants**

Create `apps/api/livewell/ingestion/__init__.py`:
```python
"""Forex OHLCV ingestion from yfinance to S3."""
```

Create `apps/api/livewell/ingestion/constants.py`:
```python
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
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd apps/api && uv run pytest tests/ingestion/test_constants.py -v
```

Expected: 3 tests pass.

- [ ] **Step 5: Commit**

```bash
git add apps/api/livewell/ingestion/ apps/api/tests/ingestion/
git commit -m "feat: add ingestion constants module"
```

---

## Task 3: S3 helpers

**Files:**
- Create: `apps/api/livewell/ingestion/s3.py`
- Test: `apps/api/tests/ingestion/test_s3.py`

- [ ] **Step 1: Write the failing tests**

Create `apps/api/tests/ingestion/test_s3.py`:

```python
import io
import os
import boto3
import pandas as pd
import pytest
from moto import mock_aws
from livewell.ingestion.s3 import read_parquet, write_parquet

BUCKET = "test-livewell"
KEY = "prices/EURUSD/1d/2026.parquet"


def make_df():
    return pd.DataFrame({
        "date":   pd.to_datetime(["2026-04-21", "2026-04-22"]),
        "open":   [1.08, 1.09],
        "high":   [1.09, 1.10],
        "low":    [1.07, 1.08],
        "close":  [1.085, 1.095],
        "volume": [1000.0, 1100.0],
    })


@pytest.fixture()
def s3_bucket():
    with mock_aws():
        conn = boto3.client("s3", region_name="us-east-1")
        conn.create_bucket(Bucket=BUCKET)
        yield conn


def test_write_then_read_roundtrip(s3_bucket):
    df = make_df()
    write_parquet(df, BUCKET, KEY)
    result = read_parquet(BUCKET, KEY)
    assert list(result.columns) == list(df.columns)
    assert len(result) == len(df)


def test_read_missing_returns_none(s3_bucket):
    result = read_parquet(BUCKET, "prices/EURUSD/1d/2099.parquet")
    assert result is None


def test_write_overwrites_existing(s3_bucket):
    df1 = make_df()
    write_parquet(df1, BUCKET, KEY)
    df2 = make_df().iloc[:1]
    write_parquet(df2, BUCKET, KEY)
    result = read_parquet(BUCKET, KEY)
    assert len(result) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd apps/api && uv run pytest tests/ingestion/test_s3.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'livewell.ingestion.s3'`

- [ ] **Step 3: Implement s3.py**

Create `apps/api/livewell/ingestion/s3.py`:

```python
"""S3 read/write helpers for OHLCV Parquet files."""
from __future__ import annotations

import io
import logging

import boto3
import pandas as pd
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


def read_parquet(bucket: str, key: str) -> pd.DataFrame | None:
    """Return DataFrame from S3 Parquet, or None if the object does not exist."""
    s3 = boto3.client("s3")
    try:
        obj = s3.get_object(Bucket=bucket, Key=key)
        return pd.read_parquet(io.BytesIO(obj["Body"].read()))
    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchKey":
            return None
        raise


def write_parquet(df: pd.DataFrame, bucket: str, key: str) -> None:
    """Write DataFrame to S3 as Parquet, overwriting any existing object."""
    s3 = boto3.client("s3")
    buf = io.BytesIO()
    df.to_parquet(buf, index=False)
    buf.seek(0)
    s3.put_object(Bucket=bucket, Key=key, Body=buf.getvalue())
    logger.info("wrote %d rows to s3://%s/%s", len(df), bucket, key)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd apps/api && uv run pytest tests/ingestion/test_s3.py -v
```

Expected: 3 tests pass.

- [ ] **Step 5: Commit**

```bash
git add apps/api/livewell/ingestion/s3.py apps/api/tests/ingestion/test_s3.py
git commit -m "feat: add S3 Parquet read/write helpers"
```

---

## Task 4: Core ingestion logic

**Files:**
- Create: `apps/api/livewell/ingestion/ingest.py`
- Test: `apps/api/tests/ingestion/test_ingest.py`

- [ ] **Step 1: Write the failing tests**

Create `apps/api/tests/ingestion/test_ingest.py`:

```python
import os
from datetime import date, timedelta
from unittest.mock import patch, MagicMock

import boto3
import pandas as pd
import pytest
from moto import mock_aws

from livewell.ingestion.ingest import fetch_ohlcv, merge_and_dedup, run_ingestion
from livewell.ingestion.constants import INSTRUMENTS


def make_ohlcv(dates: list[str]) -> pd.DataFrame:
    n = len(dates)
    return pd.DataFrame({
        "date":   pd.to_datetime(dates),
        "open":   [1.0] * n,
        "high":   [1.1] * n,
        "low":    [0.9] * n,
        "close":  [1.05] * n,
        "volume": [1000.0] * n,
    })


BUCKET = "test-livewell"


@pytest.fixture()
def s3_bucket():
    with mock_aws():
        boto3.client("s3", region_name="us-east-1").create_bucket(Bucket=BUCKET)
        yield


# --- fetch_ohlcv ---

def test_fetch_ohlcv_returns_dataframe():
    mock_ticker = MagicMock()
    mock_ticker.history.return_value = pd.DataFrame({
        "Open": [1.0], "High": [1.1], "Low": [0.9], "Close": [1.05], "Volume": [1000.0]
    }, index=pd.to_datetime(["2026-04-22"]))
    with patch("livewell.ingestion.ingest.yf.Ticker", return_value=mock_ticker):
        df = fetch_ohlcv("EURUSD=X", interval="1d", lookback_days=7)
    assert list(df.columns) == ["date", "open", "high", "low", "close", "volume"]
    assert len(df) == 1


def test_fetch_ohlcv_returns_none_on_empty():
    mock_ticker = MagicMock()
    mock_ticker.history.return_value = pd.DataFrame()
    with patch("livewell.ingestion.ingest.yf.Ticker", return_value=mock_ticker):
        result = fetch_ohlcv("EURUSD=X", interval="1d", lookback_days=7)
    assert result is None


# --- merge_and_dedup ---

def test_merge_and_dedup_appends_new_rows():
    existing = make_ohlcv(["2026-04-20", "2026-04-21"])
    new = make_ohlcv(["2026-04-21", "2026-04-22"])
    result = merge_and_dedup(existing, new)
    assert len(result) == 3
    assert list(result["date"].dt.strftime("%Y-%m-%d")) == ["2026-04-20", "2026-04-21", "2026-04-22"]


def test_merge_and_dedup_idempotent():
    existing = make_ohlcv(["2026-04-20", "2026-04-21"])
    result = merge_and_dedup(existing, existing)
    assert len(result) == 2


def test_merge_and_dedup_with_no_existing():
    new = make_ohlcv(["2026-04-21", "2026-04-22"])
    result = merge_and_dedup(None, new)
    assert len(result) == 2


# --- run_ingestion ---

def test_run_ingestion_writes_to_s3(s3_bucket):
    mock_ticker = MagicMock()
    mock_ticker.history.return_value = pd.DataFrame({
        "Open": [1.0], "High": [1.1], "Low": [0.9], "Close": [1.05], "Volume": [1000.0]
    }, index=pd.to_datetime(["2026-04-22"]))

    with patch("livewell.ingestion.ingest.yf.Ticker", return_value=mock_ticker):
        with patch.dict("os.environ", {"LIVEWELL_BUCKET": BUCKET}):
            result = run_ingestion(instruments=["EURUSD"])

    assert result["succeeded"] == ["EURUSD"]
    assert result["failed"] == []


def test_run_ingestion_isolates_failures(s3_bucket):
    def ticker_side_effect(ticker_symbol):
        mock = MagicMock()
        if ticker_symbol == "GBPUSD=X":
            mock.history.side_effect = RuntimeError("network error")
        else:
            mock.history.return_value = pd.DataFrame({
                "Open": [1.0], "High": [1.1], "Low": [0.9], "Close": [1.05], "Volume": [1000.0]
            }, index=pd.to_datetime(["2026-04-22"]))
        return mock

    with patch("livewell.ingestion.ingest.yf.Ticker", side_effect=ticker_side_effect):
        with patch.dict("os.environ", {"LIVEWELL_BUCKET": BUCKET}):
            result = run_ingestion(instruments=["EURUSD", "GBPUSD"])

    assert "EURUSD" in result["succeeded"]
    assert "GBPUSD" in result["failed"]
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd apps/api && uv run pytest tests/ingestion/test_ingest.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'livewell.ingestion.ingest'`

- [ ] **Step 3: Implement ingest.py**

Create `apps/api/livewell/ingestion/ingest.py`:

```python
"""Core ingestion logic: fetch OHLCV from yfinance, merge, write to S3."""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf

from livewell.ingestion.constants import INSTRUMENTS, INTERVALS, S3_PREFIX
from livewell.ingestion.s3 import read_parquet, write_parquet

logger = logging.getLogger(__name__)


def fetch_ohlcv(
    ticker: str,
    interval: str,
    lookback_days: int,
) -> pd.DataFrame | None:
    """Fetch OHLCV from yfinance for the last lookback_days. Returns None if empty."""
    end = datetime.utcnow()
    start = end - timedelta(days=lookback_days)
    raw = yf.Ticker(ticker).history(start=start, end=end, interval=interval)
    if raw.empty:
        return None
    df = raw[["Open", "High", "Low", "Close", "Volume"]].copy()
    df.columns = ["open", "high", "low", "close", "volume"]
    df.index.name = "date"
    df = df.reset_index()
    df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)
    return df


def fetch_ohlcv_backfill(ticker: str, interval: str, years: int) -> pd.DataFrame | None:
    """Fetch full history up to `years` back. Used on first run."""
    return fetch_ohlcv(ticker, interval, lookback_days=years * 365)


def merge_and_dedup(
    existing: pd.DataFrame | None,
    new: pd.DataFrame,
) -> pd.DataFrame:
    """Concatenate existing and new rows, dedup on date, sort ascending."""
    if existing is None:
        combined = new
    else:
        combined = pd.concat([existing, new], ignore_index=True)
    combined["date"] = pd.to_datetime(combined["date"])
    combined = combined.drop_duplicates(subset=["date"]).sort_values("date").reset_index(drop=True)
    return combined


def _s3_key(s3_key: str, interval: str, year: int) -> str:
    return f"{S3_PREFIX}/{s3_key}/{interval}/{year}.parquet"


def _ingest_one(
    instrument: dict,
    interval: str,
    bucket: str,
    backfill: bool,
) -> None:
    ticker = instrument["ticker"]
    s3_key = instrument["s3_key"]
    cfg = INTERVALS[interval]

    if backfill:
        new_df = fetch_ohlcv_backfill(ticker, interval, years=cfg["backfill_years"])
    else:
        new_df = fetch_ohlcv(ticker, interval, lookback_days=cfg["lookback_days"])

    if new_df is None or new_df.empty:
        logger.warning("no data returned for %s %s", s3_key, interval)
        return

    for year, group in new_df.groupby(new_df["date"].dt.year):
        key = _s3_key(s3_key, interval, int(year))
        existing = read_parquet(bucket, key)
        merged = merge_and_dedup(existing, group)
        write_parquet(merged, bucket, key)
        logger.info("%s/%s/%s: %d rows", s3_key, interval, year, len(merged))


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

    succeeded, failed = [], []

    for instrument in targets:
        for interval in INTERVALS:
            try:
                _ingest_one(instrument, interval, bucket, backfill)
                if instrument["s3_key"] not in succeeded:
                    succeeded.append(instrument["s3_key"])
            except Exception as exc:
                logger.error(
                    "failed to ingest %s/%s: %s",
                    instrument["s3_key"], interval, exc,
                )
                if instrument["s3_key"] not in failed:
                    failed.append(instrument["s3_key"])

    logger.info("ingestion complete — succeeded: %s, failed: %s", succeeded, failed)
    return {"succeeded": succeeded, "failed": failed}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd apps/api && uv run pytest tests/ingestion/test_ingest.py -v
```

Expected: 7 tests pass.

- [ ] **Step 5: Run full test suite**

```bash
cd apps/api && uv run pytest -q
```

Expected: all tests pass (14 existing + 3 constants + 3 s3 + 7 ingest = 27 total).

- [ ] **Step 6: Commit**

```bash
git add apps/api/livewell/ingestion/ingest.py apps/api/tests/ingestion/test_ingest.py
git commit -m "feat: add core ingestion logic with S3 write and error isolation"
```

---

## Task 5: CLI entry point + update current_step_plan

**Files:**
- Create: `apps/api/livewell/ingestion/cli.py`
- Modify: `apps/web/current_step_plan.md`

- [ ] **Step 1: Create cli.py**

Create `apps/api/livewell/ingestion/cli.py`:

```python
"""CLI entry point for running ingestion manually or from cron."""
from __future__ import annotations

import argparse
import logging

from livewell.ingestion.ingest import run_ingestion

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch OHLCV data to S3")
    parser.add_argument(
        "--instruments",
        nargs="*",
        help="S3 key names to ingest (e.g. EURUSD GBPUSD). Defaults to all.",
    )
    parser.add_argument(
        "--backfill",
        action="store_true",
        help="Fetch full 2-year history instead of incremental update.",
    )
    args = parser.parse_args()
    result = run_ingestion(instruments=args.instruments, backfill=args.backfill)
    if result["failed"]:
        raise SystemExit(f"Failed instruments: {result['failed']}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Smoke-test the CLI (requires LIVEWELL_BUCKET set)**

```bash
cd apps/api && LIVEWELL_BUCKET=your-bucket uv run python -m livewell.ingestion.cli --help
```

Expected:
```
usage: cli.py [-h] [--instruments [INSTRUMENTS ...]] [--backfill]
...
```

- [ ] **Step 3: Update current_step_plan.md**

Replace the contents of `apps/web/current_step_plan.md` with:

```markdown
# Current Step: Sub-project 1B — Feature Generation

**Sub-project 1A status:** Complete
- yfinance ingestion for 5 instruments: EUR/USD, GBP/USD, USD/JPY, Gold, US 500
- Daily (1d) and hourly (1h) OHLCV stored as Parquet in S3
- Per-instrument error isolation; idempotent re-runs
- Backfill mode fetches 2-year history; incremental mode fetches last 7d (1d) / 30d (1h)
- CLI: `uv run python -m livewell.ingestion.cli [--instruments ...] [--backfill]`
- Lambda-ready: `run_ingestion()` callable from thin handler, config via env vars
- 13 tests (constants, S3 helpers, core logic, error isolation)

**Phase 1D status:** Complete
- Vite proxy: `/api/*` forwarded to `localhost:8000`
- MSW gated behind `VITE_USE_MOCKS=true` (off by default in dev; on for tests)
- 3 new FastAPI routes with hardcoded stubs
- CORS expanded to cover ports 5173–5175 + 4173
- 65 frontend tests passing, 14 backend tests passing

---

## Next: Sub-project 1B — Feature Generation

- Read 1d and 1h OHLCV Parquet from S3
- Compute EMA-20, EMA-50, RSI-14, MACD, ATR-14 per instrument
- Write feature tables back to S3 as Parquet
- Unit-test each indicator against known values
```

- [ ] **Step 4: Commit**

```bash
git add apps/api/livewell/ingestion/cli.py apps/web/current_step_plan.md
git commit -m "feat: add ingestion CLI entry point; update step plan to 1B"
```

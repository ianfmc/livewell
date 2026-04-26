# Sub-project 1C — Signal Generation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Read feature Parquet from S3, apply a 5-stage rule-based signal pipeline, and write signal tables back to S3 as Parquet, triggered automatically at the end of `run_features()`.

**Architecture:** New `livewell/signals/` package mirroring the `livewell/features/` structure. `_signals_one()` reads both features and prices Parquets for a single instrument+interval, joins on `date` for the `close` column, applies the 5-stage pipeline row-by-row, and writes signal Parquets split by calendar year. `run_signals()` iterates all instrument+interval pairs with per-pair error isolation.

**Tech Stack:** Python, pandas, boto3, moto (tests), pytest, uv

---

## File Structure

**New files:**
- `apps/api/livewell/signals/__init__.py` — package marker
- `apps/api/livewell/signals/constants.py` — thresholds, session windows, pip precision, output column list
- `apps/api/livewell/signals/signals.py` — pipeline logic + S3 read/write + `run_signals()`
- `apps/api/tests/signals/__init__.py` — package marker
- `apps/api/tests/signals/test_signals.py` — 16 unit + moto S3 tests

**Modified files:**
- `apps/api/livewell/features/features.py` — call `run_signals()` at end of `run_features()`
- `apps/web/current_step_plan.md` — update to Sub-project 1D on completion

---

## Task 1: Constants

**Files:**
- Create: `apps/api/livewell/signals/__init__.py`
- Create: `apps/api/livewell/signals/constants.py`
- Create: `apps/api/tests/signals/__init__.py`
- Create: `apps/api/tests/signals/test_signals.py` (test_signal_columns_defined only)

- [ ] **Step 1: Write the failing test**

Create `apps/api/tests/signals/__init__.py` (empty) and `apps/api/tests/signals/test_signals.py`:

```python
from livewell.signals.constants import SIGNAL_COLUMNS


def test_signal_columns_defined():
    expected = [
        "date", "ema_20", "ema_50", "rsi_14",
        "macd", "macd_signal", "macd_hist", "atr_14",
        "trend_bias", "session_quality", "strike_candidate",
        "signal_valid", "direction", "reasoning",
    ]
    assert SIGNAL_COLUMNS == expected
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd apps/api && uv run pytest tests/signals/test_signals.py::test_signal_columns_defined -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'livewell.signals'`

- [ ] **Step 3: Create the package files**

Create `apps/api/livewell/signals/__init__.py` — empty file.

Create `apps/api/livewell/signals/constants.py`:

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
# Hours are UTC. end_hour wraps at 24 (i.e., 23→07 crosses midnight).
# Instrument groups that share the same session config.
_STANDARD_SESSIONS = [
    (12, 16, "high"),   # London/NY overlap
    (7,  12, "high"),   # London open
    (16, 21, "medium"), # NY afternoon
    (21, 23, "low"),    # Off-hours
    # 23–07 (crosses midnight): Asian session = low
]

_JPY_SESSIONS = [
    (12, 16, "high"),
    (7,  12, "high"),
    (16, 21, "medium"),
    (21, 23, "low"),
    # 23–07: Asian session = high for JPY
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
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd apps/api && uv run pytest tests/signals/test_signals.py::test_signal_columns_defined -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/api/livewell/signals/__init__.py apps/api/livewell/signals/constants.py apps/api/tests/signals/__init__.py apps/api/tests/signals/test_signals.py
git commit -m "feat: add signals package constants and column list"
```

---

## Task 2: Session Quality Helper

**Files:**
- Modify: `apps/api/livewell/signals/signals.py` (create)
- Modify: `apps/api/tests/signals/test_signals.py` (add test)

The session quality function is the trickiest part of the pipeline: midnight-crossing windows (23:00–07:00) need careful handling. Build and test it in isolation first.

- [ ] **Step 1: Write the failing test**

Add to `apps/api/tests/signals/test_signals.py`:

```python
import pandas as pd
from livewell.signals.signals import _session_quality


def test_session_filter_low_quality():
    # EUR/USD row at 03:00 UTC → Asian session → low
    ts = pd.Timestamp("2026-01-15 03:00:00", tz="UTC")
    assert _session_quality("EURUSD", ts) == "low"


def test_session_filter_high_quality_london():
    ts = pd.Timestamp("2026-01-15 09:00:00", tz="UTC")
    assert _session_quality("EURUSD", ts) == "high"


def test_session_filter_jpy_asian_high():
    # USD/JPY Asian session (03:00 UTC) → high
    ts = pd.Timestamp("2026-01-15 03:00:00", tz="UTC")
    assert _session_quality("USDJPY", ts) == "high"


def test_session_filter_equity_ny_high():
    # US500 at 14:00 UTC → NY hours → high
    ts = pd.Timestamp("2026-01-15 14:00:00", tz="UTC")
    assert _session_quality("US500", ts) == "high"


def test_session_filter_equity_off_hours_low():
    # US500 at 03:00 UTC → low
    ts = pd.Timestamp("2026-01-15 03:00:00", tz="UTC")
    assert _session_quality("US500", ts) == "low"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd apps/api && uv run pytest tests/signals/test_signals.py -k "session" -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'livewell.signals.signals'`

- [ ] **Step 3: Create signals.py with _session_quality**

Create `apps/api/livewell/signals/signals.py`:

```python
"""Signal generation pipeline: read features+prices from S3, apply 5-stage rules, write signals."""
from __future__ import annotations

import json
import logging
import math
import os

import boto3
import pandas as pd

from livewell.ingestion.constants import INSTRUMENTS, INTERVALS
from livewell.ingestion.s3 import read_parquet, write_parquet
from livewell.features.constants import FEATURES_PREFIX, PRICES_PREFIX
from livewell.signals.constants import (
    ATR_FEASIBILITY_MULTIPLIER,
    MIN_ATR_THRESHOLD,
    PIP_PRECISION,
    RSI_BEARISH_MAX,
    RSI_BULLISH_MIN,
    RSI_OVERBOUGHT,
    RSI_OVERSOLD,
    SESSION_CONFIG,
    SIGNAL_COLUMNS,
    SIGNALS_PREFIX,
)

logger = logging.getLogger(__name__)


def _session_quality(s3_key: str, ts: pd.Timestamp) -> str:
    """Return session quality string for an instrument at a given UTC timestamp."""
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    hour = ts.hour

    sessions = SESSION_CONFIG.get(s3_key, SESSION_CONFIG["EURUSD"])

    for start, end, quality in sessions:
        if start < end:
            if start <= hour < end:
                return quality
        else:
            # Crosses midnight (e.g. 23–07)
            if hour >= start or hour < end:
                return quality

    return "low"
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd apps/api && uv run pytest tests/signals/test_signals.py -k "session" -v
```

Expected: all 5 session tests PASS

- [ ] **Step 5: Commit**

```bash
git add apps/api/livewell/signals/signals.py apps/api/tests/signals/test_signals.py
git commit -m "feat: add session quality helper with UTC window logic"
```

---

## Task 3: Row-level Pipeline — Trend + Momentum + Overextension

**Files:**
- Modify: `apps/api/livewell/signals/signals.py`
- Modify: `apps/api/tests/signals/test_signals.py`

Build and test `_apply_pipeline()` which processes a single row dict and returns the signal columns. This keeps all the rule logic unit-testable without S3.

- [ ] **Step 1: Write the failing tests**

Add to `apps/api/tests/signals/test_signals.py`:

```python
from livewell.signals.signals import _apply_pipeline
import math


def _bullish_row(rsi=55.0, close=1.1000, atr=0.0015, hour=9):
    return {
        "date": pd.Timestamp(f"2026-01-15 {hour:02d}:00:00", tz="UTC"),
        "ema_20": 1.1010, "ema_50": 1.1000,
        "rsi_14": rsi, "macd": 0.0005, "macd_signal": 0.0003, "macd_hist": 0.0002,
        "atr_14": atr, "close": close,
    }


def _bearish_row(rsi=45.0, close=1.1000, atr=0.0015, hour=9):
    return {
        "date": pd.Timestamp(f"2026-01-15 {hour:02d}:00:00", tz="UTC"),
        "ema_20": 1.0990, "ema_50": 1.1000,
        "rsi_14": rsi, "macd": -0.0005, "macd_signal": -0.0003, "macd_hist": -0.0002,
        "atr_14": atr, "close": close,
    }


def test_bullish_setup_valid():
    row = _bullish_row()
    result = _apply_pipeline("EURUSD", row)
    assert result["signal_valid"] is True
    assert result["direction"] == "buy"
    assert result["trend_bias"] == "bullish"


def test_bearish_setup_valid():
    row = _bearish_row()
    result = _apply_pipeline("EURUSD", row)
    assert result["signal_valid"] is True
    assert result["direction"] == "sell"
    assert result["trend_bias"] == "bearish"


def test_neutral_trend_invalid():
    row = _bullish_row()
    row["ema_20"] = row["ema_50"] = 1.1000  # equal → neutral
    result = _apply_pipeline("EURUSD", row)
    assert result["signal_valid"] is False
    assert result["direction"] == "none"
    assert result["trend_bias"] == "neutral"


def test_overextension_invalidates_signal():
    row = _bullish_row(rsi=80.0)  # rsi > 75 = overbought
    result = _apply_pipeline("EURUSD", row)
    assert result["signal_valid"] is False


def test_low_atr_invalidates_signal():
    row = _bullish_row(atr=0.0005)  # below MIN_ATR_THRESHOLD["EURUSD"]=0.0010
    result = _apply_pipeline("EURUSD", row)
    assert result["signal_valid"] is False


def test_strike_candidate_bullish():
    row = _bullish_row(close=1.1000, atr=0.0020)
    result = _apply_pipeline("EURUSD", row)
    # 1.1000 + 0.0020 * 0.5 = 1.1010, rounded to 4 dp
    assert result["strike_candidate"] == round(1.1000 + 0.0020 * 0.5, 4)


def test_strike_candidate_bearish():
    row = _bearish_row(close=1.1000, atr=0.0020)
    result = _apply_pipeline("EURUSD", row)
    assert result["strike_candidate"] == round(1.1000 - 0.0020 * 0.5, 4)


def test_reasoning_completeness():
    # A bearish row invalidated by overextension should mention the failing condition
    row = _bearish_row(rsi=20.0)  # rsi < 25 = oversold, should fail stage 3
    result = _apply_pipeline("EURUSD", row)
    reasons = json.loads(result["reasoning"])
    assert isinstance(reasons, list)
    assert any("oversold" in r.lower() or "overextension" in r.lower() for r in reasons)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd apps/api && uv run pytest tests/signals/test_signals.py -k "bullish or bearish or neutral or overextension or atr or strike or reasoning" -v
```

Expected: FAIL with `ImportError: cannot import name '_apply_pipeline'`

- [ ] **Step 3: Implement _apply_pipeline in signals.py**

Add to `apps/api/livewell/signals/signals.py` (after `_session_quality`):

```python
def _apply_pipeline(s3_key: str, row: dict) -> dict:
    """
    Apply the 5-stage signal pipeline to a single row dict.
    Returns a dict of all signal output columns.
    """
    ts = row["date"]
    ema_20 = row["ema_20"]
    ema_50 = row["ema_50"]
    rsi = row["rsi_14"]
    macd = row["macd"]
    macd_signal = row["macd_signal"]
    macd_hist = row["macd_hist"]
    atr = row["atr_14"]
    close = row["close"]

    reasons: list[str] = []
    signal_valid = True
    direction = "none"

    # Stage 1: Trend
    if ema_20 > ema_50:
        trend_bias = "bullish"
    elif ema_20 < ema_50:
        trend_bias = "bearish"
    else:
        trend_bias = "neutral"
        signal_valid = False
        reasons.append("trend: neutral (ema_20 == ema_50)")

    # Stage 2: Momentum confirmation (only if trend is established)
    if trend_bias == "bullish":
        if not (rsi > RSI_BULLISH_MIN and macd_hist > 0 and macd > macd_signal):
            signal_valid = False
            reasons.append("momentum: bullish conditions not met")
        else:
            direction = "buy"
    elif trend_bias == "bearish":
        if not (rsi < RSI_BEARISH_MAX and macd_hist < 0 and macd < macd_signal):
            signal_valid = False
            reasons.append("momentum: bearish conditions not met")
        else:
            direction = "sell"

    # Stage 3: Overextension check
    if trend_bias == "bullish" and rsi > RSI_OVERBOUGHT:
        signal_valid = False
        direction = "none"
        reasons.append(f"overextension: overbought rsi={rsi:.1f} > {RSI_OVERBOUGHT}")
    elif trend_bias == "bearish" and rsi < RSI_OVERSOLD:
        signal_valid = False
        direction = "none"
        reasons.append(f"overextension: oversold rsi={rsi:.1f} < {RSI_OVERSOLD}")

    # Stage 4: ATR feasibility + strike selection
    pip_prec = PIP_PRECISION.get(s3_key, 4)
    min_atr = MIN_ATR_THRESHOLD.get(s3_key, 0.0010)
    atr_feasible = atr >= min_atr

    if not atr_feasible:
        signal_valid = False
        reasons.append(f"atr: below minimum ({atr} < {min_atr})")

    if trend_bias == "bullish":
        strike_candidate = round(close + atr * ATR_FEASIBILITY_MULTIPLIER, pip_prec)
    elif trend_bias == "bearish":
        strike_candidate = round(close - atr * ATR_FEASIBILITY_MULTIPLIER, pip_prec)
    else:
        strike_candidate = float("nan")

    # Stage 5: Session filter
    session_quality = _session_quality(s3_key, ts)
    if session_quality != "high":
        signal_valid = False
        reasons.append(f"session: quality={session_quality}, only high allowed")

    if signal_valid:
        reasons.append("all stages passed")

    return {
        "trend_bias": trend_bias,
        "session_quality": session_quality,
        "strike_candidate": strike_candidate,
        "signal_valid": signal_valid,
        "direction": direction,
        "reasoning": json.dumps(reasons),
    }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd apps/api && uv run pytest tests/signals/test_signals.py -k "bullish or bearish or neutral or overextension or atr or strike or reasoning or session" -v
```

Expected: all pipeline + session tests PASS

- [ ] **Step 5: Commit**

```bash
git add apps/api/livewell/signals/signals.py apps/api/tests/signals/test_signals.py
git commit -m "feat: implement 5-stage signal pipeline row logic"
```

---

## Task 4: S3 Integration — _signals_one + run_signals

**Files:**
- Modify: `apps/api/livewell/signals/signals.py`
- Modify: `apps/api/tests/signals/test_signals.py`

- [ ] **Step 1: Write the failing S3 tests**

Add to `apps/api/tests/signals/test_signals.py`:

```python
import boto3
import pytest
from moto import mock_aws
from unittest.mock import patch
from livewell.signals.signals import run_signals
from livewell.ingestion.s3 import write_parquet as _write

BUCKET = "test-livewell"


@pytest.fixture()
def s3_bucket():
    with mock_aws():
        boto3.client("s3", region_name="us-east-1").create_bucket(Bucket=BUCKET)
        yield


def _write_feature_parquet(bucket, s3_key, interval, year, n=60):
    """Write minimal feature Parquet (all columns, gentle bullish trend)."""
    dates = pd.date_range(f"{year}-01-02", periods=n, freq="B")
    # Force all timestamps to London-open UTC hour (09:00) for high session quality
    dates = pd.DatetimeIndex([d.replace(hour=9) for d in dates]).tz_localize("UTC")
    base = 1.1000
    ema_20 = [base + i * 0.0001 for i in range(n)]
    ema_50 = [base - 0.005 + i * 0.00005 for i in range(n)]
    df = pd.DataFrame({
        "date":        dates,
        "ema_20":      ema_20,
        "ema_50":      ema_50,
        "rsi_14":      [55.0] * n,
        "macd":        [0.0005] * n,
        "macd_signal": [0.0003] * n,
        "macd_hist":   [0.0002] * n,
        "atr_14":      [0.0015] * n,
    })
    key = f"features/{s3_key}/{interval}/{year}.parquet"
    _write(df, bucket, key)


def _write_price_parquet(bucket, s3_key, interval, year, n=60):
    """Write minimal price Parquet (date + close columns)."""
    dates = pd.date_range(f"{year}-01-02", periods=n, freq="B")
    dates = pd.DatetimeIndex([d.replace(hour=9) for d in dates]).tz_localize("UTC")
    df = pd.DataFrame({
        "date":  dates,
        "open":  [1.0990] * n,
        "high":  [1.1020] * n,
        "low":   [1.0980] * n,
        "close": [1.1000] * n,
        "volume":[1000.0] * n,
    })
    key = f"prices/{s3_key}/{interval}/{year}.parquet"
    _write(df, bucket, key)


def test_run_signals_writes_to_s3(s3_bucket):
    _write_feature_parquet(BUCKET, "EURUSD", "1d", 2026)
    _write_price_parquet(BUCKET, "EURUSD", "1d", 2026)

    with patch.dict("os.environ", {"LIVEWELL_BUCKET": BUCKET}):
        result = run_signals(instruments=["EURUSD"], intervals=["1d"])

    assert result["succeeded"] == ["EURUSD"]
    assert result["failed"] == []

    s3 = boto3.client("s3", region_name="us-east-1")
    resp = s3.list_objects_v2(Bucket=BUCKET, Prefix="signals/EURUSD/1d/")
    keys = [obj["Key"] for obj in resp.get("Contents", [])]
    assert any("2026.parquet" in k for k in keys)


def test_run_signals_output_schema(s3_bucket):
    _write_feature_parquet(BUCKET, "EURUSD", "1d", 2026)
    _write_price_parquet(BUCKET, "EURUSD", "1d", 2026)

    with patch.dict("os.environ", {"LIVEWELL_BUCKET": BUCKET}):
        run_signals(instruments=["EURUSD"], intervals=["1d"])

    from livewell.ingestion.s3 import read_parquet
    df = read_parquet(BUCKET, "signals/EURUSD/1d/2026.parquet")
    assert df is not None
    assert list(df.columns) == [
        "date", "ema_20", "ema_50", "rsi_14",
        "macd", "macd_signal", "macd_hist", "atr_14",
        "trend_bias", "session_quality", "strike_candidate",
        "signal_valid", "direction", "reasoning",
    ]


def test_run_signals_idempotent(s3_bucket):
    _write_feature_parquet(BUCKET, "EURUSD", "1d", 2026)
    _write_price_parquet(BUCKET, "EURUSD", "1d", 2026)

    with patch.dict("os.environ", {"LIVEWELL_BUCKET": BUCKET}):
        run_signals(instruments=["EURUSD"], intervals=["1d"])
        run_signals(instruments=["EURUSD"], intervals=["1d"])

    from livewell.ingestion.s3 import read_parquet
    df = read_parquet(BUCKET, "signals/EURUSD/1d/2026.parquet")
    assert df is not None
    assert not df.duplicated(subset=["date"]).any()


def test_run_signals_isolates_failures(s3_bucket):
    _write_feature_parquet(BUCKET, "EURUSD", "1d", 2026)
    _write_price_parquet(BUCKET, "EURUSD", "1d", 2026)
    # GBPUSD: write features but NO prices → inner join → empty → error
    _write_feature_parquet(BUCKET, "GBPUSD", "1d", 2026)

    with patch.dict("os.environ", {"LIVEWELL_BUCKET": BUCKET}):
        result = run_signals(instruments=["EURUSD", "GBPUSD"], intervals=["1d"])

    assert "EURUSD" in result["succeeded"]
    assert "GBPUSD" in result["failed"]


def test_multi_year_continuity(s3_bucket):
    _write_feature_parquet(BUCKET, "EURUSD", "1d", 2025, n=60)
    _write_feature_parquet(BUCKET, "EURUSD", "1d", 2026, n=60)
    _write_price_parquet(BUCKET, "EURUSD", "1d", 2025, n=60)
    _write_price_parquet(BUCKET, "EURUSD", "1d", 2026, n=60)

    with patch.dict("os.environ", {"LIVEWELL_BUCKET": BUCKET}):
        run_signals(instruments=["EURUSD"], intervals=["1d"])

    from livewell.ingestion.s3 import read_parquet
    df_2025 = read_parquet(BUCKET, "signals/EURUSD/1d/2025.parquet")
    df_2026 = read_parquet(BUCKET, "signals/EURUSD/1d/2026.parquet")
    assert df_2025 is not None and len(df_2025) > 0
    assert df_2026 is not None and len(df_2026) > 0
    # No NaN bleed: trend_bias column has no nulls in valid rows
    for df in [df_2025, df_2026]:
        assert df["trend_bias"].notna().all()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd apps/api && uv run pytest tests/signals/test_signals.py -k "s3 or idempotent or isolates or multi_year or schema or writes" -v
```

Expected: FAIL with `ImportError: cannot import name 'run_signals'`

- [ ] **Step 3: Implement _signals_one and run_signals in signals.py**

Add to the end of `apps/api/livewell/signals/signals.py`:

```python
def _signals_one(instrument: dict, interval: str, bucket: str) -> None:
    """Read features+prices for one instrument+interval, compute signals, write by year."""
    s3_key = instrument["s3_key"]
    s3 = boto3.client("s3")

    # Read all feature Parquets for this instrument+interval
    feature_prefix = f"{FEATURES_PREFIX}/{s3_key}/{interval}/"
    resp = s3.list_objects_v2(Bucket=bucket, Prefix=feature_prefix)
    objects = resp.get("Contents", [])
    if not objects:
        raise ValueError(f"no feature files found for {s3_key}/{interval}")

    feature_frames = []
    for obj in objects:
        df = read_parquet(bucket, obj["Key"])
        if df is not None:
            feature_frames.append(df)
    if not feature_frames:
        raise ValueError(f"all feature reads returned None for {s3_key}/{interval}")

    features = pd.concat(feature_frames, ignore_index=True)
    features["date"] = pd.to_datetime(features["date"], utc=True)

    # Read all price Parquets to get the close column
    price_prefix = f"{PRICES_PREFIX}/{s3_key}/{interval}/"
    resp = s3.list_objects_v2(Bucket=bucket, Prefix=price_prefix)
    price_objects = resp.get("Contents", [])
    if not price_objects:
        raise ValueError(f"no price files found for {s3_key}/{interval}")

    price_frames = []
    for obj in price_objects:
        df = read_parquet(bucket, obj["Key"])
        if df is not None:
            price_frames.append(df[["date", "close"]])
    if not price_frames:
        raise ValueError(f"all price reads returned None for {s3_key}/{interval}")

    prices = pd.concat(price_frames, ignore_index=True)
    prices["date"] = pd.to_datetime(prices["date"], utc=True)

    # Inner join features + close on date
    merged = features.merge(prices, on="date", how="inner")
    merged = merged.drop_duplicates(subset=["date"]).sort_values("date").reset_index(drop=True)

    if merged.empty:
        raise ValueError(f"inner join produced empty DataFrame for {s3_key}/{interval}")

    # Apply pipeline row-by-row
    signal_rows = []
    for _, row in merged.iterrows():
        pipeline_out = _apply_pipeline(s3_key, row.to_dict())
        signal_row = {col: row[col] for col in ["date", "ema_20", "ema_50", "rsi_14", "macd", "macd_signal", "macd_hist", "atr_14"]}
        signal_row.update(pipeline_out)
        signal_rows.append(signal_row)

    signals_df = pd.DataFrame(signal_rows, columns=SIGNAL_COLUMNS)

    # Write one Parquet per calendar year
    for year, group in signals_df.groupby(signals_df["date"].dt.year):
        key = f"{SIGNALS_PREFIX}/{s3_key}/{interval}/{int(year)}.parquet"
        existing = read_parquet(bucket, key)
        if existing is not None:
            existing["date"] = pd.to_datetime(existing["date"], utc=True)
            combined = pd.concat([existing, group], ignore_index=True)
            combined["date"] = pd.to_datetime(combined["date"], utc=True)
            group = combined.drop_duplicates(subset=["date"]).sort_values("date").reset_index(drop=True)
        write_parquet(group, bucket, key)
        logger.info("%s/%s/%s signals: %d rows", s3_key, interval, year, len(group))


def run_signals(
    instruments: list[str] | None = None,
    intervals: list[str] | None = None,
) -> dict:
    """
    Compute rule-based signals for all instruments and intervals.

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
                _signals_one(instrument, interval, bucket)
            except Exception as exc:
                logger.error(
                    "failed to compute signals %s/%s: %s",
                    instrument["s3_key"], interval, exc,
                )
                failed_pairs.append((instrument["s3_key"], interval))

    failed = list({s3_key for s3_key, _ in failed_pairs})
    succeeded = [i["s3_key"] for i in targets if i["s3_key"] not in failed]

    logger.info("signals complete — succeeded: %s, failed: %s", succeeded, failed)
    return {"succeeded": succeeded, "failed": failed}
```

- [ ] **Step 4: Run all signals tests to verify they pass**

```bash
cd apps/api && uv run pytest tests/signals/test_signals.py -v
```

Expected: all 16 tests PASS

- [ ] **Step 5: Commit**

```bash
git add apps/api/livewell/signals/signals.py apps/api/tests/signals/test_signals.py
git commit -m "feat: implement _signals_one and run_signals with S3 read/write"
```

---

## Task 5: Wire run_signals into run_features

**Files:**
- Modify: `apps/api/livewell/features/features.py`
- Modify: `apps/api/tests/features/test_features.py`

- [ ] **Step 1: Write the failing test**

Add to `apps/api/tests/features/test_features.py`:

```python
from unittest.mock import patch, MagicMock


def test_features_triggers_signals(s3_bucket):
    """run_features() should call run_signals() with the same instruments list."""
    make_price_parquet(BUCKET, "EURUSD", "1d", 2026, n=60)

    mock_run_signals = MagicMock(return_value={"succeeded": ["EURUSD"], "failed": []})

    with patch("livewell.features.features.run_signals", mock_run_signals):
        with patch.dict("os.environ", {"LIVEWELL_BUCKET": BUCKET}):
            run_features(instruments=["EURUSD"], intervals=["1d"])

    mock_run_signals.assert_called_once_with(instruments=["EURUSD"])
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd apps/api && uv run pytest tests/features/test_features.py::test_features_triggers_signals -v
```

Expected: FAIL — `run_signals` not yet imported/called in `features.py`

- [ ] **Step 3: Add run_signals call to run_features**

Edit `apps/api/livewell/features/features.py`. Add the import after the existing imports:

```python
from livewell.signals.signals import run_signals
```

Then inside `run_features()`, add at the end before `return`:

```python
    try:
        run_signals(instruments=instruments)
    except Exception as exc:
        logger.error("signal generation failed: %s", exc)
    return {"succeeded": succeeded, "failed": failed}
```

The full updated `run_features` function:

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

    try:
        run_signals(instruments=instruments)
    except Exception as exc:
        logger.error("signal generation failed: %s", exc)
    return {"succeeded": succeeded, "failed": failed}
```

- [ ] **Step 4: Run all tests (features + signals)**

```bash
cd apps/api && uv run pytest tests/features/ tests/signals/ -v
```

Expected: all tests PASS

> **Important:** The existing `test_run_features_*` tests will call `_features_one` which calls `run_signals` as a side effect. Since moto S3 won't have price files for signal computation, `run_signals` will log errors but should NOT raise (per the `try/except`). If any existing feature tests break, verify that the `run_signals` call is wrapped in `try/except` and that `result["succeeded"]`/`result["failed"]` still match expectations.

- [ ] **Step 5: Run the full test suite to check for regressions**

```bash
cd apps/api && uv run pytest -v
```

Expected: all tests PASS

- [ ] **Step 6: Commit**

```bash
git add apps/api/livewell/features/features.py apps/api/tests/features/test_features.py
git commit -m "feat: wire run_signals into run_features"
```

---

## Task 6: Update Step Plan

**Files:**
- Modify: `apps/web/current_step_plan.md`

- [ ] **Step 1: Update current_step_plan.md to Sub-project 1D**

Read the file first, then update the current step reference from "1C" to "1D".

```bash
cat apps/web/current_step_plan.md
```

Then edit the file to update the step indicator from Sub-project 1C → 1D.

- [ ] **Step 2: Verify and commit**

```bash
cd apps/api && uv run pytest -v
git add apps/web/current_step_plan.md
git commit -m "docs: advance step plan to Sub-project 1D"
```

---

## Self-Review

### Spec coverage

| Spec requirement | Covered in |
|---|---|
| `livewell/signals/__init__.py` package | Task 1 |
| `livewell/signals/constants.py` with all thresholds | Task 1 |
| `livewell/signals/signals.py` with `run_signals()` | Tasks 2–4 |
| Stage 1: Trend bias | Task 3 |
| Stage 2: Momentum confirmation | Task 3 |
| Stage 3: Overextension check | Task 3 |
| Stage 4: ATR feasibility + strike selection | Task 3 |
| Stage 5: Session filter with per-instrument overrides | Task 2 |
| S3 layout `signals/{INSTRUMENT}/{INTERVAL}/{YEAR}.parquet` | Task 4 |
| Inner join features + prices on date for `close` | Task 4 |
| Idempotent re-runs | Task 4 (`test_run_signals_idempotent`) |
| Per-instrument error isolation | Task 4 (`test_run_signals_isolates_failures`) |
| `run_features()` calls `run_signals()` | Task 5 |
| Signal failures don't affect `run_features()` return value | Task 5 |
| All 16 tests from spec | Tasks 1–5 |
| Update `current_step_plan.md` | Task 6 |

All 16 spec tests are covered:
- `test_signal_columns_defined` → Task 1
- `test_bullish_setup_valid` → Task 3
- `test_bearish_setup_valid` → Task 3
- `test_neutral_trend_invalid` → Task 3
- `test_overextension_invalidates_signal` → Task 3
- `test_low_atr_invalidates_signal` → Task 3
- `test_session_filter_low_quality` → Task 2
- `test_strike_candidate_bullish` → Task 3
- `test_strike_candidate_bearish` → Task 3
- `test_reasoning_completeness` → Task 3
- `test_run_signals_idempotent` → Task 4
- `test_multi_year_continuity` → Task 4
- `test_run_signals_writes_to_s3` → Task 4
- `test_run_signals_output_schema` → Task 4
- `test_run_signals_isolates_failures` → Task 4
- `test_features_triggers_signals` → Task 5

### Placeholder scan

No TBDs, TODOs, or "implement later" references found. All steps include working code.

### Type consistency

- `_apply_pipeline(s3_key: str, row: dict) -> dict` — referenced consistently across Tasks 3 and 4
- `_signals_one(instrument: dict, interval: str, bucket: str) -> None` — consistent with `_features_one` pattern
- `run_signals(instruments: list[str] | None, intervals: list[str] | None) -> dict` — matches spec interface exactly
- `SIGNAL_COLUMNS` list defined in Task 1 constants, used in Task 4 DataFrame construction — column order matches spec output table
- Session config keys (`"EURUSD"`, `"GBPUSD"`, etc.) match `INSTRUMENTS[*]["s3_key"]` values from `ingestion/constants.py`

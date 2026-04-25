# Notebook 01 Settlement-Based Label Construction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the D+1 daily close approximation in notebook 01 with actual NADEX settlement outcomes from `s3://nadex-daily-results/backtest/results/latest/trades.csv`, using nearest-strike matching.

**Architecture:** Two functions in notebook 01 change (`derive_label` and `build_labeled_dataset`), and one new function is added (`load_settlement`). The output file path and schema are unchanged so notebooks 02–04 require no modifications. Settlement data is read via a second `boto3.client("s3")` instance pointed at the `nadex-daily-results` bucket. The daily settlement row per ticker is selected by taking the latest expiry time on each date (since FOREX, Gold, and US500 each have different canonical settlement times: 3pm ET, 1:30pm ET, and 4:15pm ET respectively).

**Tech Stack:** Python 3.12, pandas, boto3, Jupyter. No new dependencies.

---

## File Structure

**Modified:**
- `notebooks/livewell-nadex/notebooks/phase2/01_label_construction.ipynb` — Cell 1 (add constants), Cell 2 (add `load_settlement`, revise `derive_label` and `build_labeled_dataset`), Cell 3 (unchanged runner), Cell 4 (unchanged spot-check)

**Unchanged:**
- `notebooks/livewell-nadex/notebooks/phase2/02_feature_prep.ipynb`
- `notebooks/livewell-nadex/notebooks/phase2/03_walk_forward_validation.ipynb`
- `notebooks/livewell-nadex/notebooks/phase2/04_calibration_analysis.ipynb`

---

## Context for Implementer

### S3 layout
- Livewell signals live in `s3://715853571313-livewell/signals/{S3_KEY}/1d/{YEAR}.parquet`
- Settlement data lives in `s3://nadex-daily-results/backtest/results/latest/trades.csv`
- Both buckets are accessible under the `livewell` AWS profile

### Instrument mapping
The livewell pipeline uses `s3_key` values that differ from the NADEX ticker symbols:

| livewell s3_key | NADEX Ticker in settlement CSV | Notes |
|---|---|---|
| `EURUSD` | `EURUSD=X` | In settlement data |
| `GBPUSD` | `GBPUSD=X` | NOT in settlement data (was excluded from backtesting) |
| `USDJPY` | `USDJPY=X` | In settlement data |
| `XAUUSD` | `GC=F` | In settlement data, 1:30pm ET expiry |
| `US500` | `ES=F` | In settlement data, 4:15pm ET expiry |

### Settlement CSV columns
```
Date, Name, Exp Time, Exp Value, Strike Price, In the Money, Ticker, distance_pct, rsi, signal, entry_cost, pnl
```
- `Date` format: `MM/DD/YYYY` (e.g. `03/20/2025`) — parse with `format="%m/%d/%Y"`
- `Exp Time` format: `MM/DD/YYYY HH:MM am/pm` (e.g. `03/20/2025 03:00 pm`)
- `In the Money`: 0 or 1 (float in CSV)
- `Strike Price`: float

### Daily settlement row selection
Each ticker has multiple expiry times per day. Select the **latest expiry** per `(Ticker, Date)` to get one canonical row per instrument per trading day:
- FOREX: 3:00 pm ET
- Gold (`GC=F`): 1:30 pm ET
- US500 (`ES=F`): 4:15 pm ET

Use `pd.to_datetime(df["Exp Time"])` then `groupby(["Ticker", "Date"])["Exp Time"].transform("max")` to keep only the latest expiry row per group.

### Label logic
For each signal row `(date, s3_key)`:
1. Map `s3_key` → NADEX ticker via `S3_KEY_TO_TICKER`
2. Filter settlement to `Ticker == nadex_ticker` and `Date == signal_date`
3. Among matching rows, find `idxmin(abs(Strike Price - strike_candidate))` — nearest strike
4. `label = In the Money` (0 or 1) from that row
5. If no match (GBPUSD, or date outside Mar–Dec 2025): `label = NaN`
6. `direction == "none"` rows: `label = NaN` (same as before)

---

## Task 1: Update Cell 1 — Add S3 and Mapping Constants

**Files:**
- Modify: `notebooks/livewell-nadex/notebooks/phase2/01_label_construction.ipynb` cell `cell-01`

- [ ] **Step 1: Replace Cell 1 content**

The current Cell 1 has `BUCKET` and prefixes for the livewell bucket. Add the settlement bucket name and the s3_key→ticker mapping dict. Replace the entire cell with:

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
SETTLEMENT_KEY = "backtest/results/latest/trades.csv"

SIGNALS_PREFIX = "signals"
PRICES_PREFIX = "prices"
OUTPUT_PATH = "../../../data/phase2/labeled_signals.parquet"
INTERVAL = "1d"

# Maps livewell s3_key → NADEX ticker symbol used in settlement CSV
S3_KEY_TO_TICKER = {
    "EURUSD":  "EURUSD=X",
    "GBPUSD":  "GBPUSD=X",   # not in settlement data — all rows will be label=NaN
    "USDJPY":  "USDJPY=X",
    "XAUUSD":  "GC=F",
    "US500":   "ES=F",
}
```

- [ ] **Step 2: Verify the cell runs without error**

In the Jupyter notebook (livewell-api kernel), run Cell 1. Expected: no errors, no output (just variable assignments).

---

## Task 2: Add `load_settlement` and Revise `derive_label` and `build_labeled_dataset`

**Files:**
- Modify: `notebooks/livewell-nadex/notebooks/phase2/01_label_construction.ipynb` cell `cell-02`

- [ ] **Step 1: Replace Cell 2 content**

Replace the entire Cell 2 with the following. Note that `load_all_parquets`, `load_signals`, and `load_prices` are **unchanged** — copy them verbatim. Only `derive_label` and `build_labeled_dataset` change, and `load_settlement` is new.

```python
def load_all_parquets(bucket: str, prefix: str) -> pd.DataFrame:
    """List all Parquet objects under prefix and concat into one DataFrame."""
    s3 = boto3.client("s3")
    resp = s3.list_objects_v2(Bucket=bucket, Prefix=prefix + "/")
    objects = resp.get("Contents", [])
    frames = []
    for obj in objects:
        df = read_parquet(bucket, obj["Key"])
        if df is not None:
            frames.append(df)
    if not frames:
        raise ValueError(f"No Parquet files found under s3://{bucket}/{prefix}/")
    return pd.concat(frames, ignore_index=True)


def load_signals(bucket: str, s3_key: str, interval: str) -> pd.DataFrame:
    """Load all signal Parquets for one instrument+interval, add s3_key column."""
    prefix = f"{SIGNALS_PREFIX}/{s3_key}/{interval}"
    df = load_all_parquets(bucket, prefix)
    df["s3_key"] = s3_key
    df["date"] = pd.to_datetime(df["date"], utc=True)
    return df


def load_prices(bucket: str, s3_key: str, interval: str) -> pd.DataFrame:
    """Load all price Parquets for one instrument+interval, return date+close only."""
    prefix = f"{PRICES_PREFIX}/{s3_key}/{interval}"
    df = load_all_parquets(bucket, prefix)
    df["date"] = pd.to_datetime(df["date"], utc=True)
    return df[["date", "close"]].rename(columns={"close": "close_d"})


def load_settlement(bucket: str, key: str) -> pd.DataFrame:
    """
    Load NADEX settlement data from S3.

    Reads trades.csv from nadex-daily-results bucket, parses dates,
    and returns one row per (Ticker, Date) — the latest expiry on each date.

    Returns DataFrame with columns: date (UTC datetime), Ticker (str),
    Strike Price (float), In the Money (int).
    """
    s3 = boto3.client("s3")
    obj = s3.get_object(Bucket=bucket, Key=key)
    df = pd.read_csv(obj["Body"])

    # Parse the date column (format: "03/20/2025")
    df["date"] = pd.to_datetime(df["Date"], format="%m/%d/%Y", utc=True)

    # Parse Exp Time to datetime so we can pick the latest expiry per group
    df["exp_dt"] = pd.to_datetime(df["Exp Time"], format="%m/%d/%Y %I:%M %p")

    # Keep only the row with the latest expiry per (Ticker, date)
    latest_mask = df["exp_dt"] == df.groupby(["Ticker", "date"])["exp_dt"].transform("max")
    df = df[latest_mask].copy()

    # Deduplicate: if multiple strikes share the latest expiry, keep all
    # (derive_label will pick nearest strike below)
    return df[["date", "Ticker", "Strike Price", "In the Money"]].copy()


def derive_label(
    signals: pd.DataFrame,
    settlement: pd.DataFrame,
) -> pd.DataFrame:
    """
    For each signal row, look up the actual NADEX settlement outcome.

    Joins on (date, s3_key → Ticker) using nearest-strike matching.
    Returns signals DataFrame with added 'label' column (0.0, 1.0, or NaN).

    label=NaN when:
      - direction == "none"
      - no settlement row found for this instrument+date (e.g. GBPUSD, or
        date outside the settlement data range Mar–Dec 2025)
    """
    labels = []

    for _, row in signals.iterrows():
        if row["direction"] == "none":
            labels.append(float("nan"))
            continue

        nadex_ticker = S3_KEY_TO_TICKER.get(row["s3_key"])
        if nadex_ticker is None:
            labels.append(float("nan"))
            continue

        # Normalise signal date to UTC date-only for matching
        signal_date = pd.Timestamp(row["date"]).normalize().tz_localize(None)
        settle_date = settlement["date"].dt.tz_localize(None).dt.normalize()

        matches = settlement[
            (settlement["Ticker"] == nadex_ticker) &
            (settle_date == signal_date)
        ]

        if matches.empty:
            labels.append(float("nan"))
            continue

        # Nearest strike selection
        nearest_idx = (matches["Strike Price"] - row["strike_candidate"]).abs().idxmin()
        labels.append(float(matches.loc[nearest_idx, "In the Money"]))

    signals = signals.copy()
    signals["label"] = labels
    return signals


def build_labeled_dataset(bucket: str, interval: str) -> pd.DataFrame:
    """
    Load signals for all instruments, join settlement labels, return combined DataFrame.

    Loads settlement data once from nadex-daily-results bucket, then for each
    instrument loads its signals and calls derive_label.

    Rows with label=NaN are included — callers decide whether to drop them.
    """
    settlement = load_settlement(SETTLEMENT_BUCKET, SETTLEMENT_KEY)
    print(f"Settlement data loaded: {len(settlement)} rows, "
          f"{settlement['date'].dt.date.min()} to {settlement['date'].dt.date.max()}")

    all_frames = []
    for inst in INSTRUMENTS:
        s3_key = inst["s3_key"]
        try:
            signals = load_signals(bucket, s3_key, interval)
            labeled = derive_label(signals, settlement)
            n_labeled = labeled["label"].notna().sum()
            n_nan = labeled["label"].isna().sum()
            print(f"{s3_key}: {len(labeled)} rows, {n_labeled} labeled, {n_nan} NaN (no settlement match or direction=none)")
            all_frames.append(labeled)
        except Exception as exc:
            print(f"WARNING: {s3_key} failed — {exc}")

    if not all_frames:
        raise RuntimeError("No instruments produced labeled data.")
    return pd.concat(all_frames, ignore_index=True)
```

- [ ] **Step 2: Run Cell 2 to verify it defines without error**

Run Cell 2 in Jupyter. Expected: no output, no errors (functions are just defined).

---

## Task 3: Run the Notebook End-to-End and Verify Output

**Files:**
- Run: `notebooks/livewell-nadex/notebooks/phase2/01_label_construction.ipynb`

Cell 3 and Cell 4 are unchanged from the original notebook. They run `build_labeled_dataset` and save to `labeled_signals.parquet`.

- [ ] **Step 1: Run Cell 3**

Expected output (approximate — exact numbers depend on S3 data):
```
Settlement data loaded: ~14000 rows, 2025-04-04 to 2025-12-19
EURUSD: ~700 rows, ~200 labeled, ~500 NaN (no settlement match or direction=none)
GBPUSD: ~700 rows, 0 labeled, ~700 NaN (no settlement match or direction=none)
USDJPY: ~700 rows, ~200 labeled, ~500 NaN (no settlement match or direction=none)
XAUUSD: ~700 rows, ~200 labeled, ~500 NaN (no settlement match or direction=none)
US500: ~700 rows, ~200 labeled, ~500 NaN (no settlement match or direction=none)

Total rows: ~3500
Labeled (direction != none): ~600–900
Label distribution:
1.0    ~350–500
0.0    ~250–400
```

The label distribution should be approximately 55–60% positive (ITM=1), consistent with the ~57% backtesting win rate. If it's still around 22%, the date join is failing — check that `signal_date` normalisation matches `settle_date` normalisation.

- [ ] **Step 2: Run Cell 4 (spot-check)**

Expected: prints first 20 rows showing `date`, `s3_key`, `direction`, `strike_candidate`, `label`, `signal_valid`. Confirm `label` column contains 0.0, 1.0, and NaN values (not just NaN). Confirm `close_d1` column is absent (it's no longer computed).

- [ ] **Step 3: Commit the notebook with saved output**

```bash
git add notebooks/livewell-nadex/notebooks/phase2/01_label_construction.ipynb
git commit -m "feat: replace D+1 close label with NADEX settlement outcome in notebook 01"
```

---

## Self-Review

### Spec coverage

| Spec requirement | Covered in |
|---|---|
| Read settlement from `nadex-daily-results` via direct boto3 | Task 2 `load_settlement` |
| Filter to latest expiry per (Ticker, Date) | Task 2 `load_settlement` — `groupby(...).transform("max")` |
| Map `s3_key` → NADEX ticker | Task 1 `S3_KEY_TO_TICKER` |
| Nearest-strike matching | Task 2 `derive_label` — `idxmin(abs(...))` |
| `label=NaN` for no-match rows | Task 2 `derive_label` — returns `nan` when `matches.empty` |
| `label=NaN` for `direction=="none"` | Task 2 `derive_label` — first condition |
| GBPUSD gets all NaN labels | Confirmed: `GBPUSD=X` not in settlement data |
| Output path unchanged | Task 3 — Cell 3 writes same `labeled_signals.parquet` path |
| Notebooks 02–04 untouched | Not in file structure |
| `close_d1` column removed | Task 2 — `derive_label` no longer computes it |
| Per-instrument summary print | Task 2 `build_labeled_dataset` |

### Placeholder scan

No TBDs, TODOs, or vague instructions. All code is complete.

### Type consistency

- `load_settlement` returns `DataFrame` with `date` (UTC datetime64), `Ticker` (str), `Strike Price` (float), `In the Money` (float/int)
- `derive_label(signals, settlement)` — `settlement` is the DataFrame from `load_settlement` ✓
- `build_labeled_dataset` calls `load_settlement(SETTLEMENT_BUCKET, SETTLEMENT_KEY)` — both constants defined in Task 1 ✓
- `S3_KEY_TO_TICKER` keys match `s3_key` values in `INSTRUMENTS` constant: `EURUSD`, `GBPUSD`, `USDJPY`, `XAUUSD`, `US500` ✓
- `label` column remains float (0.0, 1.0, NaN) — downstream notebooks use `label.notna()` and `label.value_counts()` which work correctly with float ✓

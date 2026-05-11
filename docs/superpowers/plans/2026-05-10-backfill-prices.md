# Backfill Historical Price Data Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a notebook that backfills 7 years of daily OHLCV price history for all 19 NADEX instruments into S3 so the rules-based backtest covers 2019–present.

**Architecture:** A single Jupyter notebook calls `_ingest_one` from the existing ingestion module per instrument (bypassing `run_features`), then verifies each instrument's date range in S3.

**Tech Stack:** Python, yfinance, boto3, pandas, Jupyter.

---

## File Map

**Create:**
- `notebooks/livewell-nadex/backfill_prices.ipynb` — 4-cell orchestration notebook

---

## Task 1: Create `backfill_prices.ipynb`

**Files:**
- Create: `notebooks/livewell-nadex/backfill_prices.ipynb`

- [ ] **Step 1: Verify the ingestion module is importable from the notebook directory**

```bash
cd /path/to/livewell/apps/api && uv run python -c "
from livewell.ingestion.ingest import _ingest_one
from livewell.ingestion.constants import INSTRUMENTS, INTERVALS
print('ok', len(INSTRUMENTS), 'instruments')
"
```

Expected: `ok 19 instruments`

- [ ] **Step 2: Create the notebook**

Create `notebooks/livewell-nadex/backfill_prices.ipynb` as a valid nbformat 4 Jupyter notebook with the following 4 code cells:

**Cell 1 — Setup:**
```python
import sys, os
sys.path.insert(0, os.path.abspath("../../apps/api"))

import logging
import boto3
import pandas as pd

from livewell.ingestion.ingest import _ingest_one, _s3_key
from livewell.ingestion.constants import INSTRUMENTS, INTERVALS

logging.basicConfig(level=logging.INFO)

BUCKET = "livewell-data-prod"

print(f"Setup complete. {len(INSTRUMENTS)} instruments to backfill.")
```

**Cell 2 — Dry run (print instrument list):**
```python
print(f"{'Name':<20} {'Ticker':<15} {'s3_key'}")
print("-" * 50)
for inst in INSTRUMENTS:
    print(f"{inst['name']:<20} {inst['ticker']:<15} {inst['s3_key']}")
```

**Cell 3 — Backfill loop:**
```python
failed = []

for inst in INSTRUMENTS:
    s3_key = inst["s3_key"]
    print(f"\n→ {inst['name']} ({s3_key}) ...", end=" ", flush=True)
    try:
        _ingest_one(inst, "1d", BUCKET, backfill=True)
        print("✓")
    except Exception as e:
        print(f"✗ FAILED: {e}")
        failed.append(s3_key)

print("\n" + "=" * 50)
if failed:
    print(f"FAILED ({len(failed)}): {', '.join(failed)}")
else:
    print(f"All {len(INSTRUMENTS)} instruments backfilled successfully.")
```

**Cell 4 — Verify:**
```python
s3 = boto3.client("s3")

print(f"{'Instrument':<12} {'Files':<8} {'Min Date':<14} {'Max Date':<14} {'Rows'}")
print("-" * 60)

for inst in INSTRUMENTS:
    s3_key = inst["s3_key"]
    prefix = f"prices/{s3_key}/1d/"
    resp = s3.list_objects_v2(Bucket=BUCKET, Prefix=prefix)
    keys = [o["Key"] for o in resp.get("Contents", [])]
    if not keys:
        print(f"{s3_key:<12} {'NO DATA'}")
        continue

    frames = []
    for key in sorted(keys):
        obj = s3.get_object(Bucket=BUCKET, Key=key)
        import io
        df = pd.read_parquet(io.BytesIO(obj["Body"].read()))
        frames.append(df)

    combined = pd.concat(frames, ignore_index=True)
    combined["date"] = pd.to_datetime(combined["date"])
    min_date = combined["date"].min().strftime("%Y-%m-%d")
    max_date = combined["date"].max().strftime("%Y-%m-%d")
    print(f"{s3_key:<12} {len(keys):<8} {min_date:<14} {max_date:<14} {len(combined)}")
```

- [ ] **Step 3: Confirm the notebook is valid JSON**

```bash
python3 -c "import json; json.load(open('notebooks/livewell-nadex/backfill_prices.ipynb')); print('valid')"
```

Expected: `valid`

- [ ] **Step 4: Commit**

```bash
git add notebooks/livewell-nadex/backfill_prices.ipynb
git commit -m "feat: add backfill_prices notebook to load 7-year price history into S3"
```

---

## Task 2: Run the notebook and verify results

This task is run manually — it requires live AWS credentials and takes ~2–5 minutes.

- [ ] **Step 1: Run the notebook**

```bash
cd /path/to/livewell/apps/api
uv run --with jupyter jupyter nbconvert --to notebook --execute --inplace ../../notebooks/livewell-nadex/backfill_prices.ipynb 2>&1
```

Expected: no errors, notebook written back with outputs.

- [ ] **Step 2: Check Cell 3 output**

Open the notebook and confirm Cell 3 shows `✓` for all 19 instruments and ends with:
```
All 19 instruments backfilled successfully.
```

If any instrument shows `✗ FAILED`, note it and re-run Cell 3 for that instrument alone after diagnosing the error.

- [ ] **Step 3: Check Cell 4 output**

Confirm Cell 4 shows:
- 8 files per instrument (2019–2026)
- Min date on or before `2019-01-07`
- Max date within the last 7 days
- Row counts in the hundreds per instrument

- [ ] **Step 4: Re-run the backtest notebook to confirm meaningful results**

```bash
cd /path/to/livewell/apps/api
uv run --with jupyter jupyter nbconvert --to notebook --execute --inplace ../../notebooks/livewell-nadex/backtest.ipynb 2>&1
```

Expected: Cell 4 shows `Total trades` in the hundreds or thousands, win rate is not 0%.

- [ ] **Step 5: Commit the executed notebook**

```bash
git add notebooks/livewell-nadex/backfill_prices.ipynb notebooks/livewell-nadex/backtest.ipynb
git commit -m "chore: run backfill and backtest notebooks with full price history"
```

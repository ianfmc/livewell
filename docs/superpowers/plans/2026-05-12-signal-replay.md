# Historical Signal Replay Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Populate `livewell-signals-prod` DynamoDB with ~34,000 historical signal records by reading signal Parquet files already in S3, enabling meaningful backtest results across 2019–present.

**Architecture:** A new `replay_signals()` function in `apps/api/livewell/pipeline/replay.py` reads signal Parquets from S3 year-by-year per instrument, skips records already in DynamoDB, normalises `direction` values (`"buy"` → `"call"`, `"sell"` → `"put"`), and batch-writes new records in chunks of 25. A thin notebook orchestrates the run.

**Tech Stack:** Python, boto3, pandas, moto (tests), Jupyter.

---

## File Map

**Create:**
- `apps/api/livewell/pipeline/replay.py` — `replay_signals()` function
- `apps/api/tests/pipeline/test_replay.py` — unit tests (moto + in-memory Parquet)
- `notebooks/livewell-nadex/replay_signals.ipynb` — 3-cell orchestration notebook

---

## Task 1: `replay.py` — core replay function

**Files:**
- Create: `apps/api/livewell/pipeline/replay.py`
- Create: `apps/api/tests/pipeline/test_replay.py`

### Key facts for implementation

Signal Parquet columns: `date`, `ema_20`, `ema_50`, `rsi_14`, `macd`, `macd_signal`, `macd_hist`, `atr_14`, `trend_bias`, `session_quality`, `strike_candidate`, `signal_valid`, `direction`, `reasoning`, `timing_slot`, `timing_risk`

S3 key pattern: `signals/{s3_key}/1d/{year}.parquet` for years 2019–2026

DynamoDB table: `livewell-signals-{env}`, partition key `signal_id` (string)

`direction` normalisation: `"buy"` → `"call"`, `"sell"` → `"put"` (older Parquets use buy/sell)

Existing `put_signal(record)` in `livewell.pipeline.dynamodb` writes one item. Use `batch_writer()` directly for bulk writes (25-item DynamoDB limit is handled automatically by boto3's `batch_writer`).

DynamoDB scan for existing IDs: use `ProjectionExpression="signal_id"` to avoid reading full records.

- [ ] **Step 1: Write the failing tests**

Create `apps/api/tests/pipeline/test_replay.py`:

```python
from __future__ import annotations
import io
import os
import boto3
import pandas as pd
import pytest
from moto import mock_aws
from decimal import Decimal

TABLE_SIGNALS = "livewell-signals-test"
BUCKET = "test-bucket"
YEARS = [2026]


@pytest.fixture(autouse=True)
def aws_env(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")
    monkeypatch.setenv("LIVEWELL_ENV", "test")
    monkeypatch.setenv("LIVEWELL_BUCKET", BUCKET)


def _make_parquet(rows: list[dict]) -> bytes:
    df = pd.DataFrame(rows)
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
    buf = io.BytesIO()
    df.to_parquet(buf, index=False)
    return buf.getvalue()


def _signal_rows(direction="call", n=2):
    return [
        {
            "date": f"2026-01-0{i+1}",
            "ema_20": 1.08, "ema_50": 1.07, "rsi_14": 55.0,
            "macd": 0.001, "macd_signal": 0.0009, "macd_hist": 0.0001,
            "atr_14": 0.005, "trend_bias": "bullish",
            "session_quality": "high", "strike_candidate": 1.085,
            "signal_valid": True, "direction": direction,
            "reasoning": "{}", "timing_slot": "slot1", "timing_risk": "low",
        }
        for i in range(n)
    ]


@pytest.fixture()
def aws_resources():
    with mock_aws():
        ddb = boto3.resource("dynamodb", region_name="us-east-1")
        ddb.create_table(
            TableName=TABLE_SIGNALS,
            KeySchema=[{"AttributeName": "signal_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "signal_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket=BUCKET)
        yield ddb, s3


def _put_parquet(s3, s3_key: str, rows: list[dict], year: int = 2026):
    data = _make_parquet(rows)
    s3.put_object(Bucket=BUCKET, Key=f"signals/{s3_key}/1d/{year}.parquet", Body=data)


def test_writes_records_for_directional_rows(aws_resources):
    ddb, s3 = aws_resources
    _put_parquet(s3, "EURUSD", _signal_rows("call", n=2))
    from livewell.pipeline.replay import replay_signals
    result = replay_signals(instruments=["EURUSD"], env="test", bucket=BUCKET)
    assert result["written"] == 2
    assert result["skipped"] == 0
    assert result["failed"] == []
    table = ddb.Table(TABLE_SIGNALS)
    item = table.get_item(Key={"signal_id": "EURUSD__2026-01-01"})["Item"]
    assert item["direction"] == "call"
    assert item["run_id"] == "replay"
    assert item["score"] is None
    assert item["model_version"] is None


def test_skips_rows_with_direction_none(aws_resources):
    ddb, s3 = aws_resources
    rows = _signal_rows("call", n=1) + [
        {**_signal_rows("call", n=1)[0], "date": "2026-01-02", "direction": "none"}
    ]
    _put_parquet(s3, "EURUSD", rows)
    from livewell.pipeline.replay import replay_signals
    result = replay_signals(instruments=["EURUSD"], env="test", bucket=BUCKET)
    assert result["written"] == 1
    assert result["skipped"] == 0


def test_normalises_buy_sell_direction(aws_resources):
    ddb, s3 = aws_resources
    rows = _signal_rows("buy", n=1) + [
        {**_signal_rows("sell", n=1)[0], "date": "2026-01-02", "direction": "sell"}
    ]
    _put_parquet(s3, "EURUSD", rows)
    from livewell.pipeline.replay import replay_signals
    replay_signals(instruments=["EURUSD"], env="test", bucket=BUCKET)
    table = ddb.Table(TABLE_SIGNALS)
    assert table.get_item(Key={"signal_id": "EURUSD__2026-01-01"})["Item"]["direction"] == "call"
    assert table.get_item(Key={"signal_id": "EURUSD__2026-01-02"})["Item"]["direction"] == "put"


def test_skips_existing_signal_ids(aws_resources):
    ddb, s3 = aws_resources
    _put_parquet(s3, "EURUSD", _signal_rows("call", n=2))
    table = ddb.Table(TABLE_SIGNALS)
    table.put_item(Item={"signal_id": "EURUSD__2026-01-01", "run_id": "live"})
    from livewell.pipeline.replay import replay_signals
    result = replay_signals(instruments=["EURUSD"], env="test", bucket=BUCKET)
    assert result["written"] == 1
    assert result["skipped"] == 1
    # Existing record not overwritten
    assert table.get_item(Key={"signal_id": "EURUSD__2026-01-01"})["Item"]["run_id"] == "live"


def test_returns_correct_counts(aws_resources):
    ddb, s3 = aws_resources
    _put_parquet(s3, "EURUSD", _signal_rows("call", n=3))
    table = ddb.Table(TABLE_SIGNALS)
    table.put_item(Item={"signal_id": "EURUSD__2026-01-01", "run_id": "live"})
    from livewell.pipeline.replay import replay_signals
    result = replay_signals(instruments=["EURUSD"], env="test", bucket=BUCKET)
    assert result["written"] == 2
    assert result["skipped"] == 1


def test_dry_run_writes_nothing(aws_resources):
    ddb, s3 = aws_resources
    _put_parquet(s3, "EURUSD", _signal_rows("call", n=2))
    from livewell.pipeline.replay import replay_signals
    result = replay_signals(instruments=["EURUSD"], env="test", bucket=BUCKET, dry_run=True)
    assert result["written"] == 2
    assert result["skipped"] == 0
    table = ddb.Table(TABLE_SIGNALS)
    assert table.scan(Select="COUNT")["Count"] == 0


def test_empty_parquet_produces_no_writes(aws_resources):
    ddb, s3 = aws_resources
    _put_parquet(s3, "EURUSD", [])
    from livewell.pipeline.replay import replay_signals
    result = replay_signals(instruments=["EURUSD"], env="test", bucket=BUCKET)
    assert result["written"] == 0
    assert result["skipped"] == 0


def test_missing_parquet_year_is_skipped(aws_resources):
    ddb, s3 = aws_resources
    # Only put 2025, not 2026 — 2026 key missing → should be skipped, not crash
    _put_parquet(s3, "EURUSD", _signal_rows("call", n=1), year=2025)
    from livewell.pipeline.replay import replay_signals
    result = replay_signals(instruments=["EURUSD"], env="test", bucket=BUCKET)
    assert result["written"] == 1
    assert result["failed"] == []
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd apps/api && uv run pytest tests/pipeline/test_replay.py -v 2>&1 | head -20
```

Expected: `ImportError` — `replay.py` doesn't exist yet.

- [ ] **Step 3: Create `replay.py`**

Create `apps/api/livewell/pipeline/replay.py`:

```python
from __future__ import annotations
import io
import logging
import os
from datetime import datetime, timezone

import boto3
import pandas as pd
from botocore.exceptions import ClientError

from livewell.ingestion.constants import INSTRUMENTS

logger = logging.getLogger(__name__)

_REPLAY_YEARS = list(range(2019, 2027))
_DIRECTION_MAP = {"buy": "call", "sell": "put"}


def _normalise_direction(d: str) -> str:
    return _DIRECTION_MAP.get(str(d), str(d))


def _load_existing_ids(table) -> set[str]:
    existing: set[str] = set()
    resp = table.scan(ProjectionExpression="signal_id")
    for item in resp.get("Items", []):
        existing.add(item["signal_id"])
    while "LastEvaluatedKey" in resp:
        resp = table.scan(
            ProjectionExpression="signal_id",
            ExclusiveStartKey=resp["LastEvaluatedKey"],
        )
        for item in resp.get("Items", []):
            existing.add(item["signal_id"])
    return existing


def _read_parquet(s3, bucket: str, key: str) -> pd.DataFrame | None:
    try:
        obj = s3.get_object(Bucket=bucket, Key=key)
        return pd.read_parquet(io.BytesIO(obj["Body"].read()))
    except ClientError as e:
        if e.response["Error"]["Code"] in ("NoSuchKey", "404"):
            return None
        raise


def replay_signals(
    instruments: list[str] | None = None,
    env: str = "prod",
    bucket: str = "livewell-data-prod",
    dry_run: bool = False,
) -> dict:
    """
    Read signal Parquets from S3 and batch-write to DynamoDB, skipping existing records.
    Returns {"written": N, "skipped": N, "failed": [signal_id, ...]}.
    """
    region = os.environ.get("AWS_DEFAULT_REGION", "us-west-1")
    s3 = boto3.client("s3", region_name=region)
    dynamodb = boto3.resource("dynamodb", region_name=region)
    table = dynamodb.Table(f"livewell-signals-{env}")

    targets = instruments or [i["s3_key"] for i in INSTRUMENTS]
    existing_ids = _load_existing_ids(table)

    written = 0
    skipped = 0
    failed: list[str] = []
    now = datetime.now(timezone.utc).isoformat()

    for s3_key in targets:
        batch: list[dict] = []

        for year in _REPLAY_YEARS:
            key = f"signals/{s3_key}/1d/{year}.parquet"
            df = _read_parquet(s3, bucket, key)
            if df is None:
                logger.warning("no parquet at %s — skipping year", key)
                continue
            if df.empty:
                continue

            df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)

            for _, row in df.iterrows():
                direction = _normalise_direction(row.get("direction", "none"))
                if direction == "none":
                    continue

                date_str = pd.Timestamp(row["date"]).strftime("%Y-%m-%d")
                signal_id = f"{s3_key}__{date_str}"

                if signal_id in existing_ids:
                    skipped += 1
                    continue

                record = {
                    "signal_id": signal_id,
                    "s3_key": s3_key,
                    "run_id": "replay",
                    "date": date_str,
                    "ema_20": str(row.get("ema_20", "")),
                    "ema_50": str(row.get("ema_50", "")),
                    "rsi_14": str(row.get("rsi_14", "")),
                    "macd": str(row.get("macd", "")),
                    "macd_signal": str(row.get("macd_signal", "")),
                    "macd_hist": str(row.get("macd_hist", "")),
                    "atr_14": str(row.get("atr_14", "")),
                    "trend_bias": str(row.get("trend_bias", "")),
                    "session_quality": str(row.get("session_quality", "")),
                    "strike_candidate": str(row.get("strike_candidate", "")),
                    "signal_valid": bool(row.get("signal_valid", False)),
                    "direction": direction,
                    "reasoning": str(row.get("reasoning", "{}")),
                    "timing_slot": str(row.get("timing_slot", "")),
                    "timing_risk": str(row.get("timing_risk", "")),
                    "score": None,
                    "model_version": None,
                    "created_at": now,
                }
                batch.append(record)

        if not dry_run and batch:
            try:
                with table.batch_writer() as bw:
                    for record in batch:
                        bw.put_item(Item=record)
                written += len(batch)
            except Exception as exc:
                logger.error("batch write failed for %s: %s", s3_key, exc)
                failed.extend(r["signal_id"] for r in batch)
        else:
            written += len(batch)

    return {"written": written, "skipped": skipped, "failed": failed}
```

- [ ] **Step 4: Run tests and verify they pass**

```bash
cd apps/api && uv run pytest tests/pipeline/test_replay.py -v
```

Expected: all 8 tests pass.

- [ ] **Step 5: Run full test suite to check for regressions**

```bash
cd apps/api && uv run pytest -v 2>&1 | tail -15
```

Expected: all pre-existing tests still pass (7 pre-existing failures in explain/models are expected and unrelated).

- [ ] **Step 6: Commit**

```bash
git add apps/api/livewell/pipeline/replay.py apps/api/tests/pipeline/test_replay.py
git commit -m "feat: add replay_signals to bulk-load historical signals from S3 into DynamoDB"
```

---

## Task 2: Notebook — orchestrate the replay run

**Files:**
- Create: `notebooks/livewell-nadex/replay_signals.ipynb`

- [ ] **Step 1: Create the notebook**

Create `notebooks/livewell-nadex/replay_signals.ipynb` as a valid nbformat 4 Jupyter notebook with exactly 3 code cells:

**Cell 1 — Setup:**
```python
import sys, os
sys.path.insert(0, os.path.abspath("../../apps/api"))

import logging
from livewell.pipeline.replay import replay_signals
from livewell.ingestion.constants import INSTRUMENTS

logging.basicConfig(level=logging.WARNING)

BUCKET = "livewell-data-prod"
ENV = "prod"

print(f"Setup complete. {len(INSTRUMENTS)} instruments to replay.")
```

**Cell 2 — Run replay:**
```python
total_written = 0
total_skipped = 0
total_failed = []

for inst in INSTRUMENTS:
    result = replay_signals(
        instruments=[inst["s3_key"]],
        env=ENV,
        bucket=BUCKET,
    )
    total_written += result["written"]
    total_skipped += result["skipped"]
    total_failed.extend(result["failed"])
    status = "✓" if not result["failed"] else "✗"
    print(f"{status} {inst['s3_key']:<12} written={result['written']}, skipped={result['skipped']}, failed={len(result['failed'])}")

print()
print("=" * 50)
print(f"Total written: {total_written}")
print(f"Total skipped: {total_skipped}")
print(f"Total failed:  {len(total_failed)}")
if total_failed:
    print(f"Failed IDs: {total_failed[:10]}{'...' if len(total_failed) > 10 else ''}")
```

**Cell 3 — Verify:**
```python
import boto3
dynamodb = boto3.resource("dynamodb", region_name="us-west-1")
table = dynamodb.Table(f"livewell-signals-{ENV}")
count = table.scan(Select="COUNT")["Count"]
print(f"Total signals in DynamoDB: {count}")

# Sample a replay record
resp = table.scan(
    FilterExpression=boto3.dynamodb.conditions.Attr("run_id").eq("replay"),
    Limit=1,
)
if resp["Items"]:
    sample = resp["Items"][0]
    print(f"\nSample replay record:")
    print(f"  signal_id: {sample['signal_id']}")
    print(f"  direction: {sample['direction']}")
    print(f"  signal_valid: {sample['signal_valid']}")
    print(f"  score: {sample.get('score')}")
    print(f"  run_id: {sample['run_id']}")
```

- [ ] **Step 2: Verify the notebook is valid JSON**

```bash
python3 -c "import json; json.load(open('notebooks/livewell-nadex/replay_signals.ipynb')); print('valid')"
```

Expected: `valid`

- [ ] **Step 3: Commit**

```bash
git add notebooks/livewell-nadex/replay_signals.ipynb
git commit -m "feat: add replay_signals notebook to orchestrate historical signal load"
```

---

## Task 3: Run the notebook and verify results

This task runs manually — requires live AWS credentials. Runtime: ~5–10 minutes.

- [ ] **Step 1: Run the notebook**

```bash
cd apps/api && uv run --with jupyter jupyter nbconvert --to notebook --execute --inplace ../../notebooks/livewell-nadex/replay_signals.ipynb 2>&1
```

Expected: no errors, notebook written back with outputs.

- [ ] **Step 2: Verify Cell 2 output shows all 19 instruments with ✓**

Open the notebook and confirm Cell 2 ends with:
```
Total written: ~34000  (exact number depends on direction filter)
Total skipped: ~25     (the existing live pipeline records)
Total failed:  0
```

- [ ] **Step 3: Re-run the backtest notebook**

```bash
cd apps/api && uv run --with jupyter jupyter nbconvert --to notebook --execute --inplace ../../notebooks/livewell-nadex/backtest.ipynb 2>&1
```

Expected: Cell 4 shows `Total trades` in the hundreds or thousands and `Win rate` is not 0%.

- [ ] **Step 4: Commit executed notebooks**

```bash
git add notebooks/livewell-nadex/replay_signals.ipynb notebooks/livewell-nadex/backtest.ipynb
git commit -m "chore: run signal replay and backtest notebooks with full historical data"
```

# Historical Signal Replay — Design Spec

**Date:** 2026-05-12
**Status:** Approved

---

## Goal

Populate `livewell-signals-prod` DynamoDB with ~34,000 historical signal records (2019–present, all 19 instruments) by reading the signal Parquet files already in S3. This gives the backtest enough data to produce meaningful win rates across multiple market regimes.

---

## Architecture

```
apps/api/livewell/pipeline/replay.py
    └── replay_signals(instruments, env, bucket, dry_run) -> dict
            └── reads s3://bucket/signals/{s3_key}/1d/{year}.parquet
            └── scans DynamoDB for existing signal_ids (once per run)
            └── skips records already in DynamoDB
            └── skips rows where direction == "none"
            └── batch-writes new records (25 per batch — DynamoDB limit)
            └── returns {"written": N, "skipped": N, "failed": [...]}

apps/api/tests/pipeline/test_replay.py   — unit tests (moto + mock S3)

notebooks/livewell-nadex/replay_signals.ipynb  — thin orchestration notebook
```

---

## `replay_signals` Function

### Signature

```python
def replay_signals(
    instruments: list[str] | None = None,
    env: str = "prod",
    bucket: str = "livewell-data-prod",
    dry_run: bool = False,
) -> dict:
```

- `instruments`: list of `s3_key` values (e.g. `["EURUSD", "GBPUSD"]`). Defaults to all 19 from `INSTRUMENTS`.
- `env`: DynamoDB table suffix — `livewell-signals-{env}`
- `bucket`: S3 bucket name
- `dry_run`: if `True`, counts what would be written but makes no DynamoDB writes

### Behavior

1. Scan `livewell-signals-{env}` DynamoDB table once to build a set of existing `signal_id` strings
2. For each instrument:
   - For each year 2019–2026: read `signals/{s3_key}/1d/{year}.parquet` from S3
   - If the Parquet doesn't exist, log a warning and skip that year
   - For each row where `direction != "none"`:
     - Construct `signal_id = f"{s3_key}__{date_str}"`
     - If `signal_id` is in existing set → increment skipped count, continue
     - Otherwise → construct record dict and add to write batch
3. Flush batch to DynamoDB in chunks of 25
4. Return `{"written": N, "skipped": N, "failed": [signal_id, ...]}`

### Record Schema

Matches `run_instrument` output exactly:

| Field | Source | Notes |
|-------|--------|-------|
| `signal_id` | `f"{s3_key}__{date_str}"` | Primary key |
| `s3_key` | instrument s3_key | |
| `run_id` | `"replay"` | Fixed string for all replay records |
| `date` | Parquet `date` column, formatted `YYYY-MM-DD` | |
| `ema_20` | Parquet | Stringified float |
| `ema_50` | Parquet | Stringified float |
| `rsi_14` | Parquet | Stringified float |
| `macd` | Parquet | Stringified float |
| `macd_signal` | Parquet | Stringified float |
| `macd_hist` | Parquet | Stringified float |
| `atr_14` | Parquet | Stringified float |
| `trend_bias` | Parquet | |
| `session_quality` | Parquet | |
| `strike_candidate` | Parquet | Stringified float |
| `signal_valid` | Parquet | bool |
| `direction` | Parquet | Normalise: `"buy"` → `"call"`, `"sell"` → `"put"`; older Parquets use buy/sell |
| `reasoning` | Parquet | JSON string, already populated |
| `timing_slot` | Parquet | |
| `timing_risk` | Parquet | |
| `score` | `None` | Populated in Phase 2 |
| `model_version` | `None` | Populated in Phase 2 |
| `created_at` | `datetime.now(UTC).isoformat()` | |

---

## Tests (`apps/api/tests/pipeline/test_replay.py`)

All tests use `moto` for DynamoDB and a local in-memory Parquet (no live AWS calls).

- `test_writes_records_for_directional_rows` — rows with `direction != "none"` are written
- `test_skips_rows_with_direction_none` — rows where `direction == "none"` are not written
- `test_skips_existing_signal_ids` — records already in DynamoDB are skipped, not overwritten
- `test_returns_correct_written_and_skipped_counts` — return dict counts are accurate
- `test_dry_run_writes_nothing` — `dry_run=True` returns counts but makes no DynamoDB writes
- `test_empty_parquet_produces_no_writes` — empty DataFrame → written=0, skipped=0
- `test_missing_parquet_year_is_skipped` — S3 NoSuchKey → warning logged, other years continue

---

## Notebook (`notebooks/livewell-nadex/replay_signals.ipynb`)

3 cells:

**Cell 1 — Setup:**
```python
import sys, os
sys.path.insert(0, os.path.abspath("../../apps/api"))
from livewell.pipeline.replay import replay_signals
BUCKET = "livewell-data-prod"
ENV = "prod"
print("Setup complete.")
```

**Cell 2 — Run replay:**
```python
from livewell.ingestion.constants import INSTRUMENTS
for inst in INSTRUMENTS:
    result = replay_signals(instruments=[inst["s3_key"]], env=ENV, bucket=BUCKET)
    print(f"{inst['s3_key']:<12} written={result['written']}, skipped={result['skipped']}, failed={len(result['failed'])}")
```

**Cell 3 — Verify:**
```python
import boto3
dynamodb = boto3.resource("dynamodb", region_name="us-west-1")
table = dynamodb.Table(f"livewell-signals-{ENV}")
count = table.scan(Select="COUNT")["Count"]
print(f"Total signals in DynamoDB: {count}")
# Sample a record
sample = table.scan(Limit=1)["Items"][0]
print("Sample record:", sample)
```

---

## Error Handling

- Missing S3 Parquet (NoSuchKey) → log warning, skip that year, continue
- DynamoDB `BatchWriteItem` failure → retry once; on second failure, add affected `signal_id`s to `failed` list and continue
- Returns `failed` list — notebook surfaces any failures after the run

---

## Success Criteria

- ~34,000 records written to `livewell-signals-prod` (19 instruments × ~1800 trading days)
- Re-running `backtest.ipynb` produces a non-zero win rate with equity curve spanning 2019–present
- Existing live pipeline records (25 records) are preserved unchanged

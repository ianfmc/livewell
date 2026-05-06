# Phase 4 Batch Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deploy a daily Lambda-based batch pipeline that ingests market data, generates signals, persists them to DynamoDB, and serves them through the `/api/signals` endpoint — replacing the current mock data.

**Architecture:** A Docker-packaged Lambda function is triggered nightly by EventBridge Cron (midnight UTC). It calls the existing `run_ingestion`, `run_features`, and `run_signals` Python functions for each of 18 instruments, then writes run metadata and signal records to DynamoDB. The `/api/signals` FastAPI endpoint is updated to read from DynamoDB. CloudWatch + SNS alerts on errors.

**Tech Stack:** Python 3.12, boto3, FastAPI, AWS CDK v2 TypeScript, Lambda (container image), EventBridge, DynamoDB, CloudWatch, SNS. Tests: pytest + moto (S3/DynamoDB mocking), CDK assertions.

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `apps/api/livewell/pipeline/__init__.py` | Create | Package marker |
| `apps/api/livewell/pipeline/dynamodb.py` | Create | DynamoDB write layer: `create_run`, `update_run`, `put_signal` |
| `apps/api/livewell/pipeline/runner.py` | Create | Per-instrument orchestration: calls ingest → features → signals → read latest signal row |
| `apps/api/livewell/pipeline/handler.py` | Create | Lambda entry point: orchestrates all instruments, writes run record, calls `put_signal` |
| `apps/api/tests/pipeline/__init__.py` | Create | Package marker |
| `apps/api/tests/pipeline/test_dynamodb.py` | Create | Unit tests for DynamoDB write layer |
| `apps/api/tests/pipeline/test_runner.py` | Create | Unit tests for per-instrument runner |
| `apps/api/tests/pipeline/test_handler.py` | Create | Unit tests for handler run-status logic |
| `apps/api/schemas/contract.py` | Modify | Add `signalId: str` field to `ContractCard` |
| `apps/api/routers/signals.py` | Modify | Replace mock with DynamoDB read |
| `apps/api/tests/test_signals.py` | Modify | Update tests to match new DynamoDB-backed endpoint |
| `apps/api/Dockerfile.pipeline` | Create | Container image for Lambda |
| `infra/lib/livewell-stack.ts` | Modify | Add Lambda, EventBridge rule, SNS topic, CloudWatch alarm |
| `infra/test/livewell-stack.test.ts` | Modify | Add CDK assertions for new constructs |

---

## Task 1: DynamoDB write layer

**Files:**
- Create: `apps/api/livewell/pipeline/__init__.py`
- Create: `apps/api/livewell/pipeline/dynamodb.py`
- Create: `apps/api/tests/pipeline/__init__.py`
- Create: `apps/api/tests/pipeline/test_dynamodb.py`

- [ ] **Step 1: Write failing tests**

Create `apps/api/tests/pipeline/__init__.py` (empty).

Create `apps/api/tests/pipeline/test_dynamodb.py`:

```python
from __future__ import annotations
import os
import boto3
import pytest
from moto import mock_aws

TABLE_RUNS = "livewell-model-runs-test"
TABLE_SIGNALS = "livewell-signals-test"


@pytest.fixture(autouse=True)
def aws_env(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")
    monkeypatch.setenv("LIVEWELL_ENV", "test")


@pytest.fixture()
def tables():
    with mock_aws():
        ddb = boto3.resource("dynamodb", region_name="us-east-1")
        ddb.create_table(
            TableName=TABLE_RUNS,
            KeySchema=[
                {"AttributeName": "run_id", "KeyType": "HASH"},
                {"AttributeName": "started_at", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "run_id", "AttributeType": "S"},
                {"AttributeName": "started_at", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        ddb.create_table(
            TableName=TABLE_SIGNALS,
            KeySchema=[{"AttributeName": "signal_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "signal_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        yield ddb


def test_create_run_writes_running_status(tables):
    from livewell.pipeline.dynamodb import create_run
    create_run("run-1", "2026-05-05T00:00:00Z")
    item = tables.Table(TABLE_RUNS).get_item(
        Key={"run_id": "run-1", "started_at": "2026-05-05T00:00:00Z"}
    )["Item"]
    assert item["status"] == "running"
    assert item["instruments"] == []
    assert item["errors"] == []


def test_update_run_writes_final_status(tables):
    from livewell.pipeline.dynamodb import create_run, update_run
    create_run("run-2", "2026-05-05T00:00:00Z")
    update_run(
        run_id="run-2",
        started_at="2026-05-05T00:00:00Z",
        status="completed",
        instruments=["EURUSD", "GBPUSD"],
        errors=[],
        completed_at="2026-05-05T00:05:00Z",
    )
    item = tables.Table(TABLE_RUNS).get_item(
        Key={"run_id": "run-2", "started_at": "2026-05-05T00:00:00Z"}
    )["Item"]
    assert item["status"] == "completed"
    assert item["instruments"] == ["EURUSD", "GBPUSD"]
    assert item["completed_at"] == "2026-05-05T00:05:00Z"


def test_put_signal_writes_record(tables):
    from livewell.pipeline.dynamodb import put_signal
    record = {
        "signal_id": "EURUSD__2026-05-05",
        "s3_key": "EURUSD",
        "run_id": "run-1",
        "date": "2026-05-05",
        "direction": "buy",
        "signal_valid": True,
        "score": None,
        "model_version": None,
        "created_at": "2026-05-05T00:05:00Z",
        "ema_20": "1.08",
        "ema_50": "1.07",
        "rsi_14": "55.0",
        "strike_candidate": "1.0850",
        "timing_slot": "buy_bullish",
        "timing_risk": "moderate",
    }
    put_signal(record)
    item = tables.Table(TABLE_SIGNALS).get_item(
        Key={"signal_id": "EURUSD__2026-05-05"}
    )["Item"]
    assert item["direction"] == "buy"
    assert item["run_id"] == "run-1"
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
cd apps/api && uv run pytest tests/pipeline/test_dynamodb.py -v 2>&1 | head -20
```

Expected: `ModuleNotFoundError: No module named 'livewell.pipeline'`

- [ ] **Step 3: Create package marker**

Create `apps/api/livewell/pipeline/__init__.py` (empty file).

- [ ] **Step 4: Implement `dynamodb.py`**

Create `apps/api/livewell/pipeline/dynamodb.py`:

```python
from __future__ import annotations
import os
import boto3


def _env() -> str:
    return os.environ.get("LIVEWELL_ENV", "prod")


def _runs_table():
    return boto3.resource("dynamodb").Table(f"livewell-model-runs-{_env()}")


def _signals_table():
    return boto3.resource("dynamodb").Table(f"livewell-signals-{_env()}")


def create_run(run_id: str, started_at: str) -> None:
    _runs_table().put_item(Item={
        "run_id": run_id,
        "started_at": started_at,
        "status": "running",
        "instruments": [],
        "errors": [],
        "completed_at": None,
    })


def update_run(
    run_id: str,
    started_at: str,
    status: str,
    instruments: list[str],
    errors: list[dict],
    completed_at: str,
) -> None:
    _runs_table().update_item(
        Key={"run_id": run_id, "started_at": started_at},
        UpdateExpression=(
            "SET #s = :s, instruments = :i, errors = :e, completed_at = :c"
        ),
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={
            ":s": status,
            ":i": instruments,
            ":e": errors,
            ":c": completed_at,
        },
    )


def put_signal(record: dict) -> None:
    _signals_table().put_item(Item=record)
```

- [ ] **Step 5: Run tests — verify they pass**

```bash
cd apps/api && uv run pytest tests/pipeline/test_dynamodb.py -v
```

Expected: 3 tests pass.

- [ ] **Step 6: Commit**

```bash
git add apps/api/livewell/pipeline/__init__.py apps/api/livewell/pipeline/dynamodb.py apps/api/tests/pipeline/__init__.py apps/api/tests/pipeline/test_dynamodb.py
git commit -m "feat: add DynamoDB write layer for pipeline runs and signals"
```

---

## Task 2: Per-instrument runner

**Files:**
- Create: `apps/api/livewell/pipeline/runner.py`
- Create: `apps/api/tests/pipeline/test_runner.py`

- [ ] **Step 1: Write failing tests**

Create `apps/api/tests/pipeline/test_runner.py`:

```python
from __future__ import annotations
import os
from unittest.mock import MagicMock, patch
import pytest


@pytest.fixture(autouse=True)
def env(monkeypatch):
    monkeypatch.setenv("LIVEWELL_BUCKET", "test-bucket")
    monkeypatch.setenv("LIVEWELL_ENV", "test")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")


MOCK_SIGNAL_ROW = {
    "date": "2026-05-05",
    "ema_20": 1.08,
    "ema_50": 1.07,
    "rsi_14": 55.0,
    "macd": 0.001,
    "macd_signal": 0.0009,
    "macd_hist": 0.0001,
    "atr_14": 0.005,
    "trend_bias": "bullish",
    "session_quality": "high",
    "strike_candidate": "1.0850",
    "signal_valid": True,
    "direction": "buy",
    "reasoning": "{}",
    "timing_slot": "buy_bullish",
    "timing_risk": "moderate",
}


def test_run_instrument_returns_signal_record():
    import pandas as pd
    mock_df = pd.DataFrame([MOCK_SIGNAL_ROW])

    with patch("livewell.pipeline.runner.run_ingestion") as mock_ingest, \
         patch("livewell.pipeline.runner.run_features") as mock_features, \
         patch("livewell.pipeline.runner.run_signals") as mock_signals, \
         patch("livewell.pipeline.runner._read_latest_signal", return_value=MOCK_SIGNAL_ROW):

        mock_ingest.return_value = {"succeeded": ["EURUSD"], "failed": []}
        mock_features.return_value = {"succeeded": ["EURUSD"], "failed": []}
        mock_signals.return_value = {"succeeded": ["EURUSD"], "failed": []}

        from livewell.pipeline.runner import run_instrument
        result = run_instrument("EURUSD", "run-123")

    assert result["signal_id"] == "EURUSD__2026-05-05"
    assert result["s3_key"] == "EURUSD"
    assert result["run_id"] == "run-123"
    assert result["direction"] == "buy"
    assert result["score"] is None
    assert result["model_version"] is None
    assert "created_at" in result


def test_run_instrument_propagates_exception():
    with patch("livewell.pipeline.runner.run_ingestion", side_effect=RuntimeError("yfinance down")):
        from livewell.pipeline.runner import run_instrument
        with pytest.raises(RuntimeError, match="yfinance down"):
            run_instrument("EURUSD", "run-456")
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
cd apps/api && uv run pytest tests/pipeline/test_runner.py -v 2>&1 | head -20
```

Expected: `ModuleNotFoundError: No module named 'livewell.pipeline.runner'`

- [ ] **Step 3: Implement `runner.py`**

Create `apps/api/livewell/pipeline/runner.py`:

```python
from __future__ import annotations
import logging
import os
from datetime import datetime, timezone

import boto3
import pandas as pd

from livewell.ingestion.ingest import run_ingestion
from livewell.features.features import run_features
from livewell.signals.signals import run_signals
from livewell.signals.constants import SIGNAL_COLUMNS, SIGNALS_PREFIX
from livewell.ingestion.s3 import read_parquet

logger = logging.getLogger(__name__)


def _read_latest_signal(s3_key: str, bucket: str) -> dict | None:
    """Read all signal Parquets for s3_key (1d interval) and return the most recent row."""
    s3 = boto3.client("s3")
    prefix = f"{SIGNALS_PREFIX}/{s3_key}/1d/"
    resp = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
    objects = resp.get("Contents", [])
    if not objects:
        return None

    frames = []
    for obj in sorted(objects, key=lambda o: o["Key"]):
        df = read_parquet(bucket, obj["Key"])
        if df is not None:
            frames.append(df)
    if not frames:
        return None

    combined = pd.concat(frames, ignore_index=True)
    combined["date"] = pd.to_datetime(combined["date"], utc=True)
    latest = combined.sort_values("date").iloc[-1]
    return latest.to_dict()


def run_instrument(s3_key: str, run_id: str) -> dict:
    """
    Run ingestion → features → signals for one instrument and return a DynamoDB signal record.
    Raises on any stage failure — caller catches and records the error.
    """
    bucket = os.environ["LIVEWELL_BUCKET"]

    run_ingestion(instruments=[s3_key], backfill=False)
    run_features(instruments=[s3_key])
    run_signals(instruments=[s3_key])

    row = _read_latest_signal(s3_key, bucket)
    if row is None:
        raise ValueError(f"no signal row found after pipeline for {s3_key}")

    date_str = pd.Timestamp(row["date"]).strftime("%Y-%m-%d")
    return {
        "signal_id": f"{s3_key}__{date_str}",
        "s3_key": s3_key,
        "run_id": run_id,
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
        "direction": str(row.get("direction", "none")),
        "reasoning": str(row.get("reasoning", "{}")),
        "timing_slot": str(row.get("timing_slot", "")),
        "timing_risk": str(row.get("timing_risk", "")),
        "score": None,
        "model_version": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
cd apps/api && uv run pytest tests/pipeline/test_runner.py -v
```

Expected: 2 tests pass.

- [ ] **Step 5: Commit**

```bash
git add apps/api/livewell/pipeline/runner.py apps/api/tests/pipeline/test_runner.py
git commit -m "feat: add per-instrument pipeline runner"
```

---

## Task 3: Lambda handler

**Files:**
- Create: `apps/api/livewell/pipeline/handler.py`
- Create: `apps/api/tests/pipeline/test_handler.py`

- [ ] **Step 1: Write failing tests**

Create `apps/api/tests/pipeline/test_handler.py`:

```python
from __future__ import annotations
from unittest.mock import call, patch, MagicMock
import pytest


@pytest.fixture(autouse=True)
def env(monkeypatch):
    monkeypatch.setenv("LIVEWELL_BUCKET", "test-bucket")
    monkeypatch.setenv("LIVEWELL_ENV", "test")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")


def _make_signal(s3_key: str) -> dict:
    return {
        "signal_id": f"{s3_key}__2026-05-05",
        "s3_key": s3_key,
        "run_id": "run-1",
        "direction": "buy",
        "signal_valid": True,
        "score": None,
        "model_version": None,
        "created_at": "2026-05-05T00:05:00Z",
    }


def test_all_succeed_status_is_completed():
    with patch("livewell.pipeline.handler.run_instrument", side_effect=lambda s, r: _make_signal(s)), \
         patch("livewell.pipeline.handler.create_run"), \
         patch("livewell.pipeline.handler.update_run") as mock_update, \
         patch("livewell.pipeline.handler.put_signal"):
        from livewell.pipeline.handler import handler
        result = handler({}, None)

    assert result["status"] == "completed"
    status_call = mock_update.call_args
    assert status_call.kwargs["status"] == "completed"
    assert status_call.kwargs["errors"] == []


def test_partial_failure_status_is_completed_with_errors():
    instruments_seen = []

    def side_effect(s3_key, run_id):
        instruments_seen.append(s3_key)
        if s3_key == "EURUSD":
            raise RuntimeError("yfinance down")
        return _make_signal(s3_key)

    with patch("livewell.pipeline.handler.run_instrument", side_effect=side_effect), \
         patch("livewell.pipeline.handler.create_run"), \
         patch("livewell.pipeline.handler.update_run") as mock_update, \
         patch("livewell.pipeline.handler.put_signal") as mock_put:
        from livewell.pipeline.handler import handler
        result = handler({}, None)

    assert result["status"] == "completed_with_errors"
    status_call = mock_update.call_args
    assert status_call.kwargs["status"] == "completed_with_errors"
    assert len(status_call.kwargs["errors"]) == 1
    assert status_call.kwargs["errors"][0]["s3_key"] == "EURUSD"
    # put_signal called for every instrument except the failing one
    assert mock_put.call_count == len(instruments_seen) - 1


def test_all_fail_status_is_failed():
    with patch("livewell.pipeline.handler.run_instrument", side_effect=RuntimeError("network error")), \
         patch("livewell.pipeline.handler.create_run"), \
         patch("livewell.pipeline.handler.update_run") as mock_update, \
         patch("livewell.pipeline.handler.put_signal"):
        from livewell.pipeline.handler import handler
        result = handler({}, None)

    assert result["status"] == "failed"
    assert mock_update.call_args.kwargs["status"] == "failed"


def test_put_signal_called_per_success():
    successes = 0

    def side_effect(s3_key, run_id):
        nonlocal successes
        if s3_key in ("EURUSD", "GBPUSD"):
            raise RuntimeError("fail")
        successes += 1
        return _make_signal(s3_key)

    with patch("livewell.pipeline.handler.run_instrument", side_effect=side_effect), \
         patch("livewell.pipeline.handler.create_run"), \
         patch("livewell.pipeline.handler.update_run"), \
         patch("livewell.pipeline.handler.put_signal") as mock_put:
        from livewell.pipeline.handler import handler
        handler({}, None)

    assert mock_put.call_count == successes
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
cd apps/api && uv run pytest tests/pipeline/test_handler.py -v 2>&1 | head -20
```

Expected: `ModuleNotFoundError: No module named 'livewell.pipeline.handler'`

- [ ] **Step 3: Implement `handler.py`**

Create `apps/api/livewell/pipeline/handler.py`:

```python
from __future__ import annotations
import logging
import uuid
from datetime import datetime, timezone

from livewell.ingestion.constants import INSTRUMENTS
from livewell.pipeline.dynamodb import create_run, update_run, put_signal
from livewell.pipeline.runner import run_instrument

logger = logging.getLogger(__name__)


def handler(event: dict, context) -> dict:
    run_id = str(uuid.uuid4())
    started_at = datetime.now(timezone.utc).isoformat()

    create_run(run_id, started_at)

    signals: list[dict] = []
    errors: list[dict] = []

    for instrument in INSTRUMENTS:
        s3_key = instrument["s3_key"]
        try:
            record = run_instrument(s3_key, run_id)
            signals.append(record)
        except Exception as exc:
            logger.error("instrument %s failed: %s", s3_key, exc)
            errors.append({"s3_key": s3_key, "error": str(exc)})

    n_total = len(INSTRUMENTS)
    n_err = len(errors)

    if n_err == 0:
        status = "completed"
    elif n_err == n_total:
        status = "failed"
    else:
        status = "completed_with_errors"

    completed_at = datetime.now(timezone.utc).isoformat()
    succeeded_keys = [s["s3_key"] for s in signals]

    update_run(
        run_id=run_id,
        started_at=started_at,
        status=status,
        instruments=succeeded_keys,
        errors=errors,
        completed_at=completed_at,
    )

    for record in signals:
        put_signal(record)

    logger.info("run %s %s: %d ok, %d errors", run_id, status, len(signals), n_err)
    return {"run_id": run_id, "status": status}
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
cd apps/api && uv run pytest tests/pipeline/test_handler.py -v
```

Expected: 4 tests pass.

- [ ] **Step 5: Run all pipeline tests together**

```bash
cd apps/api && uv run pytest tests/pipeline/ -v
```

Expected: 9 tests pass (3 + 2 + 4).

- [ ] **Step 6: Commit**

```bash
git add apps/api/livewell/pipeline/handler.py apps/api/tests/pipeline/test_handler.py
git commit -m "feat: add Lambda handler with per-instrument error isolation"
```

---

## Task 4: Update signals endpoint to read from DynamoDB

**Files:**
- Modify: `apps/api/schemas/contract.py`
- Modify: `apps/api/routers/signals.py`
- Modify: `apps/api/tests/test_signals.py`

- [ ] **Step 1: Add `signalId` to `ContractCard`**

Read `apps/api/schemas/contract.py`. It currently has:
```python
class ContractCard(BaseModel):
    instrument: str
    strike: str
    expiry: str
    status: str
```

Change it to:
```python
class ContractCard(BaseModel):
    instrument: str
    strike: str
    expiry: str
    status: str
    signalId: str = ""
```

- [ ] **Step 2: Write failing test for DynamoDB-backed endpoint**

Replace the contents of `apps/api/tests/test_signals.py` with:

```python
from __future__ import annotations
import os
import boto3
import pytest
from moto import mock_aws
from fastapi.testclient import TestClient


TABLE_SIGNALS = "livewell-signals-test"


@pytest.fixture(autouse=True)
def aws_env(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")
    monkeypatch.setenv("LIVEWELL_ENV", "test")


@pytest.fixture()
def signals_table():
    with mock_aws():
        ddb = boto3.resource("dynamodb", region_name="us-east-1")
        table = ddb.create_table(
            TableName=TABLE_SIGNALS,
            KeySchema=[{"AttributeName": "signal_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "signal_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        table.put_item(Item={
            "signal_id": "EURUSD__2026-05-05",
            "s3_key": "EURUSD",
            "run_id": "run-1",
            "date": "2026-05-05",
            "direction": "buy",
            "signal_valid": True,
            "strike_candidate": "1.0850",
            "timing_slot": "buy_bullish",
            "score": None,
            "model_version": None,
            "created_at": "2026-05-05T00:05:00Z",
        })
        table.put_item(Item={
            "signal_id": "GBPUSD__2026-05-05",
            "s3_key": "GBPUSD",
            "run_id": "run-1",
            "date": "2026-05-05",
            "direction": "none",
            "signal_valid": False,
            "strike_candidate": "",
            "timing_slot": "unscheduled",
            "score": None,
            "model_version": None,
            "created_at": "2026-05-05T00:05:00Z",
        })
        yield table


def test_get_signals_returns_dynamodb_records(signals_table):
    from main import app
    client = TestClient(app)
    response = client.get("/api/signals")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    signal_ids = {d["signalId"] for d in data}
    assert "EURUSD__2026-05-05" in signal_ids


def test_get_signals_returns_empty_list_when_no_data():
    with mock_aws():
        ddb = boto3.resource("dynamodb", region_name="us-east-1")
        ddb.create_table(
            TableName=TABLE_SIGNALS,
            KeySchema=[{"AttributeName": "signal_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "signal_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        from main import app
        client = TestClient(app)
        response = client.get("/api/signals")
        assert response.status_code == 200
        assert response.json() == []


def test_get_signals_returns_empty_list_when_env_not_set(monkeypatch):
    monkeypatch.delenv("LIVEWELL_ENV", raising=False)
    from main import app
    client = TestClient(app)
    response = client.get("/api/signals")
    assert response.status_code == 200
    assert response.json() == []


def test_get_signal_detail_eur_usd():
    from main import app
    client = TestClient(app)
    response = client.get("/api/signals/EUR-USD/1.0850")
    assert response.status_code == 200
    data = response.json()
    assert data["recommendation"] == "Take"


def test_get_signal_detail_not_found():
    from main import app
    client = TestClient(app)
    response = client.get("/api/signals/EUR-USD/9.9999")
    assert response.status_code == 404
```

- [ ] **Step 3: Run the new test — verify it fails**

```bash
cd apps/api && uv run pytest tests/test_signals.py::test_get_signals_returns_dynamodb_records -v 2>&1 | head -20
```

Expected: test fails because signals endpoint still returns mock data.

- [ ] **Step 4: Implement DynamoDB-backed signals endpoint**

Replace the contents of `apps/api/routers/signals.py` with:

```python
from __future__ import annotations
import logging
import os
from fastapi import APIRouter, HTTPException
import boto3
from botocore.exceptions import ClientError

from schemas.contract import ContractCard, ContractDetail, Economics, ReasonCode

logger = logging.getLogger(__name__)
router = APIRouter()

_DETAILS: list[ContractDetail] = [
    ContractDetail(
        instrument="EUR/USD",
        strike="1.0850",
        expiry="10:00 AM",
        status="Open",
        recommendation="Take",
        rationale="Strong directional setup with acceptable event risk.",
        economics=Economics(cost=42, payout=100, breakeven=0.42),
        modelProbability=0.68,
        edge=0.26,
        confidence="High",
        regime="Bullish",
        noTradeFlag=False,
        reasonCodes=[
            ReasonCode(label="Bullish regime confirmed", positive=True),
            ReasonCode(label="RSI momentum favourable", positive=True),
            ReasonCode(label="Event risk flag active", positive=False),
        ],
    ),
    ContractDetail(
        instrument="GBP/USD",
        strike="1.2650",
        expiry="11:00 AM",
        status="Open",
        recommendation="Watch",
        rationale="Setup is developing but lacks regime confirmation.",
        economics=Economics(cost=38, payout=100, breakeven=0.38),
        modelProbability=0.52,
        edge=0.14,
        confidence="Medium",
        regime="Neutral",
        noTradeFlag=False,
        reasonCodes=[
            ReasonCode(label="Price near key level", positive=True),
            ReasonCode(label="Regime not confirmed", positive=False),
            ReasonCode(label="Low volatility environment", positive=False),
        ],
    ),
    ContractDetail(
        instrument="USD/JPY",
        strike="150.00",
        expiry="09:30 AM",
        status="Review",
        recommendation="Pass",
        rationale="No-trade flag active — intervention risk too high.",
        economics=Economics(cost=55, payout=100, breakeven=0.55),
        modelProbability=0.48,
        edge=-0.07,
        confidence="Low",
        regime="Bearish",
        noTradeFlag=True,
        reasonCodes=[
            ReasonCode(label="Intervention risk elevated", positive=False),
            ReasonCode(label="Bearish momentum weakening", positive=False),
            ReasonCode(label="High volatility — spread risk", positive=False),
        ],
    ),
]


def _s3_key_to_display(s3_key: str) -> str:
    """Convert S3 key like 'EURUSD' to display format 'EUR/USD' for known forex pairs."""
    _MAP = {
        "EURUSD": "EUR/USD", "GBPUSD": "GBP/USD", "USDJPY": "USD/JPY",
        "AUDUSD": "AUD/USD", "AUDJPY": "AUD/JPY", "EURJPY": "EUR/JPY",
        "EURGBP": "EUR/GBP", "GBPJPY": "GBP/JPY", "USDCAD": "USD/CAD",
        "USDCHF": "USD/CHF", "USDMXN": "USD/MXN",
    }
    return _MAP.get(s3_key, s3_key)


def _fetch_signals_from_dynamodb() -> list[ContractCard]:
    env = os.environ.get("LIVEWELL_ENV")
    if not env:
        return []
    try:
        table = boto3.resource("dynamodb").Table(f"livewell-signals-{env}")
        resp = table.scan()
        items = resp.get("Items", [])
        if not items:
            return []
        # Return signals from the most recent date
        most_recent_date = max(item.get("date", "") for item in items)
        todays_items = [i for i in items if i.get("date") == most_recent_date]
        return [
            ContractCard(
                instrument=_s3_key_to_display(item["s3_key"]),
                strike=str(item.get("strike_candidate", "")),
                expiry=str(item.get("timing_slot", "")),
                status="Open" if item.get("signal_valid") else "Invalid",
                signalId=item["signal_id"],
            )
            for item in todays_items
        ]
    except ClientError as exc:
        logger.error("DynamoDB scan failed: %s", exc)
        return []


@router.get("/signals", response_model=list[ContractCard])
def get_signals() -> list[ContractCard]:
    return _fetch_signals_from_dynamodb()


@router.get("/signals/{instrument}/{strike}", response_model=ContractDetail)
def get_signal_detail(instrument: str, strike: str) -> ContractDetail:
    decoded = instrument.replace("-", "/")
    detail = next(
        (d for d in _DETAILS if d.instrument == decoded and d.strike == strike), None
    )
    if detail is None:
        raise HTTPException(status_code=404, detail="Not found")
    return detail
```

- [ ] **Step 5: Run all signals tests**

```bash
cd apps/api && uv run pytest tests/test_signals.py -v
```

Expected: 5 tests pass.

- [ ] **Step 6: Run the full test suite**

```bash
cd apps/api && uv run pytest -v
```

Expected: all existing tests pass (no regressions).

- [ ] **Step 7: Commit**

```bash
git add apps/api/schemas/contract.py apps/api/routers/signals.py apps/api/tests/test_signals.py
git commit -m "feat: wire signals endpoint to DynamoDB, add signalId to ContractCard"
```

---

## Task 5: Dockerfile for Lambda container

**Files:**
- Create: `apps/api/Dockerfile.pipeline`

- [ ] **Step 1: Create `apps/api/Dockerfile.pipeline`**

```dockerfile
FROM public.ecr.aws/lambda/python:3.12

RUN pip install --no-cache-dir \
    boto3 \
    pandas \
    pandas-ta \
    yfinance \
    pyarrow \
    scikit-learn \
    awslambdaric

COPY . ${LAMBDA_TASK_ROOT}

CMD ["livewell.pipeline.handler.handler"]
```

Note: `public.ecr.aws/lambda/python:3.12` is the official AWS Lambda Python base image. It includes the Lambda runtime interface and sets `LAMBDA_TASK_ROOT` to `/var/task`. No `ENTRYPOINT` override needed — the base image handles it.

- [ ] **Step 2: Verify the Dockerfile builds locally**

```bash
cd apps/api && docker build -f Dockerfile.pipeline -t livewell-pipeline:local . 2>&1 | tail -5
```

Expected: `Successfully built ...` or `=> => writing image ...` with no errors.

If Docker is not available locally, skip this step — CDK will build it during deploy.

- [ ] **Step 3: Commit**

```bash
git add apps/api/Dockerfile.pipeline
git commit -m "feat: add Dockerfile for Lambda pipeline container"
```

---

## Task 6: CDK — Lambda, EventBridge, SNS, CloudWatch alarm

**Files:**
- Modify: `infra/lib/livewell-stack.ts`
- Modify: `infra/test/livewell-stack.test.ts`

- [ ] **Step 1: Write failing CDK assertions tests**

Read the existing `infra/test/livewell-stack.test.ts`. Add these new `describe` blocks at the end of the file (before the closing of the file):

```typescript
describe('Pipeline Lambda', () => {
  const template = makeTemplate();

  it('exists with correct memory and timeout', () => {
    template.hasResourceProperties('AWS::Lambda::Function', {
      MemorySize: 512,
      Timeout: 600,
    });
  });

  it('has correct environment variables', () => {
    template.hasResourceProperties('AWS::Lambda::Function', {
      Environment: {
        Variables: Match.objectLike({
          LIVEWELL_ENV: 'test',
        }),
      },
    });
  });
});

describe('EventBridge schedule', () => {
  const template = makeTemplate();

  it('has cron rule targeting Lambda', () => {
    template.hasResourceProperties('AWS::Events::Rule', {
      ScheduleExpression: 'cron(0 0 * * ? *)',
      State: 'ENABLED',
    });
  });
});

describe('SNS and CloudWatch alarm', () => {
  const template = makeTemplate();

  it('creates SNS topic', () => {
    template.resourceCountIs('AWS::SNS::Topic', 1);
  });

  it('creates CloudWatch alarm on Lambda errors', () => {
    template.hasResourceProperties('AWS::CloudWatch::Alarm', {
      MetricName: 'Errors',
      Namespace: 'AWS/Lambda',
      ComparisonOperator: 'GreaterThanThreshold',
      Threshold: 0,
    });
  });
});
```

- [ ] **Step 2: Run tests — verify new tests fail**

```bash
export NVM_DIR="$HOME/.nvm" && source "$NVM_DIR/nvm.sh" && nvm use 20 && cd infra && npm test 2>&1 | tail -20
```

Expected: existing 15 tests pass, new tests fail with "no resources of type AWS::Lambda::Function".

- [ ] **Step 3: Add CDK constructs to `livewell-stack.ts`**

Read `infra/lib/livewell-stack.ts`. Add these imports at the top alongside the existing imports:

```typescript
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as events from 'aws-cdk-lib/aws-events';
import * as targets from 'aws-cdk-lib/aws-events-targets';
import * as sns from 'aws-cdk-lib/aws-sns';
import * as subscriptions from 'aws-cdk-lib/aws-sns-subscriptions';
import * as cloudwatch from 'aws-cdk-lib/aws-cloudwatch';
import * as cloudwatch_actions from 'aws-cdk-lib/aws-cloudwatch-actions';
import * as path from 'path';
```

Then add these constructs at the end of the constructor body, after the `CfnOutput` statements:

```typescript
    // ── Pipeline Lambda ───────────────────────────────────────────────────────
    const alertEmail = this.node.tryGetContext('alertEmail') as string | undefined;

    const pipelineLambda = new lambda.DockerImageFunction(this, 'PipelineLambda', {
      functionName: `livewell-pipeline-fn-${env}`,
      code: lambda.DockerImageCode.fromImageAsset(
        path.join(__dirname, '../../apps/api'),
        { file: 'Dockerfile.pipeline' }
      ),
      role: pipelineRole,
      memorySize: 512,
      timeout: cdk.Duration.seconds(600),
      environment: {
        LIVEWELL_BUCKET: bucket.bucketName,
        LIVEWELL_ENV: env,
      },
    });

    // ── EventBridge schedule ──────────────────────────────────────────────────
    new events.Rule(this, 'PipelineSchedule', {
      ruleName: `livewell-pipeline-schedule-${env}`,
      schedule: events.Schedule.expression('cron(0 0 * * ? *)'),
      targets: [new targets.LambdaFunction(pipelineLambda)],
    });

    // ── SNS alerts ────────────────────────────────────────────────────────────
    const alertTopic = new sns.Topic(this, 'AlertTopic', {
      topicName: `livewell-alerts-${env}`,
    });

    if (alertEmail) {
      alertTopic.addSubscription(new subscriptions.EmailSubscription(alertEmail));
    }

    // ── CloudWatch alarm ──────────────────────────────────────────────────────
    const errorAlarm = new cloudwatch.Alarm(this, 'PipelineErrorAlarm', {
      alarmName: `livewell-pipeline-errors-${env}`,
      metric: pipelineLambda.metricErrors({
        period: cdk.Duration.minutes(5),
        statistic: 'Sum',
      }),
      threshold: 0,
      evaluationPeriods: 1,
      comparisonOperator: cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
      treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
    });
    errorAlarm.addAlarmAction(new cloudwatch_actions.SnsAction(alertTopic));

    // ── Additional outputs ────────────────────────────────────────────────────
    new cdk.CfnOutput(this, 'PipelineLambdaArn', { value: pipelineLambda.functionArn });
    new cdk.CfnOutput(this, 'AlertTopicArn', { value: alertTopic.topicArn });
```

- [ ] **Step 4: Run CDK tests — verify all pass**

```bash
export NVM_DIR="$HOME/.nvm" && source "$NVM_DIR/nvm.sh" && nvm use 20 && cd infra && npm test 2>&1 | tail -20
```

Expected: all tests pass (15 original + new Lambda/EventBridge/SNS/CloudWatch tests).

- [ ] **Step 5: Verify CDK synth succeeds**

```bash
export NVM_DIR="$HOME/.nvm" && source "$NVM_DIR/nvm.sh" && nvm use 20 && cd infra && npx cdk synth --context env=prod --context alertEmail=test@example.com 2>&1 | head -20
```

Expected: CloudFormation template printed, no errors. (CDK will attempt to build the Docker image during synth — if Docker is not running, pass `--no-asset-metadata` or skip this step.)

- [ ] **Step 6: Commit**

```bash
git add infra/lib/livewell-stack.ts infra/test/livewell-stack.test.ts
git commit -m "feat: add Lambda, EventBridge schedule, SNS, CloudWatch alarm to CDK stack"
```

---

## Task 7: Deploy and verify

- [ ] **Step 1: Run all tests one final time**

```bash
cd apps/api && uv run pytest -v 2>&1 | tail -20
```

```bash
export NVM_DIR="$HOME/.nvm" && source "$NVM_DIR/nvm.sh" && nvm use 20 && cd infra && npm test 2>&1 | tail -10
```

Expected: all Python tests pass, all CDK tests pass.

- [ ] **Step 2: Deploy the stack**

```bash
cd infra && npx cdk deploy --context env=prod --context alertEmail=YOUR_EMAIL@example.com
```

Replace `YOUR_EMAIL@example.com` with your actual email address. CDK will:
1. Build the Docker image from `apps/api/Dockerfile.pipeline`
2. Push it to ECR
3. Deploy the Lambda, EventBridge rule, SNS topic, and CloudWatch alarm

Expected output ends with:
```
✅  livewell-prod

Outputs:
livewell-prod.PipelineLambdaArn = arn:aws:lambda:us-west-1:...
livewell-prod.AlertTopicArn = arn:aws:sns:us-west-1:...
```

Check your email — AWS SNS will send a subscription confirmation. Click the link to activate the alert.

- [ ] **Step 3: Test-invoke the Lambda**

In the AWS Console → Lambda → `livewell-pipeline-fn-prod` → Test tab. Create a test event with body `{}` and invoke. Check the CloudWatch logs for the run summary line:

```
run <uuid> completed: 18 ok, 0 errors
```

Also verify in DynamoDB Console:
- `livewell-model-runs-prod` has a record with `status: completed`
- `livewell-signals-prod` has 18 signal records

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "chore: Phase 4 sub-project 2 complete — batch pipeline deployed"
```

---

## Self-Review

**Spec coverage:**
- ✅ Lambda container, midnight UTC EventBridge schedule (Task 6)
- ✅ Per-instrument error isolation, `completed_with_errors` status (Task 3)
- ✅ `create_run`, `update_run`, `put_signal` DynamoDB writes (Task 1)
- ✅ `run_instrument` calls ingest → features → signals (Task 2)
- ✅ `score: null`, `model_version: null` on all signal records (Task 2)
- ✅ `/api/signals` reads from DynamoDB, returns most recent date's signals (Task 4)
- ✅ `signalId` added to `ContractCard` (Task 4)
- ✅ Fallback to empty list when `LIVEWELL_ENV` not set (Task 4)
- ✅ SNS topic + email subscription (Task 6)
- ✅ CloudWatch alarm on Lambda errors (Task 6)
- ✅ CDK assertions tests for all new constructs (Task 6)
- ✅ Dockerfile for Lambda container (Task 5)

**Placeholder scan:** None found.

**Type consistency:**
- `run_instrument(s3_key, run_id) -> dict` defined in Task 2, called in Task 3 ✅
- `create_run`, `update_run`, `put_signal` defined in Task 1, imported in Task 3 ✅
- `ContractCard.signalId` added in Task 4 Step 1, used in Task 4 Step 4 ✅
- `_fetch_signals_from_dynamodb()` defined and called within `routers/signals.py` ✅

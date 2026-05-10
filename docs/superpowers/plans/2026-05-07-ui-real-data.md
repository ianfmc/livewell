# UI Real Data Wiring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace MSW mock data with real FastAPI endpoints backed by DynamoDB, deployed as a Lambda Function URL.

**Architecture:** Deploy FastAPI as a Docker Lambda with a public Function URL. Add a `livewell/signals/` service layer in the API that reads DynamoDB and maps raw records to typed response schemas. Update the React frontend to use `VITE_API_BASE_URL` and make MSW opt-in via `VITE_USE_MOCKS`.

**Tech Stack:** FastAPI, Mangum (ASGI adapter), AWS CDK (DockerImageFunction + FunctionUrl), DynamoDB boto3, React/Vite, TypeScript.

---

## File Map

**Create:**
- `apps/api/Dockerfile.api` — uvicorn server for Lambda
- `apps/api/livewell/signals/__init__.py` — package marker (note: directory already exists with `constants.py`)
- `apps/api/livewell/signals/dynamodb.py` — DynamoDB reads
- `apps/api/livewell/signals/transform.py` — raw record → schema mapping
- `apps/api/tests/signals/test_transform.py` — transform unit tests
- `apps/api/tests/signals/test_dynamodb.py` — dynamodb unit tests
- `apps/api/tests/routers/test_signals_router.py` — router integration tests
- `apps/api/tests/routers/test_dashboard_router.py` — dashboard integration tests
- `apps/web/src/lib/api.ts` — `API_BASE` export

**Modify:**
- `apps/api/main.py` — Mangum handler, env-based CORS, `/health` endpoint
- `apps/api/routers/signals.py` — replace stub with service layer calls
- `apps/api/routers/dashboard.py` — replace hardcoded data with real aggregation
- `apps/api/routers/model_health.py` — replace stub with registry data
- `apps/api/routers/tracker.py` — replace stub with DynamoDB scan
- `apps/api/schemas/contract.py` — make `modelProbability` optional (None for unscored signals)
- `infra/lib/livewell-stack.ts` — add API Lambda + Function URL
- `apps/web/src/hooks/useSignals.ts` — use `API_BASE`
- `apps/web/src/hooks/useDashboard.ts` — use `API_BASE`
- `apps/web/src/hooks/useContractDetail.ts` — use `API_BASE`
- `apps/web/src/hooks/useModelHealth.ts` — use `API_BASE`
- `apps/web/src/hooks/useSignalTracker.ts` — use `API_BASE`
- `apps/web/src/hooks/useBacktest.ts` — use `API_BASE`
- `apps/web/.env.production` — set `VITE_API_BASE_URL` after deploy

---

## Task 1: Transform layer — core mapping functions

**Files:**
- Create: `apps/api/livewell/signals/transform.py`
- Create: `apps/api/tests/signals/__init__.py`
- Create: `apps/api/tests/signals/test_transform.py`

- [ ] **Step 1: Create the test file**

```python
# apps/api/tests/signals/test_transform.py
from __future__ import annotations
import pytest
from livewell.signals.transform import (
    to_contract_card,
    to_contract_detail,
    _recommendation,
    _confidence,
)

BASE = {
    "signal_id": "EURUSD__2026-05-07",
    "s3_key": "EURUSD",
    "date": "2026-05-07",
    "strike_candidate": "1.0850",
    "timing_slot": "12:00",
    "timing_risk": "moderate",
    "signal_valid": True,
    "direction": "buy",
    "trend_bias": "bullish",
    "reasoning": '[{"label": "EMA cross confirmed", "positive": true}]',
    "score": "0.71",
    "model_version": "20260507T144919",
}


def _rec(**kwargs):
    return {**BASE, **kwargs}


class TestRecommendation:
    def test_take_high_score_valid(self):
        assert _recommendation(0.65, True, "buy") == "Take"

    def test_take_exact_boundary(self):
        assert _recommendation(0.65, True, "buy") == "Take"

    def test_watch_mid_score(self):
        assert _recommendation(0.60, True, "buy") == "Watch"

    def test_watch_invalid_signal(self):
        assert _recommendation(0.70, False, "buy") == "Watch"

    def test_pass_low_score(self):
        assert _recommendation(0.50, True, "buy") == "Pass"

    def test_pass_no_direction(self):
        assert _recommendation(0.70, True, "none") == "Pass"

    def test_null_score_returns_watch(self):
        assert _recommendation(None, True, "buy") == "Watch"


class TestConfidence:
    def test_high(self):
        assert _confidence(0.70) == "High"

    def test_high_exact_boundary(self):
        assert _confidence(0.70) == "High"

    def test_medium(self):
        assert _confidence(0.64) == "Medium"

    def test_medium_lower_boundary(self):
        assert _confidence(0.58) == "Medium"

    def test_low(self):
        assert _confidence(0.50) == "Low"

    def test_null_score_returns_low(self):
        assert _confidence(None) == "Low"


class TestToContractCard:
    def test_instrument_display_name(self):
        card = to_contract_card(BASE)
        assert card.instrument == "EUR/USD"

    def test_strike_and_expiry(self):
        card = to_contract_card(BASE)
        assert card.strike == "1.0850"
        assert card.expiry == "12:00"

    def test_signal_id(self):
        card = to_contract_card(BASE)
        assert card.signalId == "EURUSD__2026-05-07"

    def test_status_take_maps_to_open(self):
        card = to_contract_card(_rec(score="0.71", signal_valid=True, direction="buy"))
        assert card.status == "Open"

    def test_status_watch_maps_to_review(self):
        card = to_contract_card(_rec(score="0.60", signal_valid=True, direction="buy"))
        assert card.status == "Review"

    def test_status_pass_maps_to_closed(self):
        card = to_contract_card(_rec(score="0.40", signal_valid=True, direction="buy"))
        assert card.status == "Closed"

    def test_unknown_s3_key_passes_through(self):
        card = to_contract_card(_rec(s3_key="UNKNOWN"))
        assert card.instrument == "UNKNOWN"


class TestToContractDetail:
    def test_recommendation_take(self):
        detail = to_contract_detail(BASE)
        assert detail.recommendation == "Take"

    def test_confidence_high(self):
        detail = to_contract_detail(BASE)
        assert detail.confidence == "High"

    def test_edge_calculation(self):
        detail = to_contract_detail(BASE)
        assert abs(detail.edge - (0.71 * 2 - 1)) < 0.001

    def test_model_probability_set(self):
        detail = to_contract_detail(BASE)
        assert abs(detail.modelProbability - 0.71) < 0.001

    def test_model_probability_null_for_unscored(self):
        detail = to_contract_detail(_rec(score=None, model_version=None))
        assert detail.modelProbability is None

    def test_no_trade_flag_high_risk(self):
        detail = to_contract_detail(_rec(timing_risk="high"))
        assert detail.noTradeFlag is True

    def test_no_trade_flag_moderate_risk(self):
        detail = to_contract_detail(_rec(timing_risk="moderate"))
        assert detail.noTradeFlag is False

    def test_reason_codes_parsed(self):
        detail = to_contract_detail(BASE)
        assert len(detail.reasonCodes) == 1
        assert detail.reasonCodes[0].label == "EMA cross confirmed"
        assert detail.reasonCodes[0].positive is True

    def test_reason_codes_empty_on_bad_json(self):
        detail = to_contract_detail(_rec(reasoning="not-json"))
        assert detail.reasonCodes == []

    def test_regime_passed_through(self):
        detail = to_contract_detail(BASE)
        assert detail.regime == "bullish"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd apps/api && uv run pytest tests/signals/test_transform.py -v 2>&1 | head -20
```

Expected: `ModuleNotFoundError` or `ImportError` — `transform.py` does not exist yet.

- [ ] **Step 3: Create the transform module**

```python
# apps/api/livewell/signals/transform.py
from __future__ import annotations
import json
import logging
from decimal import Decimal

from livewell.ingestion.constants import INSTRUMENTS
from schemas.contract import ContractCard, ContractDetail, Economics, ReasonCode

logger = logging.getLogger(__name__)

_S3_KEY_TO_NAME: dict[str, str] = {inst["s3_key"]: inst["name"] for inst in INSTRUMENTS}


def _score(record: dict) -> float | None:
    raw = record.get("score")
    if raw is None:
        return None
    try:
        return float(Decimal(str(raw))) if isinstance(raw, Decimal) else float(raw)
    except (ValueError, TypeError):
        return None


def _recommendation(score: float | None, signal_valid: bool, direction: str) -> str:
    if score is None:
        return "Watch"
    if direction == "none":
        return "Pass"
    if score < 0.55:
        return "Pass"
    if score >= 0.65 and signal_valid:
        return "Take"
    return "Watch"


def _confidence(score: float | None) -> str:
    if score is None or score < 0.58:
        return "Low"
    if score >= 0.70:
        return "High"
    return "Medium"


def _status(rec: str) -> str:
    return {"Take": "Open", "Watch": "Review", "Pass": "Closed"}.get(rec, "Closed")


def _parse_reason_codes(reasoning: str) -> list[ReasonCode]:
    try:
        items = json.loads(reasoning)
        return [ReasonCode(label=r["label"], positive=bool(r["positive"])) for r in items]
    except Exception:
        return []


def to_contract_card(record: dict) -> ContractCard:
    s3_key = str(record.get("s3_key", ""))
    score = _score(record)
    signal_valid = bool(record.get("signal_valid", False))
    direction = str(record.get("direction", "none"))
    rec = _recommendation(score, signal_valid, direction)
    return ContractCard(
        instrument=_S3_KEY_TO_NAME.get(s3_key, s3_key),
        strike=str(record.get("strike_candidate", "")),
        expiry=str(record.get("timing_slot", "")),
        status=_status(rec),
        signalId=str(record.get("signal_id", "")),
    )


def to_contract_detail(record: dict) -> ContractDetail:
    s3_key = str(record.get("s3_key", ""))
    score = _score(record)
    signal_valid = bool(record.get("signal_valid", False))
    direction = str(record.get("direction", "none"))
    rec = _recommendation(score, signal_valid, direction)
    conf = _confidence(score)
    edge = round(score * 2 - 1, 4) if score is not None else 0.0
    return ContractDetail(
        instrument=_S3_KEY_TO_NAME.get(s3_key, s3_key),
        strike=str(record.get("strike_candidate", "")),
        expiry=str(record.get("timing_slot", "")),
        status=_status(rec),
        recommendation=rec,
        rationale=f"{rec} — score {score:.2f}" if score is not None else "No model score available",
        economics=Economics(cost=40.0, payout=100.0, breakeven=0.40),
        modelProbability=score,
        edge=edge,
        confidence=conf,
        regime=str(record.get("trend_bias", "")),
        noTradeFlag=(str(record.get("timing_risk", "")).lower() == "high"),
        reasonCodes=_parse_reason_codes(str(record.get("reasoning", "[]"))),
    )
```

- [ ] **Step 4: Create the `__init__.py` files**

```bash
touch apps/api/livewell/signals/__init__.py
mkdir -p apps/api/tests/signals
touch apps/api/tests/signals/__init__.py
```

- [ ] **Step 5: Run tests and verify they pass**

```bash
cd apps/api && uv run pytest tests/signals/test_transform.py -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add apps/api/livewell/signals/transform.py apps/api/livewell/signals/__init__.py apps/api/tests/signals/ && git commit -m "feat: add signal transform layer (DynamoDB record → ContractCard/ContractDetail)"
```

---

## Task 2: DynamoDB read functions

**Files:**
- Create: `apps/api/livewell/signals/dynamodb.py`
- Create: `apps/api/tests/signals/test_dynamodb.py`

- [ ] **Step 1: Write the failing tests**

```python
# apps/api/tests/signals/test_dynamodb.py
from __future__ import annotations
import os
from unittest.mock import MagicMock, patch
import pytest


@pytest.fixture(autouse=True)
def env(monkeypatch):
    monkeypatch.setenv("LIVEWELL_ENV", "test")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")


SIGNAL_A = {
    "signal_id": "EURUSD__2026-05-07",
    "s3_key": "EURUSD",
    "date": "2026-05-07",
    "score": "0.71",
}

SIGNAL_B = {
    "signal_id": "EURUSD__2026-05-06",
    "s3_key": "EURUSD",
    "date": "2026-05-06",
    "score": "0.60",
}

SIGNAL_C = {
    "signal_id": "GBPUSD__2026-05-07",
    "s3_key": "GBPUSD",
    "date": "2026-05-07",
    "score": "0.55",
}


def _mock_table(items):
    table = MagicMock()
    table.scan.return_value = {"Items": items}
    return table


def test_get_latest_signals_returns_most_recent_per_instrument():
    with patch("livewell.signals.dynamodb._table", return_value=_mock_table([SIGNAL_A, SIGNAL_B, SIGNAL_C])):
        from livewell.signals.dynamodb import get_latest_signals
        result = get_latest_signals()
    signal_ids = {r["signal_id"] for r in result}
    assert "EURUSD__2026-05-07" in signal_ids
    assert "GBPUSD__2026-05-07" in signal_ids
    assert "EURUSD__2026-05-06" not in signal_ids


def test_get_latest_signals_empty_table():
    with patch("livewell.signals.dynamodb._table", return_value=_mock_table([])):
        from livewell.signals.dynamodb import get_latest_signals
        result = get_latest_signals()
    assert result == []


def test_get_signal_returns_matching_record():
    with patch("livewell.signals.dynamodb._table", return_value=_mock_table([SIGNAL_A, SIGNAL_B])):
        from livewell.signals.dynamodb import get_signal
        result = get_signal("EURUSD", "2026-05-07")
    assert result is not None
    assert result["signal_id"] == "EURUSD__2026-05-07"


def test_get_signal_returns_none_when_not_found():
    with patch("livewell.signals.dynamodb._table", return_value=_mock_table([SIGNAL_A])):
        from livewell.signals.dynamodb import get_signal
        result = get_signal("EURUSD", "2026-01-01")
    assert result is None
```

- [ ] **Step 2: Run tests to confirm failure**

```bash
cd apps/api && uv run pytest tests/signals/test_dynamodb.py -v 2>&1 | head -10
```

Expected: `ImportError` — `dynamodb.py` doesn't exist yet.

- [ ] **Step 3: Implement `dynamodb.py`**

```python
# apps/api/livewell/signals/dynamodb.py
from __future__ import annotations
import logging
import os

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


def _table():
    env = os.environ.get("LIVEWELL_ENV", "prod")
    region = os.environ.get("AWS_DEFAULT_REGION", "us-west-1")
    return boto3.resource("dynamodb", region_name=region).Table(f"livewell-signals-{env}")


def get_latest_signals() -> list[dict]:
    """Scan signals table; return one record per instrument (the most recent by date)."""
    try:
        table = _table()
        resp = table.scan()
        items: list[dict] = list(resp.get("Items", []))
        while "LastEvaluatedKey" in resp:
            resp = table.scan(ExclusiveStartKey=resp["LastEvaluatedKey"])
            items.extend(resp.get("Items", []))
    except ClientError as exc:
        logger.error("DynamoDB scan failed: %s", exc)
        return []

    # Keep only the most recent record per instrument (s3_key)
    latest: dict[str, dict] = {}
    for item in items:
        key = str(item.get("s3_key", ""))
        existing = latest.get(key)
        if existing is None or str(item.get("date", "")) > str(existing.get("date", "")):
            latest[key] = item
    return list(latest.values())


def get_signal(instrument: str, date: str) -> dict | None:
    """Return the signal record for instrument on date, or None."""
    signal_id = f"{instrument}__{date}"
    try:
        table = _table()
        resp = table.get_item(Key={"signal_id": signal_id})
        return resp.get("Item")
    except ClientError as exc:
        logger.error("DynamoDB get_item failed: %s", exc)
        return None
```

- [ ] **Step 4: Run tests and verify they pass**

```bash
cd apps/api && uv run pytest tests/signals/test_dynamodb.py -v
```

Expected: all 4 tests pass.

- [ ] **Step 5: Commit**

```bash
git add apps/api/livewell/signals/dynamodb.py apps/api/tests/signals/test_dynamodb.py && git commit -m "feat: add DynamoDB read functions for signals service layer"
```

---

## Task 3: Wire signals and dashboard routers to real data

**Files:**
- Modify: `apps/api/routers/signals.py`
- Modify: `apps/api/routers/dashboard.py`
- Modify: `apps/api/schemas/contract.py`
- Create: `apps/api/tests/routers/__init__.py`
- Create: `apps/api/tests/routers/test_signals_router.py`
- Create: `apps/api/tests/routers/test_dashboard_router.py`

- [ ] **Step 1: Update `schemas/contract.py` — make `modelProbability` optional**

```python
# apps/api/schemas/contract.py
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel


class ContractCard(BaseModel):
    instrument: str
    strike: str
    expiry: str
    status: str
    signalId: str = ""


class Economics(BaseModel):
    cost: float
    payout: float
    breakeven: float


class ReasonCode(BaseModel):
    label: str
    positive: bool


class ContractDetail(BaseModel):
    instrument: str
    strike: str
    expiry: str
    status: str
    recommendation: Literal["Take", "Watch", "Pass"]
    rationale: str
    economics: Economics
    modelProbability: float | None
    edge: float
    confidence: Literal["High", "Medium", "Low"]
    regime: str
    noTradeFlag: bool
    reasonCodes: list[ReasonCode]
```

- [ ] **Step 2: Write router tests**

```python
# apps/api/tests/routers/test_signals_router.py
from __future__ import annotations
import pytest
from unittest.mock import patch
from httpx import AsyncClient, ASGITransport
from main import app

DYNAMO_SIGNAL = {
    "signal_id": "EURUSD__2026-05-07",
    "s3_key": "EURUSD",
    "date": "2026-05-07",
    "strike_candidate": "1.0850",
    "timing_slot": "12:00",
    "timing_risk": "moderate",
    "signal_valid": True,
    "direction": "buy",
    "trend_bias": "bullish",
    "reasoning": "[]",
    "score": "0.71",
    "model_version": "20260507T144919",
}


@pytest.fixture(autouse=True)
def env(monkeypatch):
    monkeypatch.setenv("LIVEWELL_ENV", "test")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")


@pytest.mark.anyio
async def test_get_signals_returns_list():
    with patch("routers.signals.get_latest_signals", return_value=[DYNAMO_SIGNAL]):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/signals")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["instrument"] == "EUR/USD"
    assert data[0]["status"] == "Open"


@pytest.mark.anyio
async def test_get_signals_empty_returns_empty_list():
    with patch("routers.signals.get_latest_signals", return_value=[]):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/signals")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.anyio
async def test_get_signal_detail_found():
    with patch("routers.signals.get_signal", return_value=DYNAMO_SIGNAL):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/signals/EUR-USD/1.0850")
    assert resp.status_code == 200
    data = resp.json()
    assert data["recommendation"] == "Take"
    assert data["confidence"] == "High"
    assert data["noTradeFlag"] is False


@pytest.mark.anyio
async def test_get_signal_detail_not_found():
    with patch("routers.signals.get_signal", return_value=None):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/signals/EUR-USD/9.9999")
    assert resp.status_code == 404
```

```python
# apps/api/tests/routers/test_dashboard_router.py
from __future__ import annotations
import pytest
from unittest.mock import patch
from httpx import AsyncClient, ASGITransport
from main import app

SIGNALS = [
    {"s3_key": "EURUSD", "date": "2026-05-07", "signal_id": "EURUSD__2026-05-07",
     "score": "0.71", "signal_valid": True, "direction": "buy",
     "strike_candidate": "1.0850", "timing_slot": "12:00", "timing_risk": "moderate",
     "trend_bias": "bullish", "reasoning": "[]"},
    {"s3_key": "GBPUSD", "date": "2026-05-07", "signal_id": "GBPUSD__2026-05-07",
     "score": "0.58", "signal_valid": True, "direction": "buy",
     "strike_candidate": "1.2650", "timing_slot": "12:00", "timing_risk": "low",
     "trend_bias": "neutral", "reasoning": "[]"},
    {"s3_key": "USDJPY", "date": "2026-05-07", "signal_id": "USDJPY__2026-05-07",
     "score": "0.40", "signal_valid": False, "direction": "none",
     "strike_candidate": "150.00", "timing_slot": "09:30", "timing_risk": "low",
     "trend_bias": "bearish", "reasoning": "[]"},
]

REGISTRY = {
    "version": "20260507T144919",
    "trained_at": "2026-05-07T14:49:19+00:00",
    "win_rate": "0.86",
    "status": "active",
}


@pytest.fixture(autouse=True)
def env(monkeypatch):
    monkeypatch.setenv("LIVEWELL_ENV", "test")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")


@pytest.mark.anyio
async def test_dashboard_counts():
    with patch("routers.dashboard.get_latest_signals", return_value=SIGNALS), \
         patch("routers.dashboard.get_active_model", return_value=REGISTRY):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/dashboard")
    assert resp.status_code == 200
    data = resp.json()
    assert data["opportunities"]["total"] == 3
    assert data["opportunities"]["passing"] == 1   # EURUSD score >= 0.65
    assert data["opportunities"]["review"] == 1    # GBPUSD score 0.55–0.65


@pytest.mark.anyio
async def test_dashboard_top_candidates_ordered_by_score():
    with patch("routers.dashboard.get_latest_signals", return_value=SIGNALS), \
         patch("routers.dashboard.get_active_model", return_value=REGISTRY):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/dashboard")
    data = resp.json()
    candidates = data["topCandidates"]
    assert candidates[0]["instrument"] == "EUR/USD"
```

- [ ] **Step 3: Run tests to confirm failure**

```bash
cd apps/api && uv run pytest tests/routers/test_signals_router.py tests/routers/test_dashboard_router.py -v 2>&1 | head -15
```

Expected: tests fail because routers still use stub/hardcoded data.

- [ ] **Step 4: Rewrite `routers/signals.py`**

```python
# apps/api/routers/signals.py
from __future__ import annotations
import logging
from fastapi import APIRouter, HTTPException

from livewell.signals.dynamodb import get_latest_signals, get_signal
from livewell.signals.transform import to_contract_card, to_contract_detail
from schemas.contract import ContractCard, ContractDetail

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/signals", response_model=list[ContractCard])
def get_signals() -> list[ContractCard]:
    records = get_latest_signals()
    return [to_contract_card(r) for r in records]


@router.get("/signals/{instrument}/{strike}", response_model=ContractDetail)
def get_signal_detail(instrument: str, strike: str) -> ContractDetail:
    # URL encodes "/" as "-" (e.g. EUR-USD → EURUSD s3_key)
    s3_key = instrument.replace("-", "").upper()
    # Determine today's date from latest signals
    records = get_latest_signals()
    if not records:
        raise HTTPException(status_code=404, detail="No signals available")
    latest_date = max(r.get("date", "") for r in records)
    record = get_signal(s3_key, latest_date)
    if record is None:
        raise HTTPException(status_code=404, detail="Signal not found")
    return to_contract_detail(record)
```

- [ ] **Step 5: Rewrite `routers/dashboard.py`**

```python
# apps/api/routers/dashboard.py
from __future__ import annotations
import logging
from decimal import Decimal
from fastapi import APIRouter

from livewell.signals.dynamodb import get_latest_signals
from livewell.signals.transform import to_contract_card, _score, _confidence, _S3_KEY_TO_NAME
from livewell.models.registry import get_active_model
from schemas.dashboard import (
    DashboardData, MarketSnapshot, ModelHealth,
    OpportunitySummary, TopCandidate,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/dashboard", response_model=DashboardData)
def get_dashboard() -> DashboardData:
    records = get_latest_signals()

    total = len(records)
    passing = sum(1 for r in records if (_score(r) or 0) >= 0.65)
    review = sum(1 for r in records if 0.55 <= (_score(r) or 0) < 0.65)

    sorted_records = sorted(records, key=lambda r: _score(r) or 0.0, reverse=True)
    top_candidates = [
        TopCandidate(
            instrument=_S3_KEY_TO_NAME.get(str(r.get("s3_key", "")), str(r.get("s3_key", ""))),
            strike=str(r.get("strike_candidate", "")),
            expiry=str(r.get("timing_slot", "")),
            edge=f"{(_score(r) or 0) * 2 - 1:+.2f}",
            confidence=_confidence(_score(r)),
        )
        for r in sorted_records[:3]
    ]

    markets = [
        MarketSnapshot(
            instrument=_S3_KEY_TO_NAME.get(str(r.get("s3_key", "")), str(r.get("s3_key", ""))),
            regime=_map_regime(str(r.get("trend_bias", "neutral"))),
            noTrade=(str(r.get("timing_risk", "")).lower() == "high"),
        )
        for r in records
    ]

    try:
        reg = get_active_model()
        trained_at = str(reg.get("trained_at", ""))[:10]
        model_health = ModelHealth(
            trainingDate=trained_at,
            dataFreshness="Current",
            status="Healthy",
        )
    except RuntimeError:
        model_health = ModelHealth(trainingDate="unknown", dataFreshness="Stale", status="Degraded")

    return DashboardData(
        markets=markets,
        opportunities=OpportunitySummary(total=total, passing=passing, review=review),
        topCandidates=top_candidates,
        modelHealth=model_health,
    )


def _map_regime(trend_bias: str) -> str:
    mapping = {"bullish": "Bullish", "bearish": "Bearish"}
    return mapping.get(trend_bias.lower(), "Neutral")
```

- [ ] **Step 6: Run tests and verify they pass**

```bash
cd apps/api && uv run pytest tests/routers/test_signals_router.py tests/routers/test_dashboard_router.py -v
```

Expected: all tests pass.

- [ ] **Step 7: Run full test suite to check for regressions**

```bash
cd apps/api && uv run pytest -v 2>&1 | tail -20
```

Expected: all existing tests still pass.

- [ ] **Step 8: Commit**

```bash
git add apps/api/routers/signals.py apps/api/routers/dashboard.py apps/api/schemas/contract.py apps/api/tests/routers/ && git commit -m "feat: wire signals and dashboard routers to real DynamoDB data"
```

---

## Task 4: Wire model health and signal tracker routers

**Files:**
- Modify: `apps/api/routers/model_health.py`
- Modify: `apps/api/routers/tracker.py`

- [ ] **Step 1: Rewrite `routers/model_health.py`**

```python
# apps/api/routers/model_health.py
from __future__ import annotations
import logging
from fastapi import APIRouter
from livewell.models.registry import get_active_model
from schemas.model_health import DriftWarning, FeatureStatus, ModelHealth

logger = logging.getLogger(__name__)
router = APIRouter()

_FEATURE_NAMES = [
    "EMA-20", "EMA-50", "RSI-14", "MACD Signal",
    "ATR-14", "Session Flag", "Direction", "Instrument",
]


@router.get("/model/health", response_model=ModelHealth)
def get_model_health() -> ModelHealth:
    try:
        reg = get_active_model()
        trained_at = str(reg.get("trained_at", ""))[:10]
        win_rate = float(reg.get("win_rate", 0))
        validation_accuracy = win_rate
        return ModelHealth(
            overallStatus="Healthy" if win_rate >= 0.60 else "Warning",
            trainingDate=trained_at,
            dataFreshness="Current",
            calibrationError=0.0,
            validationAccuracy=validation_accuracy,
            features=[FeatureStatus(name=f, status="Available") for f in _FEATURE_NAMES],
            driftWarnings=[],
        )
    except RuntimeError:
        return ModelHealth(
            overallStatus="Degraded",
            trainingDate="unknown",
            dataFreshness="Stale",
            calibrationError=0.0,
            validationAccuracy=0.0,
            features=[FeatureStatus(name=f, status="Missing") for f in _FEATURE_NAMES],
            driftWarnings=[DriftWarning(feature="All", description="No active model in registry.")],
        )
```

- [ ] **Step 2: Rewrite `routers/tracker.py`**

The signal tracker shows historical signals. We read all signals from DynamoDB (not just the latest per instrument) and return them sorted by date descending. `outcome` is always `"Pending"` since we don't track outcomes yet — that's a future phase.

```python
# apps/api/routers/tracker.py
from __future__ import annotations
import logging
import os
from decimal import Decimal
from fastapi import APIRouter
import boto3
from botocore.exceptions import ClientError

from livewell.ingestion.constants import INSTRUMENTS
from livewell.signals.transform import _score, _recommendation, _confidence, _S3_KEY_TO_NAME
from schemas.tracker import TrackedSignal

logger = logging.getLogger(__name__)
router = APIRouter()


def _all_signals() -> list[dict]:
    env = os.environ.get("LIVEWELL_ENV", "prod")
    region = os.environ.get("AWS_DEFAULT_REGION", "us-west-1")
    try:
        table = boto3.resource("dynamodb", region_name=region).Table(f"livewell-signals-{env}")
        resp = table.scan()
        items: list[dict] = list(resp.get("Items", []))
        while "LastEvaluatedKey" in resp:
            resp = table.scan(ExclusiveStartKey=resp["LastEvaluatedKey"])
            items.extend(resp.get("Items", []))
        return items
    except ClientError as exc:
        logger.error("DynamoDB scan failed: %s", exc)
        return []


@router.get("/signals/tracker", response_model=list[TrackedSignal])
def get_signal_tracker() -> list[TrackedSignal]:
    records = sorted(_all_signals(), key=lambda r: str(r.get("date", "")), reverse=True)
    result = []
    for r in records:
        score = _score(r)
        signal_valid = bool(r.get("signal_valid", False))
        direction = str(r.get("direction", "none"))
        rec = _recommendation(score, signal_valid, direction)
        result.append(TrackedSignal(
            date=str(r.get("date", "")),
            market=_S3_KEY_TO_NAME.get(str(r.get("s3_key", "")), str(r.get("s3_key", ""))),
            strike=str(r.get("strike_candidate", "")),
            expiry=str(r.get("timing_slot", "")),
            recommendation=rec,
            actionTaken=None,
            outcome="Pending",
            edge=round((score * 2 - 1), 4) if score is not None else 0.0,
            modelProbability=score if score is not None else 0.0,
        ))
    return result
```

- [ ] **Step 3: Run full test suite**

```bash
cd apps/api && uv run pytest -v 2>&1 | tail -20
```

Expected: all tests pass.

- [ ] **Step 4: Commit**

```bash
git add apps/api/routers/model_health.py apps/api/routers/tracker.py && git commit -m "feat: wire model_health and tracker routers to real registry and DynamoDB data"
```

---

## Task 5: Update `main.py` — Mangum, health endpoint, env-based CORS

**Files:**
- Modify: `apps/api/main.py`

- [ ] **Step 1: Add `mangum` to dependencies**

```bash
cd apps/api && uv add mangum
```

- [ ] **Step 2: Rewrite `main.py`**

```python
# apps/api/main.py
from __future__ import annotations
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import signals, dashboard, backtest, model_health, tracker, explain

app = FastAPI(title="LIVEWELL API", version="0.1.0")

_default_origins = "http://localhost:5173,http://localhost:5174,http://localhost:5175,http://localhost:4173"
origins = os.environ.get("CORS_ORIGINS", _default_origins).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(signals.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(backtest.router, prefix="/api")
app.include_router(model_health.router, prefix="/api")
app.include_router(tracker.router, prefix="/api")
app.include_router(explain.router, prefix="/api")


@app.get("/health")
def health():
    return {"status": "ok"}


# Lambda entrypoint
try:
    from mangum import Mangum
    handler = Mangum(app)
except ImportError:
    pass  # not required for local dev
```

- [ ] **Step 3: Verify health endpoint works locally**

```bash
cd apps/api && uv run uvicorn main:app --port 8000 &
sleep 2
curl http://localhost:8000/health
kill %1
```

Expected: `{"status":"ok"}`

- [ ] **Step 4: Run test suite**

```bash
cd apps/api && uv run pytest -v 2>&1 | tail -10
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add apps/api/main.py apps/api/pyproject.toml apps/api/uv.lock && git commit -m "feat: add Mangum handler, env-based CORS, and /health endpoint to FastAPI"
```

---

## Task 6: Create `Dockerfile.api` for Lambda

**Files:**
- Create: `apps/api/Dockerfile.api`

- [ ] **Step 1: Create the Dockerfile**

```dockerfile
# apps/api/Dockerfile.api
FROM public.ecr.aws/lambda/python:3.12

# Install uv
RUN pip install --no-cache-dir uv

# Copy project files
COPY pyproject.toml uv.lock ./
COPY . /var/task
RUN uv pip install --system --no-cache .

CMD ["main.handler"]
```

- [ ] **Step 2: Build the image locally to verify it compiles**

```bash
cd apps/api && docker build -f Dockerfile.api -t livewell-api-test . 2>&1 | tail -5
```

Expected: `Successfully built ...` with no errors.

- [ ] **Step 3: Commit**

```bash
git add apps/api/Dockerfile.api && git commit -m "feat: add Dockerfile.api for FastAPI Lambda deployment"
```

---

## Task 7: Add API Lambda to CDK stack

**Files:**
- Modify: `infra/lib/livewell-stack.ts`

- [ ] **Step 1: Add the API Lambda and Function URL to the stack**

In `infra/lib/livewell-stack.ts`, add the following after the pipeline Lambda section (before the outputs section at the end). The existing variables `signalsTable`, `modelRegistryTable`, `bucket`, and `env` are already defined earlier in the constructor.

```typescript
// ── API Lambda (FastAPI + Mangum) ─────────────────────────────────────────
const apiLambda = new lambda.DockerImageFunction(this, 'ApiLambda', {
  functionName: `livewell-api-fn-${env}`,
  code: lambda.DockerImageCode.fromImageAsset(
    path.join(__dirname, '../../apps/api'),
    { file: 'Dockerfile.api' }
  ),
  architecture: lambda.Architecture.ARM_64,
  memorySize: 512,
  timeout: cdk.Duration.seconds(30),
  environment: {
    LIVEWELL_ENV: env,
    LIVEWELL_BUCKET: bucket.bucketName,
    CORS_ORIGINS: (this.node.tryGetContext('corsOrigins') as string | undefined) ?? '*',
  },
});

signalsTable.grantReadData(apiLambda);
modelRegistryTable.grantReadData(apiLambda);

const apiUrl = apiLambda.addFunctionUrl({
  authType: lambda.FunctionUrlAuthType.NONE,
  cors: {
    allowedOrigins: ['*'],
    allowedMethods: [lambda.HttpMethod.GET],
    allowedHeaders: ['*'],
  },
});

new cdk.CfnOutput(this, 'ApiUrl', { value: apiUrl.url });
```

- [ ] **Step 2: Verify CDK synthesizes without errors**

```bash
cd infra && npx cdk synth --context env=prod 2>&1 | tail -5
```

Expected: output ends with YAML/JSON stack template, no errors.

- [ ] **Step 3: Commit**

```bash
git add infra/lib/livewell-stack.ts && git commit -m "feat: add API Lambda with Function URL to CDK stack"
```

---

## Task 8: Deploy and smoke test

**Files:**
- Create: `apps/web/.env.production`

- [ ] **Step 1: Deploy the CDK stack**

```bash
cd infra && npx cdk deploy --context env=prod --require-approval never 2>&1 | tail -20
```

Expected: deployment succeeds. Note the `ApiUrl` output value (e.g. `https://abc123.lambda-url.us-west-1.on.aws/`).

- [ ] **Step 2: Smoke test health endpoint**

```bash
API_URL="<paste ApiUrl output here>"
curl "$API_URL/health"
```

Expected: `{"status":"ok"}`

- [ ] **Step 3: Smoke test signals endpoint**

```bash
curl "$API_URL/api/signals" | python3 -m json.tool | head -30
```

Expected: JSON array with at least one instrument, `score` not null, `status` one of "Open"/"Review"/"Closed".

- [ ] **Step 4: Create `.env.production`**

```bash
# apps/web/.env.production
VITE_API_BASE_URL=<paste ApiUrl output here, no trailing slash>
VITE_USE_MOCKS=false
```

- [ ] **Step 5: Commit**

```bash
git add apps/web/.env.production && git commit -m "feat: set VITE_API_BASE_URL to deployed Lambda Function URL"
```

---

## Task 9: Update frontend hooks to use `API_BASE`

**Files:**
- Create: `apps/web/src/lib/api.ts`
- Modify: `apps/web/src/hooks/useSignals.ts`
- Modify: `apps/web/src/hooks/useDashboard.ts`
- Modify: `apps/web/src/hooks/useContractDetail.ts`
- Modify: `apps/web/src/hooks/useModelHealth.ts`
- Modify: `apps/web/src/hooks/useSignalTracker.ts`
- Modify: `apps/web/src/hooks/useBacktest.ts`

- [ ] **Step 1: Create `src/lib/api.ts`**

```typescript
// apps/web/src/lib/api.ts
export const API_BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "";
```

- [ ] **Step 2: Update `useSignals.ts`**

```typescript
// apps/web/src/hooks/useSignals.ts
import { useEffect, useState } from 'react';
import { API_BASE } from '../lib/api';
import type { ContractCard } from '../data/mockData';

type UseSignalsResult = {
  data: ContractCard[];
  loading: boolean;
  error: string | null;
};

export function useSignals(): UseSignalsResult {
  const [data, setData] = useState<ContractCard[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    fetch(`${API_BASE}/api/signals`, { signal: controller.signal })
      .then((res) => {
        if (!res.ok) throw new Error(`Request failed: ${res.status}`);
        return res.json() as Promise<ContractCard[]>;
      })
      .then((json) => { setData(json); })
      .catch((err: unknown) => {
        if (err instanceof Error && err.name === 'AbortError') return;
        setError(err instanceof Error ? err.message : 'Unknown error');
      })
      .finally(() => { setLoading(false); });
    return () => controller.abort();
  }, []);

  return { data, loading, error };
}
```

- [ ] **Step 3: Update `useDashboard.ts`**

```typescript
// apps/web/src/hooks/useDashboard.ts
import { useEffect, useState } from 'react';
import { API_BASE } from '../lib/api';
import type { DashboardData } from '../data/mockDashboard';

type UseDashboardResult = {
  data: DashboardData | null;
  loading: boolean;
  error: string | null;
};

export function useDashboard(): UseDashboardResult {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    fetch(`${API_BASE}/api/dashboard`, { signal: controller.signal })
      .then((res) => {
        if (!res.ok) throw new Error(`Request failed: ${res.status}`);
        return res.json() as Promise<DashboardData>;
      })
      .then((json) => { setData(json); })
      .catch((err: unknown) => {
        if (err instanceof Error && err.name === 'AbortError') return;
        setError(err instanceof Error ? err.message : 'Unknown error');
      })
      .finally(() => { setLoading(false); });
    return () => controller.abort();
  }, []);

  return { data, loading, error };
}
```

- [ ] **Step 4: Read and update the remaining three hooks**

First read them to get their exact current content:
```bash
cat apps/web/src/hooks/useContractDetail.ts
cat apps/web/src/hooks/useModelHealth.ts
cat apps/web/src/hooks/useSignalTracker.ts
cat apps/web/src/hooks/useBacktest.ts
```

Then in each file, add `import { API_BASE } from '../lib/api';` at the top and change every `fetch('/api/` to `fetch(\`${API_BASE}/api/`. The pattern is identical in all hooks.

- [ ] **Step 5: Run the frontend test suite**

```bash
cd apps/web && npm test -- --run 2>&1 | tail -20
```

Expected: all tests pass. (Tests use MSW which intercepts at the fetch level regardless of base URL — they are unaffected by this change.)

- [ ] **Step 6: Commit**

```bash
git add apps/web/src/lib/api.ts apps/web/src/hooks/ && git commit -m "feat: add API_BASE to all frontend hooks for configurable API URL"
```

---

## Task 10: Test the full stack in the browser

- [ ] **Step 1: Start the API locally**

```bash
cd apps/api && uv run uvicorn main:app --port 8000 --reload
```

- [ ] **Step 2: Start the frontend with mocks OFF**

In a second terminal:
```bash
cd apps/web
# Create .env.local without mocks (or temporarily set VITE_USE_MOCKS=false)
echo "VITE_USE_MOCKS=false" > .env.local
npm run dev
```

- [ ] **Step 3: Open http://localhost:5173 and verify each page**

Check each page loads real data (not the MSW fixtures):

- **DailySignals** — should show instruments from the pipeline run (EURUSD, GBPUSD, etc.), not the 3 hardcoded mock instruments
- **Dashboard** — opportunity counts should reflect actual signal scores
- **ModelHealth** — training date should match the registry (2026-05-07)
- **SignalTracker** — should show all pipeline signals, all with `outcome: "Pending"`
- **ContractDetail** — click a signal from DailySignals; verify recommendation/confidence come from real score

- [ ] **Step 4: Restore .env.local to mocks-on for future dev**

```bash
echo "VITE_USE_MOCKS=true" > apps/web/.env.local
```

- [ ] **Step 5: Final commit**

```bash
git add -A && git commit -m "feat: complete UI real data wiring — all pages on live DynamoDB via Lambda Function URL"
```

---

## Holdovers — identified during walkthrough (2026-05-09)

These were found during the post-deployment UI walkthrough and deferred to the next phase.

- [ ] **Explain: show error message when signal not found** — Tapping Explain on a signal with no S3 data (pipeline hasn't run for that date) silently fails. The endpoint returns 404 with `"Signal not found"` but the UI shows nothing. `SignalExplainPanel` should surface this as a visible error message.

- [ ] **Options Advisor: expand markets list** — `MARKETS` in `OptionsAdvisor.tsx` is hardcoded to 5 instruments (`['EUR/USD', 'GBP/USD', 'USD/JPY', 'Gold', 'US 500']`). Should pull from the live `/api/signals` response so all active instruments appear.

- [ ] **Options Advisor: step 3 radio buttons not spreading horizontally** — The three `RadioGroup` groups on step 3 (Trend Direction, Volatility, Event Risk) have the `row` prop but render left-justified instead of spread. Likely a container width or MUI layout issue — investigate and fix.

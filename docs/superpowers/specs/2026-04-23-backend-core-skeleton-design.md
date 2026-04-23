# Backend Core Skeleton — Design Spec

## Context

LIVEWELL Phase 1B. The frontend (`livewell-ui`) currently talks to MSW mock handlers. Phase 1B creates a real FastAPI backend (`livewell-api`) with route stubs that return the same data shapes, plus the empty `livewell/` domain module structure that Phase 2B extractions will populate.

The frontend does **not** switch off MSW in this phase — that happens in Phase 3 when the API has real model logic. Phase 1B delivers a working, tested Python API that can be verified independently.

---

## Decisions Made

| Question | Decision |
|---|---|
| Repo location | New `livewell-api/` sibling of `livewell-ui/` and `livewell-nadex/` |
| Tooling | `uv`, Python 3.12, `pyproject.toml` only |
| App structure | Flat FastAPI layout (not an installed package) |
| Domain stubs | Empty `livewell/` sub-modules alongside the app |
| Frontend switch | Deferred — MSW stays in `livewell-ui` until Phase 3 |
| CORS | Allowed origins: `http://localhost:5173`, `http://localhost:4173` |

---

## Repository Layout

```
livewell-api/
  pyproject.toml           # uv project file
  .python-version          # "3.12"
  README.md
  main.py                  # FastAPI app, CORS middleware, router mounts
  routers/
    __init__.py
    signals.py             # GET /api/signals  +  GET /api/signals/{instrument}/{strike}
    dashboard.py           # GET /api/dashboard
  schemas/
    __init__.py
    contract.py            # ContractCard, Economics, ReasonCode, ContractDetail
    dashboard.py           # MarketSnapshot, OpportunitySummary, TopCandidate,
                           #   ModelHealth, DashboardData
  livewell/                # domain module stubs — all empty __init__.py + one-line docstring
    __init__.py
    data/
      __init__.py
    features/
      __init__.py
    labels/
      __init__.py
    models/
      __init__.py
    decision/
      __init__.py
    backtest/
      __init__.py
    explanations/
      __init__.py
    tracking/
      __init__.py
    api/
      __init__.py
    jobs/
      __init__.py
  tests/
    __init__.py
    test_signals.py
    test_dashboard.py
```

---

## Tooling

### `pyproject.toml`

```toml
[project]
name = "livewell-api"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.111",
    "uvicorn[standard]>=0.30",
    "pydantic>=2.7",
]

[dependency-groups]
dev = [
    "pytest>=8.0",
    "httpx>=0.27",
]
```

### `.python-version`

```
3.12
```

### Dev commands

```bash
uv sync                                        # create venv + install deps
uv run uvicorn main:app --reload --port 8000   # start dev server
uv run pytest                                  # run tests
```

---

## Pydantic Schemas

Schemas mirror the TypeScript types in `livewell-ui/src/data/` exactly so the frontend can switch from MSW to FastAPI without any shape changes.

### `schemas/contract.py`

```python
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel


class ContractCard(BaseModel):
    instrument: str
    strike: str
    expiry: str
    status: str


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
    modelProbability: float
    edge: float
    confidence: Literal["High", "Medium", "Low"]
    regime: str
    noTradeFlag: bool
    reasonCodes: list[ReasonCode]
```

### `schemas/dashboard.py`

```python
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel


class MarketSnapshot(BaseModel):
    instrument: str
    regime: Literal["Bullish", "Bearish", "Neutral"]
    noTrade: bool


class OpportunitySummary(BaseModel):
    total: int
    passing: int
    review: int


class TopCandidate(BaseModel):
    instrument: str
    strike: str
    expiry: str
    edge: str
    confidence: Literal["High", "Medium", "Low"]


class ModelHealth(BaseModel):
    trainingDate: str
    dataFreshness: Literal["Current", "Stale"]
    status: Literal["Healthy", "Warning", "Degraded"]


class DashboardData(BaseModel):
    markets: list[MarketSnapshot]
    opportunities: OpportunitySummary
    topCandidates: list[TopCandidate]
    modelHealth: ModelHealth
```

---

## Routes

### `GET /api/signals` → `list[ContractCard]`

Returns the 3 mock instruments (EUR/USD, GBP/USD, USD/JPY). Same data as `mockData` in `livewell-ui`.

### `GET /api/signals/{instrument}/{strike}` → `ContractDetail` or 404

`instrument` parameter is hyphen-encoded in the URL (e.g. `EUR-USD`). The router decodes it (`EUR-USD` → `EUR/USD`) before matching. Raises `HTTPException(status_code=404, detail="Not found")` if no match. FastAPI serialises this as `{"detail": "Not found"}`. The frontend hook does not parse the 404 body — it only checks `response.ok`.

### `GET /api/dashboard` → `DashboardData`

Returns the mock dashboard. Same data as `mockDashboard` in `livewell-ui`.

---

## App Setup (`main.py`)

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import signals, dashboard

app = FastAPI(title="LIVEWELL API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:4173"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(signals.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
```

---

## Domain Module Stubs

Each `livewell/*/__ init__.py` contains only a one-line module docstring. No logic. These stubs establish the package shape for Phase 2B extractions.

Example (`livewell/decision/__init__.py`):
```python
"""Edge computation, rule overlays, and take/watch/pass classification."""
```

Module responsibilities (for docstrings):
- `data` — loaders, adapters, normalization
- `features` — technical indicators, regime features, transforms
- `labels` — target definitions and label generation
- `models` — training, inference, calibration, artifact loading
- `decision` — edge logic, thresholds, rule overlays
- `backtest` — replay engine, metrics, logs, equity curves
- `explanations` — reason codes, explanation builders
- `tracking` — signal persistence, outcome tracking, monitoring
- `api` — FastAPI routes and schemas (long-term home once package is real)
- `jobs` — scheduled refresh, scoring, retraining workflows

---

## Testing

Uses `fastapi.testclient.TestClient` (synchronous, no async test runner needed).

### `tests/test_signals.py` (3 tests)

1. `GET /api/signals` returns 200 and a list of 3 items
2. `GET /api/signals/EUR-USD/1.0850` returns 200 and `recommendation == "Take"`
3. `GET /api/signals/EUR-USD/9.9999` returns 404

### `tests/test_dashboard.py` (1 test)

1. `GET /api/dashboard` returns 200 and `opportunities.passing == 2`

---

## CORS Verification

After `uv run uvicorn main:app --reload --port 8000`, verify manually:

```bash
curl -s http://localhost:8000/api/signals | python -m json.tool
curl -s http://localhost:8000/api/signals/EUR-USD/1.0850 | python -m json.tool
curl -s http://localhost:8000/api/dashboard | python -m json.tool
```

---

## Definition of Done

- [ ] `livewell-api/` exists as a sibling of `livewell-ui/`
- [ ] `uv sync && uv run uvicorn main:app --reload` starts without errors
- [ ] All 4 tests pass (`uv run pytest`)
- [ ] All 3 routes return correct JSON verified by `curl`
- [ ] `livewell/` package has 10 sub-module stubs with docstrings
- [ ] CORS allows `http://localhost:5173`
- [ ] `git init` + initial commit in `livewell-api/`

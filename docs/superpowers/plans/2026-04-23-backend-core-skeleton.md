# Backend Core Skeleton Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create `livewell-api/` — a FastAPI backend with stub routes matching the frontend's MSW mock shapes, Pydantic schemas mirroring the TypeScript types, and empty `livewell/` domain module stubs that Phase 2B will populate.

**Architecture:** Flat FastAPI app (`main.py`) with two routers (`routers/signals.py`, `routers/dashboard.py`) and two schema modules (`schemas/contract.py`, `schemas/dashboard.py`). Domain logic stubs live in `livewell/` alongside the app. Data is hardcoded — identical to the current MSW handlers. The frontend does not switch off MSW in this phase.

**Tech Stack:** Python 3.12, uv, FastAPI 0.111+, Pydantic 2.7+, uvicorn, pytest 8+, httpx 0.27+

**Working directory for all tasks:** `/Users/i802235/Library/CloudStorage/OneDrive-SAPSE/Development/livewell-api/` (created in Task 1)

> **Worktree note:** `livewell-api` is a brand-new repo. Task 1 creates and initialises it with an initial commit. **After Task 1 completes and before Task 2 begins**, the controller must invoke `superpowers:using-git-worktrees` inside `livewell-api/` to create a feature branch for the remaining work.

---

## File Map

| File | Action | Purpose |
|---|---|---|
| `pyproject.toml` | Create | uv project, dependencies |
| `.python-version` | Create | Pin Python 3.12 |
| `.gitignore` | Create | Exclude .venv, __pycache__, etc. |
| `README.md` | Create | Setup and run instructions |
| `main.py` | Create | FastAPI app, CORS, router mounts |
| `routers/__init__.py` | Create | Package marker |
| `routers/signals.py` | Create | GET /api/signals + GET /api/signals/{instrument}/{strike} |
| `routers/dashboard.py` | Create | GET /api/dashboard |
| `schemas/__init__.py` | Create | Package marker |
| `schemas/contract.py` | Create | ContractCard, Economics, ReasonCode, ContractDetail |
| `schemas/dashboard.py` | Create | MarketSnapshot, OpportunitySummary, TopCandidate, ModelHealth, DashboardData |
| `livewell/__init__.py` + 10 sub-modules | Create | Empty domain stubs with docstrings |
| `tests/__init__.py` | Create | Package marker |
| `tests/test_schemas_contract.py` | Create | Schema instantiation + Literal validation tests |
| `tests/test_schemas_dashboard.py` | Create | Schema instantiation + Literal validation tests |
| `tests/test_signals.py` | Create | 3 route tests for signals |
| `tests/test_dashboard.py` | Create | 1 route test for dashboard |

---

## Task 1: Repository scaffold

**Files:**
- Create: `pyproject.toml`
- Create: `.python-version`
- Create: `.gitignore`
- Create: `README.md`

> This task has no TDD cycle — it is pure infrastructure. No application code is written here.

- [ ] **Step 1: Create the directory**

```bash
mkdir /Users/i802235/Library/CloudStorage/OneDrive-SAPSE/Development/livewell-api
cd /Users/i802235/Library/CloudStorage/OneDrive-SAPSE/Development/livewell-api
```

- [ ] **Step 2: Write `pyproject.toml`**

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

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 3: Write `.python-version`**

```
3.12
```

- [ ] **Step 4: Write `.gitignore`**

```
__pycache__/
*.py[cod]
.venv/
.pytest_cache/
*.egg-info/
dist/
build/
.env
```

- [ ] **Step 5: Write `README.md`**

Create `README.md` with the following content (use plain text — no special tooling required):

````markdown
# LIVEWELL API

FastAPI backend for the LIVEWELL decision-support system.

## Setup
```bash
uv sync
```
## Run
```bash
uv run uvicorn main:app --reload --port 8000
```
## Test
```bash
uv run pytest
```
## Endpoints
- `GET /api/signals` — list of contract candidates
- `GET /api/signals/{instrument}/{strike}` — contract detail (`instrument` is hyphen-encoded, e.g. `EUR-USD`)
- `GET /api/dashboard` — dashboard summary
````

- [ ] **Step 6: Install dependencies**

```bash
uv sync
```

Expected output ends with: `Installed N packages` (exact count varies) and no errors.

- [ ] **Step 7: Initialise git and commit**

```bash
git init
git add pyproject.toml .python-version .gitignore README.md
git commit -m "chore: init livewell-api"
```

Expected: `[main (root-commit) xxxxxxx] chore: init livewell-api`

> **Stop here.** Before Task 2, the controller must invoke `superpowers:using-git-worktrees` inside this directory to create a feature branch. All subsequent work happens on that branch.

---

## Task 2: Contract schemas

**Files:**
- Create: `tests/__init__.py`
- Create: `tests/test_schemas_contract.py`
- Create: `schemas/__init__.py`
- Create: `schemas/contract.py`

- [ ] **Step 1: Create test package marker**

Create `tests/__init__.py` as an empty file.

- [ ] **Step 2: Write the failing tests**

Create `tests/test_schemas_contract.py`:

```python
import pytest
from pydantic import ValidationError
from schemas.contract import ContractCard, ContractDetail, Economics, ReasonCode


def test_contract_card_fields():
    card = ContractCard(
        instrument="EUR/USD", strike="1.0850", expiry="10:00 AM", status="Open"
    )
    assert card.instrument == "EUR/USD"
    assert card.strike == "1.0850"


def test_contract_detail_recommendation_literal():
    with pytest.raises(ValidationError):
        ContractDetail(
            instrument="EUR/USD",
            strike="1.0850",
            expiry="10:00 AM",
            status="Open",
            recommendation="Invalid",
            rationale="test",
            economics={"cost": 42, "payout": 100, "breakeven": 0.42},
            modelProbability=0.68,
            edge=0.26,
            confidence="High",
            regime="Bullish",
            noTradeFlag=False,
            reasonCodes=[],
        )
```

- [ ] **Step 3: Run tests — verify they fail**

```bash
uv run pytest tests/test_schemas_contract.py -v
```

Expected: `ModuleNotFoundError: No module named 'schemas'`

- [ ] **Step 4: Create schema package marker**

Create `schemas/__init__.py` as an empty file.

- [ ] **Step 5: Write `schemas/contract.py`**

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

- [ ] **Step 6: Run tests — verify they pass**

```bash
uv run pytest tests/test_schemas_contract.py -v
```

Expected:
```
test_schemas_contract.py::test_contract_card_fields PASSED
test_schemas_contract.py::test_contract_detail_recommendation_literal PASSED
2 passed
```

- [ ] **Step 7: Commit**

```bash
git add schemas/__init__.py schemas/contract.py tests/__init__.py tests/test_schemas_contract.py
git commit -m "feat: add contract Pydantic schemas"
```

---

## Task 3: Dashboard schema

**Files:**
- Create: `tests/test_schemas_dashboard.py`
- Create: `schemas/dashboard.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_schemas_dashboard.py`:

```python
import pytest
from pydantic import ValidationError
from schemas.dashboard import (
    DashboardData,
    MarketSnapshot,
    ModelHealth,
    OpportunitySummary,
    TopCandidate,
)


def test_dashboard_data_fields():
    data = DashboardData(
        markets=[MarketSnapshot(instrument="EUR/USD", regime="Bullish", noTrade=False)],
        opportunities=OpportunitySummary(total=5, passing=2, review=1),
        topCandidates=[
            TopCandidate(
                instrument="EUR/USD",
                strike="1.0875",
                expiry="2026-04-22T14:00:00Z",
                edge="+0.14",
                confidence="High",
            )
        ],
        modelHealth=ModelHealth(
            trainingDate="2026-04-21", dataFreshness="Current", status="Healthy"
        ),
    )
    assert data.opportunities.passing == 2


def test_market_snapshot_regime_literal():
    with pytest.raises(ValidationError):
        MarketSnapshot(instrument="EUR/USD", regime="Invalid", noTrade=False)
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
uv run pytest tests/test_schemas_dashboard.py -v
```

Expected: `ModuleNotFoundError: No module named 'schemas.dashboard'`

- [ ] **Step 3: Write `schemas/dashboard.py`**

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

- [ ] **Step 4: Run tests — verify they pass**

```bash
uv run pytest tests/test_schemas_dashboard.py -v
```

Expected:
```
test_schemas_dashboard.py::test_dashboard_data_fields PASSED
test_schemas_dashboard.py::test_market_snapshot_regime_literal PASSED
2 passed
```

- [ ] **Step 5: Commit**

```bash
git add schemas/dashboard.py tests/test_schemas_dashboard.py
git commit -m "feat: add dashboard Pydantic schemas"
```

---

## Task 4: Signals router + app

**Files:**
- Create: `tests/test_signals.py`
- Create: `main.py`
- Create: `routers/__init__.py`
- Create: `routers/signals.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_signals.py`:

```python
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_get_signals_returns_three_items():
    response = client.get("/api/signals")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3


def test_get_signal_detail_eur_usd():
    response = client.get("/api/signals/EUR-USD/1.0850")
    assert response.status_code == 200
    data = response.json()
    assert data["recommendation"] == "Take"


def test_get_signal_detail_not_found():
    response = client.get("/api/signals/EUR-USD/9.9999")
    assert response.status_code == 404
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
uv run pytest tests/test_signals.py -v
```

Expected: `ModuleNotFoundError: No module named 'main'`

- [ ] **Step 3: Create router package marker**

Create `routers/__init__.py` as an empty file.

- [ ] **Step 4: Write `routers/signals.py`**

```python
from __future__ import annotations
from fastapi import APIRouter, HTTPException
from schemas.contract import ContractCard, ContractDetail, Economics, ReasonCode

router = APIRouter()

_SIGNALS: list[ContractCard] = [
    ContractCard(instrument="EUR/USD", strike="1.0850", expiry="10:00 AM", status="Open"),
    ContractCard(instrument="GBP/USD", strike="1.2650", expiry="11:00 AM", status="Open"),
    ContractCard(instrument="USD/JPY", strike="150.00", expiry="09:30 AM", status="Review"),
]

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


@router.get("/signals", response_model=list[ContractCard])
def get_signals() -> list[ContractCard]:
    return _SIGNALS


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

- [ ] **Step 5: Write `main.py`**

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

> Note: `routers.dashboard` doesn't exist yet. The import will fail until Task 5 creates it. For now, comment out the dashboard lines temporarily so the signals tests can run:

Temporary `main.py` for this task only:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import signals

app = FastAPI(title="LIVEWELL API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:4173"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(signals.router, prefix="/api")
```

- [ ] **Step 6: Run tests — verify they pass**

```bash
uv run pytest tests/test_signals.py -v
```

Expected:
```
test_signals.py::test_get_signals_returns_three_items PASSED
test_signals.py::test_get_signal_detail_eur_usd PASSED
test_signals.py::test_get_signal_detail_not_found PASSED
3 passed
```

- [ ] **Step 7: Commit**

```bash
git add main.py routers/__init__.py routers/signals.py tests/test_signals.py
git commit -m "feat: add signals router and FastAPI app"
```

---

## Task 5: Dashboard router

**Files:**
- Create: `tests/test_dashboard.py`
- Create: `routers/dashboard.py`
- Modify: `main.py` (restore dashboard import)

- [ ] **Step 1: Write the failing test**

Create `tests/test_dashboard.py`:

```python
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_get_dashboard_returns_opportunities():
    response = client.get("/api/dashboard")
    assert response.status_code == 200
    data = response.json()
    assert data["opportunities"]["passing"] == 2
```

- [ ] **Step 2: Run test — verify it fails**

```bash
uv run pytest tests/test_dashboard.py -v
```

Expected: `assert response.status_code == 200` fails (404 — route not yet defined, or ImportError from missing `routers.dashboard`).

- [ ] **Step 3: Write `routers/dashboard.py`**

```python
from __future__ import annotations
from fastapi import APIRouter
from schemas.dashboard import (
    DashboardData,
    MarketSnapshot,
    ModelHealth,
    OpportunitySummary,
    TopCandidate,
)

router = APIRouter()

_DASHBOARD = DashboardData(
    markets=[
        MarketSnapshot(instrument="EUR/USD", regime="Bullish", noTrade=False),
        MarketSnapshot(instrument="GBP/USD", regime="Neutral", noTrade=True),
        MarketSnapshot(instrument="USD/JPY", regime="Bearish", noTrade=False),
    ],
    opportunities=OpportunitySummary(total=5, passing=2, review=1),
    topCandidates=[
        TopCandidate(
            instrument="EUR/USD",
            strike="1.0875",
            expiry="2026-04-22T14:00:00Z",
            edge="+0.14",
            confidence="High",
        ),
        TopCandidate(
            instrument="USD/JPY",
            strike="154.50",
            expiry="2026-04-22T16:00:00Z",
            edge="+0.09",
            confidence="Medium",
        ),
    ],
    modelHealth=ModelHealth(
        trainingDate="2026-04-21", dataFreshness="Current", status="Healthy"
    ),
)


@router.get("/dashboard", response_model=DashboardData)
def get_dashboard() -> DashboardData:
    return _DASHBOARD
```

- [ ] **Step 4: Restore the full `main.py`**

Replace `main.py` with the complete version that includes both routers:

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

- [ ] **Step 5: Run all tests — verify they pass**

```bash
uv run pytest -v
```

Expected:
```
test_schemas_contract.py::test_contract_card_fields PASSED
test_schemas_contract.py::test_contract_detail_recommendation_literal PASSED
test_schemas_dashboard.py::test_dashboard_data_fields PASSED
test_schemas_dashboard.py::test_market_snapshot_regime_literal PASSED
test_signals.py::test_get_signals_returns_three_items PASSED
test_signals.py::test_get_signal_detail_eur_usd PASSED
test_signals.py::test_get_signal_detail_not_found PASSED
test_dashboard.py::test_get_dashboard_returns_opportunities PASSED
8 passed
```

- [ ] **Step 6: Verify routes with curl**

In a separate terminal, start the server:

```bash
uv run uvicorn main:app --port 8000
```

In the original terminal:

```bash
curl -s http://localhost:8000/api/signals | python3 -m json.tool
```

Expected: JSON array with 3 objects, each with `instrument`, `strike`, `expiry`, `status`.

```bash
curl -s http://localhost:8000/api/signals/EUR-USD/1.0850 | python3 -m json.tool
```

Expected: JSON object with `"recommendation": "Take"`, `"economics": {"cost": 42.0, ...}`.

```bash
curl -s http://localhost:8000/api/dashboard | python3 -m json.tool
```

Expected: JSON object with `"opportunities": {"total": 5, "passing": 2, "review": 1}`.

Stop the server with `Ctrl+C`.

- [ ] **Step 7: Commit**

```bash
git add routers/dashboard.py main.py tests/test_dashboard.py
git commit -m "feat: add dashboard router; complete all routes"
```

---

## Task 6: Domain module stubs

**Files:**
- Create: `livewell/__init__.py` + 10 sub-module `__init__.py` files

> No TDD cycle for this task — these are empty stubs with one-line docstrings. The test is that `python -c "import livewell.decision"` exits 0.

- [ ] **Step 1: Create `livewell/__init__.py`**

```python
"""LIVEWELL decision engine — domain modules."""
```

- [ ] **Step 2: Create all 10 sub-module stubs**

Create each of the following files with exactly the content shown:

`livewell/data/__init__.py`:
```python
"""Loaders, adapters, and normalization for market data."""
```

`livewell/features/__init__.py`:
```python
"""Technical indicators, regime features, and transforms."""
```

`livewell/labels/__init__.py`:
```python
"""Target definitions and label generation for NADEX contracts."""
```

`livewell/models/__init__.py`:
```python
"""Model training, inference, calibration, and artifact loading."""
```

`livewell/decision/__init__.py`:
```python
"""Edge computation, rule overlays, and take/watch/pass classification."""
```

`livewell/backtest/__init__.py`:
```python
"""Historical replay engine, metrics, equity curves, and trade logs."""
```

`livewell/explanations/__init__.py`:
```python
"""Reason codes and explanation builders for contract candidates."""
```

`livewell/tracking/__init__.py`:
```python
"""Signal persistence, outcome tracking, and monitoring."""
```

`livewell/api/__init__.py`:
```python
"""FastAPI routes and schemas — long-term home for the API layer."""
```

`livewell/jobs/__init__.py`:
```python
"""Scheduled refresh, scoring, retraining, and archival workflows."""
```

- [ ] **Step 3: Verify imports resolve**

```bash
uv run python -c "import livewell.decision; import livewell.backtest; import livewell.tracking; print('ok')"
```

Expected: `ok`

- [ ] **Step 4: Run full test suite — confirm nothing broke**

```bash
uv run pytest -v
```

Expected: `8 passed`

- [ ] **Step 5: Commit**

```bash
git add livewell/
git commit -m "feat: add livewell domain module stubs"
```

---

## Definition of Done Checklist

After all tasks complete, verify:

- [ ] `livewell-api/` exists at `/Users/i802235/Library/CloudStorage/OneDrive-SAPSE/Development/livewell-api/`
- [ ] `uv run uvicorn main:app --port 8000` starts without errors
- [ ] `uv run pytest` → 8 passed, 0 failed
- [ ] All 3 curl routes return correct JSON
- [ ] `livewell/` has 11 `__init__.py` files (root + 10 sub-modules), each with a docstring
- [ ] CORS origins include `http://localhost:5173`
- [ ] `git log --oneline` shows at least 5 commits on the feature branch

# Phase 1D — Frontend/Backend Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire the React frontend off MSW and onto the real FastAPI backend for dev, add 3 missing backend routes with hardcoded stub data, and verify end-to-end data flow.

**Architecture:** The Vite dev server proxies `/api/*` to `localhost:8000`, so all hooks keep calling `fetch('/api/...')` unchanged. MSW is guarded behind `VITE_USE_MOCKS=true` so it stays available for frontend tests (which are untouched) and for working without a backend. Three new FastAPI routers with hardcoded stub data mirror the existing MSW mocks exactly.

**Tech Stack:** React 19, Vite 6, MSW v2, FastAPI 0.111+, Pydantic v2, pytest, httpx `TestClient`.

---

## File Map

**Modified:**
- `apps/web/vite.config.ts` — add `server.proxy` forwarding `/api` to `localhost:8000`
- `apps/web/src/main.tsx` — change MSW guard to `VITE_USE_MOCKS === 'true'`
- `apps/api/main.py` — include 3 new routers; expand CORS origins

**Created:**
- `apps/web/.env.local` — `VITE_USE_MOCKS=false` (gitignored, documents the flag)
- `apps/api/schemas/backtest.py` — `BacktestRow`, `BacktestSummary` Pydantic models
- `apps/api/schemas/model_health.py` — `FeatureStatus`, `DriftWarning`, `ModelHealth` Pydantic models
- `apps/api/schemas/tracker.py` — `TrackedSignal` Pydantic model
- `apps/api/routers/backtest.py` — `GET /api/backtest/summary`
- `apps/api/routers/model_health.py` — `GET /api/model/health`
- `apps/api/routers/tracker.py` — `GET /api/signals/tracker`
- `apps/api/tests/test_backtest.py`
- `apps/api/tests/test_model_health.py`
- `apps/api/tests/test_tracker.py`

---

## Task 1: Vite proxy + MSW env flag

**Files:**
- Modify: `apps/web/vite.config.ts`
- Modify: `apps/web/src/main.tsx`
- Create: `apps/web/.env.local`

- [ ] **Step 1: Read the current vite.config.ts**

```bash
cat apps/web/vite.config.ts
```

Note the existing structure — you will add a `server` key alongside whatever is already there.

- [ ] **Step 2: Add the proxy to vite.config.ts**

Add `server.proxy` so that all `/api/*` requests in the Vite dev server are forwarded to the FastAPI process. The full updated file should look like this (preserve any existing `plugins`, `test`, or `build` keys — only add the `server` block):

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
    coverage: {
      provider: 'v8',
      exclude: ['src/components/theme-provider.tsx'],
      thresholds: { lines: 80 },
    },
  },
})
```

- [ ] **Step 3: Update the MSW guard in main.tsx**

Change line:
```typescript
  if (import.meta.env.DEV) {
```
to:
```typescript
  if (import.meta.env.VITE_USE_MOCKS === 'true') {
```

The full updated `src/main.tsx`:

```typescript
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { ThemeProvider } from "./components/theme-provider";
import "./index.css";
import App from "./App";

async function prepare() {
  if (import.meta.env.VITE_USE_MOCKS === 'true') {
    const { worker } = await import("./mocks/browser");
    return worker.start({ onUnhandledRequest: "bypass" });
  }
}

prepare()
  .then(() => {
    createRoot(document.getElementById("root")!).render(
      <StrictMode>
        <BrowserRouter>
          <ThemeProvider>
            <App />
          </ThemeProvider>
        </BrowserRouter>
      </StrictMode>,
    );
  })
  .catch(console.error);
```

- [ ] **Step 4: Create .env.local**

Create `apps/web/.env.local` with:

```
VITE_USE_MOCKS=false
```

This file is already gitignored (covered by `*.local` in the root `.gitignore`). It documents the flag and keeps MSW off by default.

- [ ] **Step 5: Verify frontend tests still pass**

```bash
cd apps/web && npm run test:coverage
```

Expected: 65 tests pass, coverage ≥ 80%. The `VITE_USE_MOCKS` flag is browser-side only; Vitest uses the Node MSW server directly and is unaffected.

- [ ] **Step 6: Commit**

```bash
git add apps/web/vite.config.ts apps/web/src/main.tsx apps/web/.env.local
git commit -m "feat: proxy /api to localhost:8000; gate MSW behind VITE_USE_MOCKS"
```

---

## Task 2: Backtest schemas + router + test

**Files:**
- Create: `apps/api/schemas/backtest.py`
- Create: `apps/api/routers/backtest.py`
- Create: `apps/api/tests/test_backtest.py`

- [ ] **Step 1: Write the failing test**

```python
# apps/api/tests/test_backtest.py
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_backtest_summary_returns_200():
    response = client.get("/api/backtest/summary")
    assert response.status_code == 200


def test_backtest_summary_shape():
    response = client.get("/api/backtest/summary")
    data = response.json()
    assert data["totalTrades"] == 84
    assert len(data["rows"]) == 6
    assert len(data["equityCurve"]) == 30
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd apps/api && uv run pytest tests/test_backtest.py -v
```

Expected: FAIL — 404 Not Found (route doesn't exist yet).

- [ ] **Step 3: Create the schema**

```python
# apps/api/schemas/backtest.py
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel


class BacktestRow(BaseModel):
    market: str
    regime: str
    expiryWindow: str
    trades: int
    winRate: float
    avgEdge: float
    netReturn: float


class EquityCurvePoint(BaseModel):
    date: str
    value: float


class BacktestSummary(BaseModel):
    totalTrades: int
    winRate: float
    avgEdge: float
    maxDrawdown: float
    equityCurve: list[EquityCurvePoint]
    rows: list[BacktestRow]
```

- [ ] **Step 4: Create the router**

```python
# apps/api/routers/backtest.py
from __future__ import annotations
from fastapi import APIRouter
from schemas.backtest import BacktestRow, BacktestSummary, EquityCurvePoint

router = APIRouter()

_SUMMARY = BacktestSummary(
    totalTrades=84,
    winRate=0.61,
    avgEdge=0.14,
    maxDrawdown=-0.09,
    equityCurve=[
        EquityCurvePoint(date="2026-03-01", value=1000),
        EquityCurvePoint(date="2026-03-03", value=1018),
        EquityCurvePoint(date="2026-03-05", value=1009),
        EquityCurvePoint(date="2026-03-07", value=1031),
        EquityCurvePoint(date="2026-03-10", value=1024),
        EquityCurvePoint(date="2026-03-12", value=1047),
        EquityCurvePoint(date="2026-03-14", value=1039),
        EquityCurvePoint(date="2026-03-17", value=1062),
        EquityCurvePoint(date="2026-03-19", value=1055),
        EquityCurvePoint(date="2026-03-21", value=1078),
        EquityCurvePoint(date="2026-03-24", value=1070),
        EquityCurvePoint(date="2026-03-26", value=1093),
        EquityCurvePoint(date="2026-03-28", value=1085),
        EquityCurvePoint(date="2026-03-31", value=1108),
        EquityCurvePoint(date="2026-04-02", value=1099),
        EquityCurvePoint(date="2026-04-04", value=1122),
        EquityCurvePoint(date="2026-04-07", value=1113),
        EquityCurvePoint(date="2026-04-09", value=1136),
        EquityCurvePoint(date="2026-04-11", value=1128),
        EquityCurvePoint(date="2026-04-14", value=1151),
        EquityCurvePoint(date="2026-04-16", value=1143),
        EquityCurvePoint(date="2026-04-18", value=1134),
        EquityCurvePoint(date="2026-04-19", value=1157),
        EquityCurvePoint(date="2026-04-20", value=1149),
        EquityCurvePoint(date="2026-04-21", value=1172),
        EquityCurvePoint(date="2026-04-22", value=1163),
        EquityCurvePoint(date="2026-04-23", value=1186),
        EquityCurvePoint(date="2026-04-24", value=1177),
        EquityCurvePoint(date="2026-04-25", value=1200),
        EquityCurvePoint(date="2026-04-26", value=1191),
    ],
    rows=[
        BacktestRow(market="EUR/USD", regime="Bullish", expiryWindow="2-hour", trades=18, winRate=0.67, avgEdge=0.18, netReturn=0.21),
        BacktestRow(market="EUR/USD", regime="Bearish", expiryWindow="2-hour", trades=12, winRate=0.58, avgEdge=0.11, netReturn=0.09),
        BacktestRow(market="GBP/USD", regime="Bullish", expiryWindow="Daily",  trades=15, winRate=0.60, avgEdge=0.14, netReturn=0.12),
        BacktestRow(market="GBP/USD", regime="Bearish", expiryWindow="Daily",  trades=11, winRate=0.55, avgEdge=0.09, netReturn=0.06),
        BacktestRow(market="USD/JPY", regime="Bullish", expiryWindow="2-hour", trades=16, winRate=0.63, avgEdge=0.15, netReturn=0.14),
        BacktestRow(market="USD/JPY", regime="Bearish", expiryWindow="Daily",  trades=12, winRate=0.50, avgEdge=0.08, netReturn=0.02),
    ],
)


@router.get("/backtest/summary", response_model=BacktestSummary)
def get_backtest_summary() -> BacktestSummary:
    return _SUMMARY
```

- [ ] **Step 5: Register the router in main.py**

Add to `apps/api/main.py`:

```python
from routers import signals, dashboard, backtest

# in the app setup block, after existing include_router calls:
app.include_router(backtest.router, prefix="/api")
```

Also expand the CORS origins at this point:

```python
allow_origins=[
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:5175",
    "http://localhost:4173",
],
```

The full updated `main.py`:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import signals, dashboard, backtest

app = FastAPI(title="LIVEWELL API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://localhost:4173",
    ],
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(signals.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(backtest.router, prefix="/api")
```

- [ ] **Step 6: Run test to verify it passes**

```bash
cd apps/api && uv run pytest tests/test_backtest.py -v
```

Expected: 2 tests pass.

- [ ] **Step 7: Run full backend test suite**

```bash
cd apps/api && uv run pytest -v
```

Expected: all existing tests still pass (no regressions from the CORS change or router addition).

- [ ] **Step 8: Commit**

```bash
git add apps/api/schemas/backtest.py apps/api/routers/backtest.py apps/api/tests/test_backtest.py apps/api/main.py
git commit -m "feat: add backtest summary endpoint with stub data"
```

---

## Task 3: Model Health schemas + router + test

**Files:**
- Create: `apps/api/schemas/model_health.py`
- Create: `apps/api/routers/model_health.py`
- Create: `apps/api/tests/test_model_health.py`
- Modify: `apps/api/main.py`

- [ ] **Step 1: Write the failing test**

```python
# apps/api/tests/test_model_health.py
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_model_health_returns_200():
    response = client.get("/api/model/health")
    assert response.status_code == 200


def test_model_health_shape():
    response = client.get("/api/model/health")
    data = response.json()
    assert data["overallStatus"] == "Warning"
    assert len(data["features"]) == 8
    assert len(data["driftWarnings"]) == 1
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd apps/api && uv run pytest tests/test_model_health.py -v
```

Expected: FAIL — 404 Not Found.

- [ ] **Step 3: Create the schema**

```python
# apps/api/schemas/model_health.py
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel


class FeatureStatus(BaseModel):
    name: str
    status: Literal['Available', 'Stale', 'Missing']


class DriftWarning(BaseModel):
    feature: str
    description: str


class ModelHealth(BaseModel):
    overallStatus: Literal['Healthy', 'Warning', 'Degraded']
    trainingDate: str
    dataFreshness: str
    calibrationError: float
    validationAccuracy: float
    features: list[FeatureStatus]
    driftWarnings: list[DriftWarning]
```

- [ ] **Step 4: Create the router**

```python
# apps/api/routers/model_health.py
from __future__ import annotations
from fastapi import APIRouter
from schemas.model_health import DriftWarning, FeatureStatus, ModelHealth

router = APIRouter()

_HEALTH = ModelHealth(
    overallStatus="Warning",
    trainingDate="2026-04-18",
    dataFreshness="5 days ago",
    calibrationError=0.043,
    validationAccuracy=0.64,
    features=[
        FeatureStatus(name="EMA-20",          status="Available"),
        FeatureStatus(name="EMA-50",          status="Available"),
        FeatureStatus(name="RSI-14",          status="Available"),
        FeatureStatus(name="MACD Signal",     status="Available"),
        FeatureStatus(name="ATR-14",          status="Available"),
        FeatureStatus(name="Session Flag",    status="Available"),
        FeatureStatus(name="Volatility Reg",  status="Stale"),
        FeatureStatus(name="Event Risk Flag", status="Missing"),
    ],
    driftWarnings=[
        DriftWarning(
            feature="Volatility Reg",
            description="Last computed 6 days ago — refresh recommended before next scoring run.",
        ),
    ],
)


@router.get("/model/health", response_model=ModelHealth)
def get_model_health() -> ModelHealth:
    return _HEALTH
```

- [ ] **Step 5: Register the router in main.py**

```python
from routers import signals, dashboard, backtest, model_health

app.include_router(model_health.router, prefix="/api")
```

Full updated `main.py`:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import signals, dashboard, backtest, model_health

app = FastAPI(title="LIVEWELL API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://localhost:4173",
    ],
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(signals.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(backtest.router, prefix="/api")
app.include_router(model_health.router, prefix="/api")
```

- [ ] **Step 6: Run test to verify it passes**

```bash
cd apps/api && uv run pytest tests/test_model_health.py -v
```

Expected: 2 tests pass.

- [ ] **Step 7: Run full backend test suite**

```bash
cd apps/api && uv run pytest -v
```

Expected: all tests pass.

- [ ] **Step 8: Commit**

```bash
git add apps/api/schemas/model_health.py apps/api/routers/model_health.py apps/api/tests/test_model_health.py apps/api/main.py
git commit -m "feat: add model health endpoint with stub data"
```

---

## Task 4: Signal Tracker schemas + router + test

**Files:**
- Create: `apps/api/schemas/tracker.py`
- Create: `apps/api/routers/tracker.py`
- Create: `apps/api/tests/test_tracker.py`
- Modify: `apps/api/main.py`

- [ ] **Step 1: Write the failing test**

```python
# apps/api/tests/test_tracker.py
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_tracker_returns_200():
    response = client.get("/api/signals/tracker")
    assert response.status_code == 200


def test_tracker_shape():
    response = client.get("/api/signals/tracker")
    data = response.json()
    assert len(data) == 15
    first = data[0]
    assert "date" in first
    assert "market" in first
    assert "recommendation" in first
    assert "outcome" in first
    assert "edge" in first
    assert "modelProbability" in first
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd apps/api && uv run pytest tests/test_tracker.py -v
```

Expected: FAIL — 404 Not Found.

- [ ] **Step 3: Create the schema**

```python
# apps/api/schemas/tracker.py
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel


class TrackedSignal(BaseModel):
    date: str
    market: str
    strike: str
    expiry: str
    recommendation: Literal['Take', 'Watch', 'Pass']
    actionTaken: Literal['Taken', 'Skipped'] | None
    outcome: Literal['Win', 'Loss', 'Pending']
    edge: float
    modelProbability: float
```

- [ ] **Step 4: Create the router**

```python
# apps/api/routers/tracker.py
from __future__ import annotations
from fastapi import APIRouter
from schemas.tracker import TrackedSignal

router = APIRouter()

_SIGNALS: list[TrackedSignal] = [
    TrackedSignal(date="2026-04-23", market="EUR/USD", strike="1.0880", expiry="14:00", recommendation="Take",  actionTaken="Taken",   outcome="Pending", edge=0.18,  modelProbability=0.70),
    TrackedSignal(date="2026-04-22", market="GBP/USD", strike="1.2680", expiry="11:00", recommendation="Watch", actionTaken="Skipped", outcome="Win",     edge=0.11,  modelProbability=0.58),
    TrackedSignal(date="2026-04-22", market="USD/JPY", strike="154.50", expiry="16:00", recommendation="Pass",  actionTaken=None,      outcome="Loss",    edge=-0.04, modelProbability=0.44),
    TrackedSignal(date="2026-04-21", market="EUR/USD", strike="1.0860", expiry="12:00", recommendation="Take",  actionTaken="Taken",   outcome="Win",     edge=0.22,  modelProbability=0.72),
    TrackedSignal(date="2026-04-21", market="GBP/USD", strike="1.2650", expiry="14:00", recommendation="Take",  actionTaken="Taken",   outcome="Loss",    edge=0.15,  modelProbability=0.65),
    TrackedSignal(date="2026-04-19", market="USD/JPY", strike="154.00", expiry="10:00", recommendation="Watch", actionTaken="Skipped", outcome="Win",     edge=0.09,  modelProbability=0.55),
    TrackedSignal(date="2026-04-18", market="EUR/USD", strike="1.0840", expiry="11:00", recommendation="Take",  actionTaken="Taken",   outcome="Win",     edge=0.20,  modelProbability=0.69),
    TrackedSignal(date="2026-04-18", market="GBP/USD", strike="1.2700", expiry="16:00", recommendation="Pass",  actionTaken=None,      outcome="Win",     edge=-0.02, modelProbability=0.45),
    TrackedSignal(date="2026-04-17", market="EUR/USD", strike="1.0870", expiry="14:00", recommendation="Take",  actionTaken="Taken",   outcome="Loss",    edge=0.13,  modelProbability=0.61),
    TrackedSignal(date="2026-04-16", market="USD/JPY", strike="153.50", expiry="12:00", recommendation="Watch", actionTaken="Taken",   outcome="Win",     edge=0.10,  modelProbability=0.57),
    TrackedSignal(date="2026-04-15", market="EUR/USD", strike="1.0855", expiry="10:00", recommendation="Take",  actionTaken="Taken",   outcome="Win",     edge=0.19,  modelProbability=0.68),
    TrackedSignal(date="2026-04-14", market="GBP/USD", strike="1.2660", expiry="11:00", recommendation="Pass",  actionTaken=None,      outcome="Loss",    edge=-0.06, modelProbability=0.42),
    TrackedSignal(date="2026-04-12", market="USD/JPY", strike="153.00", expiry="14:00", recommendation="Take",  actionTaken="Skipped", outcome="Win",     edge=0.16,  modelProbability=0.64),
    TrackedSignal(date="2026-04-11", market="EUR/USD", strike="1.0830", expiry="16:00", recommendation="Watch", actionTaken="Skipped", outcome="Loss",    edge=0.07,  modelProbability=0.53),
    TrackedSignal(date="2026-04-10", market="GBP/USD", strike="1.2640", expiry="12:00", recommendation="Take",  actionTaken="Taken",   outcome="Win",     edge=0.21,  modelProbability=0.71),
]


@router.get("/signals/tracker", response_model=list[TrackedSignal])
def get_signal_tracker() -> list[TrackedSignal]:
    return _SIGNALS
```

- [ ] **Step 5: Register the router in main.py**

```python
from routers import signals, dashboard, backtest, model_health, tracker

app.include_router(tracker.router, prefix="/api")
```

Full updated `main.py`:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import signals, dashboard, backtest, model_health, tracker

app = FastAPI(title="LIVEWELL API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://localhost:4173",
    ],
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(signals.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(backtest.router, prefix="/api")
app.include_router(model_health.router, prefix="/api")
app.include_router(tracker.router, prefix="/api")
```

**Important:** The tracker route `GET /api/signals/tracker` must be registered BEFORE the parameterised `GET /api/signals/{instrument}/{strike}` route to avoid the parameter matching `tracker` as an instrument name. In `main.py`, `tracker.router` is included after `signals.router` — this is fine because FastAPI resolves routes by specificity (static segments beat path parameters), not by declaration order. No reordering needed.

- [ ] **Step 6: Run test to verify it passes**

```bash
cd apps/api && uv run pytest tests/test_tracker.py -v
```

Expected: 2 tests pass.

- [ ] **Step 7: Run full backend test suite**

```bash
cd apps/api && uv run pytest -v
```

Expected: all 11 tests pass (8 existing + 2 backtest + 2 model_health + 2 tracker = wait, previously 8 existing + 2 from Task 2 + 2 from Task 3 + 2 from this task = 14 total).

- [ ] **Step 8: Commit**

```bash
git add apps/api/schemas/tracker.py apps/api/routers/tracker.py apps/api/tests/test_tracker.py apps/api/main.py
git commit -m "feat: add signal tracker endpoint with stub data"
```

---

## Task 5: End-to-end smoke test + update current_step_plan

**Files:**
- Modify: `apps/web/current_step_plan.md`

- [ ] **Step 1: Start the FastAPI backend**

```bash
cd apps/api && uv run uvicorn main:app --reload
```

Expected output: `Uvicorn running on http://127.0.0.1:8000`

- [ ] **Step 2: Start the Vite dev server (new terminal)**

```bash
cd apps/web && npm run dev
```

Expected output: `VITE ready in ... ms` with a localhost URL (5173 or 5174).

- [ ] **Step 3: Verify each new endpoint via curl**

```bash
curl -s http://localhost:8000/api/backtest/summary | python3 -c "import sys,json; d=json.load(sys.stdin); print('totalTrades:', d['totalTrades'], '| rows:', len(d['rows']), '| curve:', len(d['equityCurve']))"
```
Expected: `totalTrades: 84 | rows: 6 | curve: 30`

```bash
curl -s http://localhost:8000/api/model/health | python3 -c "import sys,json; d=json.load(sys.stdin); print('status:', d['overallStatus'], '| features:', len(d['features']), '| warnings:', len(d['driftWarnings']))"
```
Expected: `status: Warning | features: 8 | warnings: 1`

```bash
curl -s http://localhost:8000/api/signals/tracker | python3 -c "import sys,json; d=json.load(sys.stdin); print('signals:', len(d))"
```
Expected: `signals: 15`

- [ ] **Step 4: Open the browser and verify the 5 data-fetching pages**

Navigate to the Vite dev URL (e.g. `http://localhost:5174`). Open browser DevTools → Network tab. Visit each page and confirm requests go to `localhost:8000` (not intercepted by MSW):

- `/backtest` — summary strip shows 84 trades, table shows 6 rows, equity curve visible
- `/model-health` — Warning banner, 8 feature rows, 1 drift warning
- `/tracker` — 15 signal rows
- `/signals` — 3 contract cards
- `/` (Dashboard) — market conditions + top candidates

- [ ] **Step 5: Update current_step_plan.md**

Replace the contents of `apps/web/current_step_plan.md` with:

```markdown
# Current Step: Phase 2 — Real Data Pipeline

**Phase 1D status:** Complete
- Vite proxy: `/api/*` forwarded to `localhost:8000`
- MSW gated behind `VITE_USE_MOCKS=true` (off by default in dev; on for tests)
- 3 new FastAPI routes with hardcoded stubs: `/api/backtest/summary`, `/api/model/health`, `/api/signals/tracker`
- CORS expanded to cover ports 5173–5175 + 4173
- 65 frontend tests passing (unchanged), 14 backend tests passing

---

## Next: Phase 2 — Real Data Pipeline

Per `docs/06_roadmap.md` Phase 1 → Phase 2:

- Forex data ingestion (price history → S3 Parquet)
- Feature generation: EMA, MACD, RSI, ATR
- Session and macro-event filters
- Strike feasibility and expected value logic
- Recommendation schema and DynamoDB storage
- Initial backtest framework
- Replace hardcoded backend stubs with real computed data
```

- [ ] **Step 6: Commit**

```bash
git add apps/web/current_step_plan.md
git commit -m "chore: update current_step_plan to Phase 2"
```

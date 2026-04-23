# Design: Phase 1D — Frontend/Backend Integration

**Date:** 2026-04-23
**Status:** Approved
**Scope:** Wire the React frontend off MSW and onto the real FastAPI backend for dev, while keeping MSW intact for tests. Add 3 missing backend routes with hardcoded stub data. Expand CORS to cover common Vite dev ports.

---

## Context

Phase 1C delivered 5 deferred pages against MSW mock data. The FastAPI backend (`apps/api/`) has 3 routes implemented (`GET /api/signals`, `GET /api/signals/{instrument}/{strike}`, `GET /api/dashboard`) with hardcoded stub data. Three new routes added in Phase 1C exist only in MSW:

- `GET /api/backtest/summary`
- `GET /api/model/health`
- `GET /api/signals/tracker`

This phase wires everything together so the dev browser hits the real FastAPI process, while the 65 existing frontend tests continue to run against MSW unchanged.

---

## Approach

**Option A — Vite proxy + MSW env flag (chosen)**

- Add a Vite `server.proxy` so `/api/*` requests in dev are forwarded to `http://localhost:8000`. All hooks keep calling `fetch('/api/...')` unchanged.
- Guard MSW behind `VITE_USE_MOCKS=true` so it is off by default in dev but can be re-enabled locally when working without a running backend.
- Add 3 new FastAPI routers with hardcoded stub data matching the current MSW mocks exactly.
- Expand CORS to cover ports 5173, 5174, 5175, and 4173.

---

## Architecture

### Files changed

**`apps/web/` — frontend**

| File | Change |
|---|---|
| `vite.config.ts` | Add `server.proxy`: `/api` → `http://localhost:8000` |
| `src/main.tsx` | Change MSW guard from `import.meta.env.DEV` to `import.meta.env.VITE_USE_MOCKS === 'true'` |
| `.env.local` (gitignored) | `VITE_USE_MOCKS=false` — documents the flag, not committed |

**`apps/api/` — backend**

| File | Change |
|---|---|
| `main.py` | Include 3 new routers; expand CORS origins to ports 5173–5175 + 4173 |
| `schemas/backtest.py` | `BacktestRow`, `BacktestSummary` Pydantic v2 models |
| `schemas/model_health.py` | `FeatureStatus`, `DriftWarning`, `ModelHealth` Pydantic v2 models |
| `schemas/tracker.py` | `TrackedSignal` Pydantic v2 model |
| `routers/backtest.py` | `GET /api/backtest/summary` — hardcoded stub |
| `routers/model_health.py` | `GET /api/model/health` — hardcoded stub |
| `routers/tracker.py` | `GET /api/signals/tracker` — hardcoded stub |
| `tests/test_backtest.py` | 200 + shape assertions |
| `tests/test_model_health.py` | 200 + shape assertions |
| `tests/test_tracker.py` | 200 + shape assertions |

---

## Detailed Design

### Vite proxy (`vite.config.ts`)

```ts
server: {
  proxy: {
    '/api': {
      target: 'http://localhost:8000',
      changeOrigin: true,
    },
  },
},
```

This forwards every `/api/*` request from the Vite dev server to the FastAPI process. No hook or page code changes.

### MSW guard (`src/main.tsx`)

```ts
// Before
if (import.meta.env.DEV) {

// After
if (import.meta.env.VITE_USE_MOCKS === 'true') {
```

MSW is now off by default in dev. Set `VITE_USE_MOCKS=true` in `.env.local` to re-enable (useful when running frontend without a backend).

### CORS (`apps/api/main.py`)

```python
allow_origins=[
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:5175",
    "http://localhost:4173",
],
```

### New Pydantic schemas

**`schemas/backtest.py`**
```python
class BacktestRow(BaseModel):
    market: str
    regime: str
    expiryWindow: str
    trades: int
    winRate: float
    avgEdge: float
    netReturn: float

class BacktestSummary(BaseModel):
    totalTrades: int
    winRate: float
    avgEdge: float
    maxDrawdown: float
    equityCurve: list[dict[str, str | float]]
    rows: list[BacktestRow]
```

**`schemas/model_health.py`**
```python
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

**`schemas/tracker.py`**
```python
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

### New router stubs

Each router returns hardcoded data matching the existing MSW mock values exactly (same numbers, same record count). This ensures the frontend renders identically whether MSW or the real backend is serving data.

- `GET /api/backtest/summary` → `BacktestSummary` (84 total trades, 6 rows, 30-point equity curve)
- `GET /api/model/health` → `ModelHealth` (Warning status, 8 features, 1 drift warning)
- `GET /api/signals/tracker` → `list[TrackedSignal]` (15 records)

### Backend tests (pattern)

```python
# tests/test_backtest.py
@pytest.mark.asyncio
async def test_backtest_summary():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/backtest/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["totalTrades"] == 84
    assert len(data["rows"]) == 6
    assert len(data["equityCurve"]) == 30
```

Same shape for `test_model_health.py` (asserts `overallStatus == "Warning"`, `len(features) == 8`) and `test_tracker.py` (asserts `len(response.json()) == 15`).

---

## Testing

**Frontend (unchanged):** 65 tests continue to run against MSW. The `VITE_USE_MOCKS` flag is a `import.meta.env` browser-side variable; the Node MSW server used in Vitest is completely unaffected.

**Backend:** 8 existing tests + 3 new tests = 11 total. All use `httpx.AsyncClient` against the real FastAPI app.

**Dev smoke test:** Start both servers, open browser, verify all 5 data-fetching pages load data from the real API (Network tab shows requests to `localhost:8000`, no MSW intercept).

---

## Out of Scope

- Real data (DynamoDB, S3, ML models) — Phase 2
- Production deployment / reverse proxy configuration — Phase 4
- Removing hardcoded stub data from the backend — Phase 2
- Contract tests enforcing schema parity between frontend types and Pydantic models — future

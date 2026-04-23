# Current Step: Phase 1C — UI Polish & Remaining Pages

**Phase 1A status:** Complete
- Daily Signals page (useSignals hook, ContractCard, status filter)
- Dashboard page (market conditions, opportunity summary, top candidates, model health)
- Contract Detail page (Layout C — chips + 4-up metric strip + reason codes + rationale)
- Test suite (Vitest + RTL + MSW, 32 tests, 97.87% statement coverage, 80% threshold enforced)
- Sidebar navigation (hamburger-toggled MUI temporary Drawer, replaces top nav)

**Phase 1B status:** Complete
- `livewell-api/` FastAPI backend at `/Users/i802235/Library/CloudStorage/OneDrive-SAPSE/Development/livewell-api/`
- Python 3.12, uv, FastAPI 0.111+, Pydantic v2, uvicorn
- Pydantic schemas: `ContractCard`, `ContractDetail`, `DashboardData` (mirror TypeScript types, camelCase)
- Routes: `GET /api/signals`, `GET /api/signals/{instrument}/{strike}`, `GET /api/dashboard`
- CORS configured for `localhost:5173` and `localhost:4173`
- `livewell/` domain module stubs (10 sub-modules with docstrings)
- 8 passing tests (pytest + httpx TestClient)
- Frontend still uses MSW — backend switch is a future phase

---

## Remaining Phase 1A pages (deferred)

These will be built when the UI needs them:
- Backtest Results
- Model Health (expanded)
- How It Works
- Signal Tracker / Outcome Review
- Options Advisor

---

## Next candidates

- Wire the frontend to the real `livewell-api` backend (switch off MSW)
- Build remaining deferred pages
- Phase 2: real data pipeline (DynamoDB, S3, ML models)


**Phase 1A status:** Complete
- Daily Signals page (useSignals hook, ContractCard, status filter)
- Dashboard page (market conditions, opportunity summary, top candidates, model health)
- Contract Detail page (Layout C — chips + 4-up metric strip + reason codes + rationale)
- Test suite (Vitest + RTL + MSW, 28 tests, 97.87% statement coverage, 80% threshold enforced)

---

## Goal

Stand up the backend structure so the UI is not quietly hard-coding assumptions that later fight the real system.

Per the delivery plan:
> Create the enduring system shape — prevent notebook logic from remaining the hidden source of truth — establish where every domain responsibility lives.

This phase produces a **clean backend repository structure** even if some endpoints still return mock data.

---

## What to build

Per the delivery plan:

- Python package structure (`livewell/` with sub-modules)
- FastAPI app shell
- Route and schema stubs matching the front-end data contracts
- Config scaffolding
- Storage conventions (S3 Parquet + DynamoDB)
- Placeholder services and jobs

### Module structure

```
livewell/
  data/          — loaders, adapters, normalization
  features/      — technical indicators, regime features, transforms
  labels/        — target definitions and label generation
  models/        — training, inference, calibration, artifact loading
  decision/      — edge logic, thresholds, rule overlays
  backtest/      — replay engine, metrics, logs, equity curves
  explanations/  — reason codes, explanation builders
  tracking/      — signal persistence, outcome tracking, monitoring
  api/           — FastAPI routes and schemas
  jobs/          — scheduled refresh, scoring, retraining workflows
```

### Endpoints to stub

| Route | Page that needs it |
|---|---|
| `GET /api/signals` | Daily Signals |
| `GET /api/signals/:instrument/:strike` | Contract Detail |
| `GET /api/dashboard` | Dashboard |
| `GET /api/backtest/summary` | Backtest Results |
| `GET /api/model/health` | Model Health |

---

## Open questions to resolve during brainstorming

- Repo location: separate `livewell-api` repo vs a `backend/` directory inside `livewell-ui`
- Python version and tooling: `pyproject.toml` + `uv` vs `requirements.txt` + `venv`
- Stub data strategy: return hardcoded JSON matching current MSW mocks, or define Pydantic schemas first?
- CORS: how does the FastAPI dev server talk to the Vite dev server at localhost:5173?

---

## Definition of Done

- [ ] Python package `livewell/` with sub-module stubs (empty `__init__.py` + one-line docstring per module)
- [ ] FastAPI app shell (`main.py`) with CORS configured for localhost:5173
- [ ] Route stubs returning the same JSON shape as current MSW handlers
- [ ] Pydantic schemas for `ContractCard`, `ContractDetail`, `DashboardData`
- [ ] Config via environment variable (`LIVEWELL_ENV`, `LIVEWELL_PORT`)
- [ ] `README.md` with setup instructions
- [ ] `pyproject.toml` with Python version pin and dependencies
- [ ] At least one integration test: `GET /api/signals` returns 200 with expected schema

---

## Remaining Phase 1A pages (deferred)

These will be built in parallel or after Phase 1B is scaffolded:
- Backtest Results
- Model Health (expanded)
- How It Works
- Signal Tracker / Outcome Review
- Options Advisor

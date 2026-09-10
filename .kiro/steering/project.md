---
inclusion: always
---

# LIVEWELL — Project Steering

## What it is

LIVEWELL is a decision-support system for trading NADEX binary options on forex pairs. It combines technical indicators, probability modeling, and a daily batch pipeline to produce scored, explainable trade recommendations — not automated execution.

Core output format:
```
Pair: EUR/USD  |  Strike: 1.1040  |  Direction: Buy  |  Expiry: End of Day
Model Prob: 0.62  |  Market-Implied: 0.48  |  Edge: +0.14
Reasoning: EMA uptrend, RSI > 50, MACD turning positive, strike within ATR range
```

## Architecture

Five-layer design (see `docs/livewell_design.md`):

1. **Market semantics** — NADEX price = implied probability; edge exists when model diverges (`docs/01_market_model.md`)
2. **Signal generation** — deterministic rules: EMA trend, MACD, RSI, ATR, session/news filters (`docs/02_trading_strategy.md`)
3. **Probability modeling** — logistic regression baseline, random forest benchmark (`docs/03_ml_models.md`)
4. **Pipeline** — AWS batch: ingest → features → signals → inference → DynamoDB (`docs/04_pipeline_architecture.md`)
5. **Evolution** — rules-first, then ML, then agents (`docs/06_roadmap.md`)

**Data stores (settled):**
- DynamoDB — operational records: scored signals, trade outcomes, model runs (`livewell-signals-{env}`, `livewell-outcomes-{env}`, etc.)
- S3 — analytical data: price Parquet files, model artifacts, backtest results (`livewell-data-{env}`)
- RDS/PostgreSQL was considered and rejected; serverless throughout.

## Repository Layout

```
apps/
  api/          FastAPI backend (Python 3.12, uv, Pydantic v2)
  web/          React frontend (Vite, MUI v7, MSW, Vitest)
docs/
  *.md          Architecture: design, market model, strategy, ML, pipeline, roadmap
  livewell_api_contracts.md   Endpoint contracts
  superpowers/
    specs/      Design specs (named YYYY-MM-DD-<feature>-design.md)
    plans/      Implementation plans (named YYYY-MM-DD-<feature>.md)
notebooks/
  livewell-nadex/   Research notebooks and backtesting (not production)
infra/              AWS CDK (TypeScript) — infrastructure as code
packages/           Reserved for livewell-core shared package (empty)
scripts/            Reserved for dev/maintenance scripts (empty)
```

## What Is Implemented

### Frontend (`apps/web`)
- React + MUI v7, Vite, TypeScript
- Pages: Dashboard, DailySignals, ContractDetail, BacktestResults, ModelHealth, SignalTracker, OptionsAdvisor, HowItWorks
- MSW mocking for all API endpoints in dev and tests
- Hooks: `useSignals`, `useDashboard`, `useBacktest`, `useModelHealth`, `useSignalTracker`, `useContractDetail`, `useSignalExplain`
- `SignalExplainPanel` component — a2ui-backed explanation panel
- Theme provider (light/dark), coverage threshold 80%

### API (`apps/api`)
- FastAPI with routers: `/api/signals`, `/api/dashboard`, `/api/backtest`, `/api/model_health`, `/api/tracker`, `/api/explain`
- Lambda-compatible via Mangum (CORS only added outside Lambda)
- Domain packages:
  - `livewell/ingestion/` — yfinance data fetch, S3 Parquet write
  - `livewell/features/` — EMA, MACD, RSI, ATR computation
  - `livewell/signals/` — rule-based signal generation, DynamoDB read/write, response transforms
  - `livewell/models/` — `train.py` (random forest), `train_lr.py` (logistic regression), `inference.py`, `registry.py`
  - `livewell/backtest/` — loader, outcome aggregation
  - `livewell/explain/` — signal explanation builder (Anthropic)
  - `livewell/pipeline/` — `runner.py` (ingest→features→signals→score per instrument), `handler.py` (Lambda fanout), `replay.py` (historical DynamoDB backfill)
  - `livewell/labels/`, `livewell/tracking/`, `livewell/decision/` — stubs

### Infrastructure (`infra`)
- AWS CDK stack defined: S3 bucket, DynamoDB tables (signals, outcomes, model registry), Lambda, SQS, EventBridge, SNS alerting, CloudWatch
- CDK stack is written but not necessarily deployed

### Research (`notebooks/livewell-nadex`)
- Backtest notebook, signal replay notebook, feature generation, label building, LR training notebooks
- Walk-forward validation, calibration analysis

## What Is Not Yet Implemented (Future)

- **Phase 4 AWS production pipeline** — EventBridge scheduled daily run end-to-end in deployed infra
- **Phase 5** — realized outcome tracking, calibration monitoring, feature drift, retraining cadence
- **Phase 6** — sentiment/news integration (headline ingestion, ablation tests)
- **Phase 7** — LSTM / sequence modeling experiments
- **Phase 8** — agentic extension (ingestion agent, explanation agent, monitoring agent)
- `packages/livewell-core` — shared Python package (placeholder only)
- MUI dark/light theme not fully wired to `ThemeProvider` (manual `bgcolor` switches in `App.tsx`)

## Key Conventions

**API:**
- `uv` for dependency management — use `uv add <pkg>`, never pip directly
- Routers use `APIRouter` with `/api` prefix, included in `main.py`
- Schemas are Pydantic v2 in `schemas/`; response models separate from request models
- Tests use `httpx.AsyncClient` against the real app; `moto` for AWS mocking
- Run: `uv run uvicorn main:app --reload` from `apps/api/`

**Web:**
- MUI components imported individually (`import Button from '@mui/material/Button'`)
- Hooks return `{ data, loading, error }`; pages own data fetching; components are presentational
- `ContractCard` type is the core domain type — lives in `src/data/mockData.ts`
- Test: `npm test` (watch) or `npm run test:coverage`

**Worktrees:** `.worktrees/` at monorepo root (git-ignored). Always create worktrees there.

**Workflow:** When using `superpowers:subagent-driven-development`, invoke `superpowers:using-git-worktrees` first.

## Reference Documents

| Document | Purpose |
|---|---|
| `docs/livewell_design.md` | System design overview |
| `docs/01_market_model.md` | NADEX pricing and edge definition |
| `docs/02_trading_strategy.md` | Signal rules and trade logic |
| `docs/03_ml_models.md` | Model comparison and validation design |
| `docs/04_pipeline_architecture.md` | AWS dataflow and execution |
| `docs/05_data_sources.md` | External data providers |
| `docs/06_roadmap.md` | 8-phase delivery roadmap |
| `docs/livewell_api_contracts.md` | API endpoint contracts |
| `docs/livewell_repo_structure.md` | Intended full monorepo layout |
| `docs/superpowers/specs/` | Per-feature design specs |
| `docs/superpowers/plans/` | Per-feature implementation plans |
| `CLAUDE.md` | Cross-cutting project instructions |
| `apps/api/CLAUDE.md` | API-specific conventions |
| `apps/web/CLAUDE.md` | Frontend-specific conventions |

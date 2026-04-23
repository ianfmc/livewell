# Current Step: Phase 2 — Real Data Pipeline

**Phase 1D status:** Complete
- Vite proxy: `/api/*` forwarded to `localhost:8000`
- MSW gated behind `VITE_USE_MOCKS=true` (off by default in dev; on for tests)
- 3 new FastAPI routes with hardcoded stubs: `/api/backtest/summary`, `/api/model/health`, `/api/signals/tracker`
- CORS expanded to cover ports 5173–5175 + 4173
- 65 frontend tests passing (unchanged), 14 backend tests passing

**Phase 1C status:** Complete
- Backtest Results page (useBacktest hook, BacktestResults page, 5 tests)
- Model Health page (useModelHealth hook, ModelHealth page, 6 tests)
- How It Works page (static accordion, 3 tests)
- Signal Tracker page (useSignalTracker hook, SignalTracker page, 5 tests)
- Options Advisor page (3-step wizard with MUI Stepper + Select dropdown, 5 tests)
- All 5 pages wired into App.tsx routing and sidebar navigation
- 65 tests total, 96.26% statement coverage

**Phase 1B status:** Complete
- `apps/api/` FastAPI backend skeleton
- Python 3.12, uv, FastAPI 0.111+, Pydantic v2, uvicorn
- Pydantic schemas: `ContractCard`, `ContractDetail`, `DashboardData` (mirror TypeScript types, camelCase)
- Routes: `GET /api/signals`, `GET /api/signals/{instrument}/{strike}`, `GET /api/dashboard`
- CORS configured for `localhost:5173` and `localhost:4173`
- `livewell/` domain module stubs (10 sub-modules with docstrings)
- 8 passing tests (pytest + httpx TestClient)

**Phase 1A status:** Complete
- Daily Signals page (useSignals hook, ContractCard, status filter)
- Dashboard page (market conditions, opportunity summary, top candidates, model health)
- Contract Detail page (Layout C — chips + 4-up metric strip + reason codes + rationale)
- Test suite (Vitest + RTL + MSW, 80% threshold enforced)
- Sidebar navigation (hamburger-toggled MUI temporary Drawer)

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

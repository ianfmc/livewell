# Current Step: Phase 1D — Frontend/Backend Integration

**Phase 1C status:** Complete
- Backtest Results page (useBacktest hook, BacktestResults page, 5 tests)
- Model Health page (useModelHealth hook, ModelHealth page, 6 tests)
- How It Works page (static accordion, 3 tests)
- Signal Tracker page (useSignalTracker hook, SignalTracker page, 5 tests)
- Options Advisor page (3-step wizard, local state, 5 tests)
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
- Frontend still uses MSW — backend switch is Phase 1D

**Phase 1A status:** Complete
- Daily Signals page (useSignals hook, ContractCard, status filter)
- Dashboard page (market conditions, opportunity summary, top candidates, model health)
- Contract Detail page (Layout C — chips + 4-up metric strip + reason codes + rationale)
- Test suite (Vitest + RTL + MSW, 80% threshold enforced)
- Sidebar navigation (hamburger-toggled MUI temporary Drawer)

---

## Next: Phase 1D — Frontend/Backend Integration

- Switch frontend off MSW; point fetch calls at real FastAPI backend (`localhost:8000`)
- Remove MSW service worker registration from `main.tsx` (or guard behind a flag)
- Verify all existing routes work end-to-end against real FastAPI responses
- Add matching routes/stubs to `apps/api` for the 3 new endpoints:
  - `GET /api/backtest/summary`
  - `GET /api/model/health`
  - `GET /api/signals/tracker`

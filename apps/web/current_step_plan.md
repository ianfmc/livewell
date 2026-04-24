# Current Step: Sub-project 1C — NADEX Strike Feasibility

**Sub-project 1B status:** Complete
- Reads all available OHLCV Parquet years from S3 per instrument+interval
- Computes EMA-20, EMA-50, RSI-14, MACD (line/signal/hist), ATR-14 via pandas-ta
- Writes feature tables to `features/{INSTRUMENT}/{INTERVAL}/{YEAR}.parquet`
- Idempotent re-runs; per-instrument error isolation
- Triggered automatically by `run_ingestion()` at end of each price update
- 12 tests: constants, known-value indicator tests, S3 write, schema, error isolation

**Sub-project 1A status:** Complete
- yfinance ingestion for 5 instruments: EUR/USD, GBP/USD, USD/JPY, Gold, US 500
- Daily (1d) and hourly (1h) OHLCV stored as Parquet in S3
- Per-instrument error isolation; idempotent re-runs
- Backfill mode fetches 2-year history; incremental mode fetches last 7d (1d) / 30d (1h)
- CLI: `uv run python -m livewell.ingestion.cli [--instruments ...] [--backfill]`
- Lambda-ready: `run_ingestion()` callable from thin handler, config via env vars

**Phase 1D status:** Complete
- Vite proxy: `/api/*` forwarded to `localhost:8000`
- MSW gated behind `VITE_USE_MOCKS=true` (off by default in dev; on for tests)
- 3 new FastAPI routes with hardcoded stubs
- CORS expanded to cover ports 5173–5175 + 4173
- 65 frontend tests passing, 14 backend tests passing

---

## Next: Sub-project 1C — NADEX Strike Feasibility

- Derive NADEX contract outcomes from underlying close prices
- Compute strike feasibility scores per instrument
- Filter signals by feasibility before presenting to trader

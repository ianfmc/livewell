# Current Step: Sub-project 1B — Feature Generation

**Sub-project 1A status:** Complete
- yfinance ingestion for 5 instruments: EUR/USD, GBP/USD, USD/JPY, Gold, US 500
- Daily (1d) and hourly (1h) OHLCV stored as Parquet in S3
- Per-instrument error isolation; idempotent re-runs
- Backfill mode fetches 2-year history; incremental mode fetches last 7d (1d) / 30d (1h)
- CLI: `uv run python -m livewell.ingestion.cli [--instruments ...] [--backfill]`
- Lambda-ready: `run_ingestion()` callable from thin handler, config via env vars
- 13 tests (constants, S3 helpers, core logic, error isolation)

**Phase 1D status:** Complete
- Vite proxy: `/api/*` forwarded to `localhost:8000`
- MSW gated behind `VITE_USE_MOCKS=true` (off by default in dev; on for tests)
- 3 new FastAPI routes with hardcoded stubs
- CORS expanded to cover ports 5173–5175 + 4173
- 65 frontend tests passing, 14 backend tests passing

---

## Next: Sub-project 1B — Feature Generation

- Read 1d and 1h OHLCV Parquet from S3
- Compute EMA-20, EMA-50, RSI-14, MACD, ATR-14 per instrument
- Write feature tables back to S3 as Parquet
- Unit-test each indicator against known values

# LW-605 — Kiro evaluation slice (bounded)

Prepared 2026-10-16. Owner: Ian. Local/scratch only; no deploy, no production
writes, no live data. This records the evaluation evidence governance asked for
in `docs/LW-605-kiro-evaluation-slice.md`.

## Task performed (the bounded slice)

The first bounded slice of LW-304: **define and validate the backtest summary
contract against a small frozen fixture.** Concretely:

- Documented the expected `BacktestSummary` shape from source
  (`apps/api/schemas/backtest.py`, `livewell/backtest/aggregator.py`).
- Created a sanitized synthetic frozen fixture
  (`apps/api/tests/backtest/fixtures/frozen_trades.json`) — 4 trades across two
  instruments and two regimes, mixing wins/losses and valid/invalid signals, with
  an embedded hand-computed `expected` block.
- Added a contract test (`apps/api/tests/backtest/test_contract.py`) that runs
  `build_summary` over the fixture and validates the result against the Pydantic
  `BacktestSummary` schema.

This closed a real gap: the existing `test_aggregator.py` asserts aggregator math
on inline dicts but never validates the output against the schema the API route
actually serves, and no frozen-fixture path existed.

## Evaluation evidence (required by LW-605)

- **Kiro model and session surface used:** Kiro CLI (`kiro-cli chat`), agentic
  terminal session, model selection "Auto" (server-selected). Tools used: code
  reading, filesystem write, and terminal (`uv run pytest`, git).
- **Fixture and contract/test commit:** commit `7dcb15f` on `main`
  (`frozen_trades.json` + `test_contract.py`, 141 insertions). Pushed to
  `github.com/ianfmc/livewell`.
- **Test command and result:**
  `AWS_DEFAULT_REGION=us-west-1 uv run pytest tests/backtest/ -q` →
  **46 passed** (36 pre-existing + 10 new contract tests). The new file alone:
  `uv run pytest tests/backtest/test_contract.py -v` → **10 passed**.
- **Elapsed time to a useful result:** a single working session; the test passed
  on the first run.
- **Correction loops / rework required:** none. No failing-test rework; the
  import paths (`from schemas.backtest import ...`,
  `from livewell.backtest.aggregator import ...`) resolved first try under
  `uv run pytest` from `apps/api`.
- **Kiro tool / model / integration limitations observed:** the agent execution
  environment blocks launching long-running servers (uvicorn/npm/docker) and the
  background-process control was unavailable, so live-server steps required Ian to
  start the stack. Not relevant to this slice (pure local pytest), but it is a
  recurring constraint for browser/API-render steps. No other limitation hit.
- **Sanitized result:** the fixture uses synthetic forex figures only; no
  production data, keys, or live tables. Deterministic headline figures from the
  fixture: totalTrades 4, winRate 0.75, avgEdge 0.875, maxDrawdown ≈ -0.0377,
  equity curve [1060, 1020, 1080, 1140].
- **Remaining follow-up work:** none required for this slice. The broader LW-304
  surface was already validated and accepted at revision 181; this slice adds a
  durable regression test for the contract. Optional future: extend the fixture
  pattern to a loader-level (S3 parquet → trades) frozen fixture if a
  heavier integration test is wanted.

## Guardrails

All work local/scratch. No deploy, no production S3 write, no live data, no
expansion into ingestion/ablation/scheduled backtest work. Committed and pushed
to `main` (`7dcb15f`); not deployed.

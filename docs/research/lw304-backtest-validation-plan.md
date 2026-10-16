# LW-304 — Validate backtest surface (plan, eng-reviewed)

Status: eng-reviewed plan for LW-304. Prepared 2026-10-16. Governance snapshot:
revision 180. Owner: Ian. Local/scratch-only; no deploy, no production writes
without explicit authorization (per task acceptance criteria).

## Task (governance, LW-304)

Validate the S3-backed `/api/backtest/summary` path and BacktestResults UI,
separately from the core signal workflow. Acceptance criteria:
1. Produce a backtest summary artifact from frozen baseline inputs in a
   scratch/non-production location.
2. `/api/backtest/summary` returns 200 with a schema-valid `BacktestSummary`.
3. BacktestResults UI renders the summary with zero console errors.
4. Reproduce headline figures deterministically from frozen inputs.
5. Do not deploy or write to production without explicit authorization.

## Step 0 — what already exists (read, not assumed)

- `livewell/backtest/loader.py`: `load_price_history(s3_key, bucket)` reads
  `prices/{s3_key}/1d/{year}.parquet` from S3 (present in frozen baseline);
  `load_all_signals(env)` scans DynamoDB `livewell-signals-{env}`.
- `livewell/backtest/outcome.py`: `resolve_trade(signal, price_df)` finds the
  next trading day's close and calls `is_win(direction, strike, next_close)`.
- `livewell/backtest/aggregator.py`: `build_summary(trades)` → dict matching
  `schemas/backtest.py::BacktestSummary` (totalTrades, winRate, avgEdge,
  maxDrawdown, equityCurve, rows, signalValidSplit). Cost/payout constants
  $40/$100, starting equity $1000.
- `routers/backtest.py`: `/api/backtest/summary` reads a precomputed
  `backtest/summary.json` from S3 (`LIVEWELL_BUCKET`); 404 if absent, 500 if no
  bucket. (So producing + storing the artifact is the prerequisite the route
  reads back.)
- Feasibility: backtest derives outcomes from PRICE history (not the empty
  `livewell-trades-prod`). Frozen baseline has prices (187) + signals (187), so
  it CAN be reproduced offline — prices via moto S3 (LW-302 Segment 1 pattern),
  signals via a scratch DynamoDB seeded from the frozen `signals-export.json`
  (LW-302 Segment 2 pattern). Reuse those; do not restart discovery.

## Decision D1 (from /plan-eng-review) = A — fix the direction-vocabulary bug

**Finding:** the signals pipeline emits `direction` ∈ {`buy`, `sell`, `none`}
(`signals.py` lines 114/120/125), but `outcome.py::is_win` only recognizes
`call`/`put`. Every actionable signal therefore resolves as a LOSS, so headline
figures would be a deterministic artifact of the mismatch (all-losses). The
existing `tests/backtest/test_outcome.py` uses `call`/`put` too, so it passes
while never exercising the real vocabulary — which is how the bug survived.

**Resolution A (chosen):** fix the resolver to the real vocabulary as a scoped
LW-304 change, with tests, THEN produce the artifact. Mapping:
`buy` → in-the-money when `next_close > strike`; `sell` → ITM when
`next_close < strike`. Update `is_win` (accept `buy`/`sell`; optionally keep
`call`/`put` as aliases) and update `test_outcome.py` to the real vocabulary.
Rejected: B (validate plumbing only, flag defect — criterion 4 would produce
knowingly-meaningless numbers); C (investigate-first — already confirmed the
mismatch from both code sides, so the round-trip adds no information).

## Plan

1. **Fix** `livewell/backtest/outcome.py::is_win` to map `buy`/`sell`
   (treat `call`/`put` as aliases if cheap). Update `tests/backtest/
   test_outcome.py` to the real vocabulary + keep alias coverage. `uv run pytest`
   green.
2. **Produce the artifact offline** (criterion 1): a throwaway harness —
   prices from frozen via moto S3, signals from the frozen export into a scratch
   DynamoDB, `resolve_trade` over all actionable signals, `build_summary` →
   write `summary.json` to a scratch bucket/location. No prod writes.
3. **Serve + validate** (criterion 2): point the real API at the scratch bucket
   (`LIVEWELL_BUCKET=<scratch>`), confirm `/api/backtest/summary` returns 200 and
   a schema-valid `BacktestSummary` (TestClient first; browser for the UI step).
4. **UI** (criterion 3): with the local stack up (Ian starts servers — exec
   guard blocks the agent), `/browse` BacktestResults, confirm it renders the
   summary with zero console errors.
5. **Determinism** (criterion 4): re-run step 2 twice; headline figures
   (totalTrades, winRate, avgEdge, maxDrawdown) identical. Record them.
6. **Guardrails** (criterion 5): all scratch/local; no prod S3 write; teardown
   after. Baseline (`frozen/baseline-v1/`) preserved and untouched.

## Known risks / notes

- After the fix, win rates reflect a next-day-close binary rule on frozen data —
  this validates the SURFACE (artifact → API → UI → deterministic), not model
  profitability. Record figures as validation output, not a performance claim.
- The route reads a precomputed `summary.json`; LW-304 produces that artifact in
  scratch. Wiring a scheduled/automated backtest producer is NOT in scope.
- Env constraint: agent exec tool blocks launching servers (uvicorn/npm/docker)
  and `control_bash_process` is unavailable; Ian starts the stack for the UI
  step. Agent runs the offline harness + TestClient + `/browse`.

## GSTACK REVIEW REPORT

Reviewed by: /plan-eng-review (interactive; prose decision brief — no
AskUserQuestion tool). Scope: user-named target LW-304; no prior plan file, so
Step 0 established feasibility before planning. Date: 2026-10-16. Snapshot: 180.

### Source-of-truth read
`livewell/backtest/{loader,outcome,aggregator}.py`, `routers/backtest.py`,
`schemas/backtest.py`, `livewell/signals/signals.py` (direction vocabulary),
`tests/backtest/test_outcome.py`.

### Step 0 findings
- Backtest reproducible offline from frozen prices + signals (outcomes derived
  from prices; empty trades table not required). Reuse LW-302 moto + scratch-
  DynamoDB patterns — no new infrastructure.
- Complexity gate (8+ files / 2+ services): NOT triggered — one scoped bug fix
  + a throwaway harness + validation.
- **Bug caught:** `direction` vocabulary mismatch (`buy/sell` vs `call/put`)
  that makes headline figures meaningless; existing tests mask it by using
  `call/put`.

### Decision
| ID | Topic | Resolution |
|----|-------|------------|
| D1 | Backtest direction-vocabulary mismatch | A — fix resolver + tests to real `buy/sell`, then produce artifact |

Note: options differ in coverage — Completeness A=9/10, B=6/10, C=7/10.

### Verdict
Feasible and ready to implement as written. One real bug fix (with tests) is in
scope and required for criterion 4; everything else is offline validation reusing
proven patterns. No deploy, no prod writes, baseline preserved. Implementation is
a separate step; not performed in this review.

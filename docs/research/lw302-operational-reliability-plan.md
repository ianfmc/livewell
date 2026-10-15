# LW-302 — Operational-reliability exercise (approach for /plan-eng-review)

Status: DRAFT approach doc for engineering review. Not evidence of completion.
Prepared: 2026-10-02. Governance snapshot: sourceRevision 169
(retrievedAt 2026-10-02T22:08:03Z). Owner: Ian.

## Why this doc exists

The LIVEWELL NBA (`nbas/LIVEWELL.md`, canonical rev 169) puts the current next
action at **operational reliability under LW-302**: *exercise the existing core
path, including a bounded failure/recovery scenario, and record deploy/operate
evidence before proposing LW-302 completion.* The scoring-replay sub-claim is
already recorded as complete (1,831/1,831 exact) and must not be repeated;
reproducibility is **not** operational reliability.

This is a bounded verification, not new discovery. It reuses existing docs
(`docs/04_pipeline_architecture.md`, `docs/research/lw302-replay-verification-plan.md`)
and the mapped pipeline code. Per the NBA, do not restart discovery.

## Decided scope (confirmed with Ian)

- **Option A — local end-to-end, NO deploy.** There is no deployed UI: the web
  app has no Amplify app, no `.env` hosted URL, no CloudFront/execute-api
  reference; it is wired for local dev only (`localhost:5173`, `/api` proxy to
  `localhost:8000`, MSW mocks). Confirmed by inspection and by Ian ("this is
  not yet an Amplify application … only a local UI"). Deploying is a one-way,
  Ian-gated action and is explicitly **out of scope** for this exercise.
- **UI against the REAL local API, not MSW.** A mocked UI would only prove
  fixtures render. The UI (`npm run dev`) must talk to the real local FastAPI
  backend (`uv run uvicorn main:app`). The Vite dev server already proxies
  `/api` → `http://localhost:8000`, so pointing at the real API means ensuring
  MSW does not intercept (`src/main.tsx` starts MSW under `import.meta.env.DEV`
  with `onUnhandledRequest: "bypass"` — the real-API path needs MSW disabled or
  bypassed for `/api/*`). **Open design point D-UI below.**
- **Frozen `baseline-v1` data for the core run.** Deterministic, offline, no
  live yfinance, no live writes. Ties the exercise to the already-verified
  baseline.

## The wrinkle this review must resolve (not papered over)

The core path is not trivially "frozen-friendly," and the UI reads from a
different store than the frozen artifacts live in:

1. **`run_instrument()` is hardwired to full ingestion.**
   `apps/api/livewell/pipeline/runner.py` runs
   `run_ingestion()` (yfinance) → `run_features()` → `run_signals()` →
   read-back from `LIVEWELL_BUCKET` → `score_signal()`. There is no built-in
   "skip ingestion / read frozen inputs" switch. Running it as-is would hit
   yfinance and the live bucket. The replay verification already had to work
   around this.
2. **UI read path uses DynamoDB, frozen data is S3.** The product endpoints the
   UI calls (`/api/signals`, `/api/dashboard`, …) read via
   `livewell/signals/dynamodb.py::_table()` →
   `livewell-signals-{LIVEWELL_ENV}` (default `prod`). The frozen baseline is
   S3 Parquet + `results/signals-export.json`. So serving frozen data to the UI
   requires a defined bridge, not a hand-wave.

## Proposed core-path definition + frozen-data bridge

Exercise the path in two grounded segments, both local and reversible:

**Segment 1 — compute path (backend), frozen inputs.**
Seed a scratch S3 location (or local dir) from `frozen/baseline-v1/`, point
`LIVEWELL_BUCKET` at it, and run the **features → signals → score → read-back**
portion only — i.e. the deterministic part of `run_instrument` **without**
`run_ingestion()`. Record that it reproduces frozen signals (reuse the replay
machinery; do not re-litigate the 1,831-row claim — just confirm the path runs
and reads back).

**Segment 2 — serve path (API + UI), frozen-seeded store.**
Seed a **scratch DynamoDB** table `livewell-signals-<scratch-env>` from
`frozen/baseline-v1/results/signals-export.json`, set `LIVEWELL_ENV=<scratch>`,
start the real FastAPI (`uvicorn main:app`), start the UI (`npm run dev`) with
MSW bypassed for `/api/*`, and confirm the core screens (Dashboard,
DailySignals, ContractDetail, SignalTracker) render real backend data. Capture
sanitized screenshots. No live `livewell-signals-prod` touched; scratch table
deleted after.

## Bounded failure / recovery scenario (exactly one)

Candidates (review to pick ONE):
- **F1 — missing input mid-path:** remove/corrupt one instrument's seeded input
  before Segment 1; show the path surfaces the failure (`run_instrument` raises;
  `handler._run_worker`/coordinator records the error — see
  `pipeline/handler.py` error accounting: `dispatch_failed`/`dispatch_partial`),
  then restore the input and show successful recompletion.
- **F2 — backend down for the UI:** stop the local API mid-session; show the UI
  surfaces the error state (hooks return `{error}`); restart; show recovery.

"Failure visible" and "recovered" must be defined concretely for the chosen
scenario and captured as evidence.

## Evidence to record (sanitized)

- Commands run + exit results; local run logs (sanitized).
- Segment 1: path ran on frozen inputs, read-back succeeded.
- Segment 2: UI screenshots of core screens rendering real-API data.
- Failure/recovery: before/after showing failure surfaced then recovered.
- Commit SHAs for any code touched. No signed URLs, keys, tokens, customer data.

## Gates / guardrails

- No deploy. No live DynamoDB/S3 writes — scratch stores only, deleted after.
- No yfinance / live external calls in the core run (frozen inputs).
- Nothing Ian-gated is triggered. Reversible throughout.
- A handoff after this reports operational reliability **as exercised locally**,
  explicitly states nothing is deployed, and does NOT by itself request LW-302
  `done` — governance + Ian decide, and deployed evidence (if wanted) is a
  separate gated task.

## Resolved design decisions (from /plan-eng-review, 2026-10-02)

All four decisions resolved to option A. These are now the plan of record.

- **D1 / D-COMPUTE = A.** Point `LIVEWELL_BUCKET` at a scratch location
  pre-seeded from `frozen/baseline-v1/`, and invoke only
  `run_features → run_signals → score` directly in a throwaway local script —
  NOT the full `run_instrument` (which would call `run_ingestion()`/yfinance).
  **Zero committed production-code change.** Mirrors the approved replay
  approach. Rejected: adding a `skip_ingestion` param to the production
  entrypoint (B) or monkeypatching `run_ingestion` (C) — both touch/mock
  production internals for a one-off verification.

- **D2 / D-BRIDGE = A.** Seed a **scratch DynamoDB table**
  `livewell-signals-<scratch-env>` from
  `frozen/baseline-v1/results/signals-export.json`, set
  `LIVEWELL_ENV=<scratch>`, and run the real API against it. `_table()`
  resolves the scratch name unmodified; **live `livewell-signals-prod` is never
  touched**; drop the scratch table after. Rejected: DynamoDB Local (B — needs
  an endpoint-override shim `_table()` doesn't have) and an API read-shim (C —
  bypasses the real DynamoDB read path, proving nothing operational).

- **D3 / D-UI = A.** Gate MSW startup behind an env flag (e.g. `VITE_USE_MSW`),
  **defaulting to current behavior** (MSW on in dev). Run the exercise with the
  flag off so the UI hits the real local API via the existing Vite `/api` proxy.
  One small, guarded, reusable committed line; **committed default unchanged**.
  Rejected: uncommitted local hack to `main.tsx` (B) and MSW passthrough (C).

- **D4 / D-FAIL = A.** Exercise exactly ONE scenario: **missing/corrupt input
  for one instrument mid-compute (Segment 1).** This tests the failure contract
  already specified in `docs/04_pipeline_architecture.md` ("if one pair's data
  is missing, continue processing others if safe"; "if model artifact missing
  or schema mismatch occurs, block … and surface alert") and `handler.py`'s
  error accounting (`dispatch_partial` / `dispatch_failed`). Procedure: remove/
  corrupt one seeded instrument input → show the failing instrument surfaces an
  error while others proceed → restore input → show clean recompletion. Rejected:
  backend-down-for-UI (B — tests frontend error handling, not pipeline
  reliability) and both-A-and-B (C — doubles a deliberately bounded exercise).

## GSTACK REVIEW REPORT

Reviewed by: /plan-eng-review (interactive, prose decision briefs — no
AskUserQuestion tool in session). Scope gate: user-named target
(this draft). Date: 2026-10-02. Governance snapshot: rev 169.

### Source-of-truth docs read
- `docs/04_pipeline_architecture.md` — intended production flow + the
  **failure-handling contract** the D4 scenario now tests against.
- `docs/research/lw302-replay-verification-plan.md` — reused machinery; the
  reproducibility sub-claim is already recorded (1,831/1,831) and is NOT
  repeated here.
- Code read: `pipeline/runner.py`, `pipeline/handler.py`,
  `signals/dynamodb.py`, `apps/web/vite.config.ts`, both app `CLAUDE.md`.

### Step 0 — scope challenge
- Reuses existing replay machinery, frozen artifacts, and the real API read
  path rather than rebuilding. Correct.
- Complexity gate (8+ files / 2+ services) NOT triggered — local verification
  scaffolding, no new committed services.
- Near-zero committed code change is the governing constraint; all four
  decisions chosen to honor it.
- Gap caught and fixed: the draft did not reference the pipeline doc's
  documented failure contract; D4 now tests that specified behavior.

### Decisions
| ID | Topic | Resolution |
|----|-------|------------|
| D1 | Skip-ingestion compute path | A — scratch bucket + direct features→signals→score; no prod-code change |
| D2 | Frozen→serve bridge | A — scratch DynamoDB table seeded from export; live prod untouched |
| D3 | Real API vs MSW in dev UI | A — `VITE_USE_MSW` flag, default unchanged |
| D4 | Failure/recovery scenario | A — missing-input mid-compute, tests documented contract |

Note: decisions differ in kind, not coverage — no completeness scores.

### Architecture / blast radius
- All work is local and reversible: scratch S3 location, scratch DynamoDB
  table, env flags. No deploy, no live writes, no yfinance calls.
- Blast radius on committed code: one guarded `VITE_USE_MSW` line (default
  preserved). Everything else is throwaway local scripting / env config.
- Honesty gate preserved: this exercise does NOT by itself justify marking
  LW-302 done; it covers the operational-reliability portion only, locally,
  with deployment explicitly out of scope and Ian-gated.

### Residual risks / notes
- Scratch DynamoDB table must use a clearly non-prod env suffix; verify
  `LIVEWELL_ENV` is set before the API starts so `_table()` never resolves
  `prod`. Delete the scratch table at the end.
- The frozen export mixes 1,831 scored + 15,032 unscored rows; the UI render
  check should account for unscored rows rendering as expected (not a defect).
- No test-framework change required; existing pytest/vitest suites are not the
  subject of this exercise.

### Verdict
Plan is sound and ready to execute as written, with D1–D4 = A. Smallest honest
exercise that satisfies the NBA's "exercise the core path + bounded
failure/recovery, record deploy/operate evidence (local)". Execution is a
separate step and was NOT performed during this review.



## EXECUTION RESULTS (2026-10-14)

Executed locally per D1–D4 = A. Fully offline / scratch-only; **no deploy, no
live AWS writes, no yfinance.** Verified afterward: frozen prefix intact
(187/187/187/1/1 unchanged), no `*-scratch` tables in live DynamoDB.

### Segment 1 — compute path on frozen data (D1 = A, moto in-process S3)
- Seeded an in-process moto S3 bucket from frozen `baseline-v1` prices+features
  (374 parquet objects), set `LIVEWELL_BUCKET` to the scratch bucket, and ran
  the **real** `run_signals` (1d) + read-back + score with the model pinned
  directly (bypassing the DynamoDB registry, exactly as the approved replay).
  No `run_ingestion`/yfinance.
- **Result:** `run_signals` succeeded=19 failed=0; 19/19 latest signals
  (all dated 2026-09-24) read back and scored with the pinned
  RandomForestClassifier (n_features_in_=12). Sample scores: EURUSD
  0.8514054816393779, USDJPY 0.5053177936283934, XAUUSD 0.7924157485988965,
  NQ 0.034513620611303544. **PASS.**

### D4 — bounded failure / recovery (D4 = A, missing input mid-compute)
Tests the failure contract in `docs/04_pipeline_architecture.md`
("if one pair's data is missing, continue processing others if safe").
- **Failure injected** (dropped EURUSD inputs): logged
  `ERROR ... no feature files found for EURUSD/1d`; run summary reported
  `succeeded=18 failed=1 failed_list=['EURUSD']`, `read_or_score_failures=1`.
  The other **18 instruments processed and scored normally** — graceful
  degradation, failure isolated and surfaced.
- **Recovery** (inputs restored, clean run): `succeeded=19 failed=0`; EURUSD
  returned with score 0.8514054816393779, identical to its pre-failure value.
- **No cross-contamination:** the 18 surviving instruments produced
  byte-identical scores in the degraded and recovery runs (diff = empty).
  **PASS.**

### Segment 2 — serve path, real API over scratch DynamoDB (D2 = A, D3 = A)
- D2: seeded **DynamoDB Local** (`localhost:8001`, Docker) with scratch tables
  `livewell-signals-scratch` (from the frozen `signals-export.json`; 19
  instruments latest) and `livewell-model-registry-scratch` (active
  `rf_tuned/20260507T144919`). boto3 1.42 honored
  `AWS_ENDPOINT_URL_DYNAMODB` with **no code change**. Live
  `livewell-signals-prod` never touched.
- D3: the UI's mock gate is `VITE_USE_MOCKS` and defaults **off** (MSW starts
  only when `=== 'true'`), so the real-API path needs **no code change** — the
  planned `VITE_USE_MSW` flag was unnecessary. Divergence from the plan, in the
  plan's favor (smaller blast radius).
- Exercised the **real FastAPI app** (`LIVEWELL_ENV=scratch`) against the
  scratch tables via `TestClient` (Option 2 — see constraint below), hitting
  the exact router → `get_latest_signals`/`get_signal` → transform → Pydantic
  response path the UI depends on.
- **Result:** `/health` 200; `/api/signals` 200 (**19 contract cards**, one per
  instrument); `/api/dashboard` 200 (markets/modelHealth/opportunities/
  topCandidates); `/api/model/health` 200 (reads seeded registry);
  `/api/signals/tracker` 200; contract detail `/api/signals/Gold/x` 200
  (prob 0.7924157485988965 — **matches the Segment 1 XAUUSD score exactly** —
  edge 0.5848, conf High, regime bullish). **PASS.**

### Honest gaps / exclusions
- **Browser render not exercised.** The agent execution environment blocks
  launching long-running servers (uvicorn, `npm run dev`) and has no browser
  driver, so Segment 2 used an in-process `TestClient` (Option 2) rather than a
  rendered browser against a live `uvicorn` + `npm run dev`. The **API contract
  the UI depends on is proven**; the visual render is NOT independently
  verified here. To close this, run the two dev servers manually and eyeball
  Dashboard / Daily Signals / Contract Detail (mocks off).
- **`/api/backtest/summary` not covered** — reads `backtest/summary.json` from
  S3 (`LIVEWELL_BUCKET`), not DynamoDB; no frozen backtest artifact exists, so
  it returned 500 ("no S3 bucket"). Out of scope for this DynamoDB-backed
  serve-path exercise; not a core-path defect.
- **Deployment / scheduling (EventBridge) not exercised** — explicitly out of
  scope (no deploy; Ian-gated). LW-302 is therefore **NOT** complete on the
  strength of this exercise; this covers local operational reliability of the
  compute + serve paths and the documented failure/recovery contract only.

### Teardown
Scratch DynamoDB Local container removed, `/tmp/lw302exec` deleted. No scratch
state persisted. (See teardown commands run at execution time.)



## RENDERED-UI CHECK + a2ui REMOVAL (2026-10-15)

The browser-render step revealed that the web app **blank-screened** on load:
`A2uiProvider` (wrapping the whole app in both `main.tsx` and `App.tsx`)
returned HTTP 500 because `@a2ui/react/v0_9` / `@a2ui/web_core/v0_9` subpath
imports could not be resolved (the `a2ui/` sibling repo is git-ignored and the
subpaths don't resolve). This made the rendered-UI portion of LW-302 impossible
until repaired or removed. Ian correctly scoped this as *on* the LW-302 critical
path, and chose removal.

### Finding: a2ui was vestigial
`SignalExplainPanel` and `useSignalExplain` already use plain MUI + `fetch`
against `/api/explain/{id}` — they do NOT use a2ui. The `A2uiProvider` context
was read by no component (`useA2ui` imported only by its own test). So a2ui was
dead code providing nothing; removal is pure subtraction, zero feature loss.
(Leading-practice note: had a2ui actually powered the panel, the right move
would have been an error-boundary + lazy isolate so a broken optional feature
degrades locally instead of blank-screening the app — not a full remove.)

### Removal (web-app change, commit forthcoming)
- `main.tsx`, `App.tsx`: removed both `A2uiProvider` wrappers + imports.
- Deleted `src/a2ui/` (`A2uiProvider.tsx`, `useA2ui.ts`, and its test).
- Rewrote `SignalExplainPanel.test.tsx` and `useSignalExplain.test.tsx` to the
  CURRENT fetch/`data` source (they were stale — testing an old SSE/`surface`
  a2ui design that no longer matched the shipped code).
- Removed `@a2ui/*` from `package.json`; reinstalled.
- Fixed two PRE-EXISTING `ContractCard` type-drift errors (missing `signalId`)
  in `DailySignals.tsx` and `contract-card.test.tsx` that blocked the build —
  unrelated to a2ui, but in the way.

### Verification
- `npm run build`: tsc clean, vite build OK (668 modules, no a2ui error).
- `npm run test:coverage`: 18 files / 76 tests pass; coverage 95% (>80 gate);
  rewritten explain tests at 100%.
- `/browse` (headless) against localhost:5173 (mocks off → real API on :8000 →
  scratch DynamoDB): all five core screens render, **zero console errors**.
  - Dashboard: 19 market-condition chips, Opportunity Summary (19/9/0), Top
    Candidates (Russell 2000 +0.95, Dow +0.92, GBP/USD +0.71), Model Health.
  - Contract Detail (Gold): PASS, bullish, High conf, Model 79%, Edge +58%,
    and the "Why this setup" explain panel renders "Pass — score 0.79"
    (79% matches the Segment-1 XAUUSD score 0.7924… — compute→serve→UI
    consistent end-to-end).
  - Signal Tracker: 19 total / 0 taken / 19 pending. Model Health: Warning,
    Data Freshness Current.
  - Screenshots captured (scratch, not committed): dashboard, daily-signals,
    contract-detail, signal-tracker, model-health.

### UI finding — RETRACTED (was a capture-timing artifact, not a defect)
Initial `/browse` capture reported Daily Signals showing "Visible Contracts: 0"
with the Status filter on "All". **This was a false alarm:** the snapshot was
taken ~2s after navigation, before the async `useSignals` fetch resolved
(`loading` starts `true` with 0 cards). Re-checked with a 5s wait and a direct
in-page `fetch('/api/signals')`: the page shows **"Visible Contracts: 19 |
Review Needed: 4"** and renders all 19 cards (19 "Explain" buttons). No code
change made — the page is correct. Lesson recorded: wait for async hooks to
resolve before asserting on headless-browser page text.

All five core screens re-verified with proper waits: Dashboard, Daily Signals
(19 cards), Contract Detail, Signal Tracker (19 total), Model Health — all
render real data with ZERO console errors.



## DEPLOYED SCHEDULING + CONTROLLED-RUN EVIDENCE (2026-10-15)

The LW-302 completion gate (r177 NBA) was "deployed EventBridge schedule +
one controlled production-like run." Ian authorized proceeding; the deployed
infra was found ALREADY LIVE, so this was verification, NOT a first-time
deploy. Choice C (forensic read of the latest scheduled run) was used — all
read-only via `livewell-ro`. No `cdk deploy`, no manual Lambda invoke, no prod
writes, no MFA, no infra change.

### Deployed EventBridge scheduling — VERIFIED
- Rule `livewell-pipeline-schedule-prod`: State ENABLED, ScheduleExpression
  `cron(0 0 ? * MON-FRI *)`, target Lambda `livewell-pipeline-fn-prod`
  (Target0). The deployed cron matches the CDK source
  (`infra/lib/livewell-stack.ts` line 189) exactly — deployed == code.
- Lambda `livewell-pipeline-fn-prod`: State Active, 512 MB / 300 s.
- Firing on schedule: ~20 invocations per run on 2026-10-11/-12/-13/-14
  (coordinator + ~19 workers), fresh log streams on 2026-10-15.

### One controlled production-like run — VERIFIED (choice C)
- Latest scheduled run: 2026-10-15T00:00:26Z,
  `run_id=24f0ff63-aba7-48cc-a9e0-3e50da730349`, coordinator
  `status=dispatched dispatched=19 errors=0`.
- Workers completed for that run_id (per "worker done" log lines). The only
  warnings were benign yfinance `Failed to create TzCache/CookieCache` lines
  (Lambda read-only FS cache noise) — not pipeline failures; dispatch was 19/0.
- End-to-end persistence confirmed: live `livewell-signals-prod` contains a
  record from that exact run_id (e.g. `AUDUSD__2026-10-15`) with a non-null
  score and `model_version=20260507T144919` — the same pinned baseline model.
  So schedule -> coordinator -> worker -> scored DynamoDB write is verified on
  one real scheduled run.

### Net
All LW-302 evidence dimensions are now covered: local compute + failure/
recovery (moto), local serve path (TestClient over scratch DynamoDB), rendered
UI (browser over scratch stack), AND deployed scheduling + a controlled
(observed) production run. Remaining judgement for governance/Ian: whether this
evidence set is sufficient to move LW-302 to `done`. No production behavior was
changed by this verification.

# LW-211 — Recover outcome-resolver subsystem & reconcile CDK to live

**Task:** LW-211 (governance rev 225, release-gate, `ready`, high, deps `[LW-635]`).
Make committed `main` reproduce the live production stack so a future `cdk deploy`
is safe, and fold in the out-of-band changes.

**Done bar (eng-review D1 → A, decision `f86b2460`):** an **empty/clean `cdk diff`
against `livewell-prod`** — the proof that committed CDK == live. The original
near-destruction was an unexpected diff; only a no-op diff guarantees safety.

## Scope (governance rev 225)

Reconcile into CDK: the recovered resolver subsystem, the live API image, the GSI
index IAM grant, the Anthropic configuration, and the configurable Explain model
(pinned Haiku default retained).

## Recovered material (from ECR image `...0dfdf691...`, 2026-05-14)

Extracted `/var/task` to `.lw211-recovered/var-task/` (gitignored working dir).
**The resolver source genuinely missing from `main` is small and self-contained:**
- `livewell/tracking/handler.py` — Lambda entry `handler()`; loads due open trades,
  calls `resolve_trade` per trade, returns `{resolved, errors}`.
- `livewell/tracking/resolver.py` — `resolve_trade` / `resolve_outcome` /
  `fetch_close_price` (yfinance close at expiry → won/lost vs strike).
- `livewell/tracking/dynamodb.py` — `livewell-trades-{env}` access:
  `create_trade`, `list_trades`, `patch_trade`, `get_open_trades_due`.
- `Dockerfile.resolver` — `FROM public.ecr.aws/lambda/python:3.12`, pip installs
  `boto3 pandas yfinance pyarrow`, `CMD ["livewell.tracking.handler.handler"]`.

Trades item model (from `dynamodb.py`): hash `trade_id`; fields `s3_key`,
`direction`, `strike`, `expiry_time`, `status` (open/won/lost), `outcome_price`,
`outcome_source`, `resolved_at`.

## ⚠️ CRITICAL FOOTGUN — do NOT bulk-copy the recovered tree

The image is a **5-month-old snapshot**. 24 other `livewell/*.py` files DIFFER from
`main` because **`main` is newer** (LW-104–208). Copying `/var/task` over `apps/api`
would silently revert 5 months of committed work. **Recover ONLY the 3 `tracking/`
files + `Dockerfile.resolver`.** `tracking/__init__.py` is identical to `main` —
leave it. Verified: nothing in current `main` source references `tracking`/`trades`
(no API route, no caller) — the subsystem is orphaned, its only invokers are the 4
EventBridge schedules. So recovery is purely additive.

## Changes

### A. Application source (commit as-is from recovery)
1. `apps/api/livewell/tracking/handler.py`, `resolver.py`, `dynamodb.py` — copy the
   3 recovered files verbatim.
2. `apps/api/Dockerfile.resolver` — copy verbatim.
3. Check `pyproject.toml`/`uv.lock`: resolver needs `yfinance` (ingestion already
   uses it, so likely present). Confirm `boto3/pandas/pyarrow/yfinance` resolve;
   the Dockerfile pip-installs them directly, but keep deps consistent.
4. Run the quality gate; add minimal tests for `resolve_outcome` (buy/sell
   won/lost boundary) and `get_open_trades_due` (expiry filter) — pure functions,
   cheap to cover. Mock yfinance for `fetch_close_price`.

### B. CDK — reconstruct the resolver resources (match deployed logical IDs)
In `infra/lib/livewell-stack.ts`, add using the EXACT construct IDs so CloudFormation
logical IDs regenerate identically (→ empty diff):
- `new dynamodb.Table(this, 'TradesTable', { tableName: ``livewell-trades-${env}``,
  partitionKey: { name: 'trade_id', type: STRING }, billingMode: PAY_PER_REQUEST,
  pointInTimeRecovery…, removalPolicy: RETAIN })` → logical `TradesTable1EFD6DBF`.
- `new lambda.DockerImageFunction(this, 'ResolverLambda', { functionName:
  ``livewell-outcome-resolver-fn-${env}``, code: fromImageAsset('../../apps/api',
  { file: 'Dockerfile.resolver' }), architecture: ARM_64, memorySize: 256,
  timeout: 300s, environment: { LIVEWELL_ENV: env } })` → `ResolverLambdaEC7302D3`.
- Grants: `tradesTable.grantReadWriteData(resolver)`, `signalsTable.grantReadData(resolver)`.
- 4× `new events.Rule(this, 'Resolver1100ET', { schedule: cron(min 16/19/21/22…),
  targets: [new LambdaFunction(resolver)] })` with IDs `Resolver1100ET`,
  `Resolver1400ET`, `Resolver1600ET`, `Resolver1700ET` → match deployed crons
  `cron(5 16 ? * MON-FRI *)`, `cron(5 19 …)`, `cron(5 21 …)`, `cron(5 22 …)`.
- `CfnOutput TradesTableName` (deployed template has it).

### C. CDK — fold in the three out-of-band changes
- **GSI** `by-instrument-date` on signals table — ALREADY in `main` CDK (commit
  `32da079`). Verify it matches live. ✓ likely no-op.
- **API role `/index/*` grant** — `grantReadData` on the signals table ALREADY
  grants `/index/*` in `main` CDK. The out-of-band inline policy `LW208-GSI-read`
  was a manual duplicate; once CDK deploys the grantReadData form, **delete the
  inline `LW208-GSI-read` policy** so the role matches CDK (else diff shows an
  extra inline policy). Note in plan: remove inline policy as part of reconcile.
- **ANTHROPIC_API_KEY** — currently a live env var with a secret value. CDK injects
  it via `--context anthropicKey=` (empty default). To keep the diff clean without
  committing the secret: deploy with `--context anthropicKey=<value>` at deploy
  time (Ian-supplied), OR switch to SSM. Decision deferred to execution (see Q).
- **ANTHROPIC_MODEL** (configurable-model proposal, folded in per rev 225): add
  `environment: { ANTHROPIC_MODEL: this.node.tryGetContext('anthropicModel') ??
  'claude-haiku-4-5-20251001' }` to the API Lambda, and change `builder.py:108` to
  `os.environ.get("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")`. NOTE: this
  ADDS an env var not currently live → it WILL show in `cdk diff`. Acceptable
  expected change (additive, default-preserving); call it out so it isn't mistaken
  for drift. Alternatively deploy it so live matches — but that's a deploy, gated.

### D. Verify — the done bar
`cd infra && cdk diff LivewellStack-prod --context env=prod` → drive to EMPTY
(modulo the deliberate `ANTHROPIC_MODEL` addition in C, which is the one expected
line). Match any stray logical-ID mismatches against `deployed-prod-template.json`.
Run `infra` jest tests + the seven-arm quality gate.

## Open question for execution (not blocking the plan)
`ANTHROPIC_API_KEY` reconciliation: (a) deploy-time `--context anthropicKey=` each
deploy, or (b) move to SSM + `fromSsmSecure`. Ian chose a plain env var for the
value; for CDK repro, (a) keeps it out of git but requires the context flag on
every deploy; (b) is cleaner IaC. Decide at execution.

## NOT in scope
- No change to the 24 newer `livewell/` files (main is authoritative).
- No `cdk deploy` here — this task reaches a clean diff; deploying is a separate
  gated step on Ian's go.
- No new resolver features; recover as-is.

---

## GSTACK REVIEW REPORT

**Skill:** /plan-eng-review · **Target:** LW-211 (governance task) · **Date:** 2026-10-24 · **Reviewer model:** claude

### Scope outcome
Recover a real orphaned subsystem + reconcile CDK to live. "2+ new services" smell
is expected (recovering, not inventing) — not a cut. Scope held.

### Decisions
| ID | Decision | Chosen | Recommended | Confidence |
|----|----------|--------|-------------|------------|
| D1 | Done bar | **A** empty `cdk diff` vs prod | A | 9/10 |

D1 logged `f86b2460`.

### Findings by section
1. **Architecture** — recovered resolver is self-contained (orphaned; only invoked
   by 4 schedules; no `main` caller). CDK reconstruction must match deployed logical
   IDs via exact construct IDs (`TradesTable`, `ResolverLambda`, `Resolver{1100,1400,1600,1700}ET`) to reach an empty diff. The out-of-band inline IAM policy `LW208-GSI-read` must be DELETED during reconcile (CDK's grantReadData supersedes it) or the diff won't clean.
2. **Code quality** — recover the 3 files verbatim; do NOT bulk-copy `/var/task` (24 newer files would revert — the footgun). `tracking/__init__.py` unchanged.
3. **Tests** — add cheap unit tests: `resolve_outcome` buy/sell won/lost boundaries; `get_open_trades_due` expiry filter; `fetch_close_price` with yfinance mocked. Resolver had zero committed tests.
4. **Deploy/verify** — done bar is the empty diff; `ANTHROPIC_MODEL` is the one deliberate additive diff line; `ANTHROPIC_API_KEY` repro method is an execution-time decision.

### Prior learnings applied
- `livewell-prod-cdk-drift-trades-resolver` (9) — the subject; this task closes it.
- `livewell-prod-lambdas-deployed-manually-not-from-main` (9) — image/env drift.
- `gsi-query-needs-separate-iam-grant-on-index-arn` (9) — the inline policy to retire.
- `livewell-prod-anthropic-key-empty` (9) — key/model config handling.

### Suppressed findings
None.

### Risk / watch
- **Footgun:** bulk-copying recovered `/var/task` reverts 5 months of `main`. Recover 3 files only.
- Secret handling: do NOT commit the Anthropic key; `--context` or SSM at deploy.
- Reaching a truly empty diff may need logical-ID fiddling; `deployed-prod-template.json` is the reference.
- `.lw211-recovered/` is a working dir — gitignore it; never commit the whole tree.

### Status
**DONE** — plan written, done-bar decided + logged, footgun flagged, recovery material in hand. Ready to execute on go. No code changed during review.

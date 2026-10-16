# LW-303 — Core readiness, security & operating-cost review

Status: assessment for governance (release-gate task LW-303). Prepared
2026-10-15. Governance snapshot: revision 179. Owner: Ian. Scope: personal-use
readiness of the existing LIVEWELL core system. Congressional/Track B is
explicitly out of scope (separately gated). All AWS evidence gathered read-only
via the `livewell-ro` profile; no production change, baseline preserved.

Acceptance criteria (from the task):
1. Core readiness and limitations are recorded. → this document.
2. Access and operational checks pass with the baseline preserved. → verified
   below (baseline intact 187/187/187/1/1; access posture reviewed).

## 1. Readiness (personal use)

The core system is operational end-to-end and was exercised this cycle under
LW-302:
- Compute path (features → signals → score) reproduces the frozen baseline
  (19/19 instruments; replay 1,831/1,831 exact).
- Deployed daily pipeline is live and firing: EventBridge
  `livewell-pipeline-schedule-prod` ENABLED, `cron(0 0 ? * MON-FRI *)`
  (matches CDK source), target `livewell-pipeline-fn-prod`. Latest scheduled
  run (2026-10-15, run_id 24f0ff63) dispatched 19/0 and wrote a scored record
  to `livewell-signals-prod` with the pinned model.
- Serve path (FastAPI) and the local UI render real data (five core screens,
  zero console errors).

Verdict: **ready for personal use.** It generates daily scored signals on
schedule and the results are retrievable. It is decision-support, not automated
execution.

## 2. Security / access controls

IAM (4 users, role-scoped):
- `livewell-ro` — `ReadOnlyAccess` (used for all evidence here).
- `ianfmc` — `AWSBillingReadOnlyAccess` + inline `AssumeAdminRole`
  (admin only via MFA-gated role assumption, not standing admin).
- `livewell-dev` — `AmazonS3FullAccess`.
- `checklist-tools` — checklist S3 access only.

Account posture: account-level MFA enabled, 2 MFA devices in use; `ianfmc`
carries an MFA device. No sprawling inline policies. Consistent with LW-613
(non-root administration, root MFA, key rotation program).

Findings (tightening opportunities — none a personal-use blocker):
- **S1 — `livewell-dev` has `AmazonS3FullAccess`**: broader than least
  privilege (all buckets, not just `livewell-data-*`). Recommend a scoped
  policy limited to the LIVEWELL data bucket(s).
- **S2 — access keys are 5–6 months old** (`livewell-dev` Apr 2026; others
  Sep 2026) with no rotation evident. Recommend a personal-use rotation cadence.
- **S3 — service users have no MFA**: acceptable for programmatic keys, but the
  `livewell-dev` combination (full-S3 + no MFA + stale key) is the weakest point;
  addressing S1/S2 mitigates it.

Verdict: **acceptable for personal use**, with S1/S2 as recommended hardening.

## 3. Operating cost

Resources (all serverless / on-demand):
- DynamoDB: 4 tables, all PAY_PER_REQUEST (signals ~17k items / 8.2 MB;
  model-runs 131; registry 1; trades 0).
- Lambda: 3 functions (pipeline 512 MB/300 s; api 512 MB/60 s; outcome-resolver
  256 MB/300 s).
- S3: `livewell-data-prod` ~105 MB / 1,128 objects (+ one additional bucket).
- EventBridge: 5 rules (schedule + resolvers).

Usage-based estimate (order-of-magnitude, us-west-1):
- Lambda: ~440 pipeline invocations/mo + resolvers, seconds each at 256–512 MB
  → within free tier, ≈ $0.
- DynamoDB on-demand: thousands of req/mo + 8.5 MB storage → < $1/mo.
- S3: 105 MB + thousands of requests → < $0.10/mo.
- EventBridge scheduled rules: free. CloudWatch Logs: a few cents.

Verdict: **effectively a few cents to low single-digit dollars per month.**
Caveat: this is a usage-based estimate, not the billed figure — `livewell-ro`
has no Cost Explorer access. For the authoritative number, check AWS Cost
Explorer / the Billing console under the `ianfmc` billing-read-only identity.

## 4. Known limitations (recorded)

- L1 — Single random-forest model (`rf_tuned/20260507T144919`); no ensemble and
  no live calibration monitoring yet (Phase 5).
- L2 — Ingestion depends on yfinance (external, no SLA; benign TzCache/
  CookieCache warnings in Lambda are cosmetic).
- L3 — No deployed UI/frontend; the web app is local-only (a2ui removed this
  cycle). Operators use the API/UI locally.
- L4 — Backtest surface (`/api/backtest/summary`) is not covered; tracked
  separately as **LW-304** (local/scratch-only unless Ian authorizes otherwise).
- L5 — Model Health reports overall status "Warning" (training-date/validation
  fields sparse) — worth a follow-up but not a core-path failure.
- L6 — No realized-outcome tracking / calibration monitoring live yet
  (`livewell-trades-prod` is empty); Phase 5 scope.
- L7 — Security hardening S1/S2 above.

## 5. Baseline preservation (acceptance criterion 2)

Verified intact and unchanged by all LW-302 work:
- Frozen prefix `s3://livewell-data-prod/frozen/baseline-v1/`:
  187 prices / 187 features / 187 signals / 1 model / 1 results (563 objects).
- Git tag `baseline-v1` (`e5ec61e`) present locally and on origin.
- Manifest `docs/baseline-v1-manifest.md` = FROZEN 2026-09-26.
- Pinned model `rf_tuned/20260507T144919` present and `active` in the prod
  registry.

## Overall verdict

The LIVEWELL core system is **ready for personal use**: readiness and
limitations are recorded (criterion 1); access and operational checks pass with
the baseline preserved (criterion 2). Recommended, non-blocking follow-ups:
S1/S2 (IAM tightening + key rotation), L4 (LW-304 backtest), L5/L6 (model-health
fields + outcome tracking under Phase 5). LW-303 completion is a governance/Ian
decision; this document is the recorded evidence.

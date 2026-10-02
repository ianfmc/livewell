# LW-302 — Frozen Baseline Replay Verification Plan

**Status:** Approved approach (reviewed via /plan-eng-review 2026-09-27). Not yet executed.
**Checklist:** LW-302 (release gate; builds on LW-301 / gate LW-G01).
**Related:** `docs/baseline-v1-manifest.md`, ADR-0001, LW-206,
`apps/api/livewell/pipeline/runner.py`, `models/inference.py`, `pipeline/handler.py`.

> Scope of THIS plan: the reproducibility sub-claim of LW-302 — "pinned inputs +
> pinned code + pinned model => identical scores." LW-302 as a whole ALSO covers
> deployment, scheduling, API/UI access, failure visibility, and recovery; those
> are a separate step (NBA: "operational reliability, LW-302 -> LW-303") and are
> NOT closed by this replay.

## Why the manifest procedure isn't directly executable

The manifest says "point the pipeline at the frozen prefix and don't re-fetch
yfinance." The current pipeline cannot do that as written:
- `runner.run_instrument` always calls `run_ingestion(...)` first (re-fetches
  yfinance — non-deterministic) and reads/writes via one `LIVEWELL_BUCKET` env
  var with hard-coded `prices/`/`features/`/`signals/` prefixes. No frozen-source
  switch.
- `handler._run_worker` ends with `put_signal(record)` — writes to the live
  `livewell-signals-prod` table.
- `inference.score_signal` loads `get_active_model()` — the registry's current
  active pointer, NOT the pinned `baseline-v1` version.

So a naive replay would re-fetch yfinance, overwrite live prod data, write to the
live table, and possibly score with the wrong model. The approved approach below
is an additive, read-only replay path that avoids all four.

## Approved design decisions (/plan-eng-review)

- **D1 (A):** Replay reads frozen `prices/features/signals` directly and skips
  ingestion + yfinance. It verifies the deterministic claim (pinned inputs +
  pinned model => identical scores), not a yfinance re-fetch (which is
  deliberately non-reproducible — the reason inputs were frozen).
- **D2 (A):** Replay writes NOTHING to DynamoDB and NOTHING to live S3 prefixes.
  Output goes to a scratch location (local file, or `frozen/baseline-v1/replay-<date>/`).
- **D3 (A):** Replay loads the pinned artifact
  `frozen/baseline-v1/model/v20260507T144919.joblib` (force version
  `20260507T144919`), bypassing `get_active_model()`. Clear the `/tmp` model
  cache first so a stale cache can't mask which model ran.
- **D4 (A):** Comparison is STRICT. Per `signal_id`, require exact match on
  `direction`, `signal_valid`, `model_version`, and exact `Decimal(str(score))`.
  Any mismatch is investigated (`/investigate`), not tolerated. Library-version
  drift surfacing here is a legitimate finding, not noise to hide.

## Step 0 — Dependency pinning check (do FIRST, before any replay)

The model artifact is a joblib pickle from 2026-05-07. `uv.lock` (written
2026-06-03) and the current venv agree:
`sklearn 1.8.0, numpy 2.2.6, scipy 1.17.1, joblib 1.5.3, python 3.12`.
But that is not yet proven to match the TRAINING environment.

1. Load the artifact and read any embedded version metadata
   (`sklearn.__version__` baked into the pickle, `InconsistentVersionWarning`
   on load). Record what the artifact expects vs. what is installed.
2. If a warning or mismatch appears, STOP and record it as the first LW-302
   finding (reproducibility is library-sensitive) before proceeding.
3. If clean, proceed to the replay.

## Replay procedure (read-only, non-destructive)

Run locally against `livewell-data-prod` frozen prefix (read-only). No MFA
writes, no infra, no live-table or live-prefix writes.

1. **Checkout pinned code:** `git checkout baseline-v1` (tag e5ec61e), or run the
   replay script with that tree.
2. **Read frozen inputs:** load `frozen/baseline-v1/signals/{instrument}/1d/*.parquet`
   (the frozen signal rows are the scoring input — mirrors `_read_latest_signal`,
   but pointed at the frozen prefix, read-only). Do NOT call `run_ingestion`,
   `run_features`, or `run_signals`.
3. **Pin the model (D3):** download `frozen/baseline-v1/model/v20260507T144919.joblib`
   to a clean cache path; load it directly; do not consult the active-model pointer.
4. **Re-score:** build the feature vector and `predict_proba` for each frozen
   signal row, reproducing the `score_signal` math with the pinned model.
5. **Write to scratch (D2):** emit the replayed records to a local JSON file
   (e.g. `/tmp/lw302-replay-<date>.json`) or a `replay-<date>/` S3 subprefix —
   never the live table or live prefixes.
6. **Diff strict (D4):** join replay vs `frozen/baseline-v1/results/signals-export.json`
   on `signal_id`; assert exact equality on direction, signal_valid,
   model_version, and Decimal(str(score)). Report: N matched, N mismatched, and
   for any mismatch the field + both values.

## Pass / fail

- **Pass:** every `signal_id` matches exactly. Record evidence (counts, library
  versions, scratch artifact path) and propose the reproducibility sub-claim of
  LW-302 verified.
- **Fail/mismatch:** do NOT mark verified. Open `/investigate` on the mismatch
  (most likely library drift or active-vs-pinned model). The mismatch is itself a
  valuable LW-302 finding and feeds LW-206 (which must reproduce Arm A anyway).

## Explicit non-goals (so the gate isn't over-claimed)

- Does NOT re-exercise ingestion / yfinance (pinned inputs by design).
- Does NOT verify deployment, scheduling, API/UI access, failure/recovery —
  that's the LW-302 operational-reliability step, tracked separately.
- Writes nothing to live prod; creates no infrastructure.

## Cost

Negligible AWS cost (hundreds of S3 GETs + ~65 MB egress if run locally = well
under US$0.01; no DynamoDB, no compute beyond the local machine). Effort: ~30-45
min CC to implement + run; add diagnosis time only if a mismatch surfaces.

## GSTACK REVIEW REPORT

| Section | Finding | Decision | Status |
|---|---|---|---|
| Step 0 Scope | Verification task, reuse pipeline, no parallel harness | — | agreed |
| 1 Architecture | No frozen-source switch; naive replay re-fetches yfinance + overwrites live | D1: A | approved |
| 1 Architecture | Replay would write to live DynamoDB signals table | D2: A | approved |
| 2 Code Quality | Scoring uses active model, not pinned baseline-v1 version | D3: A | approved |
| 3 Test | No defined comparison method / tolerance | D4: A (strict) | approved |
| 4 Performance | None — one-time low-volume read | — | no issues |

Reviewed by: /plan-eng-review (interactive, prose-fallback mode), 2026-09-27.
Mode: FULL_REVIEW. Outcome: approach approved; execution pending user go-ahead.

# LW-206 Ablation Notebook — Target Sketch

**Status:** Design sketch for the Track B research notebook (not yet built)
**Date:** 2026-09-13
**Related:** LW-206 (gates LW-G05/06/07), LW-107 (leakage-safe clock),
LW-108 (join protocol), LW-301 (`baseline-v1`), ADR-0001,
`docs/research/congressional-disclosure-limitations.md`.

> Goal: answer one question honestly — does the congressional feature improve the
> frozen NADEX baseline? Everything below serves that, nothing more.

## Inputs

- **Frozen baseline (Track A):** `s3://livewell-data-prod/frozen/baseline-v1/`
  — pinned prices/features/signals, model `rf_tuned@20260507T144919`, and the
  results export. This is the fixed comparison target; do not re-fetch prices.
- **Congressional disclosures (Track B pull):** normalized rows from the one-time
  bounded Quantgress pull, each carrying: transaction date, **filing-availability
  date**, owner/filer, asset text, resolved instrument(s) + confidence, value
  range. Filing-availability date is mandatory (LW-107).

## Steps

1. **Load baseline folds.** Reconstruct the exact walk-forward folds used for
   `baseline-v1` so the comparison is apples-to-apples. Same instruments, same
   dates, same model.
2. **Build the congressional feature (point-in-time).** For each scoring date `t`
   and instrument, aggregate only disclosures whose **filing-availability date <= t**
   (never transaction date). Apply recency weighting / time-decay (LW-106).
   Distinguish transaction age from disclosure age. Use value ranges/midpoints
   with explicit uncertainty — no false precision.
3. **Join to the baseline feature frame** on (date, instrument), leakage-safe
   (LW-108). Instruments with no mapped disclosures get a null/zero feature, not
   a dropped row. Forex has no direct feature in v1.
4. **Declare the retention metric BEFORE evaluating** (win rate and/or EV, plus a
   calibration/stability guard). Write it down first; do not pick the metric that
   makes the feature look good after the fact.
5. **Run the ablation.** Train/score two arms on the same folds:
   - Arm A: baseline features only (must reproduce `baseline-v1` results).
   - Arm B: baseline + congressional feature.
6. **Compare.** Report the declared metric for A vs. B per fold and pooled, plus
   calibration and stability. Include a sanity check that Arm A reproduces the
   frozen results (if it doesn't, the harness is wrong, not the signal).

## Decision rule (gates LW-G06/G07)

- **Pass:** Arm B improves the declared metric without unacceptable calibration
  or stability loss -> promote; proceed to build Track B production (LW-W2).
- **Fail:** no improvement, or improvement bought with calibration/stability loss
  -> do not promote; a superseding ADR records the rejection with this evidence.

## Leakage traps to actively check (LW-107)

- Any feature value using a disclosure before its filing-availability date =
  look-ahead. Assert `filing_availability_date <= score_date` on every row used.
- Amendments must not back-date a correction into a period before it was public.
- No survivorship or restatement leakage from the normalized dataset.

## What this notebook is NOT

Not production. No Lambda, no DynamoDB writes, no schedule. A one-time bounded
pull feeds a walk-forward comparison. Production ingest is built only on a pass.

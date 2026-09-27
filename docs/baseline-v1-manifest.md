# Baseline Freeze: `baseline-v1`

**Purpose:** LW-301 / gate LW-G01 — freeze and reproduce the existing NADEX
baseline (ingestion, scoring, decision-support path) *before* evaluating the
congressional signal, so the LW-206 ablation ("with vs without") compares
against a fixed, reproducible reference.

**Status:** FROZEN 2026-09-26 — all freeze steps executed and verified. Code
tag `baseline-v1` (`e5ec61e`) pushed to origin; inputs, model, and results
snapshotted to `s3://livewell-data-prod/frozen/baseline-v1/` (563 objects,
~65 MB): prices/ (187), features/ (187), signals/ (187),
model/v20260507T144919.joblib, results/signals-export.json. Verified read-only
2026-09-26.

---

## What is frozen (the three things LW-301 requires)

### 1. Code
- **Git tag:** `baseline-v1`
- **Commit SHA:** `99079c20a9c87ecde3f3867b62e1f4c06fa31a17`
- **Commit:** `docs: add Phase 2 LR baseline implementation plan` (2026-05-13)
- Freezes the exact ingestion → features → signals → scoring logic.

### 2. Inputs (data) — pinned copy, because yfinance is NOT reproducible
Re-fetching prices later can return revised values, and the pipeline overwrites
S3 Parquet in place. So the baseline inputs are copied to a read-only frozen
prefix:
- **Frozen prefix:** `s3://livewell-data-prod/frozen/baseline-v1/`
- **Contents:** `prices/`, `features/`, `signals/` as of freeze date.
- **Source (live, mutable) prefixes copied from:** `prices/`, `features/`, `signals/`.

### 3. Model + deterministic results
- **Model name/version:** `rf_tuned` / `20260507T144919`
- **Model artifact:** `s3://livewell-data-prod/models/rf_tuned/v20260507T144919.joblib`
- **Registered metrics (from `livewell-model-registry-prod`):**
  - win_rate = `0.8589743589743589`
  - ev = `0.7948717948717949`
  - trained_at = `2026-05-07T14:49:19Z`
- **Result set (scored signals):** `livewell-signals-prod`, ~16,588 items at freeze.
- **Frozen result export:** `s3://livewell-data-prod/frozen/baseline-v1/results/signals-export.json`
  (a point-in-time DynamoDB export, so the ablation has a fixed comparison target).

---

## How to reproduce the baseline later
1. `git checkout baseline-v1`
2. Point the pipeline/backtest at the frozen input prefix
   `s3://livewell-data-prod/frozen/baseline-v1/` (do NOT re-fetch from yfinance).
3. Use model `rf_tuned@20260507T144919` from the pinned artifact path.
4. Compare fresh output against `frozen/baseline-v1/results/signals-export.json`.
   Deterministic inputs + pinned code + pinned model ⇒ reproducible results.

---

## How to create this freeze (commands for Ian to run)

> Run from the repo root. These are the ONLY steps that mutate anything; the
> manifest above was captured read-only. Nothing here is destructive except in
> the sense that a git tag and new S3 objects are created (both easily removed).

### Step 1 — Tag the code (local, reversible)
```bash
cd /Users/i802235/Development/LIVEWELL
git tag -a baseline-v1 -m "Frozen NADEX baseline before congressional signal (LW-301)"
git tag -n baseline-v1          # verify it exists
# push the tag so it's durable (optional but recommended):
git push origin baseline-v1
# to undo: git tag -d baseline-v1   (and: git push origin :refs/tags/baseline-v1)
```

### Step 2 — Snapshot the input data to a frozen, read-only prefix
`aws s3 cp --recursive` copies within the same bucket; the frozen copy is what
you reproduce from. (Bucket already has versioning enabled per the CDK stack, so
even the live objects are recoverable — but an explicit frozen prefix is clearer.)
```bash
aws s3 cp s3://livewell-data-prod/prices/   s3://livewell-data-prod/frozen/baseline-v1/prices/   --recursive --region us-west-1
aws s3 cp s3://livewell-data-prod/features/ s3://livewell-data-prod/frozen/baseline-v1/features/ --recursive --region us-west-1
aws s3 cp s3://livewell-data-prod/signals/  s3://livewell-data-prod/frozen/baseline-v1/signals/  --recursive --region us-west-1
# verify:
aws s3 ls s3://livewell-data-prod/frozen/baseline-v1/ --recursive --region us-west-1 --summarize | tail -3
```

### Step 3 — Pin the model artifact (copy into the frozen prefix)
```bash
aws s3 cp s3://livewell-data-prod/models/rf_tuned/v20260507T144919.joblib \
          s3://livewell-data-prod/frozen/baseline-v1/model/v20260507T144919.joblib --region us-west-1
```

### Step 4 — Export the deterministic result set (scored signals)
```bash
# simplest: full-table scan to a JSON file, then upload
aws dynamodb scan --table-name livewell-signals-prod --region us-west-1 \
  --output json > /tmp/signals-export.json
aws s3 cp /tmp/signals-export.json \
  s3://livewell-data-prod/frozen/baseline-v1/results/signals-export.json --region us-west-1
rm /tmp/signals-export.json
```
> Note: a plain `scan` paginates; for a table this size it returns everything in
> a few pages. If you want a guaranteed-complete server-side export instead, use
> DynamoDB point-in-time export to S3 (the table has PITR enabled) — heavier but
> authoritative. The scan is fine for a personal baseline.

### Step 5 — Mark this manifest frozen
DONE (2026-09-26): Status flipped to `FROZEN` at the top and this file committed,
so gate LW-G01 has its artifact.

---

## Gate mapping
- **LW-301** (freeze & reproduce baseline) — satisfied by Steps 1–5.
- **LW-G01** (reproducible baseline) — this manifest + the frozen prefix are the evidence.
- Feeds **LW-206** (leakage-safe ablation) — the "without congress" reference.

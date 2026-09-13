# Congressional Signal — Notebook-First Research Spike & Track Plan

**Status:** Planning note (informs sequencing; not a scope change to ADR-0001)
**Date:** 2026-09-13
**Related:** ADR-0001, LW-D02/LW-103, LW-107, LW-206, LW-301,
`docs/research/congressional-disclosure-limitations.md` (LW-102),
`docs/research/congressional-disclosure-access.md` (LW-103),
`docs/designs/congressional-trading-signal.md`.

## Why this note

The congressional signal is unproven by design (ADR-0001): it is adopted in
principle and accepted/rejected only by a leakage-safe ablation (LW-206). That
ablation is a **research question**, answerable in a notebook, and does NOT
require the production AWS ingest chain. Building S3 -> Lambda -> DynamoDB before
the ablation risks committing to architecture before the value is demonstrated —
the failure mode ADR-0001 and the office-hours session explicitly warned against.

## Two tracks

### Track A — Finish core LIVEWELL (no congressional signal)
The existing NADEX early-warning workflow, made reproducible.
- **Immediate:** LW-301 baseline freeze (S3 snapshot to `frozen/baseline-v1/`,
  push tag, flip manifest DRAFT->FROZEN). MFA-gated writes (`--profile admin`).
- Independent of every congressional question. Nearly done. Finish it.
- Produces the fixed reference the ablation compares against (gate LW-G01).

### Track B — Congressional signal research spike (notebooks)
Explore in `notebooks/livewell-nadex/` before any production build.
- One-time **bounded** historical pull via the LW-103 recommended tool
  (self-hosted Quantgress), not scheduled automation.
- Normalize -> asset resolution -> recency-weighted aggregation (LW-105/106).
- Point-in-time join keyed on filing-availability date, never transaction date
  (LW-107, LW-108).
- LW-206 ablation: baseline vs. baseline+congress on the same walk-forward folds
  as `baseline-v1`. Declare the retention metric before evaluating.
- **Only if the ablation shows edge** do we build Track B-production
  (LW-201/202/204/208): S3 raw snapshots + canonical CSV, DynamoDB rows + lineage,
  scheduled ingest.

## The gate that orders the tracks

```
Track A: LW-301 (freeze baseline)  ─────────────┐
                                                 v
Track B: pull → normalize → PIT join ──→ LW-206 ablation ──→ [pass?] ──→ build LW-W2 prod
         (can start data wrangling in parallel;    (needs frozen        (else: superseding
          ablation itself waits on LW-301)          baseline)            ADR records rejection)
```

- Track B **data wrangling** (pull/parse/asset-map) can start now, in parallel.
- Track B **ablation** cannot run until Track A's baseline is frozen (LW-206
  depends on LW-301).
- So sequencing self-enforces: finish LW-301, wrangle disclosures in parallel,
  run the ablation once both are ready, build production only on a pass.

## Terms posture for the spike (from LW-103)

- A one-time bounded manual pull is a gentler posture than a daily scheduled
  scraper; it is closer to normal portal use. The commercial-purpose and
  automation-permission questions (LW-103 section 5) still apply but are less
  aggressive for a spike than for production automation.
- Do NOT stand up scheduled automation until the LW-103 follow-ups (commercial-
  purpose classification; automation permission) are resolved.

## What this note does not change

Scope (personal early-warning only), architecture (five-layer, S3/DynamoDB
split), and the accept/reject-by-ablation decision are all unchanged. This is
sequencing guidance: research the signal cheaply before building the chain.

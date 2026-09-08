# ADR-0001: Congressional Activity as a Contextual Signal in Ian's Personal NADEX Early-Warning Workflow

- **Status:** Accepted (implementation deferred behind discovery gates — see Consequences)
- **Date:** 2026-09-06
- **Deciders:** Ian
- **Checklist:** LW-101 (release gate); scope decision LW-D01; source decision LW-D02
- **Related:** `docs/06_roadmap.md`, `docs/05_data_sources.md`, `docs/03_ml_models.md`, `docs/04_pipeline_architecture.md`, `docs/designs/congressional-trading-signal.md`

> First ADR in the repo. Establishes the `docs/adr/` convention: numbered
> `NNNN-title.md`, MADR-style (Status / Context / Decision / Consequences).
> Supersede via a later ADR referencing this one.

---

## Context

LIVEWELL is **Ian's personal NADEX early-warning workflow** — a decision-support
system that surfaces candidate NADEX trades, presents the information needed to
assess them, and leaves the review and trading decision to Ian. It is **not** a
product: multi-user access, external customers, subscriptions, and
commercialization are explicitly out of scope (LW-D01, LW-902). This ADR does not
change that.

LIVEWELL already runs an operational daily pipeline over a mixed NADEX universe —
**stock indices** (US 500, NASDAQ 100, Russell 2000, Dow Jones, Nikkei 225),
**metals/energy** (Gold, Crude Oil, Natural Gas), and **forex** (EUR/USD and 10
other pairs) — ingesting prices, computing indicators, generating rule-based
signals, scoring with a registered model, and persisting to DynamoDB on a
weekday schedule (verified 2026-09-06).

The decision: adopt **US congressional/executive trading disclosures** as **one
additional contextual signal within that existing workflow** — information that
may help flag a candidate NADEX trade, alongside the existing technical signals.
It is not a new strategy and not a standalone trade trigger (LW-900, LW-901 are
out of scope).

### Data reality (verified this session and via research)

- **No single official machine-readable feed.** Disclosures live in three
  official systems: House Clerk Financial Disclosure portal, Senate eFD, and OGE
  (executive). `unitedstates/congress-legislators` holds legislator/committee
  metadata only — **no financial disclosures**.
- **Lagged and sparse.** STOCK Act filing windows are 30 days (Senate) / 45 days
  (House), often longer. This is why the backtest clock must key on
  **public-filing-availability date, not transaction date** (LW-107).
- **Equity-focused.** Disclosures are stock trades. They map **near-directly to
  the stock-index instruments** LIVEWELL trades, moderately to commodities,
  weakly to forex. The mixed universe is what makes the signal plausible.
- **Source:** the disclosure source is Ian's decision (LW-D02); access method
  and terms are confirmed separately (LW-103). This ADR does not pin a specific
  vendor.

### The core question

Whether congressional activity carries predictive edge for daily NADEX contracts
is an **open empirical question**, not an assumption. It is answered by a
leakage-safe ablation (LW-206), not asserted here.

---

## Decision

1. **Scope: congressional activity is a contextual signal inside the existing
   personal early-warning workflow.** It informs candidate alerts that Ian
   reviews. Not a product, not a standalone trigger, not a strategy replacement.

2. **Architecture: no change.** Reuse the settled five-layer pipeline and the
   S3 (analytical) / DynamoDB (operational) split. A daily ingestion step
   normalizes disclosures to CSV on S3, aggregates them, and joins to the
   existing feature pipeline.

3. **Signal construction: sector/index rollup (office-hours bridge A).** Map each
   disclosed ticker → sector → the NADEX instrument(s) it informs (tech buying →
   NASDAQ 100 / US 500; energy → Crude Oil / Nat Gas; materials → Gold; etc.),
   with recency-weighted (time-decay) aggregation. Ticker→instrument mapping uses
   a curated, version-controlled lookup (office-hours choice B), optionally seeded
   offline from a public sector source. Forex gets no direct feature in v1.

4. **Reuse tooling; do not hand-write parsers.** Use a maintained
   extract/normalize pipeline for the chosen source.

5. **Accept/reject by leakage-safe ablation (LW-206, gates LW-G05/06/07).**
   Compare the workflow's candidate signals **with and without** the
   congressional feature, on the same walk-forward folds as the frozen baseline
   (LW-301), using a filing-availability-dated clock (LW-107). Promote only on
   demonstrated improvement without calibration/stability loss.

6. **Implementation deferred behind discovery gates.** The signal is adopted in
   principle; building it follows the LW-W1 discovery contract (schema/lineage,
   asset resolution, leakage-safe clock, join+ablation protocol) and confirmed
   data access (LW-103).

---

## Consequences

### Positive
- Keeps the workflow personal and focused; no product surface area.
- No architectural change; reuses the operational pipeline and storage split.
- The strong congress→index bridge gives the signal a real chance of edge on the index instruments.
- Edge is proven empirically (leakage-safe ablation) before it influences alerts.

### Negative / risks
- **Signal-fit risk:** lagged, sparse, equity-oriented data may show no edge; ablation may reject it — a valid outcome.
- **Leakage risk:** using transaction date instead of filing-availability date would fabricate look-ahead edge. LW-107 mandates the filing-availability clock.
- **Source fragility:** disclosure sources can change format; the daily ingest needs idempotency, source snapshots, and staleness handling (LW-201, LW-208).
- **Asset-resolution ambiguity:** ticker/asset matches are imperfect and need confidence levels + a manual review queue (LW-105, LW-203).

### Acceptance test (promotion gate)
Leakage-safe ablation (LW-206) shows the congressional feature improves the
workflow's candidate quality (win rate and/or EV) on filing-availability-dated
walk-forward folds without unacceptable calibration or stability loss. If not,
the feature is not promoted and a superseding ADR records the rejection with its
evidence.

---

## Research limitations to document separately (LW-102)
Reporting delay, transaction value ranges (disclosures are ranges, not exact
amounts), ambiguous asset matches, and the distinction between an *observed
disclosure* and a *tested predictive signal*.

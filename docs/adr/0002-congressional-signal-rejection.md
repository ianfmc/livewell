# ADR-0002: Reject the Congressional-Trading Signal — Do Not Acquire Real Data

- **Status:** Accepted. **Supersedes ADR-0001.**
- **Date:** 2026-10-23
- **Deciders:** Ian
- **Checklist:** closes LW-110 / LW-112 / LW-206 / LW-113 (governance revisions 208–209)
- **Related:** `docs/adr/0001-congressional-trading-signal.md` (superseded),
  `docs/research/congressional-disclosure-limitations.md`,
  `docs/research/congressional-disclosure-access.md`,
  `docs/research/lw304-backtest-validation-plan.md`,
  the LW-104–108/111 design specs under `docs/superpowers/specs/2026-10-16-*-design.md`,
  the invented-fixture harness `notebooks/livewell-nadex/research/congress/`.

> Supersedes ADR-0001 per the `docs/adr/` convention (ADRs are immutable; a later
> ADR records the change). ADR-0001 adopted congressional activity as a contextual
> signal *in principle*, with edge left as an explicit empirical question. This ADR
> records the answer: the signal is rejected on evidence, and no real data will be
> acquired.

---

## Context

ADR-0001 (2026-09-06) adopted US congressional/executive trading disclosures as a
*contextual signal* inside Ian's personal NADEX early-warning workflow, explicitly
stating that whether the signal carries predictive edge is "an open empirical
question, not an assumption," to be answered by a leakage-safe ablation rather than
asserted. Implementation was deferred behind discovery gates (schema, asset
resolution, leakage-safe clock, join/ablation protocol) and confirmed data access.

Over the subsequent research-design work, LIVEWELL built the full discovery
apparatus — all on invented fixtures, no real data:

- **LW-104** canonical disclosure schema + lineage
- **LW-105** asset resolution (confidence + manual-review)
- **LW-107** leakage-safe clock (point-in-time on filing-availability date)
- **LW-106** aggregation experiments (ticker / sector / market-factor / consensus / imbalance)
- **LW-108** feature join + baseline ablation protocol
- **LW-111** invented sample records + normalization/point-in-time checks

That apparatus existed precisely to make the edge question answerable rigorously.
In an `/office-hours` premise challenge (2026-10-22), it answered it — without any
vendor spend or legal exposure.

## Decision

**Reject the congressional-trading signal. Do not acquire real congressional
disclosure data. Close the real-data track (LW-110/112/206/113).** Stop at the
research-design stage. No vendor is engaged, no commercial-purpose legal question
need be resolved, and no production integration occurs.

## Rationale

1. **The only lag-surviving mechanism is granularity-mismatched to LIVEWELL's
   instruments.** The STOCK Act 30–45+ day filing lag means "trade alongside
   Congress before the move" is not available — the move has already happened by
   the time the public can legally observe the trade. The one mechanism that
   *can* survive the lag is a **publication-echo**: the disclosure's publication is
   itself a fresh catalyst that re-disseminated copy-traders act on. But that
   catalyst is **single-equity** — it moves the specific disclosed ticker.
   LIVEWELL trades **forex pairs and stock indices**. The ADR-0001 sector→index
   rollup (bridge A) dilutes any single-name catalyst across a broad index to a
   rounding error. The mechanism behind documented "mimic Congress" outperformance
   operates at exactly the granularity LIVEWELL's instrument universe averages
   away. This is inherent to binary-options-on-indices vs. single-equity echoes —
   not an engineering gap that more work could close.

2. **The documented limitations already predict a weak-to-null result**
   (`congressional-disclosure-limitations.md`): lagged, value-ranges-not-amounts,
   sparse and incomplete by construction, equity-oriented (maps near-directly only
   to indices, weakly to forex; forex gets no v1 feature).

3. **The baseline to be improved is already underwater.** LW-304 validated the
   existing surface and found an 18.9% win rate with negative average edge on the
   naive next-day-close rule. Demonstrating that a weak, lagged, granularity-
   mismatched exogenous feature improves an already-underwater baseline is
   implausible.

4. **Cost/risk is front-loaded; payoff is speculative and the evidence points to
   null.** Acquisition would require resolving the unresolved commercial-purpose
   question, onboarding a paid vendor (Quiver + an alternative), and building the
   acquisition + ablation — weeks of effort plus standing legal/terms exposure —
   to learn an answer the evidence already indicates. LIVEWELL exists to raise the
   probability of winning trades; this signal is not expected to, for its
   instruments. Declining the bet on evidence is the correct outcome.

## Consequences

### Positive
- No vendor spend, no commercial-purpose legal exposure, no acquisition/retention
  obligations. The edge question was answered cheaply and rigorously.
- The leakage-safe apparatus did its job: it enabled a trustworthy "no" rather than
  a guess. A null reached on evidence is a successful research outcome.

### Neutral / preserved
- All design artifacts remain in the repo as the honest record of a rigorously
  considered idea that was declined: the LW-104–108/111 specs, the invented-fixture
  harness, the frozen `baseline-v1`, the ablation *protocol*, and the limitations/
  access research. None is deleted.
- The planned November House/Senate outreach may lapse; no live data is intended.

### Negative / risks
- If the premise were wrong (the index-dilution argument under-estimates a real
  index-level signal), LIVEWELL forgoes it. Accepted: the evidence and the
  underwater baseline make this low-probability, and the decision is reversible.

### Reversibility
- This rejection is **reversible without rework**. If LIVEWELL later adds
  **single-equity instruments**, or NADEX offers single-stock contracts, the
  granularity mismatch disappears and the premise flips back to live. The
  preserved apparatus can be reactivated at that point; a future ADR would
  supersede this one.

## Acceptance

Governance approved the closure (revisions 208–209) and directed that the
rejection be recorded as this new immutable ADR-0002 superseding ADR-0001, rather
than by editing ADR-0001.

# Congressional Disclosure Limitations

**Checklist:** LW-102 (release gate; gate LW-G12)
**Status:** Research note — informs signal design, not a promotion decision
**Date:** 2026-09-13
**Related:** `docs/adr/0001-congressional-trading-signal.md` (ADR-0001),
source-access decision LW-D02 / task LW-103, leakage-safe timing rules LW-107,
ablation LW-206, frozen baseline LW-301.

> Companion to ADR-0001. The ADR decides congressional activity is a *contextual
> signal* inside Ian's personal NADEX early-warning workflow. This note records
> what that data can and cannot tell you, so the signal is built and validated
> honestly. It does not assert the signal has edge — that is LW-206's job.

---

## Purpose

US congressional financial disclosures report **stock transactions by members of
Congress (and covered staff), after the fact, as value ranges.** They can tell
you *that* a covered filer reported buying or selling an asset, roughly *how
much* (as a bracket), and *when* the trade and the filing happened.

They **cannot** tell you: intent, conviction, non-covered accounts, trades below
the reporting threshold, real-time positioning, or anything predictive on their
own. A disclosure is a lagged, coarse, public record — not a trading signal until
proven to be one. In LIVEWELL it is one input that may help flag a candidate
NADEX trade for Ian's review, alongside the existing technical signals.

## Timing — three distinct clocks

The single most important distinction in this data. Conflating these dates
fabricates predictive edge that does not exist.

1. **Transaction date** — when the member actually traded. Earliest, and **not
   knowable in real time.**
2. **Filing / publication date** — when the report became public in the House
   Clerk FD portal or Senate eFD system. This is the **first moment the
   information is actually available to anyone outside the filer.**
3. **LIVEWELL observation date** — when our daily ingest first retrieved and
   normalized the record. Equal to or later than the publication date (ingest lag,
   source staleness, amendments).

**Only dates 2 and 3 are usable without look-ahead. LW-107 mandates keying the
backtest clock on filing-availability (date 2), never transaction date (date 1).**

### Reporting deadlines (official sources)

Under the STOCK Act, a covered Periodic Transaction Report (PTR) is due **within
30 days of the filer receiving notification of a transaction, but no later than
45 days after the transaction** (transactions over \$1,000). The law permits no
extensions to the PTR window. Annual Financial Disclosure reports are separately
due **May 15**.

- House: Committee on Ethics — PTR form and filing instructions
  (`https://ethics.house.gov/`); FD FAQ confirming the May 15 annual deadline
  (`https://ethics.house.gov/faqs`).
- Senate: Select Committee on Ethics — financial disclosure program and eFD
  system (`https://www.ethics.senate.gov/public/index.cfm/financialdisclosure`,
  `https://efd.senate.gov`).
- Executive branch: US Office of Government Ethics — OGE Form 278-T periodic
  transaction report (`https://www.oge.gov/`). **Out of scope for v1** (LW-D02).
- Congressional Research Service, *The STOCK Act, Insider Trading, and Public
  Financial Reporting by Federal Officials*, R42495
  (`https://www.everycrsreport.com/reports/R42495.html`) — authoritative summary
  of the 30/45-day rule.

**Practical consequence:** the information reaches the public **30 to 45+ days
after the trade**, often longer with late filings and amendments. Any market
reaction to the trade itself has usually already happened by the time we can
legally observe the disclosure. The tested hypothesis is therefore about
**edge remaining at publication time**, not edge at trade time.

## Data limitations

- **Value ranges, not amounts.** Transactions are reported in brackets (e.g.
  \$1,001–\$15,000, \$15,001–\$50,000, …). Treating a bracket as a precise dollar
  figure invents false precision. Aggregation must use ranges or bracket midpoints
  with explicit uncertainty, never point estimates presented as exact.
- **Ambiguous assets.** Free-text asset descriptions and inconsistent ticker
  usage make asset→instrument resolution imperfect. Requires confidence levels and
  a manual review queue (LW-105, LW-203); low-confidence matches must not silently
  enter features.
- **Amendments and duplicates.** Filers amend prior reports; the same transaction
  can appear across filings. Ingest must be idempotent, snapshot sources, and
  resolve amendment supersedence (LW-201, LW-202) — without back-dating a
  correction into a period before it was public.
- **Missing / late / non-covered records.** Some trades are filed late, some
  accounts and instruments are not covered, and sub-threshold trades are not
  reported. The dataset is **sparse and incomplete by construction** — absence of
  a disclosure is not absence of activity.
- **Source coverage.** v1 covers House Clerk FD + Senate eFD only (LW-D02).
  Executive-branch (OGE) disclosures are excluded. Coverage gaps bias any
  aggregate and must be stated whenever the feature is interpreted.
- **Equity-oriented.** Disclosures are stock trades. They map near-directly to
  LIVEWELL's stock-index instruments, moderately to commodities, weakly to forex.
  Forex gets no direct feature in v1 (ADR-0001).

## Research implications

- **Prevent look-ahead bias.** A disclosed trade is **historical information as of
  its publication date**, not a live opportunity. Every feature value must be
  computable using only records whose filing-availability date is on or before the
  point-in-time being scored (LW-107). This is the primary correctness constraint
  on the whole signal.
- **Observed disclosure ≠ tested signal.** That a filer traded an asset is an
  observation. Whether that observation improves next-day NADEX candidate quality
  is an empirical question, unproven until LW-206.
- **Lag reframes the hypothesis.** Because the public sees the trade 30–45+ days
  late, the signal is not "trade alongside Congress." It is "does the *public
  disclosure event*, at the time it becomes available, carry residual predictive
  context for daily NADEX contracts on the mapped instruments?"

## Validation required

This note documents limitations; it does not decide value. The congressional
feature is promoted **only if** the leakage-safe ablation (LW-206, gates
LW-G05/06/07) shows it improves the workflow's candidate quality (win rate and/or
EV) against the frozen baseline (LW-301), on filing-availability-dated
walk-forward folds (LW-107), **without unacceptable calibration or stability
loss.** The retention metric is declared before evaluation. If the evidence does
not support it, the feature is not promoted and a superseding ADR records the
rejection.

## References

- **ADR-0001** — Congressional activity as a contextual signal
  (`docs/adr/0001-congressional-trading-signal.md`).
- **LW-D02 / LW-103** — source-access decision: community extract-and-normalize
  tooling over official House Clerk FD + Senate eFD, normalized to canonical CSV
  on S3; access method and terms confirmed in LW-103. OGE out of scope for v1.
- **LW-107** — leakage-safe backtest clock keyed on public filing-availability
  date, not transaction date.
- **LW-206 / LW-301** — baseline-versus-augmented ablation against the frozen
  `baseline-v1` reference.
- Official reporting-deadline sources cited inline under **Timing** above
  (House Ethics, Senate Ethics/eFD, OGE, CRS R42495).

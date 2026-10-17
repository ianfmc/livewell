# LW-107 — Leakage-Safe Backtest Clock

- **Checklist:** LW-107 (**critical**; release gate). Discovery-contract item of LW-W1.
- **Status:** DRAFT design — for Ian's review. Design document only.
- **Date:** 2026-10-16
- **Depends on (done):** LW-104 (canonical schema), LW-101 (ADR-0001), LW-635.
- **Related:** `docs/superpowers/specs/2026-10-16-disclosure-schema-design.md`,
  `docs/research/congressional-disclosure-limitations.md` (three clocks),
  `docs/adr/0001-congressional-trading-signal.md`.
  Downstream: LW-108/LW-206 (join + ablation), LW-111 (fixtures must obey this clock).

> **Scope guardrail (governance, rev 183).** Design + invented-fixtures only. No
> real disclosure acquisition; no production integration. LW-110 blocked;
> LW-112/LW-113 deferred. All examples are invented and clearly labeled.

---

## 1. Purpose

Define the rule that decides, for any scoring date `t` and instrument, **which
disclosure records are allowed to contribute to a feature value** — such that a
feature computed "as of `t`" uses only information that was **publicly available
on or before `t`**. This is the single most important correctness constraint on
the whole congressional signal. Get it wrong and the ablation (LW-206) measures
fabricated edge.

This document defines the *clock policy*. It does not build features (LW-108) or
resolve amendments (LW-201/202); it defines the time rule those obey.

## 2. The leakage hazard, concretely

From LW-102, three clocks exist per record (LW-104 fields in parentheses):

1. **transaction date** (`transaction_date`) — when the member traded. **Not
   knowable to the public in real time.**
2. **public-availability** (`public_availability_at`) — first moment the document
   was publicly retrievable. **The only honest "we could have known" moment.**
3. **observation** (`observed_at`) — when LIVEWELL's ingest first saw it.

STOCK Act lag means (2) trails (1) by **30–45+ days**, often more. Keying a
feature on `transaction_date` would let a backtest "trade" on information that
would not be public for weeks — pure look-ahead leakage.

**Invented illustration (not real data):**
- A trade dated **2026-02-03** becomes public **2026-03-11**.
- Scoring date **t = 2026-02-10**: the trade is **invisible** (public date is in
  the future). It must not touch any feature for `t`.
- Scoring date **t = 2026-03-15**: the trade is now public and eligible.

Keying on `transaction_date` would wrongly make the record visible on 2026-02-10.

## 3. The clock rule (normative)

> **Rule C1 — point-in-time visibility.** A disclosure record `r` is **eligible**
> to contribute to a feature value computed as of scoring timestamp `t` **iff**
> `r.public_availability_at <= t`. No feature may reference `r.transaction_date`,
> `r.observed_at`, or any amendment of `r` published after `t` for any purpose
> that affects the value at `t`.

Corollaries:

- **C1a — transaction_date is descriptive only.** It may be used *inside* an
  eligible record (e.g. transaction-age weighting in LW-106), but **never** as
  the eligibility clock.
- **C1b — observed_at is an operational lower bound, not the clock.** Ingest lag
  means `observed_at >= public_availability_at`. The backtest clock keys on
  availability (what *could* have been known), not on when our pipeline happened
  to fetch it. (`observed_at` is used only for operational diagnostics and to
  detect ingest lag, not for feature eligibility.)
- **C1c — amendments are point-in-time.** An amended value is eligible only from
  **its own** `public_availability_at` forward. Before that, the record's
  then-current public version applies. (Supersedence *mechanics* are LW-201/202;
  this clock rule is the constraint they must satisfy.)

## 4. Availability-time precision and the fallback policy

`public_availability_at` is sometimes known only to the day (LW-104 carries
`public_availability_precision ∈ {timestamp, date}`). Policy:

> **Rule C2 — conservative availability.** When precision is `date` (no intraday
> publish timestamp), treat the record as available at **end of that calendar day
> in US Eastern time**, i.e. eligible for scoring timestamps `t` strictly after
> that day. A same-day scoring run may **not** use a record whose availability is
> only known to that same date.

Rationale: if we only know "published sometime on 2026-03-11," assuming it was
available at 00:00 could let an early-in-the-day score use something that only
posted that afternoon. Pushing eligibility to the **next** scoring boundary is
the leakage-safe choice. This costs at most ~1 day of latency and never
fabricates edge.

> **Rule C2a — no publish signal at all.** If a source gives no publish
> timestamp and no reliable publication date (only a `filing_date`), use
> `public_availability_at = filing_date` **plus a configurable safety offset
> `D_pub` (default 1 trading day)**, with `precision = date`, then apply C2. The
> offset is a single named parameter, recorded per run, not hidden in code.

## 5. Scoring boundary and timezone

- LIVEWELL's existing pipeline scores on a **daily (end-of-day) weekday**
  cadence. The scoring timestamp `t` for a given trading day is its **decision
  cutoff** (the moment features are frozen for that day's candidate).
- All three clocks are normalized to **UTC** in storage (LW-104), but the
  **calendar-day** reasoning in C2 uses **US Eastern** (the market/filing
  calendar), then converts. This avoids a UTC midnight splitting a US trading day.
- Weekends/holidays: a record that becomes available on a non-trading day is
  eligible for the **next** trading day's `t`.

## 6. Lookback window vs. the lag (addresses ADR open question #1)

Two distinct time spans, not to be conflated:

- **Eligibility** (Rule C1) is a hard *point-in-time gate* — binary, no window.
- **Lookback / decay** is a *feature-shaping* choice (LW-106): among eligible
  records, how far back to include and how to weight them. Because the public
  only sees trades 30–45+ days late, the signal hypothesis is about **residual
  edge at publication time**, so the lookback is measured in **availability
  time**, not transaction time:

> **Rule C3 — availability-time lookback.** A feature's lookback window `W` selects
> eligible records with `t - W <= public_availability_at <= t`. Transaction-age
> may additionally weight them (LW-106), but the window itself is defined on
> availability time. `W` is a named tunable set during the ablation, not fixed here.

## 7. What this guarantees (and what it does not)

Guarantees:
- No feature value at `t` depends on any fact not public by `t`.
- Re-running a backtest with a later data snapshot cannot change a past `t`'s
  value, **provided** amendments are applied point-in-time (C1c) — i.e. the clock
  is **reproducible** and **snapshot-stable**.

Does **not** guarantee (out of scope here):
- That the signal has edge (LW-206).
- Correct amendment/dedup resolution mechanics (LW-201/202) — this doc only
  constrains their *timing*.
- Completeness of the data (sparse/late filings; LW-102).

## 8. Verification approach (design-time, invented fixtures only)

How LW-111's fixtures will prove this clock holds — no real data:

1. **Future-availability exclusion.** A record with `public_availability_at > t`
   contributes **zero** to the feature at `t`.
2. **Boundary (C2).** A `date`-precision record dated `t` is excluded from a
   same-day `t` and included for the next scoring boundary.
3. **Amendment point-in-time (C1c).** Original value applies between its
   availability and the amendment's availability; amended value only after.
4. **Snapshot stability.** Computing the feature for a past `t` from two
   different ingest snapshots yields identical values when amendments are applied
   point-in-time.
5. **Transaction-date trap.** A deliberately constructed record where keying on
   `transaction_date` would include it but C1 excludes it — the test asserts
   exclusion.

These become executable checks in LW-111's notebook against invented records.

## 9. Parameters (named, recorded per run)

| Param | Default | Meaning |
|---|---|---|
| `D_pub` | 1 trading day | Safety offset when only `filing_date` is known (C2a). |
| `W` | TBD in ablation | Availability-time lookback window (C3). |
| `calendar` | US Eastern | Calendar for day-precision reasoning (C2/§5). |
| `score_cutoff` | existing EOD cadence | Decision cutoff defining `t`. |

## 10. Acceptance-criterion checklist (LW-107)

| Required | Where |
|---|---|
| Clock keys on public filing availability, not transaction date | Rule C1 + C1a (§3) |
| Define point-in-time eligibility | Rule C1 (§3) |
| Handle availability precision / unknown publish time | Rules C2, C2a (§4) |
| Separate lookback from the filing lag | Rule C3 (§6) |
| Leakage-safety verifiable | §8 (fixture checks for LW-111) |

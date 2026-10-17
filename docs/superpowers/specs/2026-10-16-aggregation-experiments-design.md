# LW-106 — Aggregation Experiments

- **Checklist:** LW-106 (medium; not a release gate). Milestone LW-B1.
  Discovery-contract item of LW-W1. Eng-reviewed via `/plan-eng-review`.
- **Status:** DRAFT design — for Ian's review. Design document only.
- **Date:** 2026-10-16
- **Depends on (done):** LW-104 (schema), LW-105 (asset resolution), LW-107
  (leakage-safe clock), LW-101 (ADR-0001), LW-635.
- **Related:** `docs/superpowers/specs/2026-10-16-disclosure-schema-design.md`,
  `...-asset-resolution-design.md`, `...-leakage-safe-clock-design.md`,
  `docs/designs/congressional-trading-signal.md` (bridge A),
  `docs/research/congressional-disclosure-limitations.md`,
  `docs/research/lw206-ablation-notebook-sketch.md`.
  Downstream: LW-108 (join + ablation protocol), LW-206 (ablation).

> **Scope guardrail (governance, rev 187).** Design + invented-fixtures only;
> notebook-only outputs. No real disclosure acquisition; no production
> integration. LW-110 (access gate) blocked; LW-112/LW-113 deferred. All examples
> are invented and clearly labeled. This defines *candidate* features; whether any
> has edge is LW-206's question, not asserted here.

---

## 1. Purpose

Define, as runnable experiments, the five aggregation axes that turn resolved,
eligible disclosure records into **per-(instrument, date) candidate features**:
ticker, sector, market-factor, cross-filer consensus, and purchase/sale
imbalance. All five are defined (eng-review scope decision A — define now rather
than discover complexity later). LW-108 selects among them and runs the ablation.

## 2. Shared core (eng-review A1 — single source of timing + weighting)

Every axis is a pure function over the **same** eligible, recency-weighted record
set. No axis re-implements timing. Two primitives, taken verbatim from LW-107:

- `eligible(t, W)` — records with `t - W <= public_availability_at <= t`
  (LW-107 Rule C1 eligibility + C3 availability-time lookback). Never
  `transaction_date`. Amendments applied point-in-time (C1c).
- `weight(record, t)` — recency decay on **transaction age**
  `a = t - transaction_date`: `w = 0.5 ** (a / H)`, half-life `H`.
  `H` is a **named ablation tunable** (default below), never a literal in a
  formula (eng-review Q4).

  **Why transaction age, not availability age (hypothesis — Ian):** the
  *economic* signal ages from when the trade happened, not from when the filing
  became public. A sale is maximally informative near the trade date and decays
  thereafter, regardless of filing lag. This is leakage-safe: **eligibility is
  still gated on `public_availability_at` (C1)** — a record cannot enter
  aggregation until it is public — and only *after* that gate does the weight
  read `transaction_date`, which LW-107 Rule C1a explicitly permits as a
  descriptive field (never as the eligibility clock). The two ages are distinct
  and both are used: availability age gates and windows (C1/C3); transaction age
  weights. Whether transaction-age decay beats availability-age decay is itself an
  ablation question (LW-206); `H` and the choice of decay basis are tunable.

Only records that **contribute** per LW-105 Rule R1 (resolved, confidence
≥ τ_auto, not needing review) *and* map to a LIVEWELL instrument enter
aggregation. Resolved-but-unmapped and unresolved contribute nothing.

## 3. Shared value-range rule (eng-review A3 — decide once)

Amounts are brackets, never points (LW-102). Any axis using magnitude consumes
`[amount_min, amount_max]`. **Convention (v1):** use the bracket **midpoint**
`m = (amount_min + amount_max) / 2` for the point estimate **and** carry the
half-width `u = (amount_max - amount_min) / 2` as an uncertainty companion on the
feature. No axis presents a midpoint as an exact figure; the uncertainty travels
with it so LW-206 can weight or stress it. A single helper computes `(m, u)`;
imbalance and market-factor both use it.

## 4. Output contract (eng-review A2 — per-(instrument, date) grain)

Every axis emits `feature_name -> {value, uncertainty?}` keyed on
`(instrument, date)`, where `date` is the scoring day whose cutoff is `t`.
Instrument-class applicability follows ADR bridge A: **indices** strong,
**commodities** medium, **forex** no direct feature in v1. An axis that would
otherwise produce a non-per-instrument scalar (market-factor, consensus) is
routed to instruments via the curated ticker→sector→instrument map before
emission.

**Sparse-period rule (eng-review T3):** when `eligible(t, W)` has no contributing
record for an instrument, every axis emits a **defined neutral value** (0 for
signed/imbalance axes, 0-count for count axes) with `uncertainty = None` — never
a crash and never a silent null that could poison the LW-108 join.

## 5. The five axes

Notation: `E` = contributing eligible records for (instrument, date) at cutoff
`t`; `w_i = weight(record_i, t)`; `(m_i, u_i)` = value-range midpoint/half-width;
`dir_i ∈ {+1 buy, -1 sell}` from `tx_type` (purchase→+1; sale/sale_partial/
sale_full→-1; exchange→0).

### 5.1 Ticker aggregation
Weighted signed activity for the **specific resolved ticker(s)** routed to the
instrument. `value = Σ_i w_i * dir_i` over `E` restricted to the instrument's
constituent tickers. Count companion `n = |E|`. Captures "which exact names in
this index were traded, and net which way."

### 5.2 Sector rollup
Same reduction as ticker but grouped by **sector** then routed to instrument via
the curated map (ADR bridge A's core path). `value = Σ_i w_i * dir_i` over all
`E` mapping to the instrument through its sector(s). This is the primary
congress→index bridge feature.

### 5.3 Market-factor (eng-review A4 = A: factor-bucket over mapped equities only)
Group contributing records into **factor buckets** (e.g. size/style buckets
assigned in the curated map: large-cap / small-cap / growth / value) and emit the
weighted signed activity per bucket, routed to the instruments that bucket
informs (small-cap→Russell 2000; large-cap/broad→US 500/Dow; etc.).
`value_bucket = Σ_{i∈bucket} w_i * dir_i`. **The macro/forex-proxy interpretation
is explicitly out of scope for v1** (ADR-0001 defers the macro tier); recorded
here as a documented future variant, not activated.

### 5.4 Cross-filer consensus
Agreement across **distinct filers**. For the instrument at `t`, let `F+` =
distinct `filer_name` with net buy on the mapped asset, `F-` = distinct filers
net sell. `value = (|F+| - |F-|) / max(1, |F+| + |F-|)` ∈ [-1, 1]. **Each filer
counts once** regardless of how many records they filed (dedup by content_hash
first, so a re-pull — e.g. the duplicate fixture — never double-counts).
Captures "do many members agree," which single-filer volume cannot.

### 5.5 Purchase/sale imbalance
Weighted **magnitude** imbalance using the value-range rule.
`buy = Σ_{dir_i=+1} w_i * m_i`, `sell = Σ_{dir_i=-1} w_i * m_i`,
`value = (buy - sell) / max(ε, buy + sell)` ∈ [-1, 1], with an aggregate
`uncertainty` propagated from the `u_i`. This is the axis most sensitive to the
amendment point-in-time rule: before an amendment's availability the original
direction/amount applies; after, the amended one (LW-107 C1c).

## 6. Parameters (named, recorded per run; ablation-tunable)

| Param | Default | Meaning |
|---|---|---|
| `H` | 21 days | Recency-decay half-life on **transaction age** (§2). |
| `decay_basis` | `transaction_age` | Which age the decay reads: `transaction_age` (default) or `availability_age`. Ablation-comparable. |
| `W` | inherits LW-107 default | Availability-time lookback window. |
| `τ_auto` | inherits LW-105 (0.80) | Contribution confidence floor. |
| `ε` | 1e-9 | Imbalance zero-guard. |

Defaults are starting points for LW-206, not asserted-correct values.

## 7. Worked example (invented fixtures; eng-review Q2)

Using `research/congress/sample_disclosures.json` at a cutoff `t` after all
records are available (so eligibility is not the variable under test), for
instrument **US500** (DEMO maps to US500):

- Contributing: `demo:0001` (DEMO buy, Jane), `demo:0006`→superseded-by→`demo:0007`
  (amendment: now a sale, Alex). `demo:0005` (WIDG) is unmapped → excluded.
- **Ticker/sector** (net signed, equal weights for illustration): `+1 (buy) + (-1)
  (post-amend sale) = 0`.
- **Consensus:** distinct filers — Jane (buy), Alex (sell) → `(1 - 1)/2 = 0`.
- **Imbalance:** both brackets `$1,001–$15,000` → `m = 8000.5` each; `buy = 8000.5`,
  `sell = 8000.5` → `0`, uncertainty carried from `u = 6999.5`.
- At a cutoff **before** `demo:0007`'s availability (2026-04-20): Alex's record is
  still the original **buy** → imbalance and net both **positive**, demonstrating
  the point-in-time flip.

These become executable assertions in the fixture harness (§8).

## 8. Verification (invented fixtures only)

Extends `research/congress/normalization_checks.py` — reuses the existing
`eligible`/`available_at`/`resolve_asset`; adds aggregation functions + checks:
ticker/sector net, market-factor bucket routing, consensus distinct-filer (with
dedup), imbalance point-in-time via the amendment pair, unmapped→0, sparse-period
neutral, and determinism. One new second-distinct-filer record is added so
consensus is genuinely exercised (eng-review T1).

## 9. Forward note — "unrealized signal" interaction (hypothesis for LW-108)

A richer hypothesis (Ian) is not an aggregation axis but a **feature
interaction** and is recorded here for LW-108, not implemented in LW-106: a
disclosed trade may only remain predictive **if the anticipated move has not yet
happened** by scoring time `t`. One would look from the trade forward and, using
only price data with timestamp `<= t`, gate or attenuate the aggregate by whether
the expected move already occurred. This belongs in LW-108 (how the congressional
aggregate joins the existing price/feature pipeline) and is validated by the
LW-206 ablation. Two cautions carried forward: (1) it conditions on realized
price action, so it must be strictly point-in-time (`price_ts <= t`) to avoid
encoding the label; (2) it is an interaction between the aggregate and price
history, out of LW-106's aggregation-only scope. Captured so it is tested, not
lost.

## 10. NOT in scope
Real disclosure acquisition (LW-110 gate); production integration; the feature
join itself (LW-108); the macro/forex proxy (ADR-deferred); supersedence
mechanics (LW-201/202); any claim of predictive edge (LW-206).

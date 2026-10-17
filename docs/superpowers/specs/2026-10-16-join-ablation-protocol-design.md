# LW-108 — Feature Join & Baseline Ablation Protocol

- **Checklist:** LW-108 (medium; not a release gate). Discovery-contract item of
  LW-W1. Eng-reviewed via `/plan-eng-review`.
- **Status:** DRAFT design — for Ian's review. Design document only.
- **Date:** 2026-10-16
- **Depends on (done):** LW-104, LW-105, LW-106, LW-107, LW-301 (frozen
  `baseline-v1`), LW-635.
- **Related:** `docs/superpowers/specs/2026-10-16-aggregation-experiments-design.md`
  (the columns being joined), `...-leakage-safe-clock-design.md`,
  `docs/research/lw206-ablation-notebook-sketch.md`, ADR-0001,
  `apps/api/livewell/features/` (existing feature pipeline).
  Downstream: LW-206 (runs the ablation).

> **Scope guardrail (governance, rev 189).** Design + invented-fixtures only. No
> real disclosure acquisition; no production integration. **No ablation run, no
> model training, no touching the registered model** — that is LW-206. This
> defines the join contract and the ablation *protocol*; it asserts no predictive
> edge. LW-110 blocked; LW-112/LW-113 deferred.

---

## 1. Purpose

Define two things: (A) the **join** that attaches LW-106's congressional
aggregate columns to the existing NADEX feature rows, point-in-time; and (B) the
**baseline-versus-augmented ablation protocol** that LW-206 will execute to
decide whether the congressional feature is retained. Both are defined fully
(eng-review scope A); neither is run here.

## 2. The existing feature spine (confirmed from code)

`apps/api/livewell/features/features.py` writes per-instrument Parquet to
`features/{s3_key}/{interval}/`, rows keyed on `date`, columns:
`[date, ema_20, ema_50, rsi_14, macd, macd_hist, macd_signal, atr_14]`.
These rows are the **spine**: the join is **left** on them (prices/indicators
always exist; congressional data is additive and usually absent).

## 3. Join contract

### 3.1 Grain & direction (eng-review A1)
`join(feature_rows, records, t) -> augmented_rows` is a **left join on
(instrument, date)**. For each spine row at (instrument, `date`) with scoring
cutoff `t = date`'s decision cutoff, the congressional columns are computed
**point-in-time as of that `t`** via LW-106's `aggregate(instrument, t)` — which
itself gates eligibility on `public_availability_at` (LW-107 C1) and applies
amendments point-in-time (C1c). The join must **not** attach values from a
precomputed aggregate table built from a later snapshot; each row's congressional
columns are evaluated at its own `t`. This is the central leakage control.

### 3.2 Columns added (eng-review Q3 — `cng_*` namespace)
| Column | Source axis (LW-106) | Type |
|---|---|---|
| `cng_ticker` | ticker aggregation | signed float |
| `cng_sector` | sector rollup | signed float |
| `cng_factor_<bucket>` | market-factor (factor-bucket) | signed float per bucket |
| `cng_consensus` | cross-filer consensus | [-1,1] |
| `cng_imbalance` | purchase/sale imbalance | [-1,1] |
| `cng_imbalance_u` | imbalance uncertainty companion | float \| null |
| `cng_present` | presence flag (A2a) | bool |
| `cng_unrealized` | unrealized-signal interaction (A4a) | signed float \| 0 |

### 3.3 Absence vs zero (eng-review A2a)
Most rows have no eligible disclosure. On absence: signed columns fill **0**,
`cng_present = False`, uncertainty = null. On presence: `cng_present = True`.
This lets the model distinguish *no data* from *net-balanced data* — they are not
the same and must not collapse to the same row.

### 3.4 Unmapped / dedup
Resolved-but-unmapped tickers (LW-105 §7) and unresolved records contribute to no
column. Duplicate re-pulls (same `content_hash`) are de-duplicated before
aggregation so they never double-count (consistent with LW-106 consensus).

### 3.5 Unrealized-signal interaction — fenced candidate (eng-review A4a)
`cng_unrealized` encodes Ian's hypothesis: a disclosed trade may remain
predictive only if the anticipated move **has not already happened** by `t`.

- It is **one declared candidate column**, not always-on; LW-206 tests it as a
  variant (augmented-with vs augmented-without).
- It reads price history, so it is the most leakage-prone column in the track.
  **Hard guard:** it may use only prices with `price_ts <= t`. Using any price
  at or after a future bar is forbidden.
- Construction (design intent, tuned/tested in LW-206): from the dominant
  disclosed direction, measure whether the mapped instrument has already made the
  expected move over `[transaction_date, t]` using only `price_ts <= t`; attenuate
  `cng_unrealized` toward 0 as the move is judged "already realized." The exact
  realization test and threshold are LW-206 tunables; the **leakage guard is
  not** tunable.

## 4. Baseline ablation protocol (design; run in LW-206)

### 4.1 Freeze everything but the congressional columns (eng-review A3)
The comparison is honest only if the **sole** difference is the `cng_*` columns.
Pinned by identity (eng-review Q4):
- **Data:** frozen `baseline-v1` prices/features/signals
  (`s3://livewell-data-prod/frozen/baseline-v1/`, by prefix).
- **Model:** the registered baseline model `rf_tuned@<pinned-id>` family and
  hyperparameters — unchanged.
- **Folds:** the same walk-forward folds as the Phase-2 baseline.
- **Clock:** LW-107 filing-availability dating throughout.

Baseline feature matrix `X_base` = existing indicator columns.
Augmented `X_aug` = `X_base` + the `cng_*` columns (one run per unrealized-signal
variant per A4a). Nothing else varies.

### 4.2 Pre-registered metrics & decision rule (eng-review A5)
Declared **before** any run:
- **Primary:** candidate quality — win rate and/or expected value — on
  filing-availability-dated walk-forward folds.
- **Guards:** calibration (e.g. reliability) and stability across folds must not
  degrade unacceptably.
- **Reporting granularity:** per instrument-class — indices / commodities / forex
  — because ADR bridge A expects the signal to help indices most.
- **Decision rule:** promote the congressional feature **only if** it improves
  the primary metric without unacceptable calibration/stability loss. A negative
  or inconclusive result → not promoted; a superseding ADR records the rejection.
  Finishing the research alone does not authorize promotion or production (LW-113).

### 4.3 Leakage controls carried into the ablation
- Features computed only from records eligible at each fold's point-in-time (C1).
- `cng_unrealized` prices `<= t` only (§3.5).
- No peeking across folds; the frozen baseline is never re-fit to augmented data.

## 5. Verification (invented fixtures only; no run)

Extends `research/congress/`:
- A tiny invented OHLC price series so `cng_unrealized` can be exercised
  point-in-time (prices `<= t`).
- `join_checks.py` reusing LW-106 aggregation + LW-107 clock: left-join attaches
  `cng_*` on (instrument, date); point-in-time per row across the amendment pair;
  `cng_present` absence flag; unmapped excluded; dedup not double-counted;
  `cng_unrealized` uses only `price_ts <= t`; determinism.
- A **structural** assertion that the ablation protocol spec names baseline-v1 +
  model id + folds + declared metrics + decision rule (completeness /
  pre-registration guard). **No model trained, no edge computed.**

## 6. NOT in scope
Running the ablation, training/evaluating any model, touching the registered
model (all LW-206); real disclosure acquisition (LW-110); production integration
(LW-113); the macro/forex proxy (ADR-deferred); supersedence mechanics
(LW-201/202). No predictive-edge claim is made here.

# LW-105 — Asset Resolution, Confidence Levels & Manual Review

- **Checklist:** LW-105. Discovery-contract item of LW-W1.
- **Status:** DRAFT design — for Ian's review. Design document only.
- **Date:** 2026-10-16
- **Depends on (done):** LW-104 (canonical schema), LW-101 (ADR-0001), LW-635.
- **Related:** `docs/superpowers/specs/2026-10-16-disclosure-schema-design.md`
  (asset fields), `docs/research/congressional-disclosure-limitations.md`
  (ambiguous assets), `docs/designs/congressional-trading-signal.md` (curated
  ticker→sector→instrument map, bridge A). Downstream: LW-203 (manual-review
  queue ops), LW-108/LW-106 (rollup/aggregation), LW-111 (fixtures).

> **Scope guardrail (governance, rev 183).** Design + invented-fixtures only. No
> real disclosure acquisition; no production integration. LW-110 blocked;
> LW-112/LW-113 deferred. All examples invented and clearly labeled.

---

## 1. Purpose

Define how a disclosure's free-text asset description becomes a **resolved
ticker** (or is withheld for manual review), the **confidence scale** attached to
each resolution, and the **threshold** that routes low-confidence matches to a
review queue instead of silently into features. This populates the LW-104 fields
`resolved_ticker`, `resolution_confidence`, `needs_manual_review`.

It defines the resolution *method and policy*. It does not build the aggregation
feature (LW-106/108) or operate the review queue UI/workflow (LW-203).

## 2. Why resolution is hard (from LW-102)

Disclosures carry **free-text** asset descriptions and inconsistent ticker usage:
company names with/without suffixes, fund/ETF descriptions, options described in
prose, bonds, cash-like instruments, and plain typos. A naive "ticker in
parentheses" grab is wrong often enough to poison features. The design principle
from LW-104 governs: **preserve the raw text, never overwrite it; put every
inference in separate fields; make low confidence visible.**

## 3. Resolution pipeline (deterministic, ordered tiers)

Each record's `asset_text_raw` (+ `asset_ticker_raw` if present) runs through
ordered tiers; the **first** tier that matches sets `resolved_ticker` and a base
confidence. Tiers are deterministic and offline (no live lookups in the scoring
path — consistent with ADR-0001's rejection of runtime yfinance probes).

| Tier | Rule | Base confidence |
|---|---|---|
| T1 — exact ticker | `asset_ticker_raw` present and matches a known symbol in the curated map exactly. | 0.95 |
| T2 — normalized name | `asset_text_raw` normalized (strip suffixes like "Inc/Corp/Class A", case/punct-fold) matches exactly one curated issuer name. | 0.85 |
| T3 — alias/known-variant | Matches a curated alias table (common abbreviations, former names, well-known funds/ETFs). | 0.80 |
| T4 — fuzzy | Token-set similarity ≥ `τ_fuzzy` to exactly one curated name, no competing match within `δ_margin`. | 0.55–0.75 (scaled by similarity) |
| T5 — ambiguous / none | No tier matches, OR multiple candidates within `δ_margin` (genuine ambiguity). | ≤ 0.40 |

- **Curated reference is version-controlled** (ADR-0001 bridge B): a committed
  table of symbols, issuer names, aliases, and their sector→instrument routing.
  Resolution never calls a live service; the curated table may be *seeded* offline
  once (e.g. from a public sector source) and then committed.
- **Type-awareness:** `asset_type` (LW-104) narrows candidates — e.g. an
  `option` description resolves to its underlying's ticker with a type tag;
  `bond`/`fund`/`crypto`/`other` that don't map to a tradable curated symbol go to
  T5 by construction.

## 4. Confidence scale (continuous [0,1], with bands)

`resolution_confidence ∈ [0,1]`, interpreted in three **bands**:

| Band | Range | Meaning | Routing |
|---|---|---|---|
| High | `>= τ_auto` (default **0.80**) | Confident, unambiguous. | Auto-accept → eligible for features. |
| Review | `τ_review <= c < τ_auto` (default **0.50–0.80**) | Plausible but not certain, or mild ambiguity. | `needs_manual_review = true`; excluded from features until adjudicated. |
| Reject | `< τ_review` (default **0.50**) | No credible match / genuine ambiguity. | `resolved_ticker = null`, `needs_manual_review = true`. |

> **Rule R1 — fail safe.** A record only contributes to a feature when
> `resolved_ticker != null` **and** `resolution_confidence >= τ_auto` **and**
> `needs_manual_review = false`. Anything else is withheld. (This matches the
> LW-104 default: `needs_manual_review` tends true until confidently resolved.)

> **Rule R2 — ambiguity beats score.** If two or more candidates fall within
> `δ_margin` of each other, the record is **Review** at best, regardless of the
> top raw similarity — ambiguity is not resolved by a thin margin.

## 5. Manual review (policy, not the tooling)

- Records in **Review**/**Reject** bands enter a **review queue** (the queue's
  operation — UI, assignment, SLA — is **LW-203**, out of scope here).
- A human adjudication **overrides** the automated fields: sets `resolved_ticker`,
  bumps `resolution_confidence` to a reserved **manual** value (**1.0** with an
  audit marker), clears `needs_manual_review`. The original automated values and
  the adjudicator decision are retained (lineage principle), never silently
  overwritten.
- **No back-dating into leakage:** a manual decision is applied point-in-time —
  it does not retroactively make a record eligible for a scoring date before the
  decision was made, consistent with LW-107. (The adjudication has its own
  effective timestamp.)

## 6. Interaction with the leakage-safe clock (LW-107)

Resolution is **content**, not timing — it does not change `public_availability_at`.
But two coupling rules matter:

> **Rule R3 — resolution is as-of-able.** The resolved value used at scoring time
> `t` must be the resolution state that existed **as of `t`** (including whether a
> manual review had been adjudicated by then). An adjudication made after `t` does
> not alter the feature at `t`.

This keeps asset resolution from becoming a backdoor for look-ahead (e.g.
"we later figured out the ticker, so retroactively include it" — not allowed).

## 7. Mapping to the instrument universe (ADR bridge A)

Resolution outputs a **ticker**; the curated map then routes ticker → sector →
LIVEWELL instrument(s) (NASDAQ 100 / US 500 / Russell 2000 / Dow / Gold / Crude /
Nat Gas; forex gets no direct feature in v1). A resolved ticker that maps to **no**
LIVEWELL instrument is retained (lineage) but contributes to **no** feature —
distinct from unresolved: *resolved-but-unmapped* vs *unresolved*. Both are
non-contributing, for different reasons, and both are recorded.

## 8. Parameters (named, recorded per run)

| Param | Default | Meaning |
|---|---|---|
| `τ_auto` | 0.80 | Auto-accept confidence threshold. |
| `τ_review` | 0.50 | Floor of the review band; below = reject. |
| `τ_fuzzy` | 0.85 | Min token-set similarity for a T4 fuzzy match. |
| `δ_margin` | 0.05 | Min separation between top-2 candidates to avoid ambiguity (R2). |
| `manual_confidence` | 1.0 | Reserved value for human-adjudicated resolutions. |

Thresholds are **tunables** validated during the ablation (LW-206), not asserted
as correct here.

## 9. Verification approach (design-time, invented fixtures only)

Checks LW-111's fixtures will make executable — no real data:

1. **Exact-ticker (T1).** Clean `asset_ticker_raw` → high band, auto-accept.
2. **Name normalization (T2).** "DemoCorp Inc. Class A" → resolves to the same
   symbol as "DEMO".
3. **Ambiguity (R2).** Two curated candidates within `δ_margin` → Review, not
   auto-accept, even with high top similarity.
4. **Unresolvable (T5).** Free-text with no credible match → Reject,
   `resolved_ticker = null`, `needs_manual_review = true`, contributes nothing.
5. **Resolved-but-unmapped (§7).** Valid ticker that maps to no LIVEWELL
   instrument → recorded, contributes to no feature.
6. **As-of resolution (R3).** Adjudication dated after `t` does not change the
   feature at `t`.

## 10. Acceptance-criterion checklist (LW-105)

| Required | Where |
|---|---|
| Asset-resolution method | §3 ordered tiers T1–T5 |
| Confidence levels | §4 continuous scale + bands; §8 thresholds |
| Manual review | §5 policy + Rule R1 fail-safe; queue ops deferred to LW-203 |
| Leakage-consistency | Rules R3 (§6), point-in-time manual decisions (§5) |

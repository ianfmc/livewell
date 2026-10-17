# LW-111 — Congressional disclosure sample fixtures & normalization checks

Research-prep artifact. **100% invented data — no real congressional disclosure
was accessed, downloaded, or derived.** This directory exercises the LW-104
canonical schema and the LW-105 / LW-107 rules against fabricated records.

## Files

- `sample_disclosures.json` — invented, clearly-labeled sample records covering
  normal and edge cases: high-confidence buy, name-only (no ticker), ambiguous
  asset, unresolvable free-text, resolved-but-unmapped ticker, an
  original→amendment point-in-time pair, and a byte-identical duplicate re-pull.
- `normalization_checks.py` — reference implementations of the LW-107
  leakage-safe clock and the LW-105 resolution policy, plus 16 `unittest` checks
  that make the specs' verification scenarios executable.

## Run

```
python normalization_checks.py
```

Expected: `Ran 16 tests ... OK` (4 schema-normalization, 5 clock, 6 resolution,
1 dedup).

## Scope

Design + invented-fixtures only. No real disclosure acquisition (LW-110 gate
blocked), no production integration (LW-112/LW-113 deferred). This validates
data **handling**, not predictive value (that is LW-206's job).

## Specs

- `docs/superpowers/specs/2026-10-16-disclosure-schema-design.md` (LW-104)
- `docs/superpowers/specs/2026-10-16-asset-resolution-design.md` (LW-105)
- `docs/superpowers/specs/2026-10-16-leakage-safe-clock-design.md` (LW-107)

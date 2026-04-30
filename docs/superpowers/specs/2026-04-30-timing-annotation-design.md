# Design: Timing Annotation

**Date:** 2026-04-30
**Status:** Approved
**Scope:** Add two informational columns (`timing_slot`, `timing_risk`) to the signal pipeline output, derived from asset-class timing tables that describe how market structure changes at key intraday moments.

---

## Context

`docs/nadex_timing_tables.md` defines intraday timing slots for three asset classes (Indices, Forex, Commodities). Each slot marks a point where market behaviour changes — open spikes, fade windows, inventory releases, session closes — which affects how far in or out of the money a NADEX binary is likely to move before expiry. The closer to expiration, the less volatile contracts that are well inside or outside the money tend to be. These slots provide context for interpreting a signal's position relative to known structural turning points.

This design adds a **nearest-preceding-slot lookup** to the existing `_apply_pipeline()` function, appending two informational columns to the signal output. Signal validity (`signal_valid`) is unchanged.

---

## Approach

**Nearest-preceding-slot lookup.** Each asset class has a sorted list of named time slots (UTC). At signal time, find the most recent slot that has already passed. If the signal falls before the day's first slot, return `"unscheduled"`. This is the honest representation of the timing tables, which define discrete trigger points rather than continuous windows.

---

## Architecture

### Asset class mapping

| Instrument | Asset Class |
|---|---|
| EURUSD, GBPUSD, USDJPY | forex |
| XAUUSD | commodities |
| US500 | indices |

### Timing slots (UTC)

PT to UTC conversion assumes PT = UTC−7 (PDT). If clocks change, slot times shift by 1 hour — acceptable for a first implementation.

**Indices:**

| UTC | preferred_action | risk_level |
|---|---|---|
| 13:30 | buy_bullish | moderate_high |
| 14:30 | sell_bullish_buy_bearish | moderate |
| 16:00 | avoid | low |
| 19:55 | buy_bearish | high |

**Forex:**

| UTC | preferred_action | risk_level |
|---|---|---|
| 07:00 | buy_bullish_eurusd | moderate |
| 12:00 | buy_bullish_usdjpy | high |
| 15:00 | close_positions | low |
| 16:00 | avoid | low_moderate |

**Commodities:**

| UTC | preferred_action | risk_level |
|---|---|---|
| 07:00 | buy_bullish_gold | moderate |
| 13:30 | buy_bullish_crude | moderate_high |
| 14:30 | buy_bearish_natgas | very_high |
| 16:00 | avoid | low |

### New output columns

| Column | Type | Description |
|---|---|---|
| `timing_slot` | string | `preferred_action` of nearest preceding slot, or `"unscheduled"` |
| `timing_risk` | string | `risk_level` of nearest preceding slot, or `"unknown"` |

These columns are appended to `SIGNAL_COLUMNS` after the existing columns. They are informational only — they never affect `signal_valid`.

---

## Files Changed

| File | Change |
|---|---|
| `apps/api/livewell/signals/constants.py` | Add `INSTRUMENT_ASSET_CLASS`, `TIMING_SLOTS`, update `SIGNAL_COLUMNS` |
| `apps/api/livewell/signals/signals.py` | Add `_timing_annotation()`, call in `_apply_pipeline()` |
| `apps/api/tests/signals/test_signals.py` | 4 new tests |
| `docs/superpowers/specs/2026-04-24-subproject-1c-signal-generation-design.md` | Add Timing Annotation section, update output columns table |

No changes to `_signals_one()`, `run_signals()`, `run_features()`, or S3 layout.

---

## Interface

```python
def _timing_annotation(asset_class: str, ts: pd.Timestamp) -> tuple[str, str]:
    """
    Return (timing_slot, timing_risk) for the nearest preceding slot.
    Returns ("unscheduled", "unknown") if before the day's first slot.
    """
```

Called inside `_apply_pipeline(s3_key, row)` after all existing stages.

---

## Constants

```python
INSTRUMENT_ASSET_CLASS = {
    "EURUSD": "forex",
    "GBPUSD": "forex",
    "USDJPY": "forex",
    "XAUUSD": "commodities",
    "US500":  "indices",
}

# Each entry: (utc_hour, utc_minute, preferred_action, risk_level)
# Sorted ascending by time within each asset class.
TIMING_SLOTS = {
    "indices": [
        (13, 30, "buy_bullish",              "moderate_high"),
        (14, 30, "sell_bullish_buy_bearish", "moderate"),
        (16,  0, "avoid",                    "low"),
        (19, 55, "buy_bearish",              "high"),
    ],
    "forex": [
        ( 7,  0, "buy_bullish_eurusd",  "moderate"),
        (12,  0, "buy_bullish_usdjpy",  "high"),
        (15,  0, "close_positions",     "low"),
        (16,  0, "avoid",               "low_moderate"),
    ],
    "commodities": [
        ( 7,  0, "buy_bullish_gold",  "moderate"),
        (13, 30, "buy_bullish_crude", "moderate_high"),
        (14, 30, "buy_bearish_natgas","very_high"),
        (16,  0, "avoid",             "low"),
    ],
}
```

---

## Testing

| Test | What it verifies |
|---|---|
| `test_timing_annotation_nearest_slot` | 14:00 UTC, US500 → `"sell_bullish_buy_bearish"` (nearest preceding is 13:30) |
| `test_timing_annotation_before_first_slot` | 06:00 UTC, US500 → `"unscheduled"` (before 13:30, the day's first slot) |
| `test_timing_annotation_exact_slot_time` | Exactly 13:30 UTC, US500 → `"buy_bullish"` |
| `test_timing_columns_in_output_schema` | `run_signals()` output Parquet contains `timing_slot` and `timing_risk` columns |

---

## Out of Scope

- DST-aware PT→UTC conversion — slots use a fixed UTC−7 offset
- Instrument-specific slot overrides (e.g. Natural Gas vs Gold within Commodities)
- Using `timing_slot` to gate `signal_valid` — deferred, informational only for now
- Adding timing context to the Phase 2/3 ML feature matrix — future enhancement

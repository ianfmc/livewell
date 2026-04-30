# Timing Annotation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add two informational columns (`timing_slot`, `timing_risk`) to every signal row by looking up the nearest preceding intraday timing slot for the instrument's asset class, so traders can see where each signal sits relative to known structural turning points.

**Architecture:** Add `INSTRUMENT_ASSET_CLASS` and `TIMING_SLOTS` constants to `signals/constants.py`, then add a `_timing_annotation()` helper to `signals/signals.py` that does a nearest-preceding-slot lookup keyed by asset class and UTC timestamp. Call it inside `_apply_pipeline()` after all existing stages and include the two new columns in the returned dict. `SIGNAL_COLUMNS` is updated to include them, so they flow through `_signals_one()` and `run_signals()` automatically with no other changes.

**Tech Stack:** Python, pandas, pytest, moto, uv

**Spec:** `docs/superpowers/specs/2026-04-30-timing-annotation-design.md`

---

## File Structure

**Modified files:**
- `apps/api/livewell/signals/constants.py` — add `INSTRUMENT_ASSET_CLASS`, `TIMING_SLOTS`, append `timing_slot`/`timing_risk` to `SIGNAL_COLUMNS`
- `apps/api/livewell/signals/signals.py` — add `_timing_annotation()`, call it in `_apply_pipeline()`
- `apps/api/tests/signals/test_signals.py` — 4 new tests

No other files change.

---

## Task 1: Add timing constants and update SIGNAL_COLUMNS

**Files:**
- Modify: `apps/api/livewell/signals/constants.py`
- Modify: `apps/api/tests/signals/test_signals.py`

- [ ] **Step 1: Write the failing test**

Add to `apps/api/tests/signals/test_signals.py`:

```python
from livewell.signals.constants import (
    INSTRUMENT_ASSET_CLASS,
    SIGNAL_COLUMNS,
    TIMING_SLOTS,
)


def test_timing_constants_defined():
    # All current instruments have an asset class
    for key in ["EURUSD", "GBPUSD", "USDJPY", "XAUUSD", "US500",
                "CL", "NG", "NQ", "RTY", "YM", "NKD",
                "AUDUSD", "AUDJPY", "EURJPY", "EURGBP",
                "GBPJPY", "USDCAD", "USDCHF", "USDMXN"]:
        assert key in INSTRUMENT_ASSET_CLASS, f"{key} missing from INSTRUMENT_ASSET_CLASS"

    # Each asset class has at least one slot
    for asset_class in ["indices", "forex", "commodities"]:
        assert asset_class in TIMING_SLOTS
        assert len(TIMING_SLOTS[asset_class]) > 0

    # Each slot is a 4-tuple
    for asset_class, slots in TIMING_SLOTS.items():
        for slot in slots:
            assert len(slot) == 4, f"slot {slot} in {asset_class} should be 4-tuple"

    # New columns are in SIGNAL_COLUMNS
    assert "timing_slot" in SIGNAL_COLUMNS
    assert "timing_risk" in SIGNAL_COLUMNS
    # They come after "reasoning"
    assert SIGNAL_COLUMNS.index("timing_slot") > SIGNAL_COLUMNS.index("reasoning")
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd apps/api && uv run pytest tests/signals/test_signals.py::test_timing_constants_defined -v
```

Expected: FAIL with `ImportError: cannot import name 'INSTRUMENT_ASSET_CLASS'`

- [ ] **Step 3: Update constants.py**

Add the following to the end of `apps/api/livewell/signals/constants.py`:

```python
INSTRUMENT_ASSET_CLASS = {
    # Original instruments
    "EURUSD": "forex",
    "GBPUSD": "forex",
    "USDJPY": "forex",
    "XAUUSD": "commodities",
    "US500":  "indices",
    # Futures
    "CL":  "commodities",
    "NG":  "commodities",
    "NQ":  "indices",
    "RTY": "indices",
    "YM":  "indices",
    "NKD": "indices",
    # Forex
    "AUDUSD": "forex",
    "AUDJPY": "forex",
    "EURJPY": "forex",
    "EURGBP": "forex",
    "GBPJPY": "forex",
    "USDCAD": "forex",
    "USDCHF": "forex",
    "USDMXN": "forex",
}

# Each entry: (utc_hour, utc_minute, preferred_action, risk_level)
# Sorted ascending by time. PT to UTC assumes UTC-7 (PDT).
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
        ( 7,  0, "buy_bullish_gold",   "moderate"),
        (13, 30, "buy_bullish_crude",  "moderate_high"),
        (14, 30, "buy_bearish_natgas", "very_high"),
        (16,  0, "avoid",              "low"),
    ],
}
```

Also update `SIGNAL_COLUMNS` in the same file to append the two new columns:

```python
SIGNAL_COLUMNS = [
    "date", "ema_20", "ema_50", "rsi_14",
    "macd", "macd_signal", "macd_hist", "atr_14",
    "trend_bias", "session_quality", "strike_candidate",
    "signal_valid", "direction", "reasoning",
    "timing_slot", "timing_risk",
]
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd apps/api && uv run pytest tests/signals/test_signals.py::test_timing_constants_defined -v
```

Expected: PASS

- [ ] **Step 5: Verify existing tests still pass**

```bash
cd apps/api && uv run pytest tests/signals/test_signals.py -v
```

Expected: all previously passing tests still PASS (the new columns are not yet produced by `_apply_pipeline`, so `test_run_signals_output_schema` may fail — that is expected and will be fixed in Task 2).

- [ ] **Step 6: Commit**

```bash
git add apps/api/livewell/signals/constants.py apps/api/tests/signals/test_signals.py
git commit -m "feat: add timing annotation constants and update SIGNAL_COLUMNS"
```

---

## Task 2: Implement _timing_annotation helper

**Files:**
- Modify: `apps/api/livewell/signals/signals.py`
- Modify: `apps/api/tests/signals/test_signals.py`

- [ ] **Step 1: Write the failing tests**

Add to `apps/api/tests/signals/test_signals.py`:

```python
from livewell.signals.signals import _timing_annotation


def test_timing_annotation_nearest_slot():
    # 14:00 UTC for US500 (indices) — nearest preceding slot is 13:30 "buy_bullish"
    ts = pd.Timestamp("2026-01-15 14:00:00", tz="UTC")
    slot, risk = _timing_annotation("indices", ts)
    assert slot == "buy_bullish"
    assert risk == "moderate_high"


def test_timing_annotation_exact_slot_time():
    # Exactly 13:30 UTC for US500 (indices) — should match the 13:30 slot itself
    ts = pd.Timestamp("2026-01-15 13:30:00", tz="UTC")
    slot, risk = _timing_annotation("indices", ts)
    assert slot == "buy_bullish"
    assert risk == "moderate_high"


def test_timing_annotation_before_first_slot():
    # 06:00 UTC for US500 (indices) — before 13:30, the day's first slot
    ts = pd.Timestamp("2026-01-15 06:00:00", tz="UTC")
    slot, risk = _timing_annotation("indices", ts)
    assert slot == "unscheduled"
    assert risk == "unknown"


def test_timing_annotation_forex():
    # 13:00 UTC for forex — nearest preceding slot is 12:00 "buy_bullish_usdjpy"
    ts = pd.Timestamp("2026-01-15 13:00:00", tz="UTC")
    slot, risk = _timing_annotation("forex", ts)
    assert slot == "buy_bullish_usdjpy"
    assert risk == "high"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd apps/api && uv run pytest tests/signals/test_signals.py -k "timing_annotation" -v
```

Expected: FAIL with `ImportError: cannot import name '_timing_annotation'`

- [ ] **Step 3: Add _timing_annotation to signals.py**

Add the following import at the top of `apps/api/livewell/signals/signals.py` alongside the existing constants imports:

```python
from livewell.signals.constants import (
    ATR_FEASIBILITY_MULTIPLIER,
    INSTRUMENT_ASSET_CLASS,
    MIN_ATR_THRESHOLD,
    PIP_PRECISION,
    RSI_BEARISH_MAX,
    RSI_BULLISH_MIN,
    RSI_OVERBOUGHT,
    RSI_OVERSOLD,
    SESSION_CONFIG,
    SIGNAL_COLUMNS,
    SIGNALS_PREFIX,
    TIMING_SLOTS,
)
```

Then add the function after `_session_quality` and before `_apply_pipeline`:

```python
def _timing_annotation(asset_class: str, ts: pd.Timestamp) -> tuple[str, str]:
    """
    Return (timing_slot, timing_risk) for the nearest preceding slot in the asset class.
    Returns ("unscheduled", "unknown") if the timestamp precedes the day's first slot.
    """
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")

    slots = TIMING_SLOTS.get(asset_class, [])
    signal_minutes = ts.hour * 60 + ts.minute

    best_slot = None
    best_minutes = -1

    for utc_hour, utc_minute, preferred_action, risk_level in slots:
        slot_minutes = utc_hour * 60 + utc_minute
        if slot_minutes <= signal_minutes and slot_minutes > best_minutes:
            best_minutes = slot_minutes
            best_slot = (preferred_action, risk_level)

    if best_slot is None:
        return "unscheduled", "unknown"

    return best_slot
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd apps/api && uv run pytest tests/signals/test_signals.py -k "timing_annotation" -v
```

Expected: all 4 timing annotation tests PASS

- [ ] **Step 5: Commit**

```bash
git add apps/api/livewell/signals/signals.py apps/api/tests/signals/test_signals.py
git commit -m "feat: add _timing_annotation helper with nearest-preceding-slot lookup"
```

---

## Task 3: Wire timing annotation into _apply_pipeline

**Files:**
- Modify: `apps/api/livewell/signals/signals.py`
- Modify: `apps/api/tests/signals/test_signals.py`

- [ ] **Step 1: Write the failing test**

Add to `apps/api/tests/signals/test_signals.py`:

```python
def test_timing_columns_in_pipeline_output():
    # A valid bullish row at 14:00 UTC for US500
    row = {
        "date":        pd.Timestamp("2026-01-15 14:00:00", tz="UTC"),
        "ema_20":      5200.0, "ema_50": 5100.0,
        "rsi_14":      55.0,
        "macd":        2.0, "macd_signal": 1.5, "macd_hist": 0.5,
        "atr_14":      10.0,
        "close":       5190.0,
    }
    result = _apply_pipeline("US500", row)
    assert "timing_slot" in result
    assert "timing_risk" in result
    # 14:00 UTC → nearest preceding indices slot is 13:30 "buy_bullish"
    assert result["timing_slot"] == "buy_bullish"
    assert result["timing_risk"] == "moderate_high"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd apps/api && uv run pytest tests/signals/test_signals.py::test_timing_columns_in_pipeline_output -v
```

Expected: FAIL — `_apply_pipeline` result dict has no `timing_slot` key

- [ ] **Step 3: Update _apply_pipeline in signals.py**

In `_apply_pipeline`, after the existing Stage 5 session filter block and before the final `return`, add:

```python
    # Timing annotation (informational — does not affect signal_valid)
    asset_class = INSTRUMENT_ASSET_CLASS.get(s3_key, "forex")
    timing_slot, timing_risk = _timing_annotation(asset_class, ts)
```

Then add `"timing_slot"` and `"timing_risk"` to the returned dict:

```python
    return {
        "trend_bias": trend_bias,
        "session_quality": session_quality,
        "strike_candidate": strike_candidate,
        "signal_valid": signal_valid,
        "direction": direction,
        "reasoning": json.dumps(reasons),
        "timing_slot": timing_slot,
        "timing_risk": timing_risk,
    }
```

- [ ] **Step 4: Run the new test to verify it passes**

```bash
cd apps/api && uv run pytest tests/signals/test_signals.py::test_timing_columns_in_pipeline_output -v
```

Expected: PASS

- [ ] **Step 5: Run the full signals test suite**

```bash
cd apps/api && uv run pytest tests/signals/test_signals.py -v
```

Expected: all tests PASS including `test_run_signals_output_schema` (which checks that Parquet output contains all `SIGNAL_COLUMNS`)

- [ ] **Step 6: Run the full test suite to check for regressions**

```bash
cd apps/api && uv run pytest -v
```

Expected: all tests PASS

- [ ] **Step 7: Commit**

```bash
git add apps/api/livewell/signals/signals.py apps/api/tests/signals/test_signals.py
git commit -m "feat: wire timing annotation into signal pipeline output"
```

---

## Self-Review

### Spec coverage

| Spec requirement | Covered in |
|---|---|
| `INSTRUMENT_ASSET_CLASS` dict for all instruments | Task 1 |
| `TIMING_SLOTS` dict with 3 asset classes, 4 slots each | Task 1 |
| `SIGNAL_COLUMNS` updated with `timing_slot`, `timing_risk` | Task 1 |
| `_timing_annotation(asset_class, ts) -> tuple[str, str]` | Task 2 |
| Nearest-preceding-slot lookup | Task 2 |
| Returns `("unscheduled", "unknown")` before day's first slot | Task 2 |
| Called inside `_apply_pipeline()` after existing stages | Task 3 |
| `timing_slot` / `timing_risk` in returned dict | Task 3 |
| `signal_valid` unchanged | Task 3 (annotation added after validity logic) |
| `test_timing_annotation_nearest_slot` | Task 2 |
| `test_timing_annotation_exact_slot_time` | Task 2 |
| `test_timing_annotation_before_first_slot` | Task 2 |
| `test_timing_columns_in_output_schema` | Task 3 (`test_run_signals_output_schema` covers S3 schema; `test_timing_columns_in_pipeline_output` covers pipeline dict) |
| No changes to `_signals_one`, `run_signals`, `run_features` | ✓ (only constants + pipeline function touched) |

### Placeholder scan

No TBDs, TODOs, or vague steps. All code shown in full.

### Type consistency

- `_timing_annotation(asset_class: str, ts: pd.Timestamp) -> tuple[str, str]` — defined in Task 2, called in Task 3 with `(asset_class, ts)` — consistent.
- `INSTRUMENT_ASSET_CLASS.get(s3_key, "forex")` — `s3_key` is the string key used throughout `_apply_pipeline` — consistent.
- `TIMING_SLOTS` keys `"indices"`, `"forex"`, `"commodities"` — used in `_timing_annotation` via `TIMING_SLOTS.get(asset_class, [])` — consistent with values in `INSTRUMENT_ASSET_CLASS`.
- `SIGNAL_COLUMNS` appended in Task 1 — `_signals_one` builds the output DataFrame with `columns=SIGNAL_COLUMNS` — the new columns flow through automatically since `_apply_pipeline` now returns them.

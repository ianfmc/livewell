# Design: Sub-project 1C — Signal Generation

**Date:** 2026-04-24
**Status:** Approved
**Scope:** Read feature Parquet from S3, apply full 5-stage rule-based signal pipeline, write signal tables back to S3 as Parquet. Triggered automatically by feature generation.

---

## Context

Sub-project 1B delivers technical indicator features (EMA-20, EMA-50, RSI-14, MACD, ATR-14) in S3. Sub-project 1C transforms those features into structured trade signals using the deterministic rule-based pipeline defined in `docs/02_trading_strategy.md`. This sub-project closes the gap between raw indicators and actionable signal candidates.

---

## Approach

A new `livewell/signals/` package following the same structure as `livewell/features/`. Uses only the feature columns already computed in 1B — no new external dependencies. Entry point is `run_signals()` — a standalone callable that feature generation triggers at the end of `run_features()`. Per-instrument error isolation. Idempotent re-runs.

---

## Architecture

### Files

| File | Purpose |
|---|---|
| `apps/api/livewell/signals/__init__.py` | Package marker |
| `apps/api/livewell/signals/constants.py` | Thresholds, session windows, pip precision, output column names |
| `apps/api/livewell/signals/signals.py` | Pipeline logic, S3 read/write, `run_signals()` |
| `apps/api/tests/signals/__init__.py` | Package marker |
| `apps/api/tests/signals/test_signals.py` | Unit tests + moto S3 tests |

### Modified Files

| File | Change |
|---|---|
| `apps/api/livewell/features/features.py` | Call `run_signals()` at end of `run_features()` |
| `apps/web/current_step_plan.md` | Update to Sub-project 1D on completion |

### S3 Layout

```
s3://{LIVEWELL_BUCKET}/signals/{INSTRUMENT}/{INTERVAL}/{YEAR}.parquet

# Examples
s3://livewell-data/signals/EURUSD/1d/2026.parquet
s3://livewell-data/signals/EURUSD/1h/2026.parquet
s3://livewell-data/signals/GBPUSD/1d/2025.parquet
```

Each Parquet file covers one calendar year per instrument per interval.

### Output Columns

| Column | Type | Description |
|---|---|---|
| `date` | datetime | Bar timestamp |
| `ema_20` | float64 | Passed through from features |
| `ema_50` | float64 | Passed through from features |
| `rsi_14` | float64 | Passed through from features |
| `macd` | float64 | Passed through from features |
| `macd_signal` | float64 | Passed through from features |
| `macd_hist` | float64 | Passed through from features |
| `atr_14` | float64 | Passed through from features |
| `trend_bias` | string | `"bullish"`, `"bearish"`, or `"neutral"` |
| `session_quality` | string | `"high"`, `"medium"`, or `"low"` |
| `strike_candidate` | float64 | Theoretical strike price (see Strike Selection) |
| `signal_valid` | bool | True only when all 5 stages pass |
| `direction` | string | `"buy"`, `"sell"`, or `"none"` |
| `reasoning` | string | JSON-serialised list of strings explaining pass/fail per condition |
| `timing_slot` | string | `preferred_action` of nearest preceding timing slot, or `"unscheduled"` (informational only) |
| `timing_risk` | string | `risk_level` of nearest preceding timing slot, or `"unknown"` (informational only) |

### Config

| Var | Purpose | Default |
|---|---|---|
| `LIVEWELL_BUCKET` | S3 bucket name | required |

---

## Pipeline (5 Stages)

Applied row-by-row to the full feature history per instrument+interval.

### Stage 1 — Trend

| Condition | Result |
|---|---|
| `ema_20 > ema_50` | `trend_bias = "bullish"` |
| `ema_20 < ema_50` | `trend_bias = "bearish"` |
| otherwise | `trend_bias = "neutral"` → `signal_valid = False` |

### Stage 2 — Momentum Confirmation

Bullish: `rsi_14 > RSI_BULLISH_MIN` AND `macd_hist > 0` AND `macd > macd_signal`

Bearish: `rsi_14 < RSI_BEARISH_MAX` AND `macd_hist < 0` AND `macd < macd_signal`

Failure of any condition → `signal_valid = False`, `direction = "none"`.

### Stage 3 — Overextension Check

| Condition | Result |
|---|---|
| Bullish AND `rsi_14 > RSI_OVERBOUGHT` (75) | `signal_valid = False` |
| Bearish AND `rsi_14 < RSI_OVERSOLD` (25) | `signal_valid = False` |

### Stage 4 — ATR Feasibility + Strike Selection

`_signals_one()` reads both `features/{INSTRUMENT}/{INTERVAL}/` and `prices/{INSTRUMENT}/{INTERVAL}/` Parquets, joining on `date` to obtain the `close` column needed for strike calculation. The join is an inner join — bars without a matching price row are dropped.

`strike_candidate`:
- Bullish: `round(close + atr_14 * ATR_FEASIBILITY_MULTIPLIER, PIP_PRECISION[instrument])`
- Bearish: `round(close - atr_14 * ATR_FEASIBILITY_MULTIPLIER, PIP_PRECISION[instrument])`
- Neutral/invalid: `NaN`

`atr_feasible = atr_14 >= MIN_ATR_THRESHOLD[instrument]`

If `not atr_feasible` → `signal_valid = False`.

### Stage 5 — Session Filter

`session_quality` is derived from the UTC hour of `date` against static session windows per instrument group. Low-quality session → `signal_valid = False`.

**Session windows (UTC):**

| Window | UTC hours | Quality |
|---|---|---|
| London/NY overlap | 12:00–16:00 | high |
| London open | 07:00–12:00 | high |
| NY afternoon | 16:00–21:00 | medium |
| Off-hours | 21:00–23:00 | low |
| Asian session | 23:00–07:00 | low |

**Per-instrument overrides:**
- EUR/USD, GBP/USD: standard windows above
- USD/JPY: Asian session (23:00–07:00 UTC) also tagged `"high"`
- Gold (XAUUSD), US500: NY hours (12:00–21:00 UTC) = high; all others = low

Only `"high"` session quality allows `signal_valid = True`.

---

## Constants

```python
RSI_BULLISH_MIN = 50
RSI_BEARISH_MAX = 50
RSI_OVERBOUGHT = 75
RSI_OVERSOLD = 25
ATR_FEASIBILITY_MULTIPLIER = 0.5
SIGNALS_PREFIX = "signals"

# Per-instrument pip decimal places for strike rounding
PIP_PRECISION = {
    "EURUSD": 4,
    "GBPUSD": 4,
    "USDJPY": 2,
    "XAUUSD": 1,
    "US500":  0,
}

# Minimum ATR below which setup is not tradeable
MIN_ATR_THRESHOLD = {
    "EURUSD": 0.0010,
    "GBPUSD": 0.0010,
    "USDJPY": 0.10,
    "XAUUSD": 1.0,
    "US500":  5.0,
}
```

---

## Interface

```python
def run_signals(
    instruments: list[str] | None = None,
    intervals: list[str] | None = None,
) -> dict:
    """
    Compute rule-based signals for all instruments and intervals.

    Args:
        instruments: list of s3_key values (e.g. ["EURUSD"]). Defaults to all.
        intervals: list of interval strings (e.g. ["1d"]). Defaults to all.

    Returns:
        {"succeeded": [...], "failed": [...]}
    """
```

### Integration with feature generation

```python
# apps/api/livewell/features/features.py (addition)
from livewell.signals.signals import run_signals

def run_features(instruments=None, intervals=None):
    ...  # existing logic
    try:
        run_signals(instruments=instruments)
    except Exception as exc:
        logger.error("signal generation failed: %s", exc)
    return {"succeeded": succeeded, "failed": failed}
```

Signal failures are logged but do not affect `run_features()`'s return value.

---

## Data Flow

### Per instrument+interval

1. List all year keys under `features/{INSTRUMENT}/{INTERVAL}/` and read all Parquet files; also read all `prices/{INSTRUMENT}/{INTERVAL}/` Parquets and inner-join on `date` to obtain `close`
2. Concatenate into a single DataFrame, sort by `date`, dedup — full history needed for consistent indicator context
3. Apply the 5-stage pipeline row-by-row to produce all signal columns
4. Split results by calendar year
5. For each year, read existing `signals/` Parquet (if any), merge+dedup on `date`, write back to S3

### Error isolation

Each instrument+interval pair is processed in a try/except block. A failed pair logs the error and continues. `run_signals()` returns `{"succeeded": [...], "failed": [...]}`.

---

## Testing

### In scope for 1C (16 tests)

| Test | What it verifies |
|---|---|
| `test_signal_columns_defined` | `SIGNAL_COLUMNS` contains all expected output columns |
| `test_bullish_setup_valid` | All 5 stages pass on clean bullish row → `signal_valid=True`, `direction="buy"` |
| `test_bearish_setup_valid` | All 5 stages pass on clean bearish row → `signal_valid=True`, `direction="sell"` |
| `test_neutral_trend_invalid` | `ema_20 ≈ ema_50` → `signal_valid=False`, `direction="none"` |
| `test_overextension_invalidates_signal` | Bullish setup with `rsi_14=80` → `signal_valid=False` |
| `test_low_atr_invalidates_signal` | `atr_14` below `MIN_ATR_THRESHOLD` → `signal_valid=False` |
| `test_session_filter_low_quality` | EUR/USD row in Asian session UTC → `session_quality="low"`, `signal_valid=False` |
| `test_strike_candidate_bullish` | Strike = `close + atr_14 * 0.5`, rounded to pip precision |
| `test_strike_candidate_bearish` | Strike = `close - atr_14 * 0.5`, rounded to pip precision |
| `test_reasoning_completeness` | Each rejection condition appears by name in the `reasoning` JSON string |
| `test_run_signals_idempotent` | Running `run_signals()` twice on same data produces identical S3 output |
| `test_multi_year_continuity` | Full-history read across a year boundary produces consistent signals with no NaN bleed |
| `test_run_signals_writes_to_s3` | Parquet written to correct S3 key with correct schema |
| `test_run_signals_output_schema` | All columns present with correct dtypes |
| `test_run_signals_isolates_failures` | One instrument error doesn't block others |
| `test_features_triggers_signals` | `run_features()` calls `run_signals()` with correct `instruments` arg |

### Deferred to later phases

- Boundary tests: RSI exactly at 50, 75, 25
- EMA crossover timing: signal fires on the crossover bar, not the bar before
- Session boundary transitions: row timestamped exactly at session boundary edge
- Pip precision per instrument: all 5 instruments produce correctly rounded strikes
- End-to-end integration: `run_ingestion()` → `run_features()` → `run_signals()` with moto S3

---

## Timing Annotation

An informational extension to the pipeline adds two columns — `timing_slot` and `timing_risk` — derived from asset-class timing tables in `docs/nadex_timing_tables.md`. These describe how market structure changes at key intraday moments, providing context for how far in or out of the money a NADEX binary may move before expiry. They are appended to every signal row but never affect `signal_valid`.

See `docs/superpowers/specs/2026-04-30-timing-annotation-design.md` for full design detail, constants, and test coverage.

---

## Out of Scope

- Macro event calendar / high-impact release blocking — deferred to a later phase
- Expected value calculation — Sub-project 1D or Phase 2
- ML probability scoring — Phase 2
- DynamoDB persistence of signals — Phase 4
- NADEX live contract ladder — future sub-project

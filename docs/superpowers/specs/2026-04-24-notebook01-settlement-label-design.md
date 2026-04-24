# Notebook 01 Redesign — Settlement-Based Label Construction

## Goal

Replace the D+1 daily close approximation for ITM labels with actual NADEX settlement outcomes sourced from the `nadex-daily-results` S3 bucket. This is the only change to the Phase 2 pipeline; notebooks 02–04 are untouched.

## Background

The original notebook 01 derived binary ITM labels by comparing the D+1 close price against each signal's `strike_candidate`. This approximation produced a ~22% win rate, which conflicts sharply with the ~57% win rate observed in real NADEX settlement data (Mar–Dec 2025). The root cause: NADEX daily contracts settle at 2pm ET, not at the daily close. A contract can be OTM at the close but ITM at settlement, or vice versa.

The backtesting research notebook (`20260429-nadex-backtesting.ipynb`) already parsed and saved real settlement outcomes to `s3://nadex-daily-results/backtest/results/latest/trades.csv`. This spec replaces the approximation with a direct join to that data.

## Architecture

Only `derive_label` and `build_labeled_dataset` change. All other functions (`load_all_parquets`, `load_signals`, `load_prices`) are retained unchanged. `load_prices` is no longer called from `build_labeled_dataset` since prices are no longer needed for labeling.

**New function:** `load_settlement(s3_client) -> pd.DataFrame`
- Reads `s3://nadex-daily-results/backtest/results/latest/trades.csv`
- Filters to 3pm ET expiry only (`Exp Time` contains `"03:00 pm"`) — matches the fire-and-forget daily contract
- Parses `Date` to UTC-aware datetime
- Returns columns: `date`, `Ticker`, `Strike Price`, `In the Money`

**Revised function:** `derive_label(signals, settlement) -> pd.DataFrame`
- Old signature: `derive_label(signals, prices)`
- New signature: `derive_label(signals, settlement)`
- For each signal row `(date, s3_key)`:
  1. Filter settlement to matching `date` + `Ticker` (yfinance symbols match: `EURUSD=X`, `USDJPY=X`, `GC=F`, `ES=F`)
  2. Find the row with minimum `abs(Strike Price - strike_candidate)` — nearest-strike selection
  3. `label = In the Money` (0 or 1) from that row
  4. If no settlement match (instrument absent from settlement data, or date outside Mar–Dec 2025): `label = NaN`
- `direction == "none"` rows still get `label = NaN` (same as before)
- `close_d1` column is dropped (no longer computed)

**Revised function:** `build_labeled_dataset(bucket, interval) -> pd.DataFrame`
- Loads settlement data once before the per-instrument loop using a second `boto3.client("s3")` pointed at `nadex-daily-results`
- Passes settlement into `derive_label` for each instrument
- Prints per-instrument summary: total rows, labeled rows, NaN-due-to-no-settlement rows
- Output schema is otherwise identical to the original

## Data

**Source:** `s3://nadex-daily-results/backtest/results/latest/trades.csv`

Settlement CSV columns used:
- `Date` — settlement date, format `DD-MMM-YY` (e.g. `03-Mar-25`) — parse with `format="%d-%b-%y"`
- `Exp Time` — filter to rows containing `"03:00 pm"`
- `Ticker` — yfinance symbol (e.g. `EURUSD=X`)
- `Strike Price` — float
- `In the Money` — 0 or 1

**Instrument overlap (livewell pipeline vs settlement data):**

| Instrument | livewell s3_key | NADEX Ticker | In settlement? | Backtesting P&L |
|---|---|---|---|---|
| EUR/USD | `EUR-USD` | `EURUSD=X` | Yes | Positive (+$727) |
| GBP/USD | `GBP-USD` | `GBPUSD=X` | Yes | Negative (−$265, excluded) |
| USD/JPY | `USD-JPY` | `USDJPY=X` | Yes | Positive (+$645) |
| Gold | `XAU-USD` | `GC=F` | Yes | Positive (+$612) |
| US 500 | `SPX500-USD` | `ES=F` | Yes | Positive (+$277) |

Note: `GBPUSD=X` is in the livewell pipeline but was a negative-expectancy instrument in backtesting. Its rows will be labeled (settlement data exists) but the ML may learn to discount GBP/USD signals. This is a useful signal for the model to discover, not a reason to exclude it.

**S3 key mapping:** The livewell pipeline uses `s3_key` values like `EUR-USD`. The settlement data uses yfinance tickers like `EURUSD=X`. A lookup dict maps between them:

```python
S3_KEY_TO_TICKER = {
    "EUR-USD":    "EURUSD=X",
    "GBP-USD":    "GBPUSD=X",
    "USD-JPY":    "USDJPY=X",
    "XAU-USD":    "GC=F",
    "SPX500-USD": "ES=F",
}
```

**Date range:** Settlement data covers 2025-03-03 to 2025-12-19. Signals from 2023–2024 (yfinance backfill) will get `label = NaN` and be excluded from training. This leaves approximately 200 trading days × 4 positive-expectancy instruments = ~600–800 labeled rows in the ML training set.

**Expected label distribution:** ~55–57% positive (ITM), consistent with the backtesting win rate — a major improvement over the ~22% from the D+1 close approximation.

## Output

- File: `notebooks/livewell-nadex/data/phase2/labeled_signals.parquet` (unchanged path)
- Schema: all original signal columns + `label` (float: 0.0, 1.0, or NaN)
- `close_d1` column removed (no longer computed)
- Notebooks 02–04 consume this file unchanged — they only use `label`, not `close_d1`

## AWS Access

Both S3 buckets (`715853571313-livewell` and `nadex-daily-results`) must be accessible under the `livewell` AWS profile. The notebook uses two separate `boto3.client("s3")` instances — one per bucket. No cross-bucket calls.

## What Does NOT Change

- `load_all_parquets` — unchanged
- `load_signals` — unchanged
- `load_prices` — retained in the Cell 2 function block but no longer called from `build_labeled_dataset`; leave it in place so the cell is self-contained and the function is available if needed for inspection
- Output path and file name — unchanged
- Notebooks 02, 03, 04 — untouched
- `signal_valid` rows are still included (label may be 0 or 1 regardless of rule validity)

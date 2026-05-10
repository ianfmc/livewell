# Rules-Based Backtest — Design Spec

**Date:** 2026-05-09
**Status:** Approved

---

## Goal

Validate the LIVEWELL rules-based signal logic against full historical data (2019–present) to determine whether the current indicator filters produce a durable edge across market regimes. Results feed the existing Backtest Results UI page and provide the baseline against which Phase 2 ML improvements will be measured.

---

## Architecture

```
notebooks/livewell-nadex/backtest.ipynb
    └── calls apps/api/livewell/backtest/
            ├── loader.py       — reads Parquet from S3, signals from DynamoDB
            ├── outcome.py      — win/loss determination per trade
            └── aggregator.py   — builds summary dict (win rates, equity curve, breakdowns)

apps/api/tests/backtest/
    ├── test_outcome.py
    └── test_aggregator.py

apps/api/routers/backtest.py    — updated to read S3 summary instead of hardcoded data
s3://livewell-data-prod/backtest/summary.json   — output artifact
```

---

## Backtest Module (`apps/api/livewell/backtest/`)

### `loader.py`

- `load_price_history(s3_key: str, bucket: str) -> pd.DataFrame` — reads the annual Parquet files for a given instrument from S3, concatenates into a single DataFrame sorted by date
- `load_all_signals(env: str) -> list[dict]` — scans the `livewell-signals-{env}` DynamoDB table and returns all records

### `outcome.py`

- `is_win(direction: str, strike: float, next_close: float) -> bool`
  - `"call"` → `next_close > strike`
  - `"put"` → `next_close < strike`
- `resolve_trade(signal_row: dict, price_df: pd.DataFrame) -> dict | None`
  - Finds the next trading day's close after `signal_row["date"]`
  - Returns `None` if no next-day price exists (end of data, market holiday gap) — logged as skipped
  - Returns a trade result dict: `{ signal_id, date, instrument, direction, strike, next_close, win, signal_valid, regime }`

### `aggregator.py`

- `build_summary(trades: list[dict]) -> dict` — produces the summary JSON:
  - `totalTrades`, `winRate`, `avgEdge`, `maxDrawdown`
  - `equityCurve` — list of `{ date, value }` starting at $1000, $40 cost / $100 payout per trade
  - `rows` — breakdown by instrument × regime: `{ market, regime, trades, winRate, avgEdge, netReturn }`
  - `signalValidSplit` — `{ valid: { trades, winRate }, invalid: { trades, winRate } }` to measure filter value

---

## Inclusion Rules

- Include all signals where `direction != "none"` (call or put)
- Include signals regardless of `signal_valid` value — the `signalValidSplit` output measures filter value
- Expiry: end-of-day (next trading day's close vs strike candidate)

---

## Notebook (`notebooks/livewell-nadex/backtest.ipynb`)

Orchestrates the full run:
1. Load all signals from DynamoDB
2. For each instrument, load price history from S3
3. Resolve each signal to a win/loss outcome
4. Build summary and display inline charts (win rate by instrument, equity curve, signal_valid split)
5. Write `summary.json` to S3

---

## API Update (`apps/api/routers/backtest.py`)

Replace hardcoded response with an S3 read:
- `GET /api/backtest/summary` reads `s3://livewell-data-prod/backtest/summary.json`
- Returns 404 if the file doesn't exist yet (backtest hasn't been run)
- Returns 200 with the JSON content if it exists

---

## Tests (`apps/api/tests/backtest/`)

### `test_outcome.py`
- `is_win` call/put direction logic
- `resolve_trade` with a next-day price present
- `resolve_trade` returns `None` when no next-day price exists
- `resolve_trade` handles market holiday gaps (non-consecutive dates)

### `test_aggregator.py`
- Win rate calculation
- Equity curve: starts at 1000, increases on win (+60), decreases on loss (-40)
- `maxDrawdown` calculation
- `signalValidSplit` correctly partitions valid vs invalid signals
- Empty trade list returns safe defaults

---

## Error Handling

- Missing next-day price → skip trade, log warning with signal_id
- Instrument has no Parquet file in S3 → skip instrument, log warning
- S3 write failure for `summary.json` → raise exception (don't silently swallow)

---

## Output Schema (`summary.json`)

```json
{
  "totalTrades": 840,
  "winRate": 0.54,
  "avgEdge": 0.08,
  "maxDrawdown": -0.12,
  "equityCurve": [
    { "date": "2019-01-02", "value": 1000.0 },
    ...
  ],
  "rows": [
    { "market": "EUR/USD", "regime": "Bullish", "trades": 120, "winRate": 0.58, "avgEdge": 0.12, "netReturn": 0.18 },
    ...
  ],
  "signalValidSplit": {
    "valid": { "trades": 210, "winRate": 0.61 },
    "invalid": { "trades": 630, "winRate": 0.51 }
  }
}
```

---

## Success Criteria

- Backtest runs over full 2019–present history without errors
- Win rate is reported per instrument and regime
- `signal_valid` split shows whether the filter adds value
- Summary JSON is readable by the existing Backtest Results UI page with no frontend changes
- All unit tests pass

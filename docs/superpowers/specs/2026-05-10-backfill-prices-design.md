# Backfill Historical Price Data — Design Spec

**Date:** 2026-05-10
**Status:** Approved

---

## Goal

Populate `s3://livewell-data-prod/prices/{s3_key}/1d/{year}.parquet` with 7 years of daily OHLCV history (2019–present) for all 19 NADEX instruments so the rules-based backtest produces meaningful results across multiple market regimes.

---

## Architecture

```
notebooks/livewell-nadex/backfill_prices.ipynb
    └── calls apps/api/livewell/ingestion/ingest.py
                └── run_ingestion(instruments=[s3_key], backfill=True, bucket=BUCKET)
                        └── fetch_ohlcv_backfill() via yfinance
                        └── write_parquet() → s3://livewell-data-prod/prices/{s3_key}/1d/{year}.parquet
```

No new Python modules. The notebook drives existing, tested ingestion code.

---

## Notebook (`notebooks/livewell-nadex/backfill_prices.ipynb`)

### Cell 1 — Setup

- `sys.path.insert` to `../../apps/api`
- Import `run_ingestion` from `livewell.ingestion.ingest`
- Import `INSTRUMENTS` from `livewell.ingestion.constants`
- Set `BUCKET = "livewell-data-prod"`

### Cell 2 — Dry run

- Print the full instrument list: name, ticker, s3_key
- Confirms what will be fetched before the long run starts

### Cell 3 — Backfill loop

- Iterate over all 19 instruments in `INSTRUMENTS`
- Per instrument: call `run_ingestion(instruments=[s3_key], backfill=True, bucket=BUCKET)`
- Print success or failure per instrument
- Collect failures; print summary at end
- Expected runtime: ~2–5 minutes total

### Cell 4 — Verify

- For each instrument, list S3 keys under `prices/{s3_key}/1d/`
- Read each Parquet and print the min/max date and row count
- Confirms data landed correctly and covers expected range

---

## S3 Layout

Written by existing `ingest.py` — no changes needed:

```
s3://livewell-data-prod/
  prices/
    EURUSD/1d/2019.parquet
    EURUSD/1d/2020.parquet
    ...
    EURUSD/1d/2026.parquet
    GBPUSD/1d/2019.parquet
    ...
```

---

## Instruments

All 19 from `livewell.ingestion.constants.INSTRUMENTS`:

| Name | Ticker | s3_key |
|------|--------|--------|
| EUR/USD | EURUSD=X | EURUSD |
| GBP/USD | GBPUSD=X | GBPUSD |
| USD/JPY | USDJPY=X | USDJPY |
| Gold | GC=F | XAUUSD |
| US 500 | ^GSPC | US500 |
| Crude Oil | CL=F | CL |
| Natural Gas | NG=F | NG |
| NASDAQ 100 | NQ=F | NQ |
| Russell 2000 | RTY=F | RTY |
| Dow Jones | YM=F | YM |
| Nikkei 225 | NKD=F | NKD |
| AUD/USD | AUDUSD=X | AUDUSD |
| AUD/JPY | AUDJPY=X | AUDJPY |
| EUR/JPY | EURJPY=X | EURJPY |
| EUR/GBP | EURGBP=X | EURGBP |
| GBP/JPY | GBPJPY=X | GBPJPY |
| USD/CAD | USDCAD=X | USDCAD |
| USD/CHF | USDCHF=X | USDCHF |
| USD/MXN | USDMXN=X | USDMXN |

---

## Error Handling

- `run_ingestion` catches per-instrument failures internally and returns a `failed` list
- Cell 3 checks the returned `failed` list and prints any failures
- Cell 4 skips instruments with no S3 keys and prints a warning

---

## Success Criteria

- All 19 instruments have Parquet files in S3 covering 2019–present
- Cell 4 shows min date ≤ 2019-01-07 and max date within the last 7 days for each instrument
- Re-running `backtest.ipynb` produces a non-zero win rate and a multi-year equity curve

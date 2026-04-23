# 05 Data Sources

## Purpose

This document defines the recommended data sources for LIVEWELL, with emphasis on cost-effectiveness, production practicality, and alignment with the actual recommendation problem.

The system needs two broad categories of external data:

1. forex market data for feature generation and outcome evaluation,
2. optional news / sentiment / event data for contextual filtering and model enhancement.

The design target is free or low-cost sources first.

## Data Source Principles

1. start with reliable price data before adding sentiment,
2. use data that is easy to automate and audit,
3. prefer providers with stable API behavior,
4. keep provider dependence light early in the project,
5. validate whether any additional data source materially improves results before increasing complexity.

## Core Market Data

## 1. Yahoo Finance via `yfinance`

### Why it is useful
- very easy to access from Python,
- good for historical daily data,
- easy for prototyping,
- broad symbol availability.

### Use in LIVEWELL
- historical research,
- baseline backtesting,
- rapid iteration during model development.

### Pros
- simple,
- free,
- quick setup.

### Cons
- not always ideal for institutional-grade operational dependence,
- API behavior is unofficial compared with dedicated paid feeds,
- intraday coverage and reliability may be more limited depending on use.

### Production guidance
Use it for prototyping and research. It is excellent for getting the system moving quickly.

## 2. Alpha Vantage

### Why it is useful
- explicit API access,
- supports forex endpoints,
- free tier is sufficient for modest daily workflows,
- straightforward integration for scheduled pulls.

### Use in LIVEWELL
- daily OHLC updates,
- low-cost operational source,
- alternative or complement to Yahoo Finance.

### Pros
- explicit API pattern,
- free key available,
- manageable call limits for daily jobs.

### Cons
- free tier rate limits,
- may require careful request budgeting if expanded significantly.

### Production guidance
Alpha Vantage is one of the best initial candidates for LIVEWELL’s operational price feed because the daily system does not require high request volume.

## 3. Dukascopy historical data

### Why it is useful
- granular historical data,
- useful for intraday or finer-resolution backtesting,
- valuable if later evaluating session-specific strategies.

### Use in LIVEWELL
- deeper research,
- high-resolution historical validation,
- advanced studies around session overlap and event windows.

### Pros
- strong historical depth,
- useful for minute or tick-level research.

### Cons
- more operational effort,
- less convenient than simple REST APIs for daily scheduled ingestion.

### Production guidance
Not necessary for the first implementation, but very valuable for later refinement.

## 4. HistData and similar downloadable archives

These can supplement historical testing when large downloadable datasets are useful.

### Best use
- offline backfill,
- comparative historical reconstruction,
- one-time research preparation.

## Recommended Price Data Strategy

### Phase 1
- Yahoo Finance and/or Alpha Vantage

### Phase 2
- standardize on one primary operational source
- keep second source as validation backup

### Phase 3
- add higher-resolution source like Dukascopy if needed for intraday refinement

## Contract Market Data

A major long-term advantage would come from storing historical NADEX contract prices themselves.

Desired fields:
- underlying pair
- strike
- expiry
- bid
- ask
- midpoint
- timestamp

Why important:
- lets LIVEWELL backtest actual market-implied probability,
- improves expected value realism,
- reduces dependence on approximating contract availability from underlying only.

If accessible through operational means, this is one of the most valuable future data additions.

## News and Sentiment Data

Sentiment is optional in the initial implementation and should be treated as an enhancement, not a dependency.

## 1. Finnhub

### Why it is useful
- accessible API,
- market news support,
- useful for lightweight financial sentiment workflows.

### Possible LIVEWELL use
- daily aggregated sentiment feature,
- macro mood proxy,
- headline count and relevance scoring.

## 2. NewsAPI

### Why it is useful
- broad aggregator,
- easy keyword-based pulls.

### Possible LIVEWELL use
- collect relevant headlines for USD, EUR, GBP, JPY, AUD, etc.,
- store headline corpus for later scoring.

### Caution
NewsAPI gives access to content, but sentiment may still need to be computed separately.

## 3. MarketAux or similar finance-news APIs

These services can be useful if they provide:
- precomputed sentiment,
- finance-specific filtering,
- lower implementation effort.

They are worth testing if a free or modest-cost tier is available.

## 4. RSS / direct source feeds

Examples:
- Reuters feeds where accessible,
- DailyFX,
- ForexFactory-related sources,
- other finance-news feeds.

### Use in LIVEWELL
- low-cost backup,
- custom collection pipeline.

### Trade-off
More implementation work, but less vendor dependency.

## Sentiment Modeling Options

If raw headlines are ingested, sentiment can be computed locally.

### Practical options
- simple lexicon baseline,
- finance-specific transformer such as FinBERT,
- aggregated daily sentiment score by currency or pair.

### Guidance
Do not add a sentiment feature just because it is available. Add it only if:
- it improves validation metrics,
- it improves calibration,
- or it helps avoid obvious bad trades around macro shocks.

## Economic Calendar / Event Data

Even if sentiment is deferred, macro event awareness should exist.

Useful data:
- high-impact release schedule,
- event category,
- release time,
- affected currency,
- severity.

Use this for:
- pre-event no-trade windows,
- post-event cooldown logic,
- optional regime tagging.

A simple economic calendar feed can add a lot of operational quality even before sentiment modeling is introduced.

## Data Quality Rules

All ingested data should be validated for:
- timestamp consistency,
- timezone normalization,
- missing intervals,
- duplicate records,
- stale source detection.

This matters as much as model choice. A good model on bad data is still a bad system.

## Storage Recommendation

Persist all external data in S3 before transformation.

Pattern:
- raw source-specific storage,
- normalized curated tables,
- feature generation downstream.

That makes reprocessing and provider replacement much easier.

## Recommended Initial Stack

For the first production-capable version of LIVEWELL:

### Required
- Alpha Vantage and/or Yahoo Finance for forex prices
- basic economic calendar feed

### Optional later
- Finnhub or NewsAPI for news
- local FinBERT sentiment scoring
- Dukascopy for higher-resolution historical research
- NADEX contract snapshot archive if obtainable

## Bottom Line

LIVEWELL should begin with the cleanest possible value chain:

- high-quality forex price data,
- deterministic feature generation,
- macro event awareness,
- optional sentiment only after evidence of benefit.

Start with price data first. That is where the real signal foundation lives.

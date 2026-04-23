# LIVEWELL Design

## Purpose

LIVEWELL is a production-oriented decision-support system for generating daily NADEX forex binary options recommendations. The system is designed to combine market structure, technical analysis, statistical learning, and automated cloud execution into a coherent pipeline that produces actionable, explainable trade candidates rather than opaque “black box” predictions.

The design assumes the system will operate as a daily recommendation engine, not a high-frequency execution bot. The central problem is to estimate whether a given forex pair is likely to finish above or below a relevant NADEX strike by a defined expiry, and then compare that estimated probability with the market-implied probability embedded in the contract price.

## System Objective

The core objective is:

1. ingest market and optional news data,
2. compute technical and contextual features,
3. estimate outcome probability for candidate binaries,
4. compare model probability to market-implied probability,
5. recommend only trades with positive expected value and acceptable operational risk.

The intended output is not simply “bullish” or “bearish.” It is a structured recommendation such as:

```text
Pair: EUR/USD
Expiry: End of Day
Direction: Buy
Strike: 1.1040
Max Entry Price: $48
Model Probability: 0.62
Market-Implied Probability: 0.48
Estimated Edge: +0.14
Reasoning: uptrend confirmed by EMA structure, RSI > 50, MACD turning positive, strike within ATR-adjusted daily range
```

## Design Principles

### 1. Probability-first thinking

NADEX binaries are naturally probabilistic instruments because contract prices sit on a 0 to 100 scale. LIVEWELL should therefore treat every recommendation as a probability estimation problem, not merely a directional forecast.

### 2. Explainability over unnecessary complexity

A slightly weaker but understandable model is preferable to a marginally stronger model that is difficult to debug, calibrate, or trust. This makes logistic regression and tree-based methods especially attractive early in the lifecycle.

### 3. Technical confluence before model confidence

The system should not recommend trades based on a single indicator or a raw model score alone. Trend, momentum, volatility, time-of-day, and strike feasibility should all align before a signal is emitted.

### 4. Modular architecture

The system is intentionally split into separate concerns:

- market model,
- trading strategy,
- machine learning models,
- pipeline architecture,
- data sources,
- roadmap.

That structure supports use by Claude Code, humans, and future agentic orchestration layers.

### 5. Daily operational cadence

The design is optimized for a daily workflow:
- data refresh after market close or at scheduled evening update,
- overnight or scheduled feature generation,
- recommendation generation before the next trading session.

This aligns with the target operating model of updating daily around 18:00 local time and producing next-morning guidance.

## Architecture Overview

LIVEWELL has five logical layers.

### Layer 1: Market semantics

This layer defines how NADEX binaries behave:

- price maps to implied probability,
- risk and reward are capped,
- trade value exists only when model probability diverges meaningfully from market-implied probability.

See `01_market_model.md`.

### Layer 2: Signal generation

This layer defines deterministic trade logic using:
- EMAs for trend,
- MACD for trend confirmation and momentum shift,
- RSI for timing and momentum bias,
- ATR for feasibility and strike selection,
- session timing and news-awareness filters.

See `02_trading_strategy.md`.

### Layer 3: Probability modeling

This layer translates features into calibrated outcome probabilities using:
- logistic regression,
- random forest,
- optionally LSTM later if justified by data and performance.

See `03_ml_models.md`.

### Layer 4: Data and execution pipeline

This layer handles:
- ingestion,
- storage,
- feature engineering,
- inference,
- recommendation persistence,
- scheduled execution on AWS.

See `04_pipeline_architecture.md`.

### Layer 5: Evolution path

This layer defines how the system matures from a rules-based engine to a production-grade, ML-backed, later agent-extended architecture.

See `06_roadmap.md`.

## Production Scope

LIVEWELL is not initially designed to:
- auto-execute live trades without oversight,
- optimize across full portfolio allocation,
- perform tick-level or microstructure analysis,
- behave as a continuous intraday autonomous trader.

It is designed to:
- generate daily recommendations,
- rank candidate contracts,
- provide rationale,
- preserve reproducibility and traceability,
- support progressive automation.

## Expected Repositories / Docs Usage

These markdown files should function as the canonical design package for code generation and implementation:

- `livewell_design.md` — executive and engineering overview
- `01_market_model.md` — pricing and market structure
- `02_trading_strategy.md` — signal logic and trade rules
- `03_ml_models.md` — model comparison and validation design
- `04_pipeline_architecture.md` — AWS and dataflow implementation
- `05_data_sources.md` — external data providers and integration guidance
- `06_roadmap.md` — staged delivery plan

## Definition of “production-grade” for LIVEWELL

For this project, production-grade means:

- deterministic and reproducible calculations,
- versioned features and model artifacts,
- clear separation of training and inference,
- stored outputs and audit trail,
- risk filters before recommendation output,
- easy debugging,
- cost-controlled cloud deployment,
- graceful handling of missing or low-quality data.

## Immediate Implementation Guidance

The most practical initial sequence is:

1. implement deterministic feature generation and rule-based screening,
2. backtest on historical underlying price data,
3. add logistic regression probability layer,
4. compare against random forest,
5. operationalize on AWS with daily schedule,
6. add sentiment only if it measurably improves outcomes,
7. consider deeper learning or agentic orchestration only after the baseline system is stable.

## Cross-file Dependency Map

- `01_market_model.md` defines what counts as edge.
- `02_trading_strategy.md` defines when a trade candidate is valid.
- `03_ml_models.md` defines how probabilities are estimated and validated.
- `04_pipeline_architecture.md` defines how the system runs every day.
- `05_data_sources.md` defines what information feeds the system.
- `06_roadmap.md` defines how capability is expanded without destabilizing the core.

## Final Position

LIVEWELL should be treated as a disciplined probabilistic recommendation engine for NADEX forex binaries. The system’s strength will come from combining:
- transparent market logic,
- indicator confluence,
- calibrated probabilities,
- operational rigor.

That combination is more important than maximizing model sophistication too early.

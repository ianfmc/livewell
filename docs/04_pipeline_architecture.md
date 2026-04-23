# 04 Pipeline Architecture

## Purpose

This document defines the production architecture for LIVEWELL on AWS. It covers how data should move from ingestion through feature engineering, inference, recommendation generation, storage, and future retraining.

The architecture is designed to be:
- modular,
- auditable,
- cost-conscious,
- easy to evolve,
- aligned with daily recommendation generation.

## Architectural Principles

1. **Separate training from inference**
2. **Store raw and derived data in S3**
3. **Use event-driven orchestration for daily runs**
4. **Treat features and model artifacts as versioned assets**
5. **Favor simple managed AWS services before adding complexity**
6. **Design for eventual agent integration without depending on it now**

## High-Level Production Flow

### Daily inference flow

1. ingest latest forex market data
2. optionally ingest news / macro / sentiment data
3. compute indicators and derived features
4. load approved model artifact
5. score candidate setups
6. compare model probabilities to market-implied probabilities
7. apply strategy and risk filters
8. write recommendation outputs
9. optionally notify downstream consumers or UI

### Periodic training flow

1. pull historical data from S3
2. reconstruct feature set
3. build labels
4. train and evaluate candidate models
5. calibrate probabilities
6. register winning artifact
7. promote approved model for inference

## AWS Service Recommendations

## Storage: Amazon S3

S3 should be the canonical storage layer for:

- raw market data
- raw news data
- engineered features
- training datasets
- model artifacts
- evaluation reports
- recommendation outputs

### Suggested S3 layout

```text
s3://livewell/
  raw/
    forex/
    news/
    macro/
  curated/
    candles/
    sentiment/
  features/
    pair=EURUSD/
    pair=GBPUSD/
  training/
    datasets/
    metrics/
  models/
    logistic/
    random_forest/
    production/
  outputs/
    recommendations/
    audits/
```

This keeps lineage clean and makes downstream automation simpler.

## Development environment

For development and experimentation, use a managed notebook environment.

Recommended:
- SageMaker notebook or equivalent managed Jupyter environment

Why:
- easy startup,
- good S3 integration,
- suitable for model development,
- convenient for exploratory analysis.

This matches the original design guidance that favors SageMaker notebooks for development over a more complex ECS-hosted notebook setup.

## Inference compute

Recommended early production options:
- AWS Lambda if workload remains lightweight,
- ECS Fargate if dependency stack or runtime length exceeds Lambda comfort,
- Step Functions if orchestration needs branch logic and traceability.

### Practical recommendation

Start with:
- EventBridge scheduled trigger
- Lambda or ECS task for daily inference job

Choose Lambda if:
- runtime is short,
- dependencies are manageable,
- workload is simple.

Choose ECS Fargate if:
- you want consistent containerized runtime,
- dependencies are heavier,
- execution time is longer,
- you plan to reuse the same image for development parity and future services.

Given the project direction and eventual agentic expansion, ECS Fargate is likely the stronger long-term inference container, but Lambda may be the faster initial implementation.

## Scheduling

Use EventBridge to trigger:
- daily market data refresh,
- daily recommendation generation,
- periodic retraining jobs,
- health checks if desired.

This aligns well with the project’s intended daily refresh cadence.

## Training compute

Training should be decoupled from inference.

Options:
- SageMaker training jobs,
- ECS batch-style container runs,
- notebook-triggered manual training during early stage.

Recommended production direction:
- start with controlled notebook-based training,
- move to scheduled or manual-trigger training job once process stabilizes.

## Data Ingestion Layer

## Forex data ingestion

Responsibilities:
- fetch OHLCV or equivalent candle data,
- normalize timestamps,
- write raw files to S3,
- maintain append-only raw history,
- ensure missing interval detection.

## News / sentiment ingestion

Optional early, but if implemented:
- fetch headlines and metadata,
- normalize source and timestamp,
- persist raw JSON/text in S3,
- transform later into daily or intraday sentiment features.

## Contract market data ingestion

If you later ingest NADEX contract snapshots:
- capture bid, ask, midpoint, timestamp, strike, expiry,
- persist snapshot history,
- derive implied probabilities downstream.

That is highly valuable because it allows direct historical backtesting of edge against observed contract prices rather than underlying only.

## Feature Engineering Layer

Feature generation should be deterministic and rerunnable.

Core outputs:
- EMA features,
- MACD features,
- RSI,
- ATR,
- strike distance,
- session tags,
- macro proximity features,
- optional sentiment scores.

Feature generation should write feature tables back to S3 with:
- schema version,
- pair,
- timeframe,
- generation timestamp.

### Recommended pattern

```text
raw -> curated -> features
```

Do not compute features ad hoc inside every model call. Centralize feature generation so both training and inference use the same logic.

## Model Serving Pattern

The approved production model should be loaded from a known artifact location, such as:

```text
s3://livewell/models/production/current/
```

That location should contain:
- serialized model
- calibration object
- feature manifest
- metadata JSON

### Inference steps

1. load feature manifest
2. validate incoming feature frame
3. load model
4. score probabilities
5. calibrate probabilities if needed
6. combine with contract price and rule filters
7. persist scored candidates and final recommendations

## Recommendation Output Contract

The output of the system should be structured and machine-readable.

Suggested fields:
- pair
- generation timestamp
- expiry
- strike
- side
- entry price / max acceptable entry
- implied probability
- model probability
- edge
- expected value
- technical reasons
- risk flags
- model version
- feature version
- confidence / rank

Write output to:
- S3 as JSON/CSV/Parquet,
- optionally DynamoDB or RDS if UI needs low-latency lookup,
- optionally API layer if the React frontend will consume it directly.

## UI / API Integration Direction

Because the broader project includes a React-based UI, production architecture should eventually expose recommendations through a clean API.

Possible approach:
- inference writes recommendation table to S3 and/or DynamoDB,
- lightweight API service exposes latest recommendations,
- frontend reads from that API.

This keeps the UI decoupled from core model execution.

## Logging and Auditability

Production-grade means traceability.

Every run should log:
- job start/end time,
- data freshness status,
- pairs processed,
- feature generation version,
- model version used,
- number of candidates evaluated,
- number of recommendations emitted,
- error conditions.

Store audit logs to S3 and optionally CloudWatch.

## Failure Handling

The pipeline should fail gracefully.

Examples:
- if one pair’s data is missing, continue processing others if safe,
- if sentiment feed fails, proceed without sentiment if optional,
- if model artifact missing or schema mismatch occurs, block recommendation generation and surface alert,
- if market prices unavailable, do not guess contract implied probabilities.

## Deployment Recommendation

## Early production

- SageMaker notebook for development and manual validation
- S3 for all storage
- EventBridge for scheduling
- ECS Fargate container for daily batch-style recommendation job
- CloudWatch for logs
- optional SNS/email/webhook notification for completed recommendation set

## Why ECS Fargate is attractive here

- consistent runtime environment,
- easy packaging of Python dependencies,
- good path to future container-based agents or services,
- natural fit for scheduled non-interactive jobs.

## Training / retraining policy

Do not retrain on every daily run.

Recommended:
- retrain on defined cadence, such as weekly or monthly,
- or retrain when performance monitoring detects drift.

Each promoted model must pass:
- minimum validation metrics,
- calibration threshold,
- backtest profitability checks,
- sanity review.

## Monitoring

Beyond infrastructure monitoring, maintain model monitoring:

- hit rate of recommendations
- realized vs predicted probability
- distribution drift in features
- recommendation count by pair and session
- average edge vs realized outcome

If these degrade, retraining or rule adjustments may be needed.

## Security / IAM

Use least-privilege IAM roles:
- inference task can read features, models, and raw price data, and write outputs,
- training job can read historical datasets and write model artifacts,
- UI/API service can read published outputs but not modify models.

## Future Agent Compatibility

The architecture should make it easy to introduce agents later by exposing discrete services such as:
- data fetch service,
- feature generation service,
- scoring service,
- recommendation explanation service.

That future is easier if the current pipeline is already modular and containerized.

## Bottom Line

The production architecture for LIVEWELL should be an event-driven AWS pipeline centered on S3, deterministic feature generation, model artifact versioning, and scheduled inference. Keep the first version simple, auditable, and batch-oriented. Complexity should be added only when it enables measurable business value or maintainability.

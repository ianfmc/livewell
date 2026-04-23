# 06 Roadmap

## Purpose

This document defines the staged roadmap for turning LIVEWELL from a design into a reliable production system. The roadmap is intentionally incremental so that the project gains real capability early without creating unnecessary technical debt or model complexity.

## Guiding Philosophy

The right way to build LIVEWELL is:

1. establish a technically coherent baseline,
2. validate with historical data,
3. operationalize the simplest version that works,
4. add ML only where it improves quality,
5. add sentiment only where it proves useful,
6. add automation and agents only after the core system is trustworthy.

This keeps the project grounded in measurable progress.

## Phase 1 — Market and Signal Baseline

### Goal
Create a deterministic rule-based recommendation engine driven by technical indicators and market logic.

### Deliverables
- forex data ingestion
- feature generation for EMA, MACD, RSI, ATR
- session and macro-event filters
- strike feasibility logic
- expected value and implied probability logic
- recommendation schema and storage
- initial backtest framework

### Success criteria
- reproducible historical runs
- valid “no trade” handling
- candidate recommendations can be explained in plain language
- output format is stable

### Why this phase matters
This is the control system against which all later ML should be judged.

## Phase 2 — Baseline ML Layer

### Goal
Add probability estimation using simple, interpretable models.

### Deliverables
- labeled dataset construction
- logistic regression baseline
- walk-forward validation
- calibration analysis
- comparison of rules-only vs rules-plus-model

### Success criteria
- model probabilities are at least reasonably calibrated
- model adds measurable ranking or filtering value
- no unacceptable instability across validation windows

### Exit condition
If logistic regression adds little value, do not force complexity yet. Continue improving rules and features.

## Phase 3 — Stronger Tabular Models

### Goal
Benchmark and possibly promote a stronger structured-data model.

### Deliverables
- random forest benchmark
- hyperparameter tuning workflow
- feature importance review
- calibrated output comparison vs logistic regression

### Success criteria
- material improvement over logistic on time-aware validation,
- stable generalization,
- acceptable interpretability and calibration.

### Promotion rule
Use random forest in production only if it produces a meaningful improvement rather than a cosmetic one.

## Phase 4 — Production AWS Pipeline

### Goal
Operationalize LIVEWELL as a daily batch recommendation system.

### Deliverables
- S3 data layout
- scheduled ingestion
- scheduled feature generation
- production inference job
- recommendation output persistence
- run logging and audit trail
- error handling and alerting

### Success criteria
- daily run completes unattended,
- outputs are versioned,
- failures are visible,
- recommendations are reproducible from stored inputs and model version.

### Preferred end state
- EventBridge scheduling
- ECS Fargate or Lambda inference path
- notebook or dedicated training workflow
- model artifact versioning in S3

## Phase 5 — Performance Monitoring and Retraining

### Goal
Manage LIVEWELL as an operating system, not a one-time model.

### Deliverables
- realized trade outcome tracking
- model calibration monitoring
- feature drift checks
- recommendation hit-rate reporting
- retraining cadence policy

### Success criteria
- you know when the system is improving or degrading,
- retraining is governed rather than ad hoc,
- model promotion is based on evidence.

## Phase 6 — Optional Sentiment Integration

### Goal
Add news or macro sentiment only if it helps.

### Deliverables
- headline ingestion
- sentiment scoring feature
- ablation tests: with and without sentiment
- event-window behavior analysis

### Success criteria
- sentiment improves validation or operational robustness,
- added complexity is justified,
- feature behaves consistently enough to trust.

### Caution
Sentiment should not be treated as mandatory. It is an enhancement path, not a starting dependency.

## Phase 7 — Advanced Sequence Modeling

### Goal
Explore LSTM or other temporal models if simpler models plateau.

### Deliverables
- sequence dataset generation
- temporal cross-validation experiments
- calibration comparison against tabular models

### Success criteria
- meaningful out-of-sample improvement,
- acceptable operational cost,
- sufficient interpretability / governance for production use.

### Default guidance
Do not rush here. This is research until proven otherwise.

## Phase 8 — Agentic Extension

### Goal
Evolve LIVEWELL into a modular AI-assisted operating system.

### Candidate agent roles
- data ingestion agent
- feature validation agent
- recommendation explanation agent
- monitoring / drift agent
- retraining evaluation agent

### Why this should come later
Agents amplify the architecture you already have. They do not rescue an unclear system design. Get the deterministic and ML foundation right first.

## Suggested Milestone Sequence

### Milestone 1
Rules-only historical engine complete

### Milestone 2
Probability baseline complete

### Milestone 3
Production daily run complete

### Milestone 4
Monitoring and retraining policy complete

### Milestone 5
Optional sentiment validated

### Milestone 6
Agent-assisted operations introduced

## Practical “Definition of Done” for Production v1

LIVEWELL v1 should be considered production-capable when it can:

- ingest fresh price data on schedule,
- compute indicators reproducibly,
- evaluate candidate binaries using market-implied probability and expected value logic,
- apply time-of-day and event filters,
- score candidates with an approved model or deterministic ranking,
- publish structured recommendations,
- log every run and artifact version,
- be rerun from stored data to reproduce results.

## Bottom Line

The roadmap is deliberately conservative in the right places. The system should become useful before it becomes elaborate. Production value will come from reliability, auditability, and calibrated edge — not from jumping too early to complex models or agentic workflows.

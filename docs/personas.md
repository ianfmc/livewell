# LIVEWELL Personas

Four personas reflect the different modes in which LIVEWELL is used. At this stage the same person fills all four roles.

---

## Trader
- **Goals:** Make disciplined daily trade decisions using clear, ranked recommendations; know when not to trade
- **Pain Points:** Signal noise; overtrading temptation; trusting a system that can't explain itself
- **Tech Savviness:** Medium
- **Primary surfaces:** Dashboard, Daily Signals, Contract Detail, Signal Tracker, Options Advisor

## Researcher
- **Goals:** Validate hypotheses; compare model variants; understand where the strategy works and where it fails
- **Pain Points:** Data leakage; overfitting; inconsistent experiment conditions; in-sample metrics mistaken for out-of-sample
- **Tech Savviness:** High
- **Primary surfaces:** Backtest Results, Model Health, Signal Tracker

## Developer
- **Goals:** Modular, testable code; stable contracts between pipeline layers; easy strategy and model swapping
- **Pain Points:** Notebook sprawl; ad-hoc configuration; tight coupling between stages; schema drift
- **Tech Savviness:** High
- **Primary surfaces:** How It Works (as author), API contracts, repo structure

## Operator
- **Goals:** Visibility into daily runs; fast diagnosis of failures; confidence the system ran correctly before trusting today's output
- **Pain Points:** Silent failures; no way to distinguish "no setups today" from "pipeline broke"; stale model going undetected
- **Tech Savviness:** Medium–High
- **Primary surfaces:** Model Health, Dashboard (health summary)

---

## System Properties (Non-Functional Requirements)

The following were represented as personas in an earlier draft. They are valid system constraints but not distinct user types.

- **Cost:** Cloud spend should be observable and bounded; prefer serverless/batch over always-on for this workload
- **Reliability:** Scheduled jobs must be idempotent; external data fetch failures should retry gracefully and alert on repeated failure
- **Auditability:** Every scored signal must be reconstructable from stored inputs and model version snapshot
- **Safety:** No live capital recommendations without explicitly enabled safeguards; paper-trade mode is the default
- **Security:** Least-privilege IAM; no credentials or sensitive data in logs or artifacts

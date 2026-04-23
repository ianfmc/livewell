# LIVEWELL User Stories

Persona abbreviations: **Tr** = Trader, **Re** = Researcher, **De** = Developer, **Op** = Operator.

---

## Epic A — Notebook Baseline ✓ Complete

Retained for context. These describe where the project started, not the target system.

- **A-1** *(Tr, done):* Run a single notebook to fetch data, compute indicators, and generate candidate signals
- **A-2** *(Re, done):* Backtest by simulating daily NADEX contracts on historical data
- **A-3** *(Tr, done):* View concise summary results — win rate, P&L, drawdown

---

## Epic B — Product Shell and Navigation

- **B-1** *(Tr):* As a Trader, I want a persistent navigation structure with clear page labels so I can move between views without losing context
- **B-2** *(Tr):* As a Trader, I want the app to remember my theme preference so I don't reset it each session

---

## Epic C — Dashboard

- **C-1** *(Tr):* As a Trader, I want a morning briefing showing market regime, opportunity count, and no-trade warnings so I can decide in under a minute whether today has actionable setups
- **C-2** *(Tr):* As a Trader, I want the Dashboard to display "No valid setups today" prominently when the system is being appropriately selective so I trust the output rather than second-guess it
- **C-3** *(Tr):* As a Trader, I want a recent performance snapshot on the Dashboard so I can see at a glance whether the system is in a good or poor streak

---

## Epic D — Daily Signals

- **D-1** *(Tr):* As a Trader, I want to see today's scored contract candidates in a filterable view (by market, expiry window, minimum edge, confidence tier) so I can narrow to the strongest setups quickly
- **D-2** *(Tr):* As a Trader, I want each row to show strike, payout, breakeven probability, model probability, and estimated edge so I can compare candidates without opening each one
- **D-3** *(Tr):* As a Trader, I want contracts to show whether they pass all trading rules so I can immediately identify no-trade candidates

---

## Epic E — Contract Detail

- **E-1** *(Tr):* As a Trader, I want to open a Contract Detail view and read why LIVEWELL recommends or rejects a contract so I can validate the reasoning before acting
- **E-2** *(Tr):* As a Trader, I want to see relevant features and reason codes so I understand which indicators are driving the recommendation
- **E-3** *(Re):* As a Researcher, I want to see comparable historical setups on the Contract Detail page so I can judge whether this setup type has a good track record
- **E-4** *(Tr):* As a Trader, I want an explicit recommendation status (take / watch / pass) so the system gives me a clear position, not just raw data

---

## Epic F — Backtest Results

- **F-1** *(Re):* As a Researcher, I want to view backtest results segmented by market, regime, and time-of-day so I can identify where the strategy is strongest and weakest
- **F-2** *(Re):* As a Researcher, I want calibration plots so I can verify whether model probabilities correspond to observed outcomes
- **F-3** *(Re):* As a Researcher, I want drawdown and streak analysis so I can assess the capital and emotional demands of running the strategy live
- **F-4** *(Re):* As a Researcher, I want in-sample and out-of-sample results clearly separated so I am never misled by training-period performance

---

## Epic G — Model Health

- **G-1** *(Op):* As an Operator, I want a Model Health page showing training date, data freshness, validation metrics, and drift indicators so I can tell whether today's model output should be trusted
- **G-2** *(Op):* As an Operator, I want the current production model version displayed so I can confirm which artifact is running

---

## Epic H — How It Works

- **H-1** *(Tr):* As a Trader, I want to read a plain-language explanation of how LIVEWELL generates recommendations so I can calibrate how much weight to give the system's output
- **H-2** *(Tr):* As a Trader, I want this page to explain what "edge" means in NADEX terms so the core concept is never ambiguous
- **H-3** *(De):* As a Developer, I want this page maintained as a living document so future collaborators understand the system's logic without reading the full codebase

---

## Epic I — Signal Tracker

- **I-1** *(Tr):* As a Trader, I want to review every past signal alongside its realized outcome so I can track real-world performance separately from backtested performance
- **I-2** *(Tr):* As a Trader, I want to record whether I took, skipped, or modified each signal so I can distinguish system performance from my own execution quality
- **I-3** *(Re):* As a Researcher, I want model calibration tracked over time so I can detect drift before it materially harms results

---

## Epic J — Options Advisor

- **J-1** *(Tr):* As a Trader, I want to ask the system a structured question about a specific setup and receive a reasoned response so I can pressure-test my thinking before committing to a trade
- **J-2** *(Tr):* As a Trader, I want the Options Advisor to begin as a structured interface so I get consistent, grounded responses rather than open-ended chat

*Note: The Options Advisor starts as structured UI. Agentic implementation is gated on Epic P.*

---

## Epic K — Portable Backend Core

- **K-1** *(De):* As a Developer, I want notebook logic extracted into pure Python functions so I can test and reuse it without running a notebook
- **K-2** *(De):* As a Developer, I want configuration externalized so I can adjust parameters without editing source code

---

## Epic L — Observability and Experiment Tracking

- **L-1** *(Re):* As a Researcher, I want experiment parameters, model versions, and outcomes logged automatically so I can compare runs without manual record-keeping
- **L-2** *(Op):* As an Operator, I want runtime metrics exposed per pipeline run so I can confirm each stage completed and how long it took

---

## Epic M — Data and Model Interfaces

- **M-1** *(De):* As a Developer, I want typed I/O schemas for all pipeline data objects so I catch contract violations before they reach production
- **M-2** *(De):* As a Developer, I want a pluggable strategy interface so I can swap or compare strategies without restructuring the pipeline

---

## Epic N — Scheduled Operations

- **N-1** *(Op):* As an Operator, I want a scheduled daily scoring job to run unattended so I don't need to trigger it manually each morning
- **N-2** *(Op):* As an Operator, I want health checks and retries on all data fetch steps so transient failures don't silently produce stale or missing results
- **N-3** *(Op):* As an Operator, I want a dry-run mode that exercises the full pipeline without persisting outputs so I can test changes safely

---

## Epic O — Deployment and Infrastructure

- **O-1** *(De):* As a Developer, I want the runtime containerized so I can reproduce the execution environment exactly across local and cloud
- **O-2** *(De):* As a Developer, I want least-privilege IAM roles for all cloud components so a compromised credential has minimal blast radius
- **O-3** *(Re):* As a Researcher, I want every scored signal stored with its inputs and model version so any recommendation can be reconstructed after the fact

---

## Epic P — Agent Layer *(Phase 5 — gated)*

Not scheduled until Phases 1–4 are complete and the system has stable contracts, repeatable outputs, and a strong audit trail.

- **P-1** *(Tr):* As a Trader, I want a morning briefing agent to summarize today's setups and regime context so I can start the day without manually reviewing every panel
- **P-2** *(Tr):* As a Trader, I want a signal explanation agent to answer "why does LIVEWELL like this trade?" conversationally so I can explore the reasoning interactively
- **P-3** *(Op):* As an Operator, I want an orchestration agent to coordinate data refresh, scoring, and health checks so routine operations run without manual intervention
- **P-4** *(De):* As a Developer, I want agent roles clearly separated from deterministic system logic so agents can summarize and orchestrate but never override pricing, probability, or decision calculations

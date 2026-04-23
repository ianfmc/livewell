# LIVEWELL Build Plan

## North Star
Build **LIVEWELL** as a production-capable decision support system for **NADEX binary options**, starting with a strong front end, then replacing notebook logic with services, then layering in agents only after the core workflow is reliable.

---

## Product Thesis
You found the right reference point.

What the screenshots validate is not just the visual direction, but the **interaction model**:
- a home dashboard with a market summary
- a daily signal view with filtering and explanation
- backtest and model-health pages for trust
- a “how it works” section for interpretability
- progressively deeper drill-downs instead of one giant screen

That is exactly the right shape for LIVEWELL.

The key adjustment is this:

**LIVEWELL should not begin as an “agentic trading system.”**
It should begin as a **clear, reliable, inspectable decision-support platform** for NADEX binaries.

Agents come later, after the system has stable contracts, repeatable outputs, and trustworthy metrics.

---

## Strategic Build Order

### Phase 1 — Front End First
Build the UI shell and all major pages with realistic mock or static data.

Goal:
- lock the product shape
- settle navigation and terminology
- define exact data contracts the backend must satisfy

Pages to build first:
1. **Dashboard / Home**
2. **Daily Signals**
3. **Contract Detail**
4. **Backtest Results**
5. **Model Health**
6. **How It Works**
7. **Signal Tracker / Outcome Review**
8. **Options Advisor**

Important adaptation:
This must be redesigned for **NADEX binaries**, not stocks.

So instead of:
- ticker
- long / short stock signal
- Kelly % on stock positions

LIVEWELL should center on:
- underlying market (NASDAQ, S&P 500, Gold, EUR/USD, etc.)
- contract type
- strike level / barrier
- expiration time
- probability estimate
- expected edge after fees / payout structure
- confidence level
- regime context
- reason codes / explanation
- “pass” as a first-class outcome

### Phase 2 — Backend Extraction from Jupyter
Convert notebook logic into clean services.

Goal:
- turn exploratory code into repeatable components
- separate feature engineering, training, inference, and evaluation
- make everything callable by APIs

Core modules:
1. Data ingestion
2. Feature engineering
3. Label generation
4. Model training
5. Model inference
6. Rule overlay / decision logic
7. Backtesting engine
8. Metrics + monitoring
9. Explanation generation

Design rule:
**Anything currently done manually in a notebook should become either a library function, service module, or scheduled job.**

### Phase 3 — Connect UI to Working Services
Goal:
- end-to-end usable system
- one source of truth for daily scoring and historical evaluation
- deployable internal product

This is the first point where LIVEWELL becomes “real.”

### Phase 4 — Production Hardening
Goal:
- improve reliability
- reduce hidden assumptions
- make outputs auditable

Needs:
- configuration management
- model versioning
- feature/version lineage
- test coverage
- logging and tracing
- failure alerts
- manual override / disable switch
- explicit separation of in-sample vs out-of-sample metrics

### Phase 5 — Agentic Layer
Only after Phases 1–4 are working.

Goal:
- agents orchestrate analysis and user interaction
- agents do **not** replace deterministic financial logic

Agents should sit on top of a stable system, not inside the critical path before you trust the system.

---

## Product Adaptation for NADEX
The screenshots are excellent, but they assume a stock-selection workflow. LIVEWELL needs a **contract-selection workflow**.

### Recommended core objects

#### 1. Market Snapshot
Examples:
- NASDAQ 100
- US 500
- Gold
- EUR/USD

Fields:
- current price
- short-term realized volatility
- trend state
- momentum state
- event risk flag
- session/time-of-day context

#### 2. Opportunity Window
Represents the current trading setup for a specific expiry window.

Fields:
- market
- timestamp
- expiration horizon
- regime classification
- candidate direction(s)
- model confidence
- no-trade flag

#### 3. Binary Contract Candidate
The actual trade candidate.

Fields:
- market
- contract identifier
- strike / barrier
- expiry
- payout
- cost
- implied breakeven probability
- model probability
- estimated edge
- confidence tier
- rationale summary

#### 4. Executed Trade / Paper Trade
Fields:
- entry time
- market
- contract
- cost
- payout at risk/reward
- model snapshot version
- rationale snapshot
- outcome

---

## Front-End Information Architecture

## 1. Dashboard
Purpose: “What matters right now?”

Components:
- market regime banner
- today’s opportunity count
- top candidate contracts
- no-trade warnings
- model health summary
- recent performance snapshot
- morning briefing

Headline philosophy:
The dashboard should often say **“No valid setups”** and feel useful anyway.

That will be a major sign of maturity.

## 2. Daily Signals
Purpose: inspect today’s candidate contracts.

Table ideas:
- market
- expiry
- strike
- direction
- payout
- breakeven %
- model probability
- estimated edge
- confidence
- regime
- explanation availability

Filters:
- market
- expiry window
- minimum edge
- minimum confidence
- only trades passing rules
- include/exclude event-risk windows

## 3. Contract Detail
Purpose: explain one candidate deeply.

Show:
- contract economics
- why model likes/dislikes it
- relevant features
- comparable historical setups
- risk notes
- expected failure modes
- recommendation: take / watch / pass

## 4. Backtest Results
Purpose: trust but verify.

Must include:
- out-of-sample results by contract family
- results by market regime
- results by time-of-day bucket
- results by expiration horizon
- calibration plots
- drawdown / streak analysis
- “pass rate” and selectivity

## 5. Model Health
Purpose: is the model still behaving?

Show:
- training date
- data freshness
- validation metrics
- calibration error
- drift warnings
- feature availability issues
- current model version in production

## 6. How It Works
Purpose: make the system legible.

Audience: future-you and any collaborator.

Explain:
- what is being predicted
- what labels mean
- what features matter
- what “edge” means in NADEX terms
- what can go wrong
- why no-trade is valid

## 7. Signal Tracker
Purpose: grade the real world.

Show:
- every live/paper candidate produced
- whether it was taken or skipped
- realized outcome
- model calibration over time
- regime notes
- post-trade lessons

## 8. Options Advisor
Purpose: conversational layer / guided reasoning.

This can begin as a structured interface before it becomes agentic.

---

## Technical Architecture Recommendation

## Stack direction
Given your current trajectory, a pragmatic stack would be:

### Front End
- React + TypeScript
- Vite to start
- Tailwind + component library
- Recharts for internal charts
- Figma-to-React generation for layout scaffolding where it accelerates delivery

### Backend API
- Python FastAPI

Why:
- easiest bridge from Jupyter code
- clean model-serving path
- great for data/ML APIs

### Compute / Services
- AWS Lambda for light services
- containerized services for heavier workloads if needed
- Step Functions or EventBridge for orchestration

### Storage
- S3 for artifacts and historical data exports
- DynamoDB or PostgreSQL for signals, runs, trades, model metadata

### ML / Data Science Layer
- Python packages extracted from notebooks
- scikit-learn / XGBoost / LightGBM as appropriate
- separate train vs infer flows

### Platform / AWS support
- Amplify Gen 2 for selected front-end-facing AWS concerns such as auth, hosting, and storage where it speeds delivery
- APIs remain the contract boundary between the front end and the core backend
- EventBridge is for scheduled or async workflows, not primary page rendering

### Agent Layer Later
- LangGraph for orchestration
- MCP for tool access patterns
- A2A for agent interoperability where it genuinely helps

## Architecture decision
LIVEWELL should use a **decoupled architecture**.

That means:
- React + TypeScript for the front end
- FastAPI + Python modules for the core backend
- APIs for front-end/backend integration
- EventBridge for scheduled and event-driven workflows behind the scenes
- Amplify Gen 2 as a helpful platform layer, not the center of the ML system

### Why this is the right decision
- the front end can move quickly without dictating backend design
- the backend remains aligned to Python and ML reality
- notebook logic can be extracted cleanly into services
- future agents can call the same APIs and tools the UI uses
- infrastructure convenience does not force architectural coupling

### Rejected alternative
An Amplify-first backend for core model logic was considered but is not preferred.

Reason:
LIVEWELL’s hardest logic is not CRUD or generic app data. It is feature engineering, inference, edge logic, backtesting, and tracking. That logic belongs in a Python-first service architecture.

## When to use Figma generation vs hand-coded React
Figma-to-React generation is recommended as an **accelerator**, not as the enduring source of truth for complex product logic.

### Use Figma generation for
- app shell and navigation
- page layout scaffolding
- repeated cards and summary panels
- banners, headers, empty states, and informational sections
- visually consistent static or lightly interactive components

### Prefer hand-coded React for
- dense, filterable data tables
- chart-heavy analytical pages
- stateful workflows
- pages where product logic will evolve rapidly
- any screen tightly coupled to backend contracts and domain behaviors

### LIVEWELL recommendation
Use Figma generation first on:
- Dashboard shell
- Contract Detail shell
- Model Health
- How It Works

Prefer hand-built React first on:
- Daily Signals
- Backtest Results
- Signal Tracker
- Options Advisor

### Practical rule
Let Figma generation give you the first 60–70% of the layout work.
Do not let generated code become the architecture, the state model, or the domain contract.

## What to build first
The correct next move is to build the **application scaffold first**, then the first real page inside it.

Reason:
- navigation and visual language should be settled once
- page scaffolding forces consistent component patterns
- the first page can then be implemented without later rework to the shell
- generated or hand-built page components will have a stable home

Recommended sequence:
1. build the React application shell
2. create sidebar, header, route structure, and shared card/table primitives
3. implement the Dashboard as the first real page
4. use mock JSON matching the API contracts
5. then move to Daily Signals and Contract Detail

## Service Decomposition
These should become independent backend capabilities.

1. **Market Data Service**
   - pull and normalize underlying market data

2. **Feature Service**
   - compute derived features for each market/time window

3. **Labeling Service**
   - define “winning” contract outcomes historically

4. **Training Service**
   - train and store models

5. **Inference Service**
   - score candidate contracts

6. **Decision Service**
   - combine probabilities, payout, breakeven, and rules into “edge”

7. **Backtest Service**
   - replay historical sessions under realistic NADEX constraints

8. **Explanation Service**
   - generate plain-English rationale from structured facts

9. **Tracking Service**
   - persist signals, decisions, outcomes, and evaluation

---

## Most Important Modeling Shift
This is the big one.

For NADEX, the target should not be “will the underlying move 10% in 10 or 15 days?”
That stock-style framing helped you learn, but it is probably not the right production target.

For NADEX binaries, the model should eventually predict something closer to:

- probability the contract expires in the money
- probability distribution of price at expiry
- probability the market crosses a strike before expiry
- expected edge after payout structure and fees

In other words:

**Predict contract-relevant outcomes, not generic price movement.**

That is the bridge from “interesting ML” to “tradeable decision support.”

---

## Rules for the First Real Version

1. **NADEX only**
Stay narrow. This is correct.

2. **Paper-trade first**
No live capital until tracking and calibration are proven.

3. **No-trade must be common**
A mature system filters aggressively.

4. **Explanations must be grounded**
Use structured reasons from data, not hand-wavy LLM prose.

5. **Out-of-sample metrics only for trust claims**
Backtests are useful, but the signal tracker is the truth.

6. **Economic edge beats raw accuracy**
A 60% hit rate can still lose money; a 48% hit rate can win if payouts justify it.

7. **Every signal needs a frozen snapshot**
Features, model version, thresholds, and rationale must be reconstructable.

---

## Agentic Roadmap (Later)
When the core system is working, then add agents.

### Candidate agents
1. **Market Regime Agent**
   - summarizes the environment

2. **Contract Discovery Agent**
   - finds candidate binaries for the current session

3. **Edge Evaluation Agent**
   - compares probability vs breakeven economics

4. **Risk Agent**
   - flags concentration, event windows, or overtrading

5. **Explanation Agent**
   - turns structured outputs into readable reasoning

6. **Post-Trade Review Agent**
   - evaluates whether the signal was good, bad, lucky, or invalid

7. **Workflow Orchestrator Agent**
   - coordinates the morning sequence end-to-end

### Important boundary
Agents should orchestrate and explain.
They should **not** be the authority for probabilities, payouts, or backtest math.
Those stay deterministic.

---

## Suggested Build Sequence for the Next 4 Weeks

### Week 1
- define LIVEWELL page map
- define data objects for NADEX workflow
- choose front-end stack
- build app shell and navigation

### Week 2
- build Dashboard and Daily Signals pages with mock JSON
- define all backend API contracts from the UI needs

### Week 3
- extract notebook code into Python package/modules
- create first FastAPI endpoints for signals, model health, and backtests

### Week 4
- connect front end to working endpoints
- stand up signal tracker and model metadata pages
- identify what still belongs in notebook land

---

## Immediate Recommendation
Your instinct is right, but the order matters.

The smartest move now is:

**1. Build the front end**  
**2. Let the front end force the backend contracts**  
**3. Convert notebook logic into services**  
**4. Get one full end-to-end paper-trading workflow working**  
**5. Then add agents**

That sequence gives you momentum without disappearing into architecture fantasyland.

---

## First Deliverables I Recommend

1. A **LIVEWELL product map**
2. A **front-end page spec** for each page
3. A **JSON contract** for each backend endpoint
4. A **backend extraction plan** from Jupyter modules
5. A **paper-trading MVP definition**

---

## MVP Definition
LIVEWELL v1 is successful if it can do the following:
- ingest market data for your chosen NADEX underlyings
- generate daily candidate binaries
- show them in a usable dashboard
- explain why each candidate exists
- estimate edge using payout-aware logic
- track results over time
- show model health honestly
- support paper-trading review

That is already a serious system.

Agentic orchestration after that becomes powerful instead of decorative.

---

## Canonical Backend Plan
This section is meant to be the **single source of truth** for how the LIVEWELL backend should be built from the Jupyter work already completed.

### Backend philosophy
The backend should do three things well:
1. convert research code into repeatable production logic
2. preserve separation between training, inference, evaluation, and explanation
3. expose stable APIs that the front end and future agents can call

### Source of truth
- **Jupyter notebooks** remain the research and experimentation environment
- **Python package/modules** become the production implementation
- **FastAPI services** expose that implementation to the UI
- **scheduled jobs** handle retraining, rescoring, and data refresh
- **tracking tables/storage** preserve every scored opportunity and outcome

### Recommended backend layers

#### 1. Data acquisition layer
Purpose: gather and normalize all raw inputs needed for modeling and contract scoring.

Responsibilities:
- fetch underlying market data for the selected NADEX markets
- normalize timestamps and trading sessions
- persist raw and normalized price history
- store contract metadata when available
- capture payout / breakeven economics needed for scoring

Outputs:
- clean historical price series
- current market snapshot data
- contract opportunity inputs for the current session

#### 2. Feature engineering layer
Purpose: transform raw market data into model-ready features.

Responsibilities:
- compute technical indicators
- compute regime and volatility features
- generate time-window features
- standardize feature naming and schemas
- validate that required features exist before scoring

Outputs:
- training feature tables
- inference-time feature vectors
- feature metadata for traceability

#### 3. Label generation layer
Purpose: define the historical outcomes the models are trying to predict.

Responsibilities:
- define contract-relevant target labels
- encode expiry-window outcomes
- generate binary outcome labels for each training example
- keep label definitions versioned and explicit

Design note:
This is where LIVEWELL should gradually move from stock-style targets toward **NADEX-specific contract outcomes**.

#### 4. Training layer
Purpose: train and compare models on historical data.

Responsibilities:
- split data using walk-forward / time-aware validation
- train candidate algorithms
- compare results by precision, calibration, and economic usefulness
- persist models and thresholds
- save training metadata and feature lists

Outputs:
- trained model artifacts
- threshold settings
- validation metrics
- model version records

#### 5. Inference layer
Purpose: score the current session using the latest approved models.

Responsibilities:
- load production-approved model artifacts
- generate current-session features
- score candidate opportunities
- attach probabilities and confidence tiers
- preserve scored outputs for replay and audit

Outputs:
- daily scored opportunities
- raw probabilities
- score metadata linked to model version

#### 6. Decision / edge layer
Purpose: translate model probabilities into actionable NADEX decisions.

Responsibilities:
- compare predicted probability with breakeven probability
- compute expected edge after payout structure and costs
- enforce business / trading rules
- mark candidates as take, watch, or pass
- preserve both raw and adjusted scores

This is one of the most important parts of the backend.  
The model predicts.  
The decision layer decides.

#### 7. Backtesting layer
Purpose: evaluate how the strategy would have performed under realistic historical conditions.

Responsibilities:
- replay historical sessions using the same logic as live scoring
- test rule overlays, thresholds, and filters
- evaluate by market, regime, time-of-day, and expiration window
- separate clearly between in-sample and out-of-sample results
- produce artifacts consumable by the front end

Outputs:
- strategy summary metrics
- trade logs
- equity curves
- calibration and selectivity metrics

#### 8. Explanation layer
Purpose: explain why a candidate exists using grounded facts.

Responsibilities:
- summarize model and rule outputs into reason codes
- surface comparable historical setups
- explain uncertainty and failure modes
- generate structured explanations first, prose second

Design rule:
LLM-generated language should sit **on top of structured facts**, not replace them.

#### 9. Tracking and monitoring layer
Purpose: make the system inspectable over time.

Responsibilities:
- record every scored signal/opportunity
- track whether it was taken, skipped, or invalidated
- record eventual outcome
- track model drift, data freshness, and feature issues
- support paper-trading and post-trade review

Outputs:
- signal history
- outcome history
- model health history
- audit trail for every decision

---

## Backend to Front-End Contract Map
This is the practical bridge between the product and the services.

### Dashboard needs
Backend must provide:
- market regime summary
- opportunity count
- top contract candidates
- no-trade warnings
- recent performance snapshot
- model status summary

### Daily Signals needs
Backend must provide:
- scored contract list for the session
- filterable fields
- confidence tier
- estimated edge
- explanation availability
- rule-pass / no-trade status

### Contract Detail needs
Backend must provide:
- contract economics
- model probability
- breakeven probability
- edge calculation
- feature snapshot
- reason codes
- historical analogs if available
- recommendation status

### Backtest Results needs
Backend must provide:
- summary metrics
- trade distributions
- equity curves
- regime/time bucket breakdowns
- selectivity / pass-rate analysis

### Model Health needs
Backend must provide:
- current model versions
- training dates
- validation metrics
- calibration stats
- feature availability status
- drift indicators

### Signal Tracker needs
Backend must provide:
- historical opportunities
- what was taken vs skipped
- realized outcomes
- confidence vs result review
- post-trade notes support

---

## Proposed Backend Module Structure
A clean first cut would look something like this:

- `livewell/data/`
  - loaders, adapters, normalization
- `livewell/features/`
  - technical indicators, regime features, transforms
- `livewell/labels/`
  - target definitions and label generation
- `livewell/models/`
  - training, inference, calibration, artifact loading
- `livewell/decision/`
  - edge logic, thresholds, rule overlays
- `livewell/backtest/`
  - replay engine, metrics, logs, equity curves
- `livewell/explanations/`
  - reason codes, explanation builders
- `livewell/tracking/`
  - signal persistence, outcome tracking, monitoring
- `livewell/api/`
  - FastAPI routes and schemas
- `livewell/jobs/`
  - scheduled refresh, scoring, retraining workflows

This structure preserves the path from notebook → package → API → agent.

---

## Job Schedule Concept
Not exact implementation yet, but the system will likely need:

### Daily jobs
- refresh market data
- generate current-session features
- score opportunities
- compute decision layer outputs
- publish results to the UI

### Periodic jobs
- retrain models
- rerun validation
- regenerate model-health artifacts
- archive scored sessions and outcomes

### Event-driven jobs later
- user asks for explanation
- user requests post-trade review
- agent runs morning briefing
- agent compares current contract with historical analogs

---

## Agent Exploration Plan
You are right to want a place to explore agentic systems here, because the lessons will transfer directly to RUNWELL and later to COMPASS.

So the canonical plan should explicitly include a **safe exploration lane**:

### Agent exploration lane
Agents may be introduced early in **non-critical, non-authoritative roles**, such as:
- morning briefing generation
- signal explanation assistant
- strategy coach for backtest pages
- post-trade review helper
- workflow orchestration for data refresh and scoring

### Boundary condition
These early agents can:
- summarize
- coordinate
- explain
- call tools/services

They cannot be the authority for:
- pricing logic
- probability calculations
- payout math
- backtest computation
- final decision persistence

That separation gives you a real sandbox for learning LangGraph, A2A, and MCP without contaminating the core system.

---

## Canonical Roadmap
This is now the recommended single canonical sequence.

### Stage 1 — Product shell
- finalize page map
- define NADEX-first objects
- build UI with mock data

### Stage 2 — Backend extraction
- convert Jupyter logic into Python modules
- define schemas and API contracts
- separate training, inference, backtest, and explanation paths

### Stage 3 — End-to-end MVP
- connect front end to live services
- produce daily opportunities
- expose model health and backtest views
- support paper-trading and tracking

### Stage 4 — Controlled agent experimentation
- add explanation, briefing, and orchestration agents
- learn LangGraph / A2A / MCP through bounded use cases

### Stage 5 — Mature agentic architecture
- introduce microservices and stronger orchestration where there is proven value
- apply the lessons to RUNWELL and later COMPASS

---

## Canonical Principle
LIVEWELL is not just a dashboard project and not just an ML project.
It is a **decision-support platform with an eventual agentic layer**.

That means the canonical architecture is:

**deterministic backend core → usable front end → tracked outcomes → bounded agent layer → broader agentic system design lessons**

That is the version worth building.


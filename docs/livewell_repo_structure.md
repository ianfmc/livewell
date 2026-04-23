# LIVEWELL Repository Structure

## Purpose

This document defines the recommended repository structure for LIVEWELL so that:

- Claude Code has a concrete implementation target,
- the front end, back end, and data/ML layers do not blur together,
- notebook research can evolve into reusable production code,
- and future jobs, agents, and infrastructure can be added without tearing the project apart.

The goal is not to create a perfect enterprise monorepo on day one.  
The goal is to create a layout that is clean, scalable, and aligned to how LIVEWELL actually works.

---

## Repository Philosophy

LIVEWELL should be organized around **system responsibilities**, not just frameworks.

That means:
- the React app should live in a clear front-end area,
- the FastAPI app should expose backend contracts cleanly,
- the Python package should hold the reusable domain logic,
- notebooks should remain available for research but not as the system of record,
- jobs and infrastructure should have obvious homes,
- generated outputs and docs should not be mixed with source code.

---

## Recommended Top-Level Structure

```text
livewell/
  README.md
  pyproject.toml
  package.json
  pnpm-workspace.yaml
  .gitignore
  .env.example

  docs/
  apps/
  packages/
  notebooks/
  data/
  infra/
  scripts/
  tests/
```

---

## Top-Level Directory Roles

### `docs/`
Canonical markdown documentation and design artifacts.

Use for:
- `livewell_design.md`
- `01_market_model.md`
- `02_trading_strategy.md`
- `03_ml_models.md`
- `04_pipeline_architecture.md`
- `05_data_sources.md`
- `06_roadmap.md`
- `livewell_full_stack_delivery_plan.md`
- `livewell_api_contracts.md`
- `livewell_repo_structure.md`

Why:
This keeps the design system and implementation system linked but separate.

---

### `apps/`
Runnable applications.

Recommended contents:
- `apps/web/` → React front end
- `apps/api/` → FastAPI service

This is where “things you run” live.

---

### `packages/`
Reusable implementation code shared by apps and jobs.

Recommended core package:
- `packages/livewell-core/`

This package should contain the production Python logic extracted from notebooks:
- data loaders
- features
- labels
- models
- decision logic
- backtesting
- explanations
- tracking helpers

This is the actual domain engine of LIVEWELL.

Optional later:
- `packages/shared-ui/` for React components
- `packages/contracts/` for shared API/JSON schemas if you want cross-language contract generation later

---

### `notebooks/`
Research, exploration, and experimental work.

Use for:
- feature experiments
- model exploration
- exploratory backtests
- visualization and diagnostic notebooks

Rule:
Notebooks are allowed to discover the truth.  
They are not allowed to remain the only place where truth lives.

If a notebook produces logic needed by the product, that logic must move into `packages/livewell-core/`.

---

### `data/`
Local development data, sample fixtures, and optionally ignored generated artifacts.

Recommended subfolders:
- `data/sample/`
- `data/fixtures/`
- `data/local-cache/`

Important:
Do **not** treat this as the source of truth for production history.  
Production historical and artifact storage should live in S3 or another proper storage layer.

---

### `infra/`
Infrastructure definitions and deployment scaffolding.

Use for:
- AWS infrastructure as code
- Amplify config
- ECS task definitions
- EventBridge rules
- CI/CD deployment definitions
- environment-specific infra config

This is where operational infrastructure lives, not inside notebooks or ad hoc scripts.

---

### `scripts/`
Developer and maintenance scripts.

Use for:
- one-time migration helpers
- local bootstrap scripts
- seed / fixture generators
- lint / format wrappers if useful
- local dev orchestration helpers

Keep this area disciplined.  
If a script becomes part of the real product workflow, move it into jobs or services.

---

### `tests/`
Cross-system and integration-level tests.

Recommended:
- root-level tests for integration, contract, and end-to-end flows
- package-level unit tests can also live alongside each app/package if preferred

---

## Canonical App Structure

## `apps/web/` — React Front End

Recommended structure:

```text
apps/web/
  package.json
  tsconfig.json
  vite.config.ts
  index.html

  src/
    app/
    pages/
    components/
    features/
    hooks/
    lib/
    services/
    types/
    mock/
    styles/

  public/
  tests/
```

### `src/app/`
App shell and routing.

Use for:
- route configuration
- global providers
- theme setup
- layout shell
- navigation scaffolding

### `src/pages/`
Page-level entry points.

Recommended page files:
- `DashboardPage.tsx`
- `DailySignalsPage.tsx`
- `ContractDetailPage.tsx`
- `BacktestResultsPage.tsx`
- `ModelHealthPage.tsx`
- `HowItWorksPage.tsx`
- `SignalTrackerPage.tsx`
- `OptionsAdvisorPage.tsx`

### `src/components/`
Reusable UI building blocks.

Examples:
- cards
- tables
- banners
- badges
- chart wrappers
- empty states
- filter bars

### `src/features/`
Page-domain logic grouped by business feature.

Recommended feature folders:
- `dashboard/`
- `signals/`
- `contracts/`
- `backtests/`
- `model-health/`
- `tracker/`
- `advisor/`

This is where feature-specific components, adapters, and local state should live.

### `src/hooks/`
Reusable React hooks.

Examples:
- query hooks
- filter state hooks
- layout hooks

### `src/lib/`
Pure front-end utility functions.

Examples:
- formatting helpers
- date utilities
- client-side mapping helpers

### `src/services/`
API access layer.

Examples:
- `dashboardApi.ts`
- `signalsApi.ts`
- `modelHealthApi.ts`
- `backtestsApi.ts`
- `trackerApi.ts`

The front end should call services, not hard-code fetch logic everywhere.

### `src/types/`
TypeScript types and response models.

Use for:
- DTOs matching `livewell_api_contracts.md`
- UI-specific mapped view models where needed

### `src/mock/`
Mock JSON and fixtures for front-end-first development.

This is essential early, but should gradually be replaced by live service calls.

### `src/styles/`
Global styles, theme configuration, tokens, and CSS helpers if needed.

---

## `apps/api/` — FastAPI Service

Recommended structure:

```text
apps/api/
  pyproject.toml
  app/
    main.py
    config.py
    dependencies.py
    routers/
    schemas/
    services/
    middleware/
    errors/
  tests/
```

### `app/main.py`
FastAPI entry point.

### `app/config.py`
Environment configuration loading.

### `app/dependencies.py`
Dependency wiring for services, settings, repositories, etc.

### `app/routers/`
API route definitions.

Recommended routers:
- `health.py`
- `dashboard.py`
- `signals.py`
- `model_health.py`
- `backtests.py`
- `tracker.py`
- `markets.py`
- `advisor.py`

These should map closely to `livewell_api_contracts.md`.

### `app/schemas/`
Pydantic request/response schemas.

Examples:
- `health.py`
- `dashboard.py`
- `signals.py`
- `backtests.py`

### `app/services/`
Thin application service layer that coordinates package logic and storage access.

Important:
This layer should orchestrate.  
It should not reimplement core business logic already living in `packages/livewell-core/`.

### `app/middleware/`
API middleware:
- logging
- tracing
- request metadata
- CORS configuration

### `app/errors/`
Standardized API error models and handlers.

---

## Canonical Python Domain Package

## `packages/livewell-core/`

Recommended structure:

```text
packages/livewell-core/
  pyproject.toml
  src/
    livewell_core/
      __init__.py
      config/
      data/
      features/
      labels/
      models/
      decision/
      backtest/
      explanations/
      tracking/
      contracts/
      utils/
  tests/
```

This is the beating heart of LIVEWELL.

### `config/`
Shared config models and settings helpers.

### `data/`
Data ingestion, normalization, adapters, and source abstractions.

Examples:
- `market_data_loader.py`
- `nadex_contract_loader.py`
- `session_normalizer.py`

### `features/`
Feature generation.

Examples:
- `ema.py`
- `macd.py`
- `rsi.py`
- `atr.py`
- `regime.py`
- `feature_pipeline.py`

### `labels/`
Target generation for contract-relevant outcomes.

Examples:
- `expiry_labels.py`
- `strike_outcomes.py`
- `label_versions.py`

### `models/`
Training, inference, calibration, artifact management.

Examples:
- `train_logistic.py`
- `train_random_forest.py`
- `calibration.py`
- `artifact_store.py`
- `inference.py`

### `decision/`
Payout-aware recommendation logic.

Examples:
- `breakeven.py`
- `edge.py`
- `thresholds.py`
- `recommendation.py`

This is one of the most important directories in the whole system.

### `backtest/`
Historical replay and performance evaluation.

Examples:
- `replay.py`
- `metrics.py`
- `equity_curve.py`
- `calibration_reports.py`

### `explanations/`
Structured explanation builders.

Examples:
- `reason_codes.py`
- `summary_builder.py`
- `historical_analogs.py`

### `tracking/`
Signal and outcome tracking logic.

Examples:
- `signal_store.py`
- `outcome_store.py`
- `run_metadata.py`

### `contracts/`
Shared internal domain models.

Examples:
- `market_snapshot.py`
- `contract_candidate.py`
- `recommendation.py`
- `model_metadata.py`

These are backend domain contracts, not necessarily the same as public API schemas.

### `utils/`
Low-level helpers that do not belong elsewhere.

---

## Optional Shared Front-End Package

If the UI grows substantially, you may later add:

```text
packages/shared-ui/
```

Use for:
- design system primitives
- shared chart wrappers
- common badges, cards, and layout elements

Do **not** add this too early unless duplication is becoming painful.

---

## Optional Shared Contract Package

If you later want stricter cross-language alignment between FastAPI and TypeScript, you could add:

```text
packages/contracts/
```

Potential uses:
- JSON schema exports
- OpenAPI-derived generated clients
- shared examples and fixtures

This is nice later, not mandatory on day one.

---

## Notebook Structure Recommendation

Recommended structure:

```text
notebooks/
  exploration/
  features/
  modeling/
  backtests/
  diagnostics/
  archive/
```

### `exploration/`
Early raw experiments.

### `features/`
Indicator and feature testing notebooks.

### `modeling/`
Training experiments and comparisons.

### `backtests/`
Strategy replay analysis.

### `diagnostics/`
Calibration plots, drift analysis, failure investigations.

### `archive/`
Old notebooks that should not clutter the active working set.

Naming rule:
Use descriptive prefixes, for example:
- `01_feature_ema_macd_rsi.ipynb`
- `02_label_expiry_outcomes.ipynb`
- `03_model_logistic_baseline.ipynb`

---

## Data Layout Recommendation

Recommended local structure:

```text
data/
  sample/
  fixtures/
  local-cache/
```

Examples:
- `sample/signals_response.json`
- `fixtures/dashboard_summary.json`
- `local-cache/eurusd_daily.parquet`

Local data is helpful for:
- front-end mocking,
- local API testing,
- rapid iteration.

But the production system should treat S3 as the true store for:
- historical market data,
- features,
- model artifacts,
- scored runs,
- backtest artifacts.

---

## Infrastructure Layout Recommendation

Recommended structure:

```text
infra/
  aws/
    amplify/
    ecs/
    eventbridge/
    iam/
    s3/
  environments/
    dev/
    prod/
```

Alternative:
If you standardize on Terraform or AWS CDK, reflect that tool clearly.

Examples:
- `infra/aws/ecs/daily_scoring_task.json`
- `infra/aws/eventbridge/daily_scoring_rule.json`
- `infra/environments/dev/variables.example`

Keep environment-specific concerns explicit.

---

## Tests Strategy

Recommended structure:

```text
tests/
  integration/
  e2e/
  contracts/
```

And package/app-local tests too, such as:
- `apps/api/tests/`
- `apps/web/tests/`
- `packages/livewell-core/tests/`

### What to test where

#### Unit tests
Close to package/app code:
- feature calculations
- decision logic
- label generation
- utility functions

#### Contract tests
Root or API tests:
- response shape validity
- required fields for dashboard/signals/detail endpoints

#### Integration tests
- API calling real core services
- scoring flow from features to recommendation

#### End-to-end tests
- UI renders real API responses
- user can inspect signals and drill into detail

---

## Root Configuration Files

Recommended root files:

### `README.md`
Short repo entry point:
- what LIVEWELL is
- how to run apps
- where docs live
- where to start

### `pyproject.toml`
Python workspace configuration if using a unified toolchain.

### `package.json`
JS workspace scripts if using pnpm or npm workspaces.

### `pnpm-workspace.yaml`
Useful if using a frontend-focused monorepo workflow.

### `.env.example`
Document all required environment variables.

Examples:
- API base URL
- AWS region
- S3 bucket names
- feature / model environment settings

---

## Suggested Script Conventions

At the root or via workspace scripts, define obvious commands:

```text
pnpm dev:web
pnpm dev:api
pnpm test:web
pnpm test:api
pnpm lint:web
pnpm lint:api
pnpm build:web
pnpm build:api
```

And Python-side equivalents for jobs or modules, for example:
- train baseline model
- run daily scoring locally
- regenerate fixtures

Keep these discoverable and boring.

---

## Recommended First Real Layout

If you want the most pragmatic initial cut, start with this:

```text
livewell/
  docs/
  apps/
    web/
    api/
  packages/
    livewell-core/
  notebooks/
  infra/
  tests/
```

That is enough structure to:
- let Claude scaffold both front end and backend,
- extract notebook logic cleanly,
- define contract boundaries early,
- and grow into jobs, agents, and production deployment later.

---

## Migration Rule from Notebook to Production

This should be treated as canonical:

> If logic affects scoring, edge, backtesting, explanation, or tracking, it must leave the notebook and move into `packages/livewell-core/`.

That one rule will save you an enormous amount of drift and confusion later.

---

## Claude Code Guidance

Claude should use this repository structure as follows:

1. scaffold `apps/web/` for the React application shell,
2. scaffold `apps/api/` for FastAPI routes matching `livewell_api_contracts.md`,
3. scaffold `packages/livewell-core/` with the domain directories,
4. move reusable notebook logic into `livewell-core`,
5. keep notebooks only for exploration and diagnostics,
6. wire UI to API, and API to `livewell-core`,
7. add jobs and infra only after the local workflow works.

This creates a clean dependency chain:

**web → api → livewell-core**

and not the other way around.

---

## Bottom Line

The right repo structure for LIVEWELL is one that makes the system legible:

- docs explain it,
- apps run it,
- packages implement it,
- notebooks explore it,
- infra deploys it,
- tests verify it.

That is the shape that gives you both speed now and control later.

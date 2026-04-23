# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with this repository.

## Project

LIVEWELL is a decision-support system for trading NADEX binary options. It transforms raw market data into scored, filterable signals that guide disciplined trade decisions. The system is built product-first and evolves incrementally toward a full stack with a React UI, FastAPI backend, ML scoring models, and agent workflows.

## Repository Structure

```
livewell/
  docs/                       ← all design docs, specs, plans, architecture
  apps/
    web/                      ← React front end (Vite, MUI, MSW)
    api/                      ← FastAPI backend (uv, Pydantic v2)
  packages/                   ← shared Python packages (empty — livewell-core lives here eventually)
  notebooks/
    livewell-nadex/           ← research notebooks and backtesting (not production)
  infra/                      ← AWS infrastructure as code (empty initially)
  scripts/                    ← dev and maintenance scripts (empty initially)
```

Each app has its own `CLAUDE.md` with app-specific conventions:
- `apps/web/CLAUDE.md` — React, Vite, MUI, MSW, Vitest
- `apps/api/CLAUDE.md` — FastAPI, uv, Pydantic

## Data Store (settled)

- **DynamoDB** — operational records: scored signals, trade outcomes, model runs, model metadata
- **S3** — analytical data: historical price data (Parquet), model artifacts, backtest results, feature tables
- RDS/PostgreSQL was considered and rejected in favour of serverless end-to-end.
- The **DynamoDB MCP server** (`awslabs.dynamodb-mcp-server`) will be used to design table schemas and generate CDK + Python access layer code before backend implementation begins.

## Worktrees

Worktree directory: `.worktrees/` (monorepo root, git-ignored). Always use this location when creating git worktrees for feature branches.

## Docs

All cross-cutting design documents, architecture decisions, API contracts, and roadmap files live in `docs/`. Superpowers specs and plans are in `docs/superpowers/`.

Key documents:
- `docs/livewell_design.md` — overall system design
- `docs/livewell_api_contracts.md` — API endpoint contracts
- `docs/livewell_repo_structure.md` — intended full monorepo structure
- `docs/06_roadmap.md` — product roadmap

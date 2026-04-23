# Monorepo Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate three separate LIVEWELL repos into a single clean-cut monorepo at `~/Development/livewell/`, push to GitHub, and archive the old repos.

**Architecture:** New `livewell/` repo is created from scratch with no history preservation. Contents of `livewell-ui`, `livewell-api`, and `livewell-nadex` are copied into their target subdirectories. A single root `CLAUDE.md` covers cross-cutting context; each app gets its own app-level `CLAUDE.md`.

**Tech Stack:** git, gh CLI, bash (rsync for copying), existing React/Vite (`apps/web`), FastAPI/uv (`apps/api`), Python research notebooks (`notebooks/livewell-nadex`)

---

### Task 1: Initialise the monorepo

**Files:**
- Create: `~/Development/livewell/` (new git repo)

- [ ] **Step 1: Create the repo directory and initialise git**

```bash
mkdir -p ~/Library/CloudStorage/OneDrive-SAPSE/Development/livewell
cd ~/Library/CloudStorage/OneDrive-SAPSE/Development/livewell
git init
git checkout -b main
```

Expected: `Initialized empty Git repository in .../livewell/.git/`

- [ ] **Step 2: Create the full directory scaffold**

```bash
mkdir -p apps/web apps/api packages notebooks/livewell-nadex infra scripts
```

Expected: no output, directories created

- [ ] **Step 3: Add a .gitkeep to each empty placeholder directory so git tracks them**

```bash
touch packages/.gitkeep infra/.gitkeep scripts/.gitkeep
```

---

### Task 2: Write the root .gitignore

**Files:**
- Create: `~/Development/livewell/.gitignore`

- [ ] **Step 1: Write .gitignore covering all app types**

Create `~/Library/CloudStorage/OneDrive-SAPSE/Development/livewell/.gitignore` with this content:

```gitignore
# JS / Node
node_modules/
dist/
.vite/
*.local

# Python
__pycache__/
*.py[cod]
*.egg-info/
.venv/
.env
*.env.*
!*.env.example
dist/
build/
*.parquet

# Data / ML artifacts
*.pkl
*.joblib
*.h5
*.onnx
data/local-cache/

# OS
.DS_Store
Thumbs.db

# IDE
.idea/
.vscode/
*.swp

# Coverage
coverage/
.coverage
htmlcov/

# git worktrees
.worktrees/
```

---

### Task 3: Copy livewell-ui into apps/web

**Files:**
- Create: `apps/web/` — all livewell-ui source (excluding docs/, CLAUDE.md, node_modules/, dist/, .git/)

- [ ] **Step 1: Copy livewell-ui contents into apps/web, excluding irrelevant directories**

```bash
rsync -av \
  --exclude='.git/' \
  --exclude='node_modules/' \
  --exclude='dist/' \
  --exclude='.vite/' \
  --exclude='docs/' \
  --exclude='CLAUDE.md' \
  ~/Library/CloudStorage/OneDrive-SAPSE/Development/livewell-ui/ \
  ~/Library/CloudStorage/OneDrive-SAPSE/Development/livewell/apps/web/
```

Expected: list of copied files ending with no errors

- [ ] **Step 2: Verify key files landed correctly**

```bash
ls ~/Library/CloudStorage/OneDrive-SAPSE/Development/livewell/apps/web/src
ls ~/Library/CloudStorage/OneDrive-SAPSE/Development/livewell/apps/web/public
```

Expected: `src/` contains `components/`, `hooks/`, `pages/`, `mocks/`, etc. `public/` contains `mockServiceWorker.js`.

---

### Task 4: Copy livewell-api into apps/api

**Files:**
- Create: `apps/api/` — all livewell-api source (excluding .git/, __pycache__/, .venv/)

- [ ] **Step 1: Copy livewell-api contents into apps/api**

```bash
rsync -av \
  --exclude='.git/' \
  --exclude='__pycache__/' \
  --exclude='.venv/' \
  --exclude='*.egg-info/' \
  ~/Library/CloudStorage/OneDrive-SAPSE/Development/livewell-api/ \
  ~/Library/CloudStorage/OneDrive-SAPSE/Development/livewell/apps/api/
```

Expected: list of copied files (README.md, main.py, pyproject.toml, routers/, schemas/, tests/, uv.lock)

- [ ] **Step 2: Verify key files landed correctly**

```bash
ls ~/Library/CloudStorage/OneDrive-SAPSE/Development/livewell/apps/api/
```

Expected: `main.py  pyproject.toml  routers/  schemas/  tests/  uv.lock  README.md`

---

### Task 5: Copy livewell-nadex into notebooks/livewell-nadex

**Files:**
- Create: `notebooks/livewell-nadex/` — all livewell-nadex source (excluding .git/, __pycache__/, .venv/)

- [ ] **Step 1: Copy livewell-nadex contents into notebooks/livewell-nadex**

```bash
rsync -av \
  --exclude='.git/' \
  --exclude='__pycache__/' \
  --exclude='.venv/' \
  --exclude='*.egg-info/' \
  ~/Library/CloudStorage/OneDrive-SAPSE/Development/livewell-nadex/ \
  ~/Library/CloudStorage/OneDrive-SAPSE/Development/livewell/notebooks/livewell-nadex/
```

Expected: list of copied files (notebooks/, src/, tests/, configs/, pyproject.toml, etc.)

- [ ] **Step 2: Verify key directories landed correctly**

```bash
ls ~/Library/CloudStorage/OneDrive-SAPSE/Development/livewell/notebooks/livewell-nadex/
```

Expected: `notebooks/  src/  tests/  configs/  pyproject.toml  requirements.txt  README.md` (and others)

---

### Task 6: Copy docs from livewell-ui

**Files:**
- Create: `docs/` — moved from livewell-ui/docs/

- [ ] **Step 1: Copy the docs directory to the monorepo root**

```bash
rsync -av \
  ~/Library/CloudStorage/OneDrive-SAPSE/Development/livewell-ui/docs/ \
  ~/Library/CloudStorage/OneDrive-SAPSE/Development/livewell/docs/
```

Expected: list of all docs files including `livewell_design.md`, `01_market_model.md`, `superpowers/` etc.

- [ ] **Step 2: Verify the superpowers specs and plans are present**

```bash
ls ~/Library/CloudStorage/OneDrive-SAPSE/Development/livewell/docs/superpowers/specs/
ls ~/Library/CloudStorage/OneDrive-SAPSE/Development/livewell/docs/superpowers/plans/
```

Expected: spec and plan files including `2026-04-23-monorepo-migration-design.md` and `2026-04-23-monorepo-migration.md`

---

### Task 7: Write apps/web/CLAUDE.md

**Files:**
- Create: `apps/web/CLAUDE.md`

- [ ] **Step 1: Write apps/web/CLAUDE.md with the React/web-specific guidance from livewell-ui**

Create `~/Library/CloudStorage/OneDrive-SAPSE/Development/livewell/apps/web/CLAUDE.md` with this content:

```markdown
# apps/web — CLAUDE.md

React front end for LIVEWELL. See the root `CLAUDE.md` for project overview and cross-cutting decisions.

## Commands

```bash
npm run dev           # Start dev server at http://localhost:5173
npm run build         # Type-check (tsc -b) then bundle (vite build)
npm run lint          # ESLint across the project
npm test              # Vitest in watch mode — reruns affected tests on save
npm run test:coverage # Single run with coverage report (80% line threshold enforced)
```

Run a single test file: `npx vitest run src/hooks/useSignals.test.ts`

## Architecture

**Data flow:** `src/data/mockData.ts` defines the `ContractCard` type and seed data → `src/mocks/handlers.ts` exposes it as `GET /api/signals` via MSW → `src/hooks/useSignals.ts` fetches that endpoint → `src/pages/DailySignals.tsx` renders the result.

**MSW in dev:** `src/main.tsx` conditionally starts the MSW service worker before mounting React (`import.meta.env.DEV` guard). All unhandled requests are bypassed (`onUnhandledRequest: "bypass"`). The worker file lives at `public/mockServiceWorker.js`. Adding a new mock endpoint means adding a handler in `src/mocks/handlers.ts` only.

**Theme:** `src/components/theme-provider.tsx` wraps the app in a React context that persists `"light" | "dark"` to `localStorage` and toggles a class on `<html>`. Access it with `useTheme()`. MUI theming is not yet wired to this — the toggle currently drives manual `bgcolor` switches in `App.tsx`.

**Pages vs components:** Pages (`src/pages/`) own data fetching and page-level layout. Components (`src/components/`) are presentational and receive props.

**Testing:** Vitest + React Testing Library. Test files live next to the code they test (`useSignals.test.ts` beside `useSignals.ts`). MSW intercepts `fetch` in tests via `src/mocks/server.ts` (Node runtime), reusing the same `src/mocks/handlers.ts` as the dev service worker. `src/test/setup.ts` runs before every test file and manages the MSW lifecycle. Use `renderHook` for hooks, `render` + `screen` for components and pages. Dashboard tests require `MemoryRouter` wrapper (component uses `Link`). `ThemeProvider` is excluded from coverage — infrastructure with no product logic.

## Key Conventions

- MUI components are imported individually (`import Button from '@mui/material/Button'`), not from the barrel (`@mui/material`).
- Hooks live in `src/hooks/` and return a typed result object (`{ data, loading, error }`).
- The `ContractCard` type (instrument, strike, expiry, status) is the core domain type. It lives in `src/data/mockData.ts` and is imported by the hook — not by pages directly.

## Worktrees

Worktree directory: `.worktrees/` (relative to monorepo root). Always use `../../.worktrees/` when creating git worktrees from this app directory, or run git worktree commands from the monorepo root.
```

---

### Task 8: Write apps/api/CLAUDE.md

**Files:**
- Create: `apps/api/CLAUDE.md`

- [ ] **Step 1: Write apps/api/CLAUDE.md with FastAPI conventions**

Create `~/Library/CloudStorage/OneDrive-SAPSE/Development/livewell/apps/api/CLAUDE.md` with this content:

```markdown
# apps/api — CLAUDE.md

FastAPI backend for LIVEWELL. See the root `CLAUDE.md` for project overview and cross-cutting decisions.

## Commands

```bash
uv run uvicorn main:app --reload   # Start dev server at http://localhost:8000
uv run pytest                      # Run tests
uv run pytest tests/test_health.py # Run a single test file
```

## Architecture

**Entrypoint:** `main.py` creates the FastAPI app and includes routers.

**Structure:**
- `routers/` — route definitions, one file per domain area
- `schemas/` — Pydantic request/response models
- `livewell/` — application services and domain logic
- `tests/` — pytest tests, using `httpx.AsyncClient` against the app

**Toolchain:** uv for dependency management. `pyproject.toml` is the source of truth. No requirements.txt — use `uv add <package>` to add dependencies.

## Key Conventions

- Routers use `APIRouter` with a prefix. Include them in `main.py`.
- Schemas are Pydantic v2 models in `schemas/`. Response models are separate from request models.
- Tests use `pytest` with `httpx` for HTTP-level testing against the real app. No mocking of internal services in unit tests unless unavoidable.
```

---

### Task 9: Write the root CLAUDE.md

**Files:**
- Create: `~/Development/livewell/CLAUDE.md`

- [ ] **Step 1: Write the root CLAUDE.md covering cross-cutting project context**

Create `~/Library/CloudStorage/OneDrive-SAPSE/Development/livewell/CLAUDE.md` with this content:

```markdown
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
```

---

### Task 10: Write the root README.md

**Files:**
- Create: `~/Development/livewell/README.md`

- [ ] **Step 1: Write a minimal README**

Create `~/Library/CloudStorage/OneDrive-SAPSE/Development/livewell/README.md` with this content:

```markdown
# LIVEWELL

Decision-support system for trading NADEX binary options.

## What's in this repo

| Directory | Contents |
|-----------|----------|
| `apps/web` | React front end (Vite, MUI) |
| `apps/api` | FastAPI backend |
| `notebooks/livewell-nadex` | Research notebooks and backtesting |
| `docs` | Design docs, architecture, API contracts, roadmap |
| `packages` | Shared Python packages (future: livewell-core) |
| `infra` | AWS infrastructure as code (future) |

## Quickstart

**Web:**
```bash
cd apps/web
npm install
npm run dev        # http://localhost:5173
```

**API:**
```bash
cd apps/api
uv sync
uv run uvicorn main:app --reload   # http://localhost:8000
```

## Docs

See `docs/` for design documents, architecture decisions, and the product roadmap.
```

---

### Task 11: Initial commit

**Files:**
- All files in `~/Development/livewell/`

- [ ] **Step 1: Stage all files**

```bash
cd ~/Library/CloudStorage/OneDrive-SAPSE/Development/livewell
git add .
```

- [ ] **Step 2: Verify what will be committed (check nothing sensitive is included)**

```bash
git status
```

Expected: Long list of new files. Confirm no `.env` files, no `node_modules/`, no `__pycache__/`, no `.venv/` appear.

- [ ] **Step 3: Create the initial commit**

```bash
git commit -m "$(cat <<'EOF'
chore: initialise livewell monorepo

Clean-cut migration from livewell-ui, livewell-api, and livewell-nadex.
No git history preserved. See docs/superpowers/specs/2026-04-23-monorepo-migration-design.md.
EOF
)"
```

Expected: commit hash and summary of files added

---

### Task 12: Create GitHub repo and push

**Files:**
- No file changes — GitHub + git operations only

- [ ] **Step 1: Create the public GitHub repo and push**

```bash
cd ~/Library/CloudStorage/OneDrive-SAPSE/Development/livewell
gh repo create ianfmc/livewell --public --source=. --remote=origin --push
```

Expected: GitHub repo URL printed, e.g. `https://github.com/ianfmc/livewell`

- [ ] **Step 2: Verify the push**

```bash
gh repo view ianfmc/livewell
```

Expected: repo details showing `main` branch with recent commit

---

### Task 13: Archive old repos on GitHub

**Files:**
- No file changes — GitHub operations only

- [ ] **Step 1: Archive livewell-ui on GitHub**

```bash
gh repo archive ianfmc/livewell-ui --yes
```

Expected: `✓ Archived repository ianfmc/livewell-ui`

- [ ] **Step 2: Archive livewell-nadex on GitHub**

```bash
gh repo archive ianfmc/livewell-nadex --yes
```

Expected: `✓ Archived repository ianfmc/livewell-nadex`

- [ ] **Step 3: Verify both repos show as archived**

```bash
gh repo view ianfmc/livewell-ui --json isArchived --jq '.isArchived'
gh repo view ianfmc/livewell-nadex --json isArchived --jq '.isArchived'
```

Expected: `true` for both

---

### Task 14: Smoke-test the web app from its new location

**Files:**
- No file changes — verification only

- [ ] **Step 1: Install dependencies and run the dev server**

```bash
cd ~/Library/CloudStorage/OneDrive-SAPSE/Development/livewell/apps/web
npm install
npm run dev
```

Expected: `VITE v... ready in ...ms` — server running at http://localhost:5173

- [ ] **Step 2: Run the test suite**

```bash
npm run test:coverage
```

Expected: all tests pass, coverage at or above 80%

- [ ] **Step 3: Kill the dev server (Ctrl+C), then run the linter**

```bash
npm run lint
```

Expected: no lint errors

---

### Task 15: Smoke-test the API from its new location

**Files:**
- No file changes — verification only

- [ ] **Step 1: Install dependencies and run the API**

```bash
cd ~/Library/CloudStorage/OneDrive-SAPSE/Development/livewell/apps/api
uv sync
uv run uvicorn main:app --reload
```

Expected: `Application startup complete.` at http://localhost:8000

- [ ] **Step 2: Run the API tests**

```bash
uv run pytest
```

Expected: all tests pass

- [ ] **Step 3: Kill the server (Ctrl+C)**

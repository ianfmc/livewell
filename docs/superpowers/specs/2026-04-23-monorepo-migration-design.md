# LIVEWELL Monorepo Migration Design

**Date:** 2026-04-23  
**Status:** Approved  
**Approach:** Clean-cut (no history preservation)

---

## Problem

Project documentation lives in `livewell-ui` but spans the entire LIVEWELL system — architecture, API contracts, roadmap, ML models, data sources. Three separate repos (`livewell-ui`, `livewell-api`, `livewell-nadex`) are evolving independently with no shared context. The intended destination has always been a monorepo (documented in `livewell_repo_structure.md`). Now is the right time to make the move while the repos are still small and `livewell-api` has no remote.

---

## Decision

Migrate to a clean-cut monorepo. No git history preservation. One initial commit captures the full starting state.

---

## Target Structure

```
livewell/
  CLAUDE.md                     ← root: cross-cutting project context
  README.md
  .gitignore
  docs/                         ← moved from livewell-ui/docs/
  apps/
    web/                        ← contents of livewell-ui/ (minus docs/, CLAUDE.md)
      CLAUDE.md                 ← React/MSW/MUI/test conventions
    api/                        ← contents of livewell-api/
      CLAUDE.md                 ← FastAPI conventions (minimal initially)
  packages/                     ← empty initially; livewell-core lives here eventually
  notebooks/
    livewell-nadex/             ← contents of livewell-nadex/ (research, not production)
  infra/                        ← empty; AWS CDK/Terraform lives here eventually
  scripts/                      ← empty; dev and maintenance scripts
```

### Key placement decisions

- `livewell-nadex` → `notebooks/livewell-nadex/` because it is research notebooks today. Production logic extracted from it will eventually move to `packages/livewell-core/`.
- `docs/` → monorepo root. All cross-cutting design docs, specs, plans, and architecture docs live here. App-specific docs (if any) live inside their app directory.
- `packages/` → created but empty. Placeholder for `livewell-core/` when domain logic is ready to be extracted.

---

## CLAUDE.md Strategy

### Root `livewell/CLAUDE.md`
Covers:
- What LIVEWELL is (project overview)
- Repository structure (where things live and why)
- Cross-cutting decisions: DynamoDB + S3 data store, worktree location (`.worktrees/`)
- Pointers to each app's own CLAUDE.md for app-specific guidance

### `apps/web/CLAUDE.md`
Current `livewell-ui` CLAUDE.md content:
- React conventions, MUI individual imports
- MSW setup (dev + test)
- Hook patterns (`{ data, loading, error }`)
- Test patterns (Vitest + RTL, `renderHook`, `MemoryRouter`)
- `ContractCard` as core domain type
- Commands (`npm run dev`, `build`, `lint`, `test`)

### `apps/api/CLAUDE.md`
Minimal initially:
- FastAPI conventions
- Python toolchain (uv, pyproject.toml)
- Router/schema/service structure

### `notebooks/livewell-nadex/CLAUDE.md`
Not created initially — no Claude Code guidance needed for research notebooks.

---

## Migration Steps

1. **Create monorepo locally**
   ```bash
   mkdir ~/Development/livewell
   cd ~/Development/livewell
   git init
   ```

2. **Create directory scaffold**
   ```bash
   mkdir -p apps/web apps/api packages notebooks/livewell-nadex infra scripts docs
   ```

3. **Copy app contents** (excluding `.git/`, build artifacts, old CLAUDE.md files)
   - `livewell-ui/` → `apps/web/` (exclude: `.git/`, `node_modules/`, `dist/`, `docs/`, `CLAUDE.md`)
   - `livewell-api/` → `apps/api/` (exclude: `.git/`, `__pycache__/`, `.venv/`)
   - `livewell-nadex/` → `notebooks/livewell-nadex/` (exclude: `.git/`, `__pycache__/`, `.venv/`)

4. **Move docs**
   - `livewell-ui/docs/` → `livewell/docs/`

5. **Write CLAUDE.md files**
   - Root `livewell/CLAUDE.md` — merged cross-cutting context
   - `apps/web/CLAUDE.md` — current livewell-ui CLAUDE.md content (updated paths)
   - `apps/api/CLAUDE.md` — minimal FastAPI guidance

6. **Write root README.md and .gitignore**

7. **Initial commit**
   ```
   chore: initialise livewell monorepo
   ```

8. **Create GitHub repo and push**
   ```bash
   gh repo create ianfmc/livewell --public --source=. --remote=origin --push
   ```

9. **Archive old repos on GitHub**
   - Archive `ianfmc/livewell-ui`
   - Archive `ianfmc/livewell-nadex`
   - `livewell-api` has no remote — no action needed

10. **Update local tooling**
    - Future Claude Code sessions open from `livewell/` root or `livewell/apps/web/`
    - Superpowers memory for the new repo will be at `~/.claude/projects/-Users-i802235-Library-CloudStorage-OneDrive-SAPSE-Development-livewell/memory/` — a new directory, separate from the current `livewell-ui` memory

---

## What Is Not In Scope

- Workspace wiring (pnpm workspaces, uv workspaces) — added when cross-app dependencies exist
- CI/CD — not yet configured in any repo
- `packages/livewell-core/` — created when notebook logic is ready to productionise
- Import path updates inside apps — each app is self-contained and continues to work as-is

---

## Success Criteria

- All three repos' contents live under `livewell/` in the correct subdirectories
- `docs/` is at the monorepo root
- Claude Code opened from `livewell/` gets cross-cutting context
- Claude Code opened from `livewell/apps/web/` gets both root and web-specific context
- Old repos are archived on GitHub, not deleted
- `livewell-api` can be worked on without needing a separate GitHub repo

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

# LIVEWELL API

FastAPI backend for the LIVEWELL decision-support system.

## Setup

```bash
uv sync
```

## Run

```bash
uv run uvicorn main:app --reload --port 8000
```

## Test

```bash
uv run pytest
```

## Endpoints

- `GET /api/signals` — list of contract candidates
- `GET /api/signals/{instrument}/{strike}` — contract detail (`instrument` is hyphen-encoded, e.g. `EUR-USD`)
- `GET /api/dashboard` — dashboard summary

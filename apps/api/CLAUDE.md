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

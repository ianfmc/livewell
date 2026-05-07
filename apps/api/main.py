from __future__ import annotations
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import signals, dashboard, backtest, model_health, tracker, explain

app = FastAPI(title="LIVEWELL API", version="0.1.0")

_default_origins = "http://localhost:5173,http://localhost:5174,http://localhost:5175,http://localhost:4173"
origins = os.environ.get("CORS_ORIGINS", _default_origins).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(signals.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(backtest.router, prefix="/api")
app.include_router(model_health.router, prefix="/api")
app.include_router(tracker.router, prefix="/api")
app.include_router(explain.router, prefix="/api")


@app.get("/health")
def health():
    return {"status": "ok"}


# Lambda entrypoint
try:
    from mangum import Mangum
    handler = Mangum(app)
except ImportError:
    pass  # not required for local dev

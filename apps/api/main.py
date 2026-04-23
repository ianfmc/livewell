from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import signals, dashboard, backtest, model_health

app = FastAPI(title="LIVEWELL API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://localhost:4173",
    ],
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(signals.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(backtest.router, prefix="/api")
app.include_router(model_health.router, prefix="/api")

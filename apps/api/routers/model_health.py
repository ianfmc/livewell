from __future__ import annotations
from fastapi import APIRouter
from schemas.model_health import DriftWarning, FeatureStatus, ModelHealth

router = APIRouter()

_HEALTH = ModelHealth(
    overallStatus="Warning",
    trainingDate="2026-04-18",
    dataFreshness="5 days ago",
    calibrationError=0.043,
    validationAccuracy=0.64,
    features=[
        FeatureStatus(name="EMA-20",          status="Available"),
        FeatureStatus(name="EMA-50",          status="Available"),
        FeatureStatus(name="RSI-14",          status="Available"),
        FeatureStatus(name="MACD Signal",     status="Available"),
        FeatureStatus(name="ATR-14",          status="Available"),
        FeatureStatus(name="Session Flag",    status="Available"),
        FeatureStatus(name="Volatility Reg",  status="Stale"),
        FeatureStatus(name="Event Risk Flag", status="Missing"),
    ],
    driftWarnings=[
        DriftWarning(
            feature="Volatility Reg",
            description="Last computed 6 days ago — refresh recommended before next scoring run.",
        ),
    ],
)


@router.get("/model/health", response_model=ModelHealth)
def get_model_health() -> ModelHealth:
    return _HEALTH

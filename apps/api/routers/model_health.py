from __future__ import annotations
import logging
from fastapi import APIRouter
from livewell.models.registry import get_active_model
from schemas.model_health import DriftWarning, FeatureStatus, ModelHealth

logger = logging.getLogger(__name__)
router = APIRouter()

_FEATURE_NAMES = [
    "EMA-20", "EMA-50", "RSI-14", "MACD Signal",
    "ATR-14", "Session Flag", "Direction", "Instrument",
]


@router.get("/model/health", response_model=ModelHealth)
def get_model_health() -> ModelHealth:
    try:
        reg = get_active_model()
        trained_at = str(reg.get("trained_at", ""))[:10]
        win_rate = float(reg.get("win_rate", 0))
        return ModelHealth(
            overallStatus="Healthy" if win_rate >= 0.60 else "Warning",
            trainingDate=trained_at,
            dataFreshness="Current",
            calibrationError=0.0,
            validationAccuracy=win_rate,
            features=[FeatureStatus(name=f, status="Available") for f in _FEATURE_NAMES],
            driftWarnings=[],
        )
    except Exception as exc:
        logger.warning("model registry unavailable: %s", exc)
        return ModelHealth(
            overallStatus="Degraded",
            trainingDate="unknown",
            dataFreshness="Stale",
            calibrationError=0.0,
            validationAccuracy=0.0,
            features=[FeatureStatus(name=f, status="Missing") for f in _FEATURE_NAMES],
            driftWarnings=[DriftWarning(feature="All", description="No active model in registry.")],
        )

# apps/api/routers/dashboard.py
from __future__ import annotations
import logging
from fastapi import APIRouter

from livewell.signals.dynamodb import get_latest_signals
from livewell.signals.transform import (
    to_contract_card,
    score_from_record,
    confidence_from_record,
    NAME_BY_S3_KEY,
)
from livewell.models.registry import get_active_model
from schemas.dashboard import (
    DashboardData,
    MarketSnapshot,
    ModelHealth,
    OpportunitySummary,
    TopCandidate,
)

logger = logging.getLogger(__name__)
router = APIRouter()


def _map_regime(trend_bias: str) -> str:
    mapping = {"bullish": "Bullish", "bearish": "Bearish"}
    return mapping.get(trend_bias.lower(), "Neutral")


@router.get("/dashboard", response_model=DashboardData)
def get_dashboard() -> DashboardData:
    records = get_latest_signals()

    total = len(records)
    passing = sum(1 for r in records if (score_from_record(r) or 0) >= 0.65)
    review = sum(1 for r in records if 0.55 <= (score_from_record(r) or 0) < 0.65)

    sorted_records = sorted(records, key=lambda r: score_from_record(r) or 0.0, reverse=True)
    top_candidates = [
        TopCandidate(
            instrument=NAME_BY_S3_KEY.get(str(r.get("s3_key", "")), str(r.get("s3_key", ""))),
            strike=str(r.get("strike_candidate", "")),
            expiry=str(r.get("timing_slot", "")),
            edge=f"{(score_from_record(r) or 0) * 2 - 1:+.2f}",
            confidence=confidence_from_record(score_from_record(r)),
        )
        for r in sorted_records[:3]
    ]

    markets = [
        MarketSnapshot(
            instrument=NAME_BY_S3_KEY.get(str(r.get("s3_key", "")), str(r.get("s3_key", ""))),
            regime=_map_regime(str(r.get("trend_bias", "neutral"))),
            noTrade=(str(r.get("timing_risk", "")).lower() == "high"),
        )
        for r in records
    ]

    try:
        reg = get_active_model()
        trained_at = str(reg.get("trained_at", ""))[:10]
        model_health = ModelHealth(
            trainingDate=trained_at,
            dataFreshness="Current",
            status="Healthy",
        )
    except RuntimeError:
        model_health = ModelHealth(trainingDate="unknown", dataFreshness="Stale", status="Degraded")

    return DashboardData(
        markets=markets,
        opportunities=OpportunitySummary(total=total, passing=passing, review=review),
        topCandidates=top_candidates,
        modelHealth=model_health,
    )

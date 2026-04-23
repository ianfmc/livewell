from __future__ import annotations
from fastapi import APIRouter
from schemas.dashboard import (
    DashboardData,
    MarketSnapshot,
    ModelHealth,
    OpportunitySummary,
    TopCandidate,
)

router = APIRouter()

_DASHBOARD = DashboardData(
    markets=[
        MarketSnapshot(instrument="EUR/USD", regime="Bullish", noTrade=False),
        MarketSnapshot(instrument="GBP/USD", regime="Neutral", noTrade=True),
        MarketSnapshot(instrument="USD/JPY", regime="Bearish", noTrade=False),
    ],
    opportunities=OpportunitySummary(total=5, passing=2, review=1),
    topCandidates=[
        TopCandidate(
            instrument="EUR/USD",
            strike="1.0875",
            expiry="2026-04-22T14:00:00Z",
            edge="+0.14",
            confidence="High",
        ),
        TopCandidate(
            instrument="USD/JPY",
            strike="154.50",
            expiry="2026-04-22T16:00:00Z",
            edge="+0.09",
            confidence="Medium",
        ),
    ],
    modelHealth=ModelHealth(
        trainingDate="2026-04-21", dataFreshness="Current", status="Healthy"
    ),
)


@router.get("/dashboard", response_model=DashboardData)
def get_dashboard() -> DashboardData:
    return _DASHBOARD

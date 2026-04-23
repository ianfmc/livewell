import pytest
from pydantic import ValidationError
from schemas.dashboard import (
    DashboardData,
    MarketSnapshot,
    ModelHealth,
    OpportunitySummary,
    TopCandidate,
)


def test_dashboard_data_fields():
    data = DashboardData(
        markets=[MarketSnapshot(instrument="EUR/USD", regime="Bullish", noTrade=False)],
        opportunities=OpportunitySummary(total=5, passing=2, review=1),
        topCandidates=[
            TopCandidate(
                instrument="EUR/USD",
                strike="1.0875",
                expiry="2026-04-22T14:00:00Z",
                edge="+0.14",
                confidence="High",
            )
        ],
        modelHealth=ModelHealth(
            trainingDate="2026-04-21", dataFreshness="Current", status="Healthy"
        ),
    )
    assert data.opportunities.passing == 2


def test_market_snapshot_regime_literal():
    with pytest.raises(ValidationError):
        MarketSnapshot(instrument="EUR/USD", regime="Invalid", noTrade=False)

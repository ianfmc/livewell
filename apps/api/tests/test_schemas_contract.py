import pytest
from pydantic import ValidationError
from schemas.contract import ContractCard, ContractDetail, Economics, ReasonCode


def test_contract_card_fields():
    card = ContractCard(
        instrument="EUR/USD", strike="1.0850", expiry="10:00 AM", status="Open"
    )
    assert card.instrument == "EUR/USD"
    assert card.strike == "1.0850"


def test_contract_detail_recommendation_literal():
    with pytest.raises(ValidationError):
        ContractDetail(
            instrument="EUR/USD",
            strike="1.0850",
            expiry="10:00 AM",
            status="Open",
            recommendation="Invalid",
            rationale="test",
            economics={"cost": 42, "payout": 100, "breakeven": 0.42},
            modelProbability=0.68,
            edge=0.26,
            confidence="High",
            regime="Bullish",
            noTradeFlag=False,
            reasonCodes=[],
        )

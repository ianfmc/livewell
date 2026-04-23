from __future__ import annotations
from fastapi import APIRouter, HTTPException
from schemas.contract import ContractCard, ContractDetail, Economics, ReasonCode

router = APIRouter()

_DETAILS: list[ContractDetail] = [
    ContractDetail(
        instrument="EUR/USD",
        strike="1.0850",
        expiry="10:00 AM",
        status="Open",
        recommendation="Take",
        rationale="Strong directional setup with acceptable event risk.",
        economics=Economics(cost=42, payout=100, breakeven=0.42),
        modelProbability=0.68,
        edge=0.26,
        confidence="High",
        regime="Bullish",
        noTradeFlag=False,
        reasonCodes=[
            ReasonCode(label="Bullish regime confirmed", positive=True),
            ReasonCode(label="RSI momentum favourable", positive=True),
            ReasonCode(label="Event risk flag active", positive=False),
        ],
    ),
    ContractDetail(
        instrument="GBP/USD",
        strike="1.2650",
        expiry="11:00 AM",
        status="Open",
        recommendation="Watch",
        rationale="Setup is developing but lacks regime confirmation.",
        economics=Economics(cost=38, payout=100, breakeven=0.38),
        modelProbability=0.52,
        edge=0.14,
        confidence="Medium",
        regime="Neutral",
        noTradeFlag=False,
        reasonCodes=[
            ReasonCode(label="Price near key level", positive=True),
            ReasonCode(label="Regime not confirmed", positive=False),
            ReasonCode(label="Low volatility environment", positive=False),
        ],
    ),
    ContractDetail(
        instrument="USD/JPY",
        strike="150.00",
        expiry="09:30 AM",
        status="Review",
        recommendation="Pass",
        rationale="No-trade flag active — intervention risk too high.",
        economics=Economics(cost=55, payout=100, breakeven=0.55),
        modelProbability=0.48,
        edge=-0.07,
        confidence="Low",
        regime="Bearish",
        noTradeFlag=True,
        reasonCodes=[
            ReasonCode(label="Intervention risk elevated", positive=False),
            ReasonCode(label="Bearish momentum weakening", positive=False),
            ReasonCode(label="High volatility — spread risk", positive=False),
        ],
    ),
]

_SIGNALS: list[ContractCard] = [
    ContractCard(
        instrument=d.instrument,
        strike=d.strike,
        expiry=d.expiry,
        status=d.status,
    )
    for d in _DETAILS
]


@router.get("/signals", response_model=list[ContractCard])
def get_signals() -> list[ContractCard]:
    return _SIGNALS


@router.get("/signals/{instrument}/{strike}", response_model=ContractDetail)
def get_signal_detail(instrument: str, strike: str) -> ContractDetail:
    decoded = instrument.replace("-", "/")
    detail = next(
        (d for d in _DETAILS if d.instrument == decoded and d.strike == strike), None
    )
    if detail is None:
        raise HTTPException(status_code=404, detail="Not found")
    return detail

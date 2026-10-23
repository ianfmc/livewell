from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class Economics(BaseModel):
    cost: float
    payout: float
    breakeven: float


class ReasonCode(BaseModel):
    label: str
    positive: bool


class SupportingSignals(BaseModel):
    ema20: float | None = None
    ema50: float | None = None
    rsi14: float | None = None
    macdHist: float | None = None
    atr14: float | None = None


class ContractCard(BaseModel):
    instrument: str
    strike: str
    expiry: str
    status: str
    signalId: str = ""
    # LW-207: candidate must show direction, timestamp, supporting signals,
    # reason codes, and confidence/uncertainty context.
    direction: str = "none"
    date: str = ""
    recommendation: Literal["Take", "Watch", "Pass"] = "Watch"
    confidence: Literal["High", "Medium", "Low"] = "Low"
    scoreAvailable: bool = False
    edge: float = 0.0
    supportingSignals: SupportingSignals = SupportingSignals()
    reasonCodes: list[ReasonCode] = []


class ContractDetail(BaseModel):
    instrument: str
    strike: str
    expiry: str
    status: str
    recommendation: Literal["Take", "Watch", "Pass"]
    rationale: str
    economics: Economics
    modelProbability: float | None
    edge: float
    confidence: Literal["High", "Medium", "Low"]
    regime: str
    noTradeFlag: bool
    reasonCodes: list[ReasonCode]

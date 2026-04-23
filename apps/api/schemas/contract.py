from __future__ import annotations
from typing import Literal
from pydantic import BaseModel


class ContractCard(BaseModel):
    instrument: str
    strike: str
    expiry: str
    status: str


class Economics(BaseModel):
    cost: float
    payout: float
    breakeven: float


class ReasonCode(BaseModel):
    label: str
    positive: bool


class ContractDetail(BaseModel):
    instrument: str
    strike: str
    expiry: str
    status: str
    recommendation: Literal["Take", "Watch", "Pass"]
    rationale: str
    economics: Economics
    modelProbability: float
    edge: float
    confidence: Literal["High", "Medium", "Low"]
    regime: str
    noTradeFlag: bool
    reasonCodes: list[ReasonCode]

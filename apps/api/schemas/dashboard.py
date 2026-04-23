from __future__ import annotations
from typing import Literal
from pydantic import BaseModel


class MarketSnapshot(BaseModel):
    instrument: str
    regime: Literal["Bullish", "Bearish", "Neutral"]
    noTrade: bool


class OpportunitySummary(BaseModel):
    total: int
    passing: int
    review: int


class TopCandidate(BaseModel):
    instrument: str
    strike: str
    expiry: str
    edge: str
    confidence: Literal["High", "Medium", "Low"]


class ModelHealth(BaseModel):
    trainingDate: str
    dataFreshness: Literal["Current", "Stale"]
    status: Literal["Healthy", "Warning", "Degraded"]


class DashboardData(BaseModel):
    markets: list[MarketSnapshot]
    opportunities: OpportunitySummary
    topCandidates: list[TopCandidate]
    modelHealth: ModelHealth

from __future__ import annotations
from pydantic import BaseModel


class BacktestRow(BaseModel):
    market: str
    regime: str
    expiryWindow: str = "Daily"
    trades: int
    winRate: float
    avgEdge: float
    netReturn: float


class EquityCurvePoint(BaseModel):
    date: str
    value: float


class SignalValidGroup(BaseModel):
    trades: int
    winRate: float


class SignalValidSplit(BaseModel):
    valid: SignalValidGroup
    invalid: SignalValidGroup


class BacktestSummary(BaseModel):
    totalTrades: int
    winRate: float
    avgEdge: float
    maxDrawdown: float
    equityCurve: list[EquityCurvePoint]
    rows: list[BacktestRow]
    signalValidSplit: SignalValidSplit | None = None

from __future__ import annotations
from pydantic import BaseModel


class BacktestRow(BaseModel):
    market: str
    regime: str
    expiryWindow: str
    trades: int
    winRate: float
    avgEdge: float
    netReturn: float


class EquityCurvePoint(BaseModel):
    date: str
    value: float


class BacktestSummary(BaseModel):
    totalTrades: int
    winRate: float
    avgEdge: float
    maxDrawdown: float
    equityCurve: list[EquityCurvePoint]
    rows: list[BacktestRow]

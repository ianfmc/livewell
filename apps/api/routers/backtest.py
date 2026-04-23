from __future__ import annotations
from fastapi import APIRouter
from schemas.backtest import BacktestRow, BacktestSummary, EquityCurvePoint

router = APIRouter()

_SUMMARY = BacktestSummary(
    totalTrades=84,
    winRate=0.61,
    avgEdge=0.14,
    maxDrawdown=-0.09,
    equityCurve=[
        EquityCurvePoint(date="2026-03-01", value=1000),
        EquityCurvePoint(date="2026-03-03", value=1018),
        EquityCurvePoint(date="2026-03-05", value=1009),
        EquityCurvePoint(date="2026-03-07", value=1031),
        EquityCurvePoint(date="2026-03-10", value=1024),
        EquityCurvePoint(date="2026-03-12", value=1047),
        EquityCurvePoint(date="2026-03-14", value=1039),
        EquityCurvePoint(date="2026-03-17", value=1062),
        EquityCurvePoint(date="2026-03-19", value=1055),
        EquityCurvePoint(date="2026-03-21", value=1078),
        EquityCurvePoint(date="2026-03-24", value=1070),
        EquityCurvePoint(date="2026-03-26", value=1093),
        EquityCurvePoint(date="2026-03-28", value=1085),
        EquityCurvePoint(date="2026-03-31", value=1108),
        EquityCurvePoint(date="2026-04-02", value=1099),
        EquityCurvePoint(date="2026-04-04", value=1122),
        EquityCurvePoint(date="2026-04-07", value=1113),
        EquityCurvePoint(date="2026-04-09", value=1136),
        EquityCurvePoint(date="2026-04-11", value=1128),
        EquityCurvePoint(date="2026-04-14", value=1151),
        EquityCurvePoint(date="2026-04-16", value=1143),
        EquityCurvePoint(date="2026-04-18", value=1134),
        EquityCurvePoint(date="2026-04-19", value=1157),
        EquityCurvePoint(date="2026-04-20", value=1149),
        EquityCurvePoint(date="2026-04-21", value=1172),
        EquityCurvePoint(date="2026-04-22", value=1163),
        EquityCurvePoint(date="2026-04-23", value=1186),
        EquityCurvePoint(date="2026-04-24", value=1177),
        EquityCurvePoint(date="2026-04-25", value=1200),
        EquityCurvePoint(date="2026-04-26", value=1191),
    ],
    rows=[
        BacktestRow(market="EUR/USD", regime="Bullish", expiryWindow="2-hour", trades=18, winRate=0.67, avgEdge=0.18, netReturn=0.21),
        BacktestRow(market="EUR/USD", regime="Bearish", expiryWindow="2-hour", trades=12, winRate=0.58, avgEdge=0.11, netReturn=0.09),
        BacktestRow(market="GBP/USD", regime="Bullish", expiryWindow="Daily",  trades=15, winRate=0.60, avgEdge=0.14, netReturn=0.12),
        BacktestRow(market="GBP/USD", regime="Bearish", expiryWindow="Daily",  trades=11, winRate=0.55, avgEdge=0.09, netReturn=0.06),
        BacktestRow(market="USD/JPY", regime="Bullish", expiryWindow="2-hour", trades=16, winRate=0.63, avgEdge=0.15, netReturn=0.14),
        BacktestRow(market="USD/JPY", regime="Bearish", expiryWindow="Daily",  trades=12, winRate=0.50, avgEdge=0.08, netReturn=0.02),
    ],
)


@router.get("/backtest/summary", response_model=BacktestSummary)
def get_backtest_summary() -> BacktestSummary:
    return _SUMMARY

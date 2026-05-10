from __future__ import annotations
from collections import defaultdict

_COST = 40.0
_PAYOUT = 100.0
_STARTING_EQUITY = 1000.0


def build_summary(trades: list[dict]) -> dict:
    """Build the backtest summary dict from a list of resolved trade dicts."""
    if not trades:
        return {
            "totalTrades": 0,
            "winRate": 0.0,
            "avgEdge": 0.0,
            "maxDrawdown": 0.0,
            "equityCurve": [],
            "rows": [],
            "signalValidSplit": {
                "valid": {"trades": 0, "winRate": 0.0},
                "invalid": {"trades": 0, "winRate": 0.0},
            },
        }

    sorted_trades = sorted(trades, key=lambda t: t["date"])
    wins = sum(1 for t in sorted_trades if t["win"])
    total = len(sorted_trades)
    win_rate = wins / total

    # Equity curve — N+1 points: sentinel "start" point at initial equity,
    # then one post-trade point per trade.  Using "start" avoids duplicating
    # the first trade's date as both the pre-trade and post-trade label.
    equity = _STARTING_EQUITY
    curve = [{"date": "start", "value": equity}]
    for trade in sorted_trades:
        equity += (_PAYOUT - _COST) if trade["win"] else -_COST
        curve.append({"date": trade["date"], "value": round(equity, 2)})

    # Max drawdown
    peak = _STARTING_EQUITY
    max_dd = 0.0
    for point in curve:
        v = point["value"]
        if v > peak:
            peak = v
        dd = (v - peak) / peak
        if dd < max_dd:
            max_dd = dd

    avg_edge = round((win_rate * _PAYOUT - _COST) / _COST, 4)

    # Rows by instrument × regime
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for t in sorted_trades:
        groups[(t["instrument"], t["regime"])].append(t)

    rows = []
    for (market, regime), group in sorted(groups.items()):
        g_wins = sum(1 for t in group if t["win"])
        g_total = len(group)
        g_wr = g_wins / g_total
        g_edge = round((g_wr * _PAYOUT - _COST) / _COST, 4)
        g_net = round(
            sum((_PAYOUT - _COST) if t["win"] else -_COST for t in group) / (_COST * g_total),
            4,
        )
        # NOTE: for binary outcomes netReturn == avgEdge algebraically; kept because
        # BacktestRow schema (schemas/backtest.py) declares it as a required field.
        rows.append({
            "market": market,
            "regime": regime,
            "trades": g_total,
            "winRate": round(g_wr, 4),
            "avgEdge": g_edge,
            "netReturn": g_net,
        })

    valid = [t for t in sorted_trades if t["signal_valid"]]
    invalid = [t for t in sorted_trades if not t["signal_valid"]]

    def _split_stats(group: list[dict]) -> dict:
        if not group:
            return {"trades": 0, "winRate": 0.0}
        w = sum(1 for t in group if t["win"])
        return {"trades": len(group), "winRate": round(w / len(group), 4)}

    return {
        "totalTrades": total,
        "winRate": round(win_rate, 4),
        "avgEdge": avg_edge,
        "maxDrawdown": round(max_dd, 4),
        "equityCurve": curve,
        "rows": rows,
        "signalValidSplit": {
            "valid": _split_stats(valid),
            "invalid": _split_stats(invalid),
        },
    }

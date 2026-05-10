from __future__ import annotations
import pytest
from livewell.backtest.aggregator import build_summary

WIN_TRADE = {"date": "2026-05-07", "instrument": "EURUSD", "win": True,
             "signal_valid": True, "regime": "bullish", "direction": "call",
             "strike": 1.0850, "next_close": 1.0900}
LOSS_TRADE = {"date": "2026-05-08", "instrument": "EURUSD", "win": False,
              "signal_valid": True, "regime": "bullish", "direction": "call",
              "strike": 1.0850, "next_close": 1.0800}
INVALID_WIN = {"date": "2026-05-09", "instrument": "GBPUSD", "win": True,
               "signal_valid": False, "regime": "bearish", "direction": "put",
               "strike": 1.2650, "next_close": 1.2600}


class TestWinRate:
    def test_all_wins(self):
        summary = build_summary([WIN_TRADE, WIN_TRADE])
        assert summary["winRate"] == pytest.approx(1.0)

    def test_all_losses(self):
        summary = build_summary([LOSS_TRADE, LOSS_TRADE])
        assert summary["winRate"] == pytest.approx(0.0)

    def test_mixed(self):
        summary = build_summary([WIN_TRADE, LOSS_TRADE])
        assert summary["winRate"] == pytest.approx(0.5)

    def test_total_trades(self):
        summary = build_summary([WIN_TRADE, LOSS_TRADE, INVALID_WIN])
        assert summary["totalTrades"] == 3


class TestEquityCurve:
    def test_starts_at_post_first_trade_value(self):
        summary = build_summary([WIN_TRADE])
        assert summary["equityCurve"][0]["value"] == pytest.approx(1060.0)

    def test_win_adds_60(self):
        summary = build_summary([WIN_TRADE])
        assert summary["equityCurve"][-1]["value"] == pytest.approx(1060.0)

    def test_loss_subtracts_40(self):
        summary = build_summary([LOSS_TRADE])
        assert summary["equityCurve"][-1]["value"] == pytest.approx(960.0)

    def test_sequence(self):
        summary = build_summary([WIN_TRADE, LOSS_TRADE])
        values = [p["value"] for p in summary["equityCurve"]]
        assert values == pytest.approx([1060.0, 1020.0])

    def test_dates_match_trade_dates(self):
        summary = build_summary([WIN_TRADE, LOSS_TRADE])
        dates = [p["date"] for p in summary["equityCurve"]]
        assert len(dates) == 2
        assert dates[0] == "2026-05-07"
        assert dates[1] == "2026-05-08"

    def test_trades_sorted_by_date_regardless_of_input_order(self):
        # LOSS_TRADE (2026-05-08) passed before WIN_TRADE (2026-05-07) — should sort correctly
        summary = build_summary([LOSS_TRADE, WIN_TRADE])
        values = [p["value"] for p in summary["equityCurve"]]
        # Sorted by date: WIN (05-07) first, LOSS (05-08) second
        assert values == pytest.approx([1060.0, 1020.0])


class TestMaxDrawdown:
    def test_no_drawdown_all_wins(self):
        summary = build_summary([WIN_TRADE, WIN_TRADE])
        assert summary["maxDrawdown"] == pytest.approx(0.0)

    def test_drawdown_after_win_then_loss(self):
        summary = build_summary([WIN_TRADE, LOSS_TRADE])
        assert summary["maxDrawdown"] == pytest.approx((1020 - 1060) / 1060, abs=0.001)


class TestSignalValidSplit:
    def test_split_counts(self):
        summary = build_summary([WIN_TRADE, LOSS_TRADE, INVALID_WIN])
        split = summary["signalValidSplit"]
        assert split["valid"]["trades"] == 2
        assert split["invalid"]["trades"] == 1

    def test_split_win_rates(self):
        summary = build_summary([WIN_TRADE, LOSS_TRADE, INVALID_WIN])
        split = summary["signalValidSplit"]
        assert split["valid"]["winRate"] == pytest.approx(0.5)
        assert split["invalid"]["winRate"] == pytest.approx(1.0)


class TestRows:
    def test_rows_by_instrument_and_regime(self):
        summary = build_summary([WIN_TRADE, LOSS_TRADE, INVALID_WIN])
        rows = {(r["market"], r["regime"]): r for r in summary["rows"]}
        assert ("EURUSD", "bullish") in rows
        assert ("GBPUSD", "bearish") in rows

    def test_row_win_rate(self):
        summary = build_summary([WIN_TRADE, LOSS_TRADE])
        rows = {(r["market"], r["regime"]): r for r in summary["rows"]}
        assert rows[("EURUSD", "bullish")]["winRate"] == pytest.approx(0.5)


class TestEmptyTrades:
    def test_empty_returns_safe_defaults(self):
        summary = build_summary([])
        assert summary["totalTrades"] == 0
        assert summary["winRate"] == 0.0
        assert summary["avgEdge"] == 0.0
        assert summary["maxDrawdown"] == 0.0
        assert summary["equityCurve"] == []
        assert summary["rows"] == []
        assert summary["signalValidSplit"]["valid"]["trades"] == 0
        assert summary["signalValidSplit"]["invalid"]["trades"] == 0

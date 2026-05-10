from __future__ import annotations
import pandas as pd
import pytest
from livewell.backtest.outcome import is_win, resolve_trade


def _price_df(dates_and_closes: list[tuple[str, float]]) -> pd.DataFrame:
    return pd.DataFrame(
        {"date": pd.to_datetime([d for d, _ in dates_and_closes]),
         "close": [c for _, c in dates_and_closes]}
    ).sort_values("date").reset_index(drop=True)


class TestIsWin:
    def test_call_win(self):
        assert is_win("call", 1.0850, 1.0900) is True

    def test_call_loss(self):
        assert is_win("call", 1.0850, 1.0800) is False

    def test_call_exact_strike(self):
        assert is_win("call", 1.0850, 1.0850) is False

    def test_put_win(self):
        assert is_win("put", 1.0850, 1.0800) is True

    def test_put_loss(self):
        assert is_win("put", 1.0850, 1.0900) is False

    def test_put_exact_strike(self):
        assert is_win("put", 1.0850, 1.0850) is False


class TestResolveTrade:
    def test_returns_trade_result_when_next_day_exists(self):
        df = _price_df([("2026-05-07", 1.0900), ("2026-05-08", 1.0950)])
        signal = {
            "signal_id": "EURUSD__2026-05-07",
            "date": "2026-05-07",
            "s3_key": "EURUSD",
            "direction": "call",
            "strike_candidate": "1.0850",
            "signal_valid": True,
            "trend_bias": "bullish",
        }
        result = resolve_trade(signal, df)
        assert result is not None
        assert result["signal_id"] == "EURUSD__2026-05-07"
        assert result["win"] is True
        assert result["next_close"] == pytest.approx(1.0950)
        assert result["strike"] == pytest.approx(1.0850)
        assert result["direction"] == "call"
        assert result["instrument"] == "EURUSD"
        assert result["signal_valid"] is True
        assert result["regime"] == "bullish"

    def test_returns_none_when_no_next_day(self):
        df = _price_df([("2026-05-07", 1.0900)])
        signal = {
            "signal_id": "EURUSD__2026-05-07",
            "date": "2026-05-07",
            "s3_key": "EURUSD",
            "direction": "call",
            "strike_candidate": "1.0850",
            "signal_valid": True,
            "trend_bias": "bullish",
        }
        result = resolve_trade(signal, df)
        assert result is None

    def test_handles_market_holiday_gap(self):
        df = _price_df([("2026-05-07", 1.0900), ("2026-05-09", 1.0800)])
        signal = {
            "signal_id": "EURUSD__2026-05-07",
            "date": "2026-05-07",
            "s3_key": "EURUSD",
            "direction": "put",
            "strike_candidate": "1.0850",
            "signal_valid": False,
            "trend_bias": "bearish",
        }
        result = resolve_trade(signal, df)
        assert result is not None
        assert result["win"] is True
        assert result["next_close"] == pytest.approx(1.0800)

    def test_returns_none_for_empty_price_df(self):
        df = _price_df([])
        signal = {
            "signal_id": "EURUSD__2026-05-07",
            "date": "2026-05-07",
            "s3_key": "EURUSD",
            "direction": "call",
            "strike_candidate": "1.0850",
            "signal_valid": True,
            "trend_bias": "bullish",
        }
        result = resolve_trade(signal, df)
        assert result is None

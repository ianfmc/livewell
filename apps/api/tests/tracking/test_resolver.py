# apps/api/tests/tracking/test_resolver.py
from __future__ import annotations

from unittest.mock import patch

from livewell.tracking.resolver import resolve_outcome


class TestResolveOutcome:
    """Binary settlement: buy wins above strike, sell wins below (at-strike loses)."""

    def test_buy_above_strike_wins(self):
        assert resolve_outcome("buy", "1.1000", 1.1050) == "won"

    def test_buy_below_strike_loses(self):
        assert resolve_outcome("buy", "1.1000", 1.0950) == "lost"

    def test_buy_at_strike_loses(self):
        # close == strike is NOT strictly greater → lost
        assert resolve_outcome("buy", "1.1000", 1.1000) == "lost"

    def test_sell_below_strike_wins(self):
        assert resolve_outcome("sell", "1.1000", 1.0950) == "won"

    def test_sell_above_strike_loses(self):
        assert resolve_outcome("sell", "1.1000", 1.1050) == "lost"

    def test_sell_at_strike_loses(self):
        assert resolve_outcome("sell", "1.1000", 1.1000) == "lost"

    def test_strike_parsed_from_string(self):
        # strike arrives as a string (DynamoDB storage); must coerce to float
        assert resolve_outcome("buy", "2300.50", 2301.0) == "won"


class TestResolveTradeSkips:
    """resolve_trade should skip (not raise) on unknown instrument or no price."""

    def test_unknown_s3_key_skips(self):
        from livewell.tracking import resolver

        trade = {"trade_id": "t1", "s3_key": "NOTREAL", "direction": "buy",
                 "strike": "1.1", "expiry_time": "2026-05-05T20:00:00Z"}
        # no ticker → returns without calling patch_trade
        with patch.object(resolver, "patch_trade") as mock_patch:
            resolver.resolve_trade(trade, as_of="2026-05-05T21:00:00Z")
            mock_patch.assert_not_called()

    def test_no_price_skips(self):
        from livewell.tracking import resolver

        trade = {"trade_id": "t2", "s3_key": "EURUSD", "direction": "buy",
                 "strike": "1.1", "expiry_time": "2026-05-05T20:00:00Z"}
        with patch.object(resolver, "fetch_close_price", return_value=None), \
             patch.object(resolver, "patch_trade") as mock_patch:
            resolver.resolve_trade(trade, as_of="2026-05-05T21:00:00Z")
            mock_patch.assert_not_called()

    def test_resolves_and_patches_when_price_available(self):
        from livewell.tracking import resolver

        trade = {"trade_id": "t3", "s3_key": "EURUSD", "direction": "buy",
                 "strike": "1.1000", "expiry_time": "2026-05-05T20:00:00Z"}
        with patch.object(resolver, "fetch_close_price", return_value=1.1050), \
             patch.object(resolver, "patch_trade") as mock_patch:
            resolver.resolve_trade(trade, as_of="2026-05-05T21:00:00Z")
            mock_patch.assert_called_once()
            kwargs = mock_patch.call_args.kwargs
            assert kwargs["trade_id"] == "t3"
            assert kwargs["status"] == "won"
            assert kwargs["outcome_source"] == "auto"

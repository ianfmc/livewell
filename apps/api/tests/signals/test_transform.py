# apps/api/tests/signals/test_transform.py
from __future__ import annotations
import pytest
from livewell.signals.transform import (
    to_contract_card,
    to_contract_detail,
    _recommendation,
    _confidence,
)

BASE = {
    "signal_id": "EURUSD__2026-05-07",
    "s3_key": "EURUSD",
    "date": "2026-05-07",
    "strike_candidate": "1.0850",
    "timing_slot": "12:00",
    "timing_risk": "moderate",
    "signal_valid": True,
    "direction": "buy",
    "trend_bias": "bullish",
    "reasoning": '[{"label": "EMA cross confirmed", "positive": true}]',
    "score": "0.71",
    "model_version": "20260507T144919",
}


def _rec(**kwargs):
    return {**BASE, **kwargs}


class TestRecommendation:
    def test_take_high_score_valid(self):
        assert _recommendation(0.65, True, "buy") == "Take"

    def test_watch_score_just_below_take(self):
        assert _recommendation(0.64, True, "buy") == "Watch"

    def test_watch_mid_score(self):
        assert _recommendation(0.60, True, "buy") == "Watch"

    def test_watch_invalid_signal(self):
        assert _recommendation(0.70, False, "buy") == "Watch"

    def test_pass_low_score(self):
        assert _recommendation(0.50, True, "buy") == "Pass"

    def test_pass_no_direction(self):
        assert _recommendation(0.70, True, "none") == "Pass"

    def test_null_score_returns_watch(self):
        assert _recommendation(None, True, "buy") == "Watch"

    def test_null_score_none_direction_returns_watch(self):
        assert _recommendation(None, True, "none") == "Watch"


class TestConfidence:
    def test_high(self):
        assert _confidence(0.70) == "High"

    def test_high_exact_boundary(self):
        assert _confidence(0.70) == "High"

    def test_medium(self):
        assert _confidence(0.64) == "Medium"

    def test_medium_lower_boundary(self):
        assert _confidence(0.58) == "Medium"

    def test_low(self):
        assert _confidence(0.50) == "Low"

    def test_null_score_returns_low(self):
        assert _confidence(None) == "Low"


class TestToContractCard:
    def test_instrument_display_name(self):
        card = to_contract_card(BASE)
        assert card.instrument == "EUR/USD"

    def test_strike_and_expiry(self):
        card = to_contract_card(BASE)
        assert card.strike == "1.0850"
        assert card.expiry == "12:00"

    def test_signal_id(self):
        card = to_contract_card(BASE)
        assert card.signalId == "EURUSD__2026-05-07"

    def test_status_take_maps_to_open(self):
        card = to_contract_card(_rec(score="0.71", signal_valid=True, direction="buy"))
        assert card.status == "Open"

    def test_status_watch_maps_to_review(self):
        card = to_contract_card(_rec(score="0.60", signal_valid=True, direction="buy"))
        assert card.status == "Review"

    def test_status_pass_maps_to_closed(self):
        card = to_contract_card(_rec(score="0.40", signal_valid=True, direction="buy"))
        assert card.status == "Closed"

    def test_unknown_s3_key_passes_through(self):
        card = to_contract_card(_rec(s3_key="UNKNOWN"))
        assert card.instrument == "UNKNOWN"


class TestToContractDetail:
    def test_recommendation_take(self):
        detail = to_contract_detail(BASE)
        assert detail.recommendation == "Take"

    def test_confidence_high(self):
        detail = to_contract_detail(BASE)
        assert detail.confidence == "High"

    def test_edge_calculation(self):
        detail = to_contract_detail(BASE)
        assert abs(detail.edge - (0.71 * 2 - 1)) < 0.001

    def test_model_probability_set(self):
        detail = to_contract_detail(BASE)
        assert abs(detail.modelProbability - 0.71) < 0.001

    def test_model_probability_null_for_unscored(self):
        detail = to_contract_detail(_rec(score=None, model_version=None))
        assert detail.modelProbability is None

    def test_no_trade_flag_high_risk(self):
        detail = to_contract_detail(_rec(timing_risk="high"))
        assert detail.noTradeFlag is True

    def test_no_trade_flag_moderate_risk(self):
        detail = to_contract_detail(_rec(timing_risk="moderate"))
        assert detail.noTradeFlag is False

    def test_reason_codes_parsed(self):
        detail = to_contract_detail(BASE)
        assert len(detail.reasonCodes) == 1
        assert detail.reasonCodes[0].label == "EMA cross confirmed"
        assert detail.reasonCodes[0].positive is True

    def test_reason_codes_empty_on_bad_json(self):
        detail = to_contract_detail(_rec(reasoning="not-json"))
        assert detail.reasonCodes == []

    def test_regime_passed_through(self):
        detail = to_contract_detail(BASE)
        assert detail.regime == "bullish"

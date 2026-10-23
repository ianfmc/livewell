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

    def test_null_score_invalid_signal_returns_watch(self):
        assert _recommendation(None, False, "buy") == "Watch"


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

    def test_signal_valid_string_false_treated_as_false(self):
        card = to_contract_card(_rec(score="0.71", signal_valid="False", direction="buy"))
        # "False" string is not True, so signal not valid → Watch → Review
        assert card.status == "Review"


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


# --- LW-207: reason-code string-format fix, card/detail consistency, no-score state ---

# A realistic pipeline reasoning payload is a JSON list of PLAIN STRINGS.
_PIPELINE_REASONS = '["trend: bullish (ema_20 > ema_50)", "momentum: bullish conditions not met", "all stages passed"]'


class TestReasonCodeParsing:
    def test_pipeline_string_format_is_not_empty(self):
        # The real pipeline emits plain strings; this used to silently yield [].
        detail = to_contract_detail(_rec(reasoning=_PIPELINE_REASONS))
        assert len(detail.reasonCodes) == 3

    def test_pass_marker_is_positive(self):
        detail = to_contract_detail(_rec(reasoning='["all stages passed"]'))
        assert detail.reasonCodes[0].positive is True

    def test_failed_stage_is_negative(self):
        detail = to_contract_detail(_rec(reasoning='["momentum: bullish conditions not met"]'))
        assert detail.reasonCodes[0].positive is False
        assert "Momentum" in detail.reasonCodes[0].label

    def test_dict_format_still_supported(self):
        # Back-compat with already-structured {label, positive}.
        detail = to_contract_detail(_rec(reasoning='[{"label": "X", "positive": false}]'))
        assert detail.reasonCodes[0].label == "X"
        assert detail.reasonCodes[0].positive is False

    def test_garbage_returns_empty_not_raise(self):
        assert to_contract_detail(_rec(reasoning="not-json")).reasonCodes == []
        assert to_contract_detail(_rec(reasoning='{"not": "a list"}')).reasonCodes == []


class TestCardDetailConsistency:
    """A2: card and detail derive from one source and must agree on shared fields."""

    def test_status_recommendation_confidence_agree(self):
        rec = _rec(reasoning=_PIPELINE_REASONS)
        card = to_contract_card(rec)
        detail = to_contract_detail(rec)
        assert card.status == detail.status
        assert card.recommendation == detail.recommendation
        assert card.confidence == detail.confidence
        assert abs(card.edge - detail.edge) < 1e-9
        assert card.reasonCodes == detail.reasonCodes


class TestCandidateFields:
    """A1: candidate card now carries direction, timestamp, supporting signals."""

    def test_card_exposes_direction_and_date(self):
        card = to_contract_card(_rec(ema_20="1.085", ema_50="1.080", rsi_14="58", macd_hist="0.0002", atr_14="0.005"))
        assert card.direction == "buy"
        assert card.date == "2026-05-07"

    def test_card_exposes_supporting_signals(self):
        card = to_contract_card(_rec(ema_20="1.085", ema_50="1.080", rsi_14="58", macd_hist="0.0002", atr_14="0.005"))
        assert card.supportingSignals.ema20 == pytest.approx(1.085)
        assert card.supportingSignals.rsi14 == pytest.approx(58.0)
        assert card.supportingSignals.atr14 == pytest.approx(0.005)

    def test_missing_signals_are_none_not_error(self):
        card = to_contract_card(_rec())  # BASE has no ema/rsi/... keys
        assert card.supportingSignals.ema20 is None


class TestNoScoreState:
    """A3a: frozen baseline has score=None — must be honest, not misleading Low."""

    def test_score_available_true_when_scored(self):
        assert to_contract_card(BASE).scoreAvailable is True

    def test_score_available_false_when_unscored(self):
        card = to_contract_card(_rec(score=None, model_version=None))
        assert card.scoreAvailable is False

    def test_valid_signal_no_score_is_rule_high_not_low(self):
        # all-passed, valid, no score -> rule-based High (not a misleading "Low")
        card = to_contract_card(_rec(score=None, signal_valid=True, reasoning='["all stages passed"]'))
        assert card.scoreAvailable is False
        assert card.confidence == "High"

    def test_invalid_signal_no_score_is_low(self):
        card = to_contract_card(_rec(score=None, signal_valid="False",
                                     reasoning='["momentum: bullish conditions not met"]'))
        assert card.confidence == "Low"

    def test_detail_rationale_mentions_rule_based_when_no_score(self):
        detail = to_contract_detail(_rec(score=None, model_version=None))
        assert "rule-based" in detail.rationale.lower()


# --- D1 (design-review): rule confidence must not read "High" for a non-actionable signal ---

class TestRuleConfidenceActionability:
    def test_no_direction_unscored_is_low_not_high(self):
        # valid=True but direction=none, no score -> must NOT be High (was the D1 bug)
        card = to_contract_card(_rec(
            score=None, model_version=None, signal_valid=True, direction="none",
            reasoning='["all stages passed"]',
        ))
        assert card.scoreAvailable is False
        assert card.confidence == "Low"

    def test_actionable_valid_unscored_is_high(self):
        card = to_contract_card(_rec(
            score=None, model_version=None, signal_valid=True, direction="buy",
            reasoning='["all stages passed"]',
        ))
        assert card.confidence == "High"

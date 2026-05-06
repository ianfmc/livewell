from __future__ import annotations
import pytest
from livewell.models.features import build_feature_vector, INSTRUMENT_ENC


RECORD = {
    "ema_20": "1.08",
    "ema_50": "1.07",
    "rsi_14": "55.0",
    "macd": "0.001",
    "macd_signal": "0.0009",
    "macd_hist": "0.0001",
    "atr_14": "0.005",
    "session_quality": "high",
    "direction": "buy",
    "signal_valid": True,
}


def test_returns_12_features():
    vec = build_feature_vector(RECORD, "EURUSD")
    assert len(vec) == 12


def test_ema_ratio():
    vec = build_feature_vector(RECORD, "EURUSD")
    assert abs(vec[0] - (1.08 / 1.07)) < 1e-9


def test_direction_enc_buy():
    vec = build_feature_vector(RECORD, "EURUSD")
    assert vec[5] == 1


def test_direction_enc_sell():
    r = {**RECORD, "direction": "sell"}
    assert build_feature_vector(r, "EURUSD")[5] == -1


def test_direction_enc_none():
    r = {**RECORD, "direction": "none"}
    assert build_feature_vector(r, "EURUSD")[5] == 0


def test_session_quality_enc_high():
    vec = build_feature_vector(RECORD, "EURUSD")
    assert vec[4] == 2


def test_session_quality_enc_medium():
    r = {**RECORD, "session_quality": "medium"}
    assert build_feature_vector(r, "EURUSD")[4] == 1


def test_session_quality_enc_low():
    r = {**RECORD, "session_quality": "low"}
    assert build_feature_vector(r, "EURUSD")[4] == 0


def test_signal_valid_enc_true():
    vec = build_feature_vector(RECORD, "EURUSD")
    assert vec[6] == 1


def test_signal_valid_enc_false():
    r = {**RECORD, "signal_valid": False}
    assert build_feature_vector(r, "EURUSD")[6] == 0


def test_instrument_enc_eurusd():
    vec = build_feature_vector(RECORD, "EURUSD")
    assert vec[11] == 0


def test_instrument_enc_usdmxn():
    vec = build_feature_vector(RECORD, "USDMXN")
    assert vec[11] == 18


def test_instrument_enc_unknown_raises():
    with pytest.raises(KeyError):
        build_feature_vector(RECORD, "UNKNOWN")


def test_all_values_are_float_or_int():
    vec = build_feature_vector(RECORD, "EURUSD")
    for v in vec:
        assert isinstance(v, (int, float))

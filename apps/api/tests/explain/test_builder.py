from io import BytesIO
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from livewell.explain.builder import (
    parse_signal_id,
    load_signal_row,
)


# ---------------------------------------------------------------------------
# parse_signal_id
# ---------------------------------------------------------------------------

def test_parse_signal_id_valid():
    s3_key, date_str = parse_signal_id("EURUSD__2026-05-04")
    assert s3_key == "EURUSD"
    assert date_str == "2026-05-04"


def test_parse_signal_id_invalid_raises():
    with pytest.raises(ValueError, match="Invalid signal_id"):
        parse_signal_id("EURUSD-2026-05-04")  # single underscore — wrong separator


# ---------------------------------------------------------------------------
# load_signal_row (mocked S3 + parquet)
# ---------------------------------------------------------------------------

def _make_parquet_bytes(rows: list[dict]) -> bytes:
    buf = BytesIO()
    pd.DataFrame(rows).to_parquet(buf, index=False)
    return buf.getvalue()


@patch("livewell.explain.builder.boto3.client")
def test_load_signal_row_found(mock_boto):
    row = {
        "date": pd.Timestamp("2026-05-04", tz="UTC"),
        "s3_key": "EURUSD",
        "direction": "buy",
        "ema_20": 1.085,
        "ema_50": 1.080,
        "rsi_14": 58.0,
        "macd_hist": 0.0002,
        "atr_14": 0.005,
        "session_quality": "high",
        "timing_slot": "buy_bullish",
        "timing_risk": "moderate",
        "signal_valid": True,
        "reasoning": '["all stages passed"]',
    }
    parquet_bytes = _make_parquet_bytes([row])

    s3_mock = MagicMock()
    mock_boto.return_value = s3_mock
    s3_mock.get_object.return_value = {"Body": BytesIO(parquet_bytes)}

    result = load_signal_row("test-bucket", "EURUSD", "2026-05-04")

    assert result is not None
    assert result["direction"] == "buy"
    assert result["s3_key"] == "EURUSD"


@patch("livewell.explain.builder.boto3.client")
def test_load_signal_row_not_found_returns_none(mock_boto):
    parquet_bytes = _make_parquet_bytes([
        {
            "date": pd.Timestamp("2026-01-01", tz="UTC"),
            "s3_key": "EURUSD",
            "direction": "buy",
            "ema_20": 1.085, "ema_50": 1.080, "rsi_14": 55.0,
            "macd_hist": 0.0001, "atr_14": 0.004, "session_quality": "high",
            "timing_slot": "default", "timing_risk": "low", "signal_valid": True,
            "reasoning": "[]",
        }
    ])
    s3_mock = MagicMock()
    mock_boto.return_value = s3_mock
    s3_mock.get_object.return_value = {"Body": BytesIO(parquet_bytes)}

    result = load_signal_row("test-bucket", "EURUSD", "2026-05-04")
    assert result is None

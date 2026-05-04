import json
from io import BytesIO
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from livewell.explain.builder import (
    parse_signal_id,
    load_signal_row,
    build_explain_messages,
    SURFACE_ID_PREFIX,
    CATALOG_ID,
    SECTIONS,
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


# ---------------------------------------------------------------------------
# build_explain_messages
# ---------------------------------------------------------------------------

FIXTURE_ROW = {
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


def test_build_explain_first_two_messages_are_surface_and_components():
    surface_id = f"{SURFACE_ID_PREFIX}EURUSD__2026-05-04"
    claude_paragraphs = ["Trend text.", "Momentum text.", "Session text.", "Timing text."]

    messages = list(build_explain_messages(surface_id, FIXTURE_ROW, claude_paragraphs))

    assert len(messages) == 7  # createSurface + updateComponents + header + 4 sections

    first = json.loads(messages[0])
    assert "createSurface" in first
    assert first["createSurface"]["surfaceId"] == surface_id
    assert first["createSurface"]["catalogId"] == CATALOG_ID

    second = json.loads(messages[1])
    assert "updateComponents" in second
    comp_ids = [c["id"] for c in second["updateComponents"]["components"]]
    assert comp_ids == ["root", "header", "trend", "momentum", "session", "timing"]


def test_build_explain_header_message():
    surface_id = f"{SURFACE_ID_PREFIX}EURUSD__2026-05-04"
    messages = list(build_explain_messages(surface_id, FIXTURE_ROW, ["T.", "M.", "S.", "Ti."]))

    header_msg = json.loads(messages[2])
    assert "updateDataModel" in header_msg
    assert header_msg["updateDataModel"]["path"] == "/header"
    assert "EURUSD" in header_msg["updateDataModel"]["value"]
    assert "buy" in header_msg["updateDataModel"]["value"]


def test_build_explain_section_messages_match_paragraphs():
    surface_id = f"{SURFACE_ID_PREFIX}EURUSD__2026-05-04"
    paragraphs = ["Trend text.", "Momentum text.", "Session text.", "Timing text."]
    messages = list(build_explain_messages(surface_id, FIXTURE_ROW, paragraphs))

    section_msgs = [json.loads(m) for m in messages[3:]]
    paths = [m["updateDataModel"]["path"] for m in section_msgs]
    assert paths == ["/trend", "/momentum", "/session", "/timing"]
    assert section_msgs[0]["updateDataModel"]["value"] == "Trend text."


def test_sections_constant():
    assert SECTIONS == ["trend", "momentum", "session", "timing"]

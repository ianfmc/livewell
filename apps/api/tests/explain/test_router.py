from unittest.mock import patch

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

# The explain endpoint is a plain JSON endpoint (A2UI/SSE streaming was removed):
# GET /api/explain/{signal_id} -> ExplainResponse via build_explanation().
# These tests exercise that current contract and its error mapping.

SAMPLE = {
    "header": "EUR/USD · buy · 2026-05-04",
    "trend": "EMA-20 above EMA-50 (bullish).",
    "momentum": "RSI > 50, MACD histogram positive.",
    "session": "London session, high quality.",
    "timing": "Within the morning slot.",
}


def test_explain_returns_json_content_type():
    """The endpoint returns application/json."""
    with patch("routers.explain.build_explanation", return_value=SAMPLE):
        response = client.get("/api/explain/EURUSD__2026-05-04")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")


def test_explain_returns_all_sections():
    """The JSON body carries the five explanation sections."""
    with patch("routers.explain.build_explanation", return_value=SAMPLE):
        response = client.get("/api/explain/EURUSD__2026-05-04")
    body = response.json()
    for key in ("header", "trend", "momentum", "session", "timing"):
        assert key in body
    assert body == SAMPLE


def test_explain_signal_not_found_returns_404():
    """build_explanation raising LookupError maps to 404."""
    with patch("routers.explain.build_explanation",
               side_effect=LookupError("Signal not found: EURUSD__2099-01-01")):
        response = client.get("/api/explain/EURUSD__2099-01-01")
    assert response.status_code == 404


def test_explain_invalid_signal_id_returns_422():
    """build_explanation raising ValueError maps to 422."""
    with patch("routers.explain.build_explanation",
               side_effect=ValueError("Invalid signal_id")):
        response = client.get("/api/explain/EURUSD-badformat")
    assert response.status_code == 422

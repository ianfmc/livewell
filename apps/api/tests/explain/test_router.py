import json
from unittest.mock import patch

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_explain_returns_sse_content_type():
    """The endpoint must return text/event-stream."""
    with patch("routers.explain.stream_explanation") as mock_stream:
        mock_stream.return_value = iter([
            'data: {"version": "v0.9", "createSurface": {"surfaceId": "explain-X", "catalogId": "C"}}\n\n',
        ])
        response = client.get("/api/explain/EURUSD__2026-05-04", headers={"Accept": "text/event-stream"})
    assert response.headers["content-type"].startswith("text/event-stream")


def test_explain_yields_json_messages():
    """Each data: line must be valid JSON with a known A2UI message type."""
    messages = [
        'data: {"version": "v0.9", "createSurface": {"surfaceId": "explain-EURUSD__2026-05-04", "catalogId": "C"}}\n\n',
        'data: {"version": "v0.9", "updateComponents": {"surfaceId": "explain-EURUSD__2026-05-04", "components": []}}\n\n',
    ]
    with patch("routers.explain.stream_explanation") as mock_stream:
        mock_stream.return_value = iter(messages)
        response = client.get("/api/explain/EURUSD__2026-05-04")

    lines = [l for l in response.text.split("\n\n") if l.startswith("data: ")]
    parsed = [json.loads(l[6:]) for l in lines]
    assert any("createSurface" in m for m in parsed)
    assert any("updateComponents" in m for m in parsed)


def test_explain_signal_not_found_returns_404():
    """If signal row not found in S3, return 404 before opening stream."""
    with patch("routers.explain.stream_explanation") as mock_stream:
        mock_stream.side_effect = LookupError("Signal not found: EURUSD__2099-01-01")
        response = client.get("/api/explain/EURUSD__2099-01-01")
    assert response.status_code == 404


def test_explain_invalid_signal_id_returns_422():
    """Malformed signal_id (no double underscore) returns 422."""
    with patch("routers.explain.stream_explanation") as mock_stream:
        mock_stream.side_effect = ValueError("Invalid signal_id")
        response = client.get("/api/explain/EURUSD-badformat")
    assert response.status_code == 422

# apps/api/tests/explain/test_resolve_key.py
from __future__ import annotations

from unittest.mock import MagicMock, patch

import livewell.explain.builder as builder


def _reset_cache():
    builder._ANTHROPIC_KEY_CACHE = None


def test_direct_env_var_wins(monkeypatch):
    _reset_cache()
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-direct")
    monkeypatch.delenv("ANTHROPIC_API_KEY_SSM_PARAM", raising=False)
    assert builder._resolve_anthropic_key() == "sk-direct"


def test_falls_back_to_ssm_and_caches(monkeypatch):
    _reset_cache()
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY_SSM_PARAM", "/livewell/prod/anthropic-api-key")

    mock_client = MagicMock()
    mock_client.get_parameter.return_value = {"Parameter": {"Value": "sk-from-ssm"}}
    with patch("boto3.client", return_value=mock_client) as mock_boto:
        assert builder._resolve_anthropic_key() == "sk-from-ssm"
        # second call uses the cache — no second SSM fetch
        assert builder._resolve_anthropic_key() == "sk-from-ssm"
        assert mock_boto.call_count == 1
        mock_client.get_parameter.assert_called_once_with(
            Name="/livewell/prod/anthropic-api-key", WithDecryption=True
        )
    _reset_cache()


def test_returns_none_when_unconfigured(monkeypatch):
    _reset_cache()
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY_SSM_PARAM", raising=False)
    assert builder._resolve_anthropic_key() is None

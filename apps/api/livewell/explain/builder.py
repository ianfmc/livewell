"""Build a JSON signal explanation (four Claude-written sections + a header)."""

from __future__ import annotations

import os

import boto3
import pandas as pd

from livewell.signals.constants import SIGNALS_PREFIX

SYSTEM_PROMPT = """\
You are a trading signal analyst for NADEX binary options. Given a signal row, \
write a concise explanation for a trader. Be factual, specific, and brief.
Write exactly four sections in order: Trend, Momentum, Session, Timing.
Each section is 1-2 sentences. Use the indicator values provided.
Do not recommend trading. Do not add hedging language.
Output format: one section per paragraph, no headers.\
"""


def parse_signal_id(signal_id: str) -> tuple[str, str]:
    """Parse '{s3_key}__{date}' into (s3_key, date_str). Raises ValueError on bad format."""
    parts = signal_id.split("__", 1)
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError(f"Invalid signal_id '{signal_id}': expected '{{s3_key}}__{{date}}'")
    return parts[0], parts[1]


def load_signal_row(bucket: str, s3_key: str, date_str: str) -> dict | None:
    """Read the signal row for s3_key on date_str from S3. Returns None if not found."""
    year = date_str[:4]
    key = f"{SIGNALS_PREFIX}/{s3_key}/1d/{year}.parquet"

    client = boto3.client("s3")
    try:
        obj = client.get_object(Bucket=bucket, Key=key)
        df = pd.read_parquet(obj["Body"])
    except Exception:  # noqa: BLE001  # any S3/parquet read failure -> treat as "not found"
        return None

    df["date"] = pd.to_datetime(df["date"], utc=True)
    target = pd.Timestamp(date_str, tz="UTC")
    match = df[df["date"].dt.date == target.date()]
    if match.empty:
        return None
    return match.iloc[0].to_dict()


def _num(row: dict, key: str) -> float:
    """Coerce a possibly-string numeric field to float (DynamoDB stores these as
    strings; S3 parquet as floats). Returns NaN when missing/unparseable so the
    prompt still formats."""
    raw = row.get(key)
    if raw is None:
        return float("nan")
    try:
        return float(raw)
    except (ValueError, TypeError):
        return float("nan")


_ANTHROPIC_KEY_CACHE: str | None = None


def _resolve_anthropic_key() -> str | None:
    """Resolve the Anthropic API key.

    Order: an explicit ANTHROPIC_API_KEY env var (local dev / override), else the
    SSM SecureString named by ANTHROPIC_API_KEY_SSM_PARAM (fetched + decrypted once
    per cold start and cached). CloudFormation cannot inject an ssm-secure value
    into a Lambda env var, so prod passes the param NAME and the Lambda fetches it
    at runtime. Returns None if neither is configured (lets the Anthropic client
    raise its own clear auth error).
    """
    global _ANTHROPIC_KEY_CACHE

    direct = os.environ.get("ANTHROPIC_API_KEY")
    if direct:
        return direct

    if _ANTHROPIC_KEY_CACHE is not None:
        return _ANTHROPIC_KEY_CACHE

    param_name = os.environ.get("ANTHROPIC_API_KEY_SSM_PARAM")
    if not param_name:
        return None

    import boto3

    resp = boto3.client("ssm").get_parameter(Name=param_name, WithDecryption=True)
    _ANTHROPIC_KEY_CACHE = resp["Parameter"]["Value"]
    return _ANTHROPIC_KEY_CACHE


def _format_row_for_prompt(row: dict) -> str:
    """Format a signal row as structured text for the Claude prompt."""
    return (
        f"Instrument: {row.get('s3_key')}\n"
        f"Direction: {row.get('direction')}\n"
        f"Date: {row.get('date')}\n"
        f"EMA 20: {_num(row, 'ema_20'):.5f}, EMA 50: {_num(row, 'ema_50'):.5f}\n"
        f"RSI 14: {_num(row, 'rsi_14'):.2f}\n"
        f"MACD hist: {_num(row, 'macd_hist'):.6f}\n"
        f"ATR 14: {_num(row, 'atr_14'):.5f}\n"
        f"Session quality: {row.get('session_quality')}\n"
        f"Timing slot: {row.get('timing_slot')}, risk: {row.get('timing_risk')}\n"
        f"Signal valid: {row.get('signal_valid')}\n"
        f"Reasoning: {row.get('reasoning')}"
    )


def _build_header(row: dict) -> str:
    date_label = str(row.get("date", ""))[:10]
    return f"{row.get('s3_key')} · {row.get('direction')} · {date_label}"


def build_explanation(bucket: str, signal_id: str) -> dict:
    """
    Full pipeline: parse signal_id, load S3 row, call Claude, return dict.

    Returns keys: header, trend, momentum, session, timing.
    Raises ValueError if signal_id is malformed.
    Raises LookupError if the signal row is not found.
    """
    import anthropic
    from anthropic.types import TextBlock

    from livewell.signals.dynamodb import get_signal

    s3_key, date_str = parse_signal_id(signal_id)
    # Read the signal from DynamoDB first — the same source /api/signals serves,
    # so Explain resolves for exactly the signals the list shows. Fall back to the
    # S3 parquet for historical/frozen signals that predate the operational table.
    row = get_signal(s3_key, date_str) or load_signal_row(bucket, s3_key, date_str)
    if row is None:
        raise LookupError(f"Signal not found: {signal_id}")

    user_message = _format_row_for_prompt(row)

    client = anthropic.Anthropic(api_key=_resolve_anthropic_key())
    response = client.messages.create(
        model=os.environ.get("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001"),
        max_tokens=512,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )
    block = response.content[0]
    if not isinstance(block, TextBlock):
        raise RuntimeError(f"Expected a text block from Claude, got {type(block).__name__}")
    full_text = block.text.strip()

    # Split on double newlines into up to 4 paragraphs
    raw_paragraphs = [p.strip() for p in full_text.split("\n\n") if p.strip()]
    paragraphs = raw_paragraphs[:4]
    # Pad with empty string if Claude returns fewer than 4 sections
    while len(paragraphs) < 4:
        paragraphs.append("")

    return {
        "header": _build_header(row),
        "trend": paragraphs[0],
        "momentum": paragraphs[1],
        "session": paragraphs[2],
        "timing": paragraphs[3],
    }

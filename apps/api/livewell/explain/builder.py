"""Assemble A2UI SSE messages for a signal explanation."""
from __future__ import annotations

import json
import os
from collections.abc import Iterator

import boto3
import pandas as pd

from livewell.signals.constants import SIGNALS_PREFIX

SURFACE_ID_PREFIX = "explain-"
CATALOG_ID = "https://a2ui.org/specification/v0_9/basic_catalog.json"
SECTIONS = ["trend", "momentum", "session", "timing"]

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
    except Exception:
        return None

    df["date"] = pd.to_datetime(df["date"], utc=True)
    target = pd.Timestamp(date_str, tz="UTC")
    match = df[df["date"].dt.date == target.date()]
    if match.empty:
        return None
    return match.iloc[0].to_dict()


def _format_row_for_prompt(row: dict) -> str:
    """Format a signal row as structured text for the Claude prompt."""
    return (
        f"Instrument: {row.get('s3_key')}\n"
        f"Direction: {row.get('direction')}\n"
        f"Date: {row.get('date')}\n"
        f"EMA 20: {row.get('ema_20'):.5f}, EMA 50: {row.get('ema_50'):.5f}\n"
        f"RSI 14: {row.get('rsi_14'):.2f}\n"
        f"MACD hist: {row.get('macd_hist'):.6f}\n"
        f"ATR 14: {row.get('atr_14'):.5f}\n"
        f"Session quality: {row.get('session_quality')}\n"
        f"Timing slot: {row.get('timing_slot')}, risk: {row.get('timing_risk')}\n"
        f"Signal valid: {row.get('signal_valid')}\n"
        f"Reasoning: {row.get('reasoning')}"
    )


def _build_header(row: dict) -> str:
    date_label = str(row.get("date", ""))[:10]
    return f"{row.get('s3_key')} · {row.get('direction')} · {date_label}"


def build_explain_messages(
    surface_id: str,
    row: dict,
    paragraphs: list[str],
) -> Iterator[str]:
    """
    Yield A2UI JSON message strings for a signal explanation.

    Args:
        surface_id: Full surface ID string e.g. "explain-EURUSD__2026-05-04"
        row: Signal row dict (output of load_signal_row)
        paragraphs: List of 4 prose strings [trend, momentum, session, timing]
    """
    # ① createSurface
    yield json.dumps({
        "version": "v0.9",
        "createSurface": {"surfaceId": surface_id, "catalogId": CATALOG_ID},
    })

    # ② updateComponents — deterministic layout skeleton
    yield json.dumps({
        "version": "v0.9",
        "updateComponents": {
            "surfaceId": surface_id,
            "components": [
                {"id": "root", "component": "Column", "children": ["header", "trend", "momentum", "session", "timing"]},
                {"id": "header", "component": "Text", "text": {"path": "/header"}},
                {"id": "trend",    "component": "Text", "text": {"path": "/trend"}},
                {"id": "momentum", "component": "Text", "text": {"path": "/momentum"}},
                {"id": "session",  "component": "Text", "text": {"path": "/session"}},
                {"id": "timing",   "component": "Text", "text": {"path": "/timing"}},
            ],
        },
    })

    # ③ header (assembled by backend, not Claude)
    yield json.dumps({
        "version": "v0.9",
        "updateDataModel": {
            "surfaceId": surface_id,
            "path": "/header",
            "value": _build_header(row),
        },
    })

    # ④–⑦ one updateDataModel per Claude paragraph
    for section, text in zip(SECTIONS, paragraphs):
        yield json.dumps({
            "version": "v0.9",
            "updateDataModel": {
                "surfaceId": surface_id,
                "path": f"/{section}",
                "value": text,
            },
        })


def stream_explanation(bucket: str, signal_id: str) -> Iterator[str]:
    """
    Full pipeline: parse signal_id, load S3 row, call Claude, yield SSE data lines.

    Each yielded string is a complete SSE line: "data: {json}\\n\\n".
    Raises ValueError if signal_id is malformed.
    Raises LookupError if signal row not found in S3.
    """
    import anthropic

    s3_key, date_str = parse_signal_id(signal_id)
    row = load_signal_row(bucket, s3_key, date_str)
    if row is None:
        raise LookupError(f"Signal not found: {signal_id}")

    surface_id = f"{SURFACE_ID_PREFIX}{signal_id}"
    user_message = _format_row_for_prompt(row)

    # Stream Claude response and collect paragraphs
    client = anthropic.Anthropic()
    paragraphs: list[str] = []
    current: list[str] = []

    # Yield createSurface and updateComponents first (before Claude starts)
    yield f"data: {json.dumps({'version': 'v0.9', 'createSurface': {'surfaceId': surface_id, 'catalogId': CATALOG_ID}})}\n\n"
    yield f"data: {json.dumps({'version': 'v0.9', 'updateComponents': {'surfaceId': surface_id, 'components': [{'id': 'root', 'component': 'Column', 'children': ['header', 'trend', 'momentum', 'session', 'timing']}, {'id': 'header', 'component': 'Text', 'text': {'path': '/header'}}, {'id': 'trend', 'component': 'Text', 'text': {'path': '/trend'}}, {'id': 'momentum', 'component': 'Text', 'text': {'path': '/momentum'}}, {'id': 'session', 'component': 'Text', 'text': {'path': '/session'}}, {'id': 'timing', 'component': 'Text', 'text': {'path': '/timing'}}]}})}\n\n"
    yield f"data: {json.dumps({'version': 'v0.9', 'updateDataModel': {'surfaceId': surface_id, 'path': '/header', 'value': _build_header(row)}})}\n\n"

    with client.messages.stream(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    ) as stream:
        for text_chunk in stream.text_stream:
            current.append(text_chunk)
            combined = "".join(current)
            # Split on double newline (paragraph boundary)
            while "\n\n" in combined and len(paragraphs) < len(SECTIONS):
                para, remainder = combined.split("\n\n", 1)
                para = para.strip()
                if para:
                    paragraphs.append(para)
                    section = SECTIONS[len(paragraphs) - 1]
                    yield f"data: {json.dumps({'version': 'v0.9', 'updateDataModel': {'surfaceId': surface_id, 'path': f'/{section}', 'value': para}})}\n\n"
                current = [remainder]

        # Emit any remaining text as the last section
        remainder = "".join(current).strip()
        if remainder and len(paragraphs) < len(SECTIONS):
            section = SECTIONS[len(paragraphs)]
            yield f"data: {json.dumps({'version': 'v0.9', 'updateDataModel': {'surfaceId': surface_id, 'path': f'/{section}', 'value': remainder}})}\n\n"

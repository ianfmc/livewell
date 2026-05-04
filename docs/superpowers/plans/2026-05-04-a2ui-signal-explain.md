# A2UI Signal Explanation Panel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a "Explain ›" button to the DailySignals page that streams a Claude-generated explanation via SSE into an inline A2UI panel below the signal list.

**Architecture:** FastAPI streams A2UI v0.9 JSON messages (createSurface → updateComponents → updateDataModel×4 → done) over SSE from `GET /api/explain/{signal_id}`. React holds a singleton `MessageProcessor` in context (A2uiProvider), and `useSignalExplain` feeds SSE messages to it. `SignalExplainPanel` renders `<A2uiSurface>` inline below the signal list.

**Tech Stack:** Python `anthropic` SDK (streaming), FastAPI `StreamingResponse`, `@a2ui/react/v0_9` + `@a2ui/web_core/v0_9` (local file: path), React 19, Vitest, pytest + httpx

---

## File Structure

### New files

**Backend:**
- `apps/api/livewell/explain/__init__.py` — package marker
- `apps/api/livewell/explain/builder.py` — `signal_id` parser, S3 read, Claude streaming, A2UI message assembly
- `apps/api/routers/explain.py` — `GET /api/explain/{signal_id}` SSE endpoint

**Backend tests:**
- `apps/api/tests/explain/__init__.py`
- `apps/api/tests/explain/test_builder.py` — unit tests for builder (mocked Claude + S3)
- `apps/api/tests/explain/test_router.py` — integration test via FastAPI `TestClient`

**Frontend:**
- `apps/web/src/a2ui/A2uiProvider.tsx` — creates `MessageProcessor<ReactComponentImplementation>` with `basicCatalog`, exposes via React context
- `apps/web/src/a2ui/useA2ui.ts` — hook that reads the processor from context, throws if used outside provider
- `apps/web/src/a2ui/A2uiProvider.test.tsx` — tests that context provides processor, throws outside
- `apps/web/src/a2ui/useA2ui.test.ts` — (covered in A2uiProvider.test.tsx via renderHook)
- `apps/web/src/hooks/useSignalExplain.ts` — opens/closes `EventSource`, feeds messages to processor, returns `{ surface, loading, error }`
- `apps/web/src/hooks/useSignalExplain.test.ts` — mocks `EventSource`, feeds message sequence, asserts surface state
- `apps/web/src/components/SignalExplainPanel.tsx` — renders loading state or `<A2uiSurface>`, handles close button
- `apps/web/src/components/SignalExplainPanel.test.tsx` — render with mock surface, assert loading/sections

### Modified files
- `apps/api/main.py` — `include_router(explain.router, prefix="/api")`
- `apps/web/src/main.tsx` — wrap app in `<A2uiProvider>`
- `apps/web/src/pages/DailySignals.tsx` — add "Explain ›" button, `selectedSignalId` state, `<SignalExplainPanel>`
- `apps/web/src/mocks/handlers.ts` — add SSE mock handler for `/api/explain/:signal_id`
- `apps/api/pyproject.toml` — add `anthropic` dependency

---

## Task 1: Build the a2ui packages (prerequisite)

The `@a2ui/react` and `@a2ui/web_core` packages live at `a2ui/renderers/react` and `a2ui/renderers/web_core` but have no `dist/` directory. They must be built before the frontend tasks can import them.

**Files:**
- Read/run: `a2ui/renderers/web_core/` (build)
- Read/run: `a2ui/renderers/react/` (build)

- [ ] **Step 1: Install web_core deps and build**

```bash
cd /path/to/repo/a2ui/renderers/web_core
npm install
npm run build
```

Expected: `dist/` directory appears with `dist/src/v0_9/index.js` and `dist/src/v0_9/index.d.ts`.

- [ ] **Step 2: Install react renderer deps and build**

```bash
cd /path/to/repo/a2ui/renderers/react
npm install
npm run build
```

Expected: `dist/` directory appears with `dist/v0_9/index.js` and `dist/v0_9/index.d.ts`.

- [ ] **Step 3: Add local package references to apps/web/package.json**

In `apps/web/package.json`, add to `dependencies`:

```json
"@a2ui/react": "file:../../a2ui/renderers/react",
"@a2ui/web_core": "file:../../a2ui/renderers/web_core"
```

- [ ] **Step 4: npm install in apps/web**

```bash
cd apps/web
npm install
```

Expected: `node_modules/@a2ui/react` and `node_modules/@a2ui/web_core` now exist.

- [ ] **Step 5: Verify import works**

```bash
cd apps/web
node -e "import('@a2ui/react/v0_9').then(m => console.log('OK:', Object.keys(m).slice(0,3)))"
```

Expected output: `OK: [ 'A2uiSurface', ... ]`

- [ ] **Step 6: Commit**

```bash
git add apps/web/package.json apps/web/package-lock.json
git commit -m "feat: add @a2ui/react and @a2ui/web_core local package references"
```

---

## Task 2: Add anthropic to the API

**Files:**
- Modify: `apps/api/pyproject.toml`
- Modify: `apps/api/uv.lock` (auto-generated)

- [ ] **Step 1: Add anthropic dependency**

```bash
cd apps/api
uv add anthropic
```

Expected: `anthropic` appears in `pyproject.toml` dependencies and `uv.lock` is updated.

- [ ] **Step 2: Verify import**

```bash
cd apps/api
uv run python -c "import anthropic; print(anthropic.__version__)"
```

Expected: prints a version number (e.g. `0.50.0`).

- [ ] **Step 3: Commit**

```bash
git add apps/api/pyproject.toml apps/api/uv.lock
git commit -m "feat: add anthropic SDK dependency to API"
```

---

## Task 3: Backend — explain/builder.py

This module does three things: parse the `signal_id` parameter into `(s3_key, date)`, read the signal row from S3 Parquet, and yield A2UI JSON messages — two immediately (`createSurface`, `updateComponents`), then four progressively as Claude streams prose paragraphs (`updateDataModel` for `/header`, `/trend`, `/momentum`, `/session`, `/timing`).

**Files:**
- Create: `apps/api/livewell/explain/__init__.py`
- Create: `apps/api/livewell/explain/builder.py`
- Create: `apps/api/tests/explain/__init__.py`
- Create: `apps/api/tests/explain/test_builder.py`

### Signal ID format

`signal_id` is `{s3_key}__{iso_date}` e.g. `EURUSD__2026-05-04`. Double underscore separates key from date (avoids URL encoding problems with slashes and colons).

### S3 path

Signals are stored at `signals/{s3_key}/1d/{year}.parquet`. Read the correct year's file, filter to the matching date row.

### A2UI message structure

Each yielded message is a JSON string of one A2UI message object:

```json
{"version": "v0.9", "createSurface": {"surfaceId": "explain-EURUSD__2026-05-04", "catalogId": "https://a2ui.org/specification/v0_9/basic_catalog.json"}}
```

```json
{"version": "v0.9", "updateComponents": {"surfaceId": "explain-EURUSD__2026-05-04", "components": [{"id": "root", "component": "Column", "children": ["header", "trend", "momentum", "session", "timing"]}, {"id": "header", "component": "Text", "text": {"path": "/header"}}, {"id": "trend", "component": "Text", "text": {"path": "/trend"}}, {"id": "momentum", "component": "Text", "text": {"path": "/momentum"}}, {"id": "session", "component": "Text", "text": {"path": "/session"}}, {"id": "timing", "component": "Text", "text": {"path": "/timing"}}]}}
```

```json
{"version": "v0.9", "updateDataModel": {"surfaceId": "explain-EURUSD__2026-05-04", "path": "/header", "value": "EURUSD · buy · 2026-05-04"}}
```

Then one `updateDataModel` per section as Claude streams.

**Note on `catalogId`:** The basic catalog's ID in the `@a2ui/react` source is `"https://a2ui.org/specification/v0_9/basic_catalog.json"`. Use this exact string — it must match what the frontend `basicCatalog` registers.

- [ ] **Step 1: Write the failing tests**

Create `apps/api/tests/explain/__init__.py` (empty).

Create `apps/api/tests/explain/test_builder.py`:

```python
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
```

- [ ] **Step 2: Run tests — verify they all fail**

```bash
cd apps/api
uv run pytest tests/explain/test_builder.py -v
```

Expected: `ImportError` — `livewell.explain.builder` not found.

- [ ] **Step 3: Create the package and builder module**

Create `apps/api/livewell/explain/__init__.py` (empty).

Create `apps/api/livewell/explain/builder.py`:

```python
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
```

- [ ] **Step 4: Run tests — verify they all pass**

```bash
cd apps/api
uv run pytest tests/explain/test_builder.py -v
```

Expected: 8 tests pass.

- [ ] **Step 5: Run full test suite — verify no regressions**

```bash
cd apps/api
uv run pytest --tb=short -q
```

Expected: 90 passed (82 existing + 8 new).

- [ ] **Step 6: Commit**

```bash
git add apps/api/livewell/explain/ apps/api/tests/explain/
git commit -m "feat: add explain/builder.py — signal id parsing, S3 read, A2UI message assembly"
```

---

## Task 4: Backend — explain router + main.py wiring

**Files:**
- Create: `apps/api/routers/explain.py`
- Modify: `apps/api/main.py`
- Create: `apps/api/tests/explain/test_router.py`

- [ ] **Step 1: Write the failing router test**

Create `apps/api/tests/explain/test_router.py`:

```python
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
```

- [ ] **Step 2: Run test — verify it fails**

```bash
cd apps/api
uv run pytest tests/explain/test_router.py -v
```

Expected: FAIL — `explain` router not found in `main.py`.

- [ ] **Step 3: Create the router**

Create `apps/api/routers/explain.py`:

```python
from __future__ import annotations

import os
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from livewell.explain.builder import stream_explanation

router = APIRouter()


@router.get("/explain/{signal_id}")
def explain_signal(signal_id: str) -> StreamingResponse:
    """Stream A2UI SSE messages explaining a signal."""
    bucket = os.environ.get("LIVEWELL_BUCKET", "")

    try:
        gen = stream_explanation(bucket, signal_id)
        # Eagerly consume the LookupError / ValueError that bubble up before streaming starts
        # by wrapping with a peek — FastAPI needs the error before the response opens.
        first = next(gen)  # may raise LookupError or ValueError
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    def _stream():
        yield first
        yield from gen

    return StreamingResponse(
        _stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
```

- [ ] **Step 4: Wire router into main.py**

Edit `apps/api/main.py` — add the import and `include_router` call:

```python
from routers import signals, dashboard, backtest, model_health, tracker, explain

# ... existing middleware ...

app.include_router(explain.router, prefix="/api")
```

- [ ] **Step 5: Run router tests — verify they pass**

```bash
cd apps/api
uv run pytest tests/explain/test_router.py -v
```

Expected: 4 tests pass.

- [ ] **Step 6: Run full test suite — verify no regressions**

```bash
cd apps/api
uv run pytest --tb=short -q
```

Expected: 94 passed (82 + 8 + 4).

- [ ] **Step 7: Commit**

```bash
git add apps/api/routers/explain.py apps/api/main.py apps/api/tests/explain/test_router.py
git commit -m "feat: add GET /api/explain/{signal_id} SSE endpoint"
```

---

## Task 5: Frontend — A2uiProvider + useA2ui hook

The provider creates one `MessageProcessor<ReactComponentImplementation>` instance (with `basicCatalog`) at app startup and exposes it via React context. The hook reads it.

**Files:**
- Create: `apps/web/src/a2ui/A2uiProvider.tsx`
- Create: `apps/web/src/a2ui/useA2ui.ts`
- Create: `apps/web/src/a2ui/A2uiProvider.test.tsx`

- [ ] **Step 1: Write the failing tests**

Create `apps/web/src/a2ui/A2uiProvider.test.tsx`:

```typescript
import { describe, it, expect } from 'vitest';
import { render, renderHook } from '@testing-library/react';
import React from 'react';
import { A2uiProvider } from './A2uiProvider';
import { useA2ui } from './useA2ui';

describe('A2uiProvider', () => {
  it('provides a MessageProcessor to children via useA2ui', () => {
    const { result } = renderHook(() => useA2ui(), {
      wrapper: ({ children }) => <A2uiProvider>{children}</A2uiProvider>,
    });
    expect(result.current).toBeDefined();
    expect(typeof result.current.processMessages).toBe('function');
  });

  it('useA2ui throws when used outside A2uiProvider', () => {
    expect(() => {
      renderHook(() => useA2ui());
    }).toThrow('useA2ui must be used inside <A2uiProvider>');
  });

  it('provider renders children', () => {
    const { getByText } = render(
      <A2uiProvider>
        <span>hello</span>
      </A2uiProvider>
    );
    expect(getByText('hello')).toBeDefined();
  });
});
```

- [ ] **Step 2: Run test — verify it fails**

```bash
export NVM_DIR="$HOME/.nvm" && source "$NVM_DIR/nvm.sh" && nvm use 20
cd apps/web
npx vitest run src/a2ui/A2uiProvider.test.tsx
```

Expected: FAIL — `A2uiProvider` module not found.

- [ ] **Step 3: Create A2uiProvider.tsx**

Create `apps/web/src/a2ui/A2uiProvider.tsx`:

```typescript
import { createContext, useMemo, type ReactNode } from 'react';
import { MessageProcessor } from '@a2ui/web_core/v0_9';
import { basicCatalog, type ReactComponentImplementation } from '@a2ui/react/v0_9';

export const A2uiContext = createContext<MessageProcessor<ReactComponentImplementation> | null>(null);

export function A2uiProvider({ children }: { children: ReactNode }) {
  const processor = useMemo(
    () => new MessageProcessor<ReactComponentImplementation>([basicCatalog]),
    []
  );
  return <A2uiContext.Provider value={processor}>{children}</A2uiContext.Provider>;
}
```

- [ ] **Step 4: Create useA2ui.ts**

Create `apps/web/src/a2ui/useA2ui.ts`:

```typescript
import { useContext } from 'react';
import type { MessageProcessor } from '@a2ui/web_core/v0_9';
import type { ReactComponentImplementation } from '@a2ui/react/v0_9';
import { A2uiContext } from './A2uiProvider';

export function useA2ui(): MessageProcessor<ReactComponentImplementation> {
  const ctx = useContext(A2uiContext);
  if (!ctx) throw new Error('useA2ui must be used inside <A2uiProvider>');
  return ctx;
}
```

- [ ] **Step 5: Run tests — verify they pass**

```bash
cd apps/web
npx vitest run src/a2ui/A2uiProvider.test.tsx
```

Expected: 3 tests pass.

- [ ] **Step 6: Run full test suite — verify no regressions**

```bash
npx vitest run
```

Expected: all 65 existing tests pass plus 3 new = 68.

- [ ] **Step 7: Commit**

```bash
git add apps/web/src/a2ui/
git commit -m "feat: add A2uiProvider and useA2ui hook"
```

---

## Task 6: Frontend — useSignalExplain hook

This hook opens an `EventSource` to `/api/explain/{signalId}`, feeds each SSE message to the shared `MessageProcessor`, and returns `{ surface, loading, error }`.

**Key design notes:**
- `EventSource` is opened when `signalId` changes and is non-null; closed on cleanup.
- The `surface` is read from `processor.model.surfacesMap` by `surfaceId`. State is updated by subscribing to `processor.onSurfaceCreated`.
- `loading` becomes false when `EventSource` receives the first message (or errors).
- On close (unmount or signalId change), the hook calls `processor.processMessage` with a `deleteSurface` message for the old surfaceId.
- `EventSource` has no native mock in jsdom — the test provides a class mock.

**Files:**
- Create: `apps/web/src/hooks/useSignalExplain.ts`
- Create: `apps/web/src/hooks/useSignalExplain.test.ts`

- [ ] **Step 1: Write the failing tests**

Create `apps/web/src/hooks/useSignalExplain.test.ts`:

```typescript
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import React from 'react';
import { A2uiProvider } from '../a2ui/A2uiProvider';
import { useSignalExplain } from './useSignalExplain';

// ── EventSource mock ──────────────────────────────────────────────────────────
type ESHandler = (event: MessageEvent) => void;

class MockEventSource {
  static instances: MockEventSource[] = [];
  url: string;
  onmessage: ESHandler | null = null;
  onerror: ((e: Event) => void) | null = null;
  readyState = 0;
  private _closed = false;

  constructor(url: string) {
    this.url = url;
    MockEventSource.instances.push(this);
  }

  dispatchMessage(data: string) {
    this.onmessage?.(new MessageEvent('message', { data }));
  }

  close() { this._closed = true; this.readyState = 2; }
  get closed() { return this._closed; }
}

// ── Tests ─────────────────────────────────────────────────────────────────────

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <A2uiProvider>{children}</A2uiProvider>
);

beforeEach(() => {
  MockEventSource.instances = [];
  vi.stubGlobal('EventSource', MockEventSource);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('useSignalExplain', () => {
  it('starts loading when signalId is provided', () => {
    const { result } = renderHook(() => useSignalExplain('EURUSD__2026-05-04'), { wrapper });
    expect(result.current.loading).toBe(true);
    expect(result.current.surface).toBeNull();
  });

  it('returns null surface and loading=false when signalId is null', () => {
    const { result } = renderHook(() => useSignalExplain(null), { wrapper });
    expect(result.current.loading).toBe(false);
    expect(result.current.surface).toBeNull();
  });

  it('opens EventSource to correct URL', () => {
    renderHook(() => useSignalExplain('EURUSD__2026-05-04'), { wrapper });
    expect(MockEventSource.instances).toHaveLength(1);
    expect(MockEventSource.instances[0].url).toBe('/api/explain/EURUSD__2026-05-04');
  });

  it('processes SSE messages through MessageProcessor', async () => {
    const { result } = renderHook(() => useSignalExplain('EURUSD__2026-05-04'), { wrapper });
    const es = MockEventSource.instances[0];

    await act(async () => {
      es.dispatchMessage(JSON.stringify({
        version: 'v0.9',
        createSurface: {
          surfaceId: 'explain-EURUSD__2026-05-04',
          catalogId: 'https://a2ui.org/specification/v0_9/basic_catalog.json',
        },
      }));
    });

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.surface).not.toBeNull();
  });

  it('sets error when EventSource fires onerror', async () => {
    const { result } = renderHook(() => useSignalExplain('EURUSD__2026-05-04'), { wrapper });
    const es = MockEventSource.instances[0];

    await act(async () => {
      es.onerror?.(new Event('error'));
    });

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.error).not.toBeNull();
  });

  it('closes EventSource on unmount', () => {
    const { result, unmount } = renderHook(() => useSignalExplain('EURUSD__2026-05-04'), { wrapper });
    const es = MockEventSource.instances[0];
    unmount();
    expect(es.closed).toBe(true);
  });
});
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
cd apps/web
npx vitest run src/hooks/useSignalExplain.test.ts
```

Expected: FAIL — `useSignalExplain` not found.

- [ ] **Step 3: Create useSignalExplain.ts**

Create `apps/web/src/hooks/useSignalExplain.ts`:

```typescript
import { useEffect, useState, useRef } from 'react';
import type { SurfaceModel } from '@a2ui/web_core/v0_9';
import type { ReactComponentImplementation } from '@a2ui/react/v0_9';
import { useA2ui } from '../a2ui/useA2ui';

type UseSignalExplainResult = {
  surface: SurfaceModel<ReactComponentImplementation> | null;
  loading: boolean;
  error: string | null;
};

export function useSignalExplain(signalId: string | null): UseSignalExplainResult {
  const processor = useA2ui();
  const [surface, setSurface] = useState<SurfaceModel<ReactComponentImplementation> | null>(null);
  const [loading, setLoading] = useState(signalId !== null);
  const [error, setError] = useState<string | null>(null);
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!signalId) {
      setLoading(false);
      setSurface(null);
      setError(null);
      return;
    }

    const surfaceId = `explain-${signalId}`;
    setLoading(true);
    setError(null);
    setSurface(null);

    const es = new EventSource(`/api/explain/${signalId}`);
    esRef.current = es;

    es.onmessage = (event: MessageEvent) => {
      try {
        const msg = JSON.parse(event.data as string);
        processor.processMessages([msg]);

        if ('createSurface' in msg) {
          const s = processor.model.getSurface(surfaceId);
          if (s) setSurface(s);
          setLoading(false);
        }
      } catch {
        setError('Failed to parse SSE message');
        setLoading(false);
      }
    };

    es.onerror = () => {
      setError('Connection error');
      setLoading(false);
      es.close();
    };

    return () => {
      es.close();
      esRef.current = null;
      // Clean up surface in processor
      try {
        processor.processMessages([{ version: 'v0.9', deleteSurface: { surfaceId } }]);
      } catch {
        // Surface may not exist if stream didn't start
      }
      setSurface(null);
    };
  }, [signalId, processor]);

  return { surface, loading, error };
}
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
cd apps/web
npx vitest run src/hooks/useSignalExplain.test.ts
```

Expected: 6 tests pass.

- [ ] **Step 5: Run full test suite — no regressions**

```bash
npx vitest run
```

Expected: 68 + 6 = 74 tests pass.

- [ ] **Step 6: Commit**

```bash
git add apps/web/src/hooks/useSignalExplain.ts apps/web/src/hooks/useSignalExplain.test.ts
git commit -m "feat: add useSignalExplain hook — EventSource + MessageProcessor integration"
```

---

## Task 7: Frontend — SignalExplainPanel component

This is the inline expansion panel rendered below the signal list. It calls `useSignalExplain`, shows a loading spinner, renders `<A2uiSurface>` when surface is available, and has a close button.

**Files:**
- Create: `apps/web/src/components/SignalExplainPanel.tsx`
- Create: `apps/web/src/components/SignalExplainPanel.test.tsx`

- [ ] **Step 1: Write the failing tests**

Create `apps/web/src/components/SignalExplainPanel.test.tsx`:

```typescript
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';
import { A2uiProvider } from '../a2ui/A2uiProvider';
import { SignalExplainPanel } from './SignalExplainPanel';

// Mock useSignalExplain so we control what it returns
vi.mock('../hooks/useSignalExplain');
import { useSignalExplain } from '../hooks/useSignalExplain';
const mockUseSignalExplain = vi.mocked(useSignalExplain);

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <A2uiProvider>{children}</A2uiProvider>
);

beforeEach(() => {
  mockUseSignalExplain.mockReturnValue({ surface: null, loading: false, error: null });
});

afterEach(() => vi.clearAllMocks());

describe('SignalExplainPanel', () => {
  it('renders nothing when signalId is null', () => {
    const { container } = render(
      <SignalExplainPanel signalId={null} onClose={() => {}} />,
      { wrapper }
    );
    expect(container.firstChild).toBeNull();
  });

  it('shows loading spinner when loading=true', () => {
    mockUseSignalExplain.mockReturnValue({ surface: null, loading: true, error: null });
    render(
      <SignalExplainPanel signalId="EURUSD__2026-05-04" onClose={() => {}} />,
      { wrapper }
    );
    expect(screen.getByRole('progressbar')).toBeDefined();
  });

  it('shows error message when error is set', () => {
    mockUseSignalExplain.mockReturnValue({ surface: null, loading: false, error: 'Connection error' });
    render(
      <SignalExplainPanel signalId="EURUSD__2026-05-04" onClose={() => {}} />,
      { wrapper }
    );
    expect(screen.getByText(/connection error/i)).toBeDefined();
  });

  it('calls onClose when close button is clicked', () => {
    const onClose = vi.fn();
    render(
      <SignalExplainPanel signalId="EURUSD__2026-05-04" onClose={onClose} />,
      { wrapper }
    );
    fireEvent.click(screen.getByRole('button', { name: /close/i }));
    expect(onClose).toHaveBeenCalledOnce();
  });

  it('renders surface container when surface is available', () => {
    // Provide a minimal surface mock — A2uiSurface will handle rendering
    const mockSurface = { id: 'explain-EURUSD__2026-05-04' } as any;
    mockUseSignalExplain.mockReturnValue({ surface: mockSurface, loading: false, error: null });

    render(
      <SignalExplainPanel signalId="EURUSD__2026-05-04" onClose={() => {}} />,
      { wrapper }
    );
    // The panel wrapper should be present (identified by data-testid)
    expect(screen.getByTestId('signal-explain-panel')).toBeDefined();
  });
});
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
cd apps/web
npx vitest run src/components/SignalExplainPanel.test.tsx
```

Expected: FAIL — `SignalExplainPanel` module not found.

- [ ] **Step 3: Create SignalExplainPanel.tsx**

Create `apps/web/src/components/SignalExplainPanel.tsx`:

```typescript
import Box from '@mui/material/Box';
import CircularProgress from '@mui/material/CircularProgress';
import Alert from '@mui/material/Alert';
import IconButton from '@mui/material/IconButton';
import CloseIcon from '@mui/icons-material/Close';
import Typography from '@mui/material/Typography';
import { A2uiSurface } from '@a2ui/react/v0_9';
import { useSignalExplain } from '../hooks/useSignalExplain';

type Props = {
  signalId: string | null;
  onClose: () => void;
};

export function SignalExplainPanel({ signalId, onClose }: Props) {
  const { surface, loading, error } = useSignalExplain(signalId);

  if (!signalId) return null;

  return (
    <Box
      data-testid="signal-explain-panel"
      sx={{
        mt: 2,
        p: 2,
        border: '1px solid',
        borderColor: 'divider',
        borderRadius: 2,
        position: 'relative',
        minHeight: 80,
      }}
    >
      <IconButton
        aria-label="close"
        size="small"
        onClick={onClose}
        sx={{ position: 'absolute', top: 8, right: 8 }}
      >
        <CloseIcon fontSize="small" />
      </IconButton>

      {loading && (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 3 }}>
          <CircularProgress size={24} />
        </Box>
      )}

      {error && (
        <Alert severity="error" sx={{ mt: 1 }}>
          {error}
        </Alert>
      )}

      {!loading && !error && surface && (
        <Box sx={{ pr: 4 }}>
          <A2uiSurface surface={surface} />
        </Box>
      )}

      {!loading && !error && !surface && (
        <Typography variant="body2" color="text.secondary">
          Generating explanation…
        </Typography>
      )}
    </Box>
  );
}
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
cd apps/web
npx vitest run src/components/SignalExplainPanel.test.tsx
```

Expected: 5 tests pass.

- [ ] **Step 5: Run full test suite — no regressions**

```bash
npx vitest run
```

Expected: 74 + 5 = 79 tests pass.

- [ ] **Step 6: Commit**

```bash
git add apps/web/src/components/SignalExplainPanel.tsx apps/web/src/components/SignalExplainPanel.test.tsx
git commit -m "feat: add SignalExplainPanel component"
```

---

## Task 8: Wire everything into the app (main.tsx + DailySignals)

**Files:**
- Modify: `apps/web/src/main.tsx`
- Modify: `apps/web/src/pages/DailySignals.tsx`
- Modify: `apps/web/src/mocks/handlers.ts`

- [ ] **Step 1: Wrap app in A2uiProvider in main.tsx**

Edit `apps/web/src/main.tsx` — add the import and wrap:

```typescript
import { A2uiProvider } from './a2ui/A2uiProvider';

// Inside the render() call, wrap ThemeProvider:
<StrictMode>
  <BrowserRouter>
    <A2uiProvider>
      <ThemeProvider>
        <App />
      </ThemeProvider>
    </A2uiProvider>
  </BrowserRouter>
</StrictMode>
```

- [ ] **Step 2: Add "Explain ›" to DailySignals**

Edit `apps/web/src/pages/DailySignals.tsx`:

```typescript
// Add these imports at the top:
import Button from '@mui/material/Button';
import { SignalExplainPanel } from '../components/SignalExplainPanel';

// Add state inside the component (after existing useState calls):
const [selectedSignalId, setSelectedSignalId] = useState<string | null>(null);

// In the Grid where ContractCard is rendered, add the Explain button after ContractCard:
<ContractCard ... />
<Button
  size="small"
  variant="text"
  onClick={() => {
    const id = `${card.instrument}__${card.expiry}`;
    setSelectedSignalId(prev => prev === id ? null : id);
  }}
  sx={{ mt: 1 }}
>
  Explain ›
</Button>

// After the closing </Grid> tag (inside the !loading && !error block), add the panel:
<SignalExplainPanel
  signalId={selectedSignalId}
  onClose={() => setSelectedSignalId(null)}
/>
```

- [ ] **Step 3: Add SSE mock handler to handlers.ts**

Edit `apps/web/src/mocks/handlers.ts` — add the explain handler:

```typescript
import { http, HttpResponse } from 'msw';

// Add to handlers array:
http.get('/api/explain/:signal_id', ({ params }) => {
  const { signal_id } = params;
  const surfaceId = `explain-${signal_id as string}`;
  const catalogId = 'https://a2ui.org/specification/v0_9/basic_catalog.json';

  const messages = [
    JSON.stringify({ version: 'v0.9', createSurface: { surfaceId, catalogId } }),
    JSON.stringify({ version: 'v0.9', updateComponents: { surfaceId, components: [
      { id: 'root', component: 'Column', children: ['header', 'trend', 'momentum', 'session', 'timing'] },
      { id: 'header', component: 'Text', text: { path: '/header' } },
      { id: 'trend', component: 'Text', text: { path: '/trend' } },
      { id: 'momentum', component: 'Text', text: { path: '/momentum' } },
      { id: 'session', component: 'Text', text: { path: '/session' } },
      { id: 'timing', component: 'Text', text: { path: '/timing' } },
    ]}}),
    JSON.stringify({ version: 'v0.9', updateDataModel: { surfaceId, path: '/header', value: `${signal_id as string} · mock` } }),
    JSON.stringify({ version: 'v0.9', updateDataModel: { surfaceId, path: '/trend', value: 'EMA 20 above EMA 50 — bullish bias.' } }),
    JSON.stringify({ version: 'v0.9', updateDataModel: { surfaceId, path: '/momentum', value: 'RSI at 58 — neutral with room to extend.' } }),
    JSON.stringify({ version: 'v0.9', updateDataModel: { surfaceId, path: '/session', value: 'London session — high quality.' } }),
    JSON.stringify({ version: 'v0.9', updateDataModel: { surfaceId, path: '/timing', value: 'buy_bullish slot — moderate risk.' } }),
  ];

  const body = messages.map(m => `data: ${m}\n\n`).join('');
  return new HttpResponse(body, {
    headers: { 'Content-Type': 'text/event-stream' },
  });
}),
```

- [ ] **Step 4: Run DailySignals tests — verify no regressions**

```bash
cd apps/web
npx vitest run src/pages/DailySignals.test.tsx
```

Expected: all existing DailySignals tests pass.

- [ ] **Step 5: Run full test suite**

```bash
npx vitest run
```

Expected: 79+ tests pass.

- [ ] **Step 6: Start dev server and manually verify in browser**

```bash
# Terminal 1: start API
cd apps/api
LIVEWELL_BUCKET=livewell-dev uv run uvicorn main:app --reload

# Terminal 2: start frontend
cd apps/web
npm run dev
```

Open http://localhost:5173. Navigate to Daily Signals. Click "Explain ›" on a signal card. Verify:
- Panel appears inline below the signal list
- Loading spinner shows briefly
- Sections fill in progressively (or appear all at once with mock data)
- Close button dismisses the panel
- Clicking "Explain ›" on a different card switches the panel

- [ ] **Step 7: Commit**

```bash
git add apps/web/src/main.tsx apps/web/src/pages/DailySignals.tsx apps/web/src/mocks/handlers.ts
git commit -m "feat: wire A2uiProvider, Explain button, and SignalExplainPanel into DailySignals"
```

---

## Self-Review Checklist

After all tasks complete, run:

```bash
# Backend
cd apps/api && uv run pytest --tb=short -q

# Frontend
cd apps/web && npx vitest run
```

Both must pass with zero regressions before finishing the branch.

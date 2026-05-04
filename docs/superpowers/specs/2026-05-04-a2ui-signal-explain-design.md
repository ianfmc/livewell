# A2UI Signal Explanation Panel — Design Spec

## Goal

Integrate the A2UI protocol into LIVEWELL as a proving-ground pattern, starting with a "Explain This Signal" feature on the DailySignals page. A user clicks "Explain ›" on any signal card; the FastAPI backend streams A2UI JSON messages over SSE; the React front end renders a progressively-appearing explanation panel inline below the signal list.

This integration is the reference pattern for A2UI use across other projects. It must be idiomatic — using SSE streaming, a shared `MessageProcessor`, and React context — not a one-off shortcut.

## Scope

- One new FastAPI endpoint: `GET /api/explain/{signal_id}` (SSE)
- One new A2UI provider + context in the React app (wraps the entire app; scales to future surfaces)
- One new feature: `SignalExplainPanel` inline expansion on DailySignals
- Signal data read from S3 Parquet (real pipeline output, not mock data)
- Claude generates prose explanation text; FastAPI assembles A2UI component structure

**Out of scope:** WebSocket transport, user interaction events back to the agent, custom A2UI component catalog, other pages using A2UI (those come later).

## Architecture

### Transport: SSE

FastAPI streams A2UI v0.9 JSON messages over Server-Sent Events. React opens an `EventSource`, feeds messages to a shared `MessageProcessor`, and `A2uiSurface` renders progressively as data arrives. SSE is the correct transport for this use case — unidirectional, streaming, no polling.

### Shared MessageProcessor

A single `MessageProcessor` instance (from `@a2ui/web_core/v0_9`) is created at app startup and held for the application lifetime. It supports multiple named surfaces simultaneously. It is exposed via React context so any future page can access it without prop drilling.

```
<App>
  └── <A2uiProvider>          ← creates MessageProcessor once
        ├── <DailySignals>
        │     └── useSignalExplain()   ← reads processor from context
        │           └── <A2uiSurface> ← renders "explain-{surfaceId}" surface
        └── ... future pages using same processor
```

### Inline Expansion Layout

"Explain ›" link appears on each signal card. Clicking it expands a panel inline below the signal list (not a modal, not a side panel). The currently-selected signal card is highlighted. Clicking a different signal re-uses the panel for the new signal. Closing dismisses the panel and sends `deleteSurface`.

## A2UI Message Stream

For each explanation request, `builder.py` yields this sequence of SSE messages:

| # | Type | When | Content |
|---|---|---|---|
| ① | `createSurface` | Immediately | `surfaceId: "explain-{instrument}-{timestamp}"`, `catalogId: "basic"` |
| ② | `updateComponents` | Immediately after ① | Fixed layout: `Column` → `[header, trend, momentum, session, timing]`, each a `Text` node bound to a data path |
| ③–⑥ | `updateDataModel` | As Claude streams | One message per section: `/header`, `/trend`, `/momentum`, `/session`, `/timing` |
| ⑦ | `deleteSurface` | On panel close or new signal | Cleans up processor state |

The component structure (②) is deterministic and sent immediately — the panel skeleton appears at once. Claude's prose fills in each section progressively as it's generated.

### Signal ID and Surface ID format

The `signal_id` URL parameter is `{s3_key}__{iso_timestamp}` e.g. `EURUSD__2026-05-04T14:00:00Z` (double underscore separator — avoids URL encoding issues with colons/slashes).

The surface ID is `explain-{signal_id}` e.g. `explain-EURUSD__2026-05-04T14:00:00Z`. Unique per signal row. The endpoint uses this to look up `s3_key` and `date` from the signal_id when reading from S3.

### Explanation sections

| Section | Data path | What Claude writes |
|---|---|---|
| Header | `/header` | `"{instrument} · {direction} · {date}"` — assembled by FastAPI, not Claude |
| Trend | `/trend` | 1–2 sentences on EMA bias and trend context |
| Momentum | `/momentum` | 1–2 sentences on RSI, MACD histogram, and momentum direction |
| Session | `/session` | 1 sentence on session quality and ATR feasibility |
| Timing | `/timing` | 1 sentence on timing slot, risk level, and structural context |

## Claude Prompt Design

`builder.py` calls Claude with a structured prompt. The model generates prose for each section sequentially. FastAPI wraps each completed section in an `updateDataModel` message and yields it immediately.

**Prompt structure (system):**
```
You are a trading signal analyst for NADEX binary options. Given a signal row,
write a concise explanation for a trader. Be factual, specific, and brief.
Write exactly four sections in order: Trend, Momentum, Session, Timing.
Each section is 1-2 sentences. Use the indicator values provided.
Do not recommend trading. Do not add hedging language.
Output format: one section per paragraph, no headers.
```

**User message:** Signal row as structured text (instrument, direction, EMA values, RSI, MACD, ATR, session_quality, timing_slot, timing_risk, signal_valid, reasoning).

`builder.py` parses Claude's streamed output by paragraph boundary and emits one `updateDataModel` per completed paragraph.

## File Structure

### New files

**Backend:**
- `apps/api/livewell/explain/__init__.py`
- `apps/api/livewell/explain/router.py` — `GET /api/explain/{signal_id}` SSE endpoint
- `apps/api/livewell/explain/builder.py` — reads signal from S3, calls Claude, yields A2UI messages
- `apps/api/tests/explain/test_explain.py`

**Frontend:**
- `apps/web/src/a2ui/A2uiProvider.tsx` — creates `MessageProcessor`, exposes via context
- `apps/web/src/a2ui/useA2ui.ts` — hook to access shared processor
- `apps/web/src/a2ui/A2uiProvider.test.tsx`
- `apps/web/src/a2ui/useA2ui.test.ts`
- `apps/web/src/hooks/useSignalExplain.ts` — opens/closes `EventSource`, feeds processor, returns `{ surface, loading, error }`
- `apps/web/src/hooks/useSignalExplain.test.ts`
- `apps/web/src/components/SignalExplainPanel.tsx` — inline expansion panel, hosts `A2uiSurface`
- `apps/web/src/components/SignalExplainPanel.test.tsx`

### Modified files

- `apps/api/livewell/main.py` — register explain router
- `apps/web/src/main.tsx` — wrap app in `<A2uiProvider>`
- `apps/web/src/pages/DailySignals.tsx` — add "Explain ›" button and `<SignalExplainPanel>`

### Dependencies

**Backend:** `anthropic` (already in use), `fastapi` SSE via `StreamingResponse` + `text/event-stream`

**Frontend:** `@a2ui/react`, `@a2ui/web_core` (installed from local `a2ui/` directory or npm once published)

## Data Flow

1. User clicks "Explain ›" on a signal card in `DailySignals`
2. `SignalExplainPanel` mounts; calls `useSignalExplain(signalId)`
3. Hook reads `MessageProcessor` from context; opens `EventSource` to `/api/explain/{signal_id}`
4. FastAPI `explain_signal()`:
   - Reads signal row from S3 Parquet at `signals/{instrument}/{date}.parquet`
   - Yields `createSurface` and `updateComponents` immediately
   - Calls Claude API with signal data
   - As Claude streams each paragraph, yields `updateDataModel` for that section
5. Hook feeds each SSE message to `processor.processMessage()`; updates surface state
6. `SignalExplainPanel` renders `<A2uiSurface surface={surface} />` — sections appear as data arrives
7. User closes panel → hook closes `EventSource`; backend sends `deleteSurface`

## Error Handling

- **Signal not found in S3:** SSE endpoint returns HTTP 404 before opening stream
- **Claude API error mid-stream:** Backend yields a final `updateDataModel` to `/error` path with an error message; frontend renders it in the panel
- **SSE connection dropped:** `EventSource` auto-reconnects; backend is stateless so a fresh reconnect starts a new explanation
- **Panel closed before stream completes:** Hook closes `EventSource`; backend generator is garbage-collected; `deleteSurface` is sent by the frontend directly

## Testing

### Backend (`test_explain.py`)
- Unit test `builder.py` with a fixture signal row; assert the message sequence (types, surfaceId, component tree, data paths)
- Mock Claude API — return canned paragraph responses; assert each triggers the correct `updateDataModel`
- Test SSE endpoint with FastAPI `TestClient`; assert `Content-Type: text/event-stream` and messages are valid JSON

### Frontend
- `useSignalExplain.test.ts`: mock `EventSource`; feed a sequence of A2UI messages; assert hook returns correct surface state and handles loading/error states
- `SignalExplainPanel.test.tsx`: render with mock surface; assert loading state, then sections render in order
- Follow existing patterns: `renderHook` for hooks, `render` + `screen` for components

**Not tested:** Claude prose quality (evaluation, not unit testing), `@a2ui/react` renderer internals (library responsibility).

## Success Criteria

- Clicking "Explain ›" on any valid signal card opens the inline panel
- Panel skeleton appears immediately; sections fill in progressively as Claude streams
- Closing the panel cleans up the surface and SSE connection
- All new tests pass; existing 82 API tests and frontend tests unaffected
- `MessageProcessor` is a singleton — shared across the app, ready for future surfaces

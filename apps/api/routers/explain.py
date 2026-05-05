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

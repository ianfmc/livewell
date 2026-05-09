import logging
import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from livewell.explain.builder import build_explanation

logger = logging.getLogger(__name__)
router = APIRouter()


class ExplainResponse(BaseModel):
    header: str
    trend: str
    momentum: str
    session: str
    timing: str


@router.get("/explain/{signal_id}", response_model=ExplainResponse)
def explain_signal(signal_id: str) -> ExplainResponse:
    """Return a JSON explanation of a signal (four sections from Claude)."""
    bucket = os.environ.get("LIVEWELL_BUCKET", "")

    try:
        result = build_explanation(bucket, signal_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        logger.exception("Unexpected error in explain_signal: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))

    return ExplainResponse(**result)

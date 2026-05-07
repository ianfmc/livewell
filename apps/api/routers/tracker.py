from __future__ import annotations
import logging
from fastapi import APIRouter

from livewell.signals.dynamodb import get_latest_signals
from livewell.signals.transform import score_from_record, recommendation_from_record, NAME_BY_S3_KEY
from schemas.tracker import TrackedSignal

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/signals/tracker", response_model=list[TrackedSignal])
def get_signal_tracker() -> list[TrackedSignal]:
    records = get_latest_signals()
    records_sorted = sorted(records, key=lambda r: str(r.get("date", "")), reverse=True)
    result = []
    for r in records_sorted:
        score = score_from_record(r)
        signal_valid = r.get("signal_valid") is True
        direction = str(r.get("direction", "none"))
        rec = recommendation_from_record(score, signal_valid, direction)
        result.append(TrackedSignal(
            date=str(r.get("date", "")),
            market=NAME_BY_S3_KEY.get(str(r.get("s3_key", "")), str(r.get("s3_key", ""))),
            strike=str(r.get("strike_candidate", "")),
            expiry=str(r.get("timing_slot", "")),
            recommendation=rec,
            actionTaken=None,
            outcome="Pending",
            edge=round((score * 2 - 1), 4) if score is not None else 0.0,
            modelProbability=score if score is not None else 0.0,
        ))
    return result

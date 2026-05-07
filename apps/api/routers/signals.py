# apps/api/routers/signals.py
from __future__ import annotations
import logging
from fastapi import APIRouter, HTTPException

from livewell.signals.dynamodb import get_latest_signals, get_signal
from livewell.signals.transform import to_contract_card, to_contract_detail, NAME_BY_S3_KEY
from schemas.contract import ContractCard, ContractDetail

logger = logging.getLogger(__name__)
router = APIRouter()

# Invert: display name (with / → -) → s3_key
_SLUG_TO_S3_KEY: dict[str, str] = {
    name.replace("/", "-").replace(" ", "-"): key for key, name in NAME_BY_S3_KEY.items()
}


@router.get("/signals", response_model=list[ContractCard])
def get_signals() -> list[ContractCard]:
    records = get_latest_signals()
    return [to_contract_card(r) for r in records]


@router.get("/signals/{instrument}/{strike}", response_model=ContractDetail)
def get_signal_detail(instrument: str, strike: str) -> ContractDetail:
    s3_key = _SLUG_TO_S3_KEY.get(instrument) or None
    if s3_key is None:
        raise HTTPException(status_code=404, detail="Signal not found")
    records = get_latest_signals()
    match = next((r for r in records if str(r.get("s3_key", "")) == s3_key), None)
    if match is None:
        raise HTTPException(status_code=404, detail="Signal not found")
    latest_date = str(match.get("date", ""))
    record = get_signal(s3_key, latest_date)
    if record is None:
        raise HTTPException(status_code=404, detail="Signal not found")
    return to_contract_detail(record)


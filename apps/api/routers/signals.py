# apps/api/routers/signals.py
from __future__ import annotations
import logging
from fastapi import APIRouter, HTTPException

from livewell.signals.dynamodb import get_latest_signals, get_signal
from livewell.signals.transform import to_contract_card, to_contract_detail
from schemas.contract import ContractCard, ContractDetail

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/signals", response_model=list[ContractCard])
def get_signals() -> list[ContractCard]:
    records = get_latest_signals()
    return [to_contract_card(r) for r in records]


@router.get("/signals/{instrument}/{strike}", response_model=ContractDetail)
def get_signal_detail(instrument: str, strike: str) -> ContractDetail:
    # URL uses "-" as separator (e.g. EUR-USD → EURUSD s3_key)
    s3_key = instrument.replace("-", "").upper()
    records = get_latest_signals()
    if not records:
        raise HTTPException(status_code=404, detail="No signals available")
    latest_date = max(r.get("date", "") for r in records)
    record = get_signal(s3_key, latest_date)
    if record is None:
        raise HTTPException(status_code=404, detail="Signal not found")
    return to_contract_detail(record)

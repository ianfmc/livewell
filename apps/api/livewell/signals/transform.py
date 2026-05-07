# apps/api/livewell/signals/transform.py
from __future__ import annotations
import json
import logging
from decimal import Decimal

from livewell.ingestion.constants import INSTRUMENTS
from schemas.contract import ContractCard, ContractDetail, Economics, ReasonCode

logger = logging.getLogger(__name__)

_S3_KEY_TO_NAME: dict[str, str] = {inst["s3_key"]: inst["name"] for inst in INSTRUMENTS}


def _score(record: dict) -> float | None:
    raw = record.get("score")
    if raw is None:
        return None
    try:
        return float(Decimal(str(raw))) if isinstance(raw, Decimal) else float(raw)
    except (ValueError, TypeError):
        return None


def _recommendation(score: float | None, signal_valid: bool, direction: str) -> str:
    if score is None:
        return "Watch"
    if score >= 0.65 and signal_valid and direction != "none":
        return "Take"
    if score < 0.55 or direction == "none":
        return "Pass"
    return "Watch"


def _confidence(score: float | None) -> str:
    if score is None or score < 0.58:
        return "Low"
    if score >= 0.70:
        return "High"
    return "Medium"


def _status(rec: str) -> str:
    return {"Take": "Open", "Watch": "Review", "Pass": "Closed"}.get(rec, "Closed")


def _parse_reason_codes(reasoning: str) -> list[ReasonCode]:
    try:
        items = json.loads(reasoning)
        return [ReasonCode(label=r["label"], positive=bool(r["positive"])) for r in items]
    except Exception:
        return []


def to_contract_card(record: dict) -> ContractCard:
    s3_key = str(record.get("s3_key", ""))
    score = _score(record)
    signal_valid = record.get("signal_valid") is True
    direction = str(record.get("direction", "none"))
    rec = _recommendation(score, signal_valid, direction)
    return ContractCard(
        instrument=_S3_KEY_TO_NAME.get(s3_key, s3_key),
        strike=str(record.get("strike_candidate", "")),
        expiry=str(record.get("timing_slot", "")),
        status=_status(rec),
        signalId=str(record.get("signal_id", "")),
    )


def to_contract_detail(record: dict) -> ContractDetail:
    s3_key = str(record.get("s3_key", ""))
    score = _score(record)
    signal_valid = record.get("signal_valid") is True
    direction = str(record.get("direction", "none"))
    rec = _recommendation(score, signal_valid, direction)
    conf = _confidence(score)
    edge = round(score * 2 - 1, 4) if score is not None else 0.0
    return ContractDetail(
        instrument=_S3_KEY_TO_NAME.get(s3_key, s3_key),
        strike=str(record.get("strike_candidate", "")),
        expiry=str(record.get("timing_slot", "")),
        status=_status(rec),
        recommendation=rec,
        rationale=f"{rec} — score {score:.2f}" if score is not None else "No model score available",
        economics=Economics(cost=40.0, payout=100.0, breakeven=0.40),
        modelProbability=score,
        edge=edge,
        confidence=conf,
        regime=str(record.get("trend_bias", "")),
        noTradeFlag=(str(record.get("timing_risk", "")).lower() == "high"),
        reasonCodes=_parse_reason_codes(str(record.get("reasoning", "[]"))),
    )

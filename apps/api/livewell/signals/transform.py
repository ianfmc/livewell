# apps/api/livewell/signals/transform.py
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from livewell.ingestion.constants import INSTRUMENTS
from schemas.contract import ContractCard, ContractDetail, Economics, ReasonCode, SupportingSignals

logger = logging.getLogger(__name__)

Recommendation = Literal["Take", "Watch", "Pass"]
Confidence = Literal["High", "Medium", "Low"]
Regime = Literal["Bullish", "Bearish", "Neutral"]

_S3_KEY_TO_NAME: dict[str, str] = {inst["s3_key"]: inst["name"] for inst in INSTRUMENTS}


def _score(record: dict) -> float | None:
    raw = record.get("score")
    if raw is None:
        return None
    try:
        return float(Decimal(str(raw))) if isinstance(raw, Decimal) else float(raw)
    except (ValueError, TypeError):
        return None


def _recommendation(score: float | None, signal_valid: bool, direction: str) -> Recommendation:
    if score is None:
        return "Watch"
    if score >= 0.65 and signal_valid and direction != "none":
        return "Take"
    if score < 0.55 or direction == "none":
        return "Pass"
    return "Watch"


def _confidence(score: float | None) -> Confidence:
    if score is None or score < 0.58:
        return "Low"
    if score >= 0.70:
        return "High"
    return "Medium"


def _rule_confidence(signal_valid: bool, direction: str, reason_codes: list[ReasonCode]) -> Confidence:
    """Rule-based confidence proxy for when no model score exists (A3a).

    Derived from the deterministic signal pipeline alone: a fully valid signal
    with an actionable direction (all stages passed) is High; a valid signal with
    caveats is Medium; an invalid or no-direction signal is Low. This keeps
    frozen-baseline candidates (score=None) honestly informative instead of a
    misleading constant "Low" — while never showing "High" for a signal that is
    not actually actionable (D1: a "No direction / Closed" card must not read
    "High confidence").
    """
    if not signal_valid or direction == "none":
        return "Low"
    negatives = sum(1 for rc in reason_codes if not rc.positive)
    return "High" if negatives == 0 else "Medium"


def _status(rec: str) -> str:
    return {"Take": "Open", "Watch": "Review", "Pass": "Closed"}.get(rec, "Closed")


# Humanized labels for the pipeline's "<stage>: <detail>" reason strings.
_REASON_PASS_MARKER = "all stages passed"


def _parse_reason_codes(reasoning: str) -> list[ReasonCode]:
    """Parse the signal pipeline's `reasoning` field into reason codes.

    The pipeline (_apply_pipeline) writes a JSON list of PLAIN STRINGS, e.g.
    "momentum: bullish conditions not met" or "all stages passed". Older/mock
    data may instead carry a list of {label, positive} dicts. Handle both, and
    never raise — return [] on anything unparseable.
    """
    try:
        items = json.loads(reasoning)
    except (json.JSONDecodeError, TypeError):
        return []
    if not isinstance(items, list):
        return []

    out: list[ReasonCode] = []
    for item in items:
        if isinstance(item, dict):
            # Back-compat: already-structured {label, positive}.
            try:
                out.append(ReasonCode(label=str(item["label"]), positive=bool(item["positive"])))
            except (KeyError, TypeError):
                continue
        elif isinstance(item, str):
            text = item.strip()
            if not text:
                continue
            positive = text.lower() == _REASON_PASS_MARKER
            # Humanize "stage: detail" -> "Stage — detail"
            if ":" in text:
                stage, detail = text.split(":", 1)
                label = f"{stage.strip().capitalize()} — {detail.strip()}"
            else:
                label = text[:1].upper() + text[1:]
            out.append(ReasonCode(label=label, positive=positive))
    return out


_DEFAULT_ECONOMICS = Economics(cost=40.0, payout=100.0, breakeven=0.40)


@dataclass
class _DerivedSignal:
    """Single source of truth for everything derived from a signal record.

    Both to_contract_card and to_contract_detail build from this, so a candidate
    and its detail view can never disagree (eng-review A2).
    """

    instrument: str
    strike: str
    expiry: str
    direction: str
    date: str
    status: str
    recommendation: Recommendation
    confidence: Confidence
    score_available: bool
    model_probability: float | None
    edge: float
    regime: str
    no_trade_flag: bool
    reason_codes: list[ReasonCode]
    supporting: SupportingSignals


def _f(record: dict, key: str) -> float | None:
    raw = record.get(key)
    if raw is None:
        return None
    try:
        return float(Decimal(str(raw))) if isinstance(raw, Decimal) else float(raw)
    except (ValueError, TypeError):
        return None


def _derive(record: dict) -> _DerivedSignal:
    s3_key = str(record.get("s3_key", ""))
    score = _score(record)
    signal_valid = record.get("signal_valid") is True
    direction = str(record.get("direction", "none"))
    reason_codes = _parse_reason_codes(str(record.get("reasoning", "[]")))
    rec = _recommendation(score, signal_valid, direction)
    score_available = score is not None
    # A3a: real model confidence when a score exists; honest rule-based proxy otherwise.
    confidence = _confidence(score) if score_available else _rule_confidence(signal_valid, direction, reason_codes)
    edge = round(score * 2 - 1, 4) if score is not None else 0.0
    return _DerivedSignal(
        instrument=_S3_KEY_TO_NAME.get(s3_key, s3_key),
        strike=str(record.get("strike_candidate", "")),
        expiry=str(record.get("timing_slot", "")),
        direction=direction,
        date=str(record.get("date", "")),
        status=_status(rec),
        recommendation=rec,
        confidence=confidence,
        score_available=score_available,
        model_probability=score,
        edge=edge,
        regime=str(record.get("trend_bias", "")),
        no_trade_flag=(str(record.get("timing_risk", "")).lower() == "high"),
        reason_codes=reason_codes,
        supporting=SupportingSignals(
            ema20=_f(record, "ema_20"),
            ema50=_f(record, "ema_50"),
            rsi14=_f(record, "rsi_14"),
            macdHist=_f(record, "macd_hist"),
            atr14=_f(record, "atr_14"),
        ),
    )


def to_contract_card(record: dict) -> ContractCard:
    d = _derive(record)
    return ContractCard(
        instrument=d.instrument,
        strike=d.strike,
        expiry=d.expiry,
        status=d.status,
        signalId=str(record.get("signal_id", "")),
        direction=d.direction,
        date=d.date,
        recommendation=d.recommendation,
        confidence=d.confidence,
        scoreAvailable=d.score_available,
        edge=d.edge,
        supportingSignals=d.supporting,
        reasonCodes=d.reason_codes,
    )


def to_contract_detail(record: dict) -> ContractDetail:
    d = _derive(record)
    score = d.model_probability
    return ContractDetail(
        instrument=d.instrument,
        strike=d.strike,
        expiry=d.expiry,
        status=d.status,
        recommendation=d.recommendation,
        rationale=(
            f"{d.recommendation} — score {score:.2f}"
            if score is not None
            else f"{d.recommendation} — rule-based candidate (no model score)"
        ),
        economics=_DEFAULT_ECONOMICS,
        modelProbability=score,
        edge=d.edge,
        confidence=d.confidence,
        regime=d.regime,
        noTradeFlag=d.no_trade_flag,
        reasonCodes=d.reason_codes,
    )


# Public aliases — internal helpers needed by dashboard aggregation
score_from_record = _score
confidence_from_score = _confidence
recommendation_from_record = _recommendation
NAME_BY_S3_KEY = _S3_KEY_TO_NAME


def map_regime(trend_bias: str) -> Regime:
    mapping: dict[str, Regime] = {"bullish": "Bullish", "bearish": "Bearish"}
    return mapping.get(trend_bias.lower(), "Neutral")

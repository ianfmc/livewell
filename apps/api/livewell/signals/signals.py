"""Signal generation pipeline: read features+prices from S3, apply 5-stage rules, write signals."""
from __future__ import annotations

import json
import logging
import math
import os

import boto3
import pandas as pd

from livewell.ingestion.constants import INSTRUMENTS, INTERVALS
from livewell.ingestion.s3 import read_parquet, write_parquet
from livewell.features.constants import FEATURES_PREFIX, PRICES_PREFIX
from livewell.signals.constants import (
    ATR_FEASIBILITY_MULTIPLIER,
    MIN_ATR_THRESHOLD,
    PIP_PRECISION,
    RSI_BEARISH_MAX,
    RSI_BULLISH_MIN,
    RSI_OVERBOUGHT,
    RSI_OVERSOLD,
    SESSION_CONFIG,
    SIGNAL_COLUMNS,
    SIGNALS_PREFIX,
)

logger = logging.getLogger(__name__)


def _session_quality(s3_key: str, ts: pd.Timestamp) -> str:
    """Return session quality string for an instrument at a given UTC timestamp."""
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    hour = ts.hour

    sessions = SESSION_CONFIG.get(s3_key, SESSION_CONFIG["EURUSD"])

    for start, end, quality in sessions:
        if start < end:
            if start <= hour < end:
                return quality
        else:
            # Crosses midnight (e.g. 23–07)
            if hour >= start or hour < end:
                return quality

    return "low"


def _apply_pipeline(s3_key: str, row: dict) -> dict:
    """
    Apply the 5-stage signal pipeline to a single row dict.
    Returns a dict of all signal output columns.
    """
    ts = row["date"]
    ema_20 = row["ema_20"]
    ema_50 = row["ema_50"]
    rsi = row["rsi_14"]
    macd = row["macd"]
    macd_signal = row["macd_signal"]
    macd_hist = row["macd_hist"]
    atr = row["atr_14"]
    close = row["close"]

    reasons: list[str] = []
    signal_valid = True
    direction = "none"

    # Stage 1: Trend
    if ema_20 > ema_50:
        trend_bias = "bullish"
    elif ema_20 < ema_50:
        trend_bias = "bearish"
    else:
        trend_bias = "neutral"
        signal_valid = False
        reasons.append("trend: neutral (ema_20 == ema_50)")

    # Stage 2: Momentum confirmation (only if trend is established)
    if trend_bias == "bullish":
        if not (rsi > RSI_BULLISH_MIN and macd_hist > 0 and macd > macd_signal):
            signal_valid = False
            reasons.append("momentum: bullish conditions not met")
        else:
            direction = "buy"
    elif trend_bias == "bearish":
        if not (rsi < RSI_BEARISH_MAX and macd_hist < 0 and macd < macd_signal):
            signal_valid = False
            reasons.append("momentum: bearish conditions not met")
        else:
            direction = "sell"

    # Stage 3: Overextension check
    if trend_bias == "bullish" and rsi > RSI_OVERBOUGHT:
        signal_valid = False
        direction = "none"
        reasons.append(f"overextension: overbought rsi={rsi:.1f} > {RSI_OVERBOUGHT}")
    elif trend_bias == "bearish" and rsi < RSI_OVERSOLD:
        signal_valid = False
        direction = "none"
        reasons.append(f"overextension: oversold rsi={rsi:.1f} < {RSI_OVERSOLD}")

    # Stage 4: ATR feasibility + strike selection
    pip_prec = PIP_PRECISION.get(s3_key, 4)
    min_atr = MIN_ATR_THRESHOLD.get(s3_key, 0.0010)
    atr_feasible = atr >= min_atr

    if not atr_feasible:
        signal_valid = False
        reasons.append(f"atr: below minimum ({atr} < {min_atr})")

    if trend_bias == "bullish":
        strike_candidate = round(close + atr * ATR_FEASIBILITY_MULTIPLIER, pip_prec)
    elif trend_bias == "bearish":
        strike_candidate = round(close - atr * ATR_FEASIBILITY_MULTIPLIER, pip_prec)
    else:
        strike_candidate = float("nan")

    # Stage 5: Session filter
    session_quality = _session_quality(s3_key, ts)
    if session_quality != "high":
        signal_valid = False
        reasons.append(f"session: quality={session_quality}, only high allowed")

    if signal_valid:
        reasons.append("all stages passed")

    return {
        "trend_bias": trend_bias,
        "session_quality": session_quality,
        "strike_candidate": strike_candidate,
        "signal_valid": signal_valid,
        "direction": direction,
        "reasoning": json.dumps(reasons),
    }

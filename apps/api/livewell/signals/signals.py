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
    INSTRUMENT_ASSET_CLASS,
    MIN_ATR_THRESHOLD,
    PIP_PRECISION,
    RSI_BEARISH_MAX,
    RSI_BULLISH_MIN,
    RSI_OVERBOUGHT,
    RSI_OVERSOLD,
    SESSION_CONFIG,
    SIGNAL_COLUMNS,
    SIGNALS_PREFIX,
    TIMING_SLOTS,
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


def _timing_annotation(asset_class: str, ts: pd.Timestamp) -> tuple[str, str]:
    """
    Return (timing_slot, timing_risk) for the nearest preceding slot in the asset class.
    Returns ("unscheduled", "unknown") if the timestamp precedes the day's first slot.
    """
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")

    slots = TIMING_SLOTS.get(asset_class, [])
    signal_minutes = ts.hour * 60 + ts.minute

    best_slot = None
    best_minutes = -1

    for utc_hour, utc_minute, timing_slot, timing_risk in slots:
        slot_minutes = utc_hour * 60 + utc_minute
        if slot_minutes <= signal_minutes and slot_minutes > best_minutes:
            best_minutes = slot_minutes
            best_slot = (timing_slot, timing_risk)

    if best_slot is None:
        return "unscheduled", "unknown"

    return best_slot


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

    # Timing annotation (informational — does not affect signal_valid)
    asset_class = INSTRUMENT_ASSET_CLASS.get(s3_key, "forex")
    timing_slot, timing_risk = _timing_annotation(asset_class, ts)

    return {
        "trend_bias": trend_bias,
        "session_quality": session_quality,
        "strike_candidate": strike_candidate,
        "signal_valid": signal_valid,
        "direction": direction,
        "reasoning": json.dumps(reasons),
        "timing_slot": timing_slot,
        "timing_risk": timing_risk,
    }


def _signals_one(instrument: dict, interval: str, bucket: str) -> None:
    """Read features+prices for one instrument+interval, compute signals, write by year."""
    s3_key = instrument["s3_key"]
    s3 = boto3.client("s3")

    # Read all feature Parquets for this instrument+interval
    feature_prefix = f"{FEATURES_PREFIX}/{s3_key}/{interval}/"
    resp = s3.list_objects_v2(Bucket=bucket, Prefix=feature_prefix)
    objects = resp.get("Contents", [])
    if not objects:
        raise ValueError(f"no feature files found for {s3_key}/{interval}")

    feature_frames = []
    for obj in objects:
        df = read_parquet(bucket, obj["Key"])
        if df is not None:
            feature_frames.append(df)
    if not feature_frames:
        raise ValueError(f"all feature reads returned None for {s3_key}/{interval}")

    features = pd.concat(feature_frames, ignore_index=True)
    features["date"] = pd.to_datetime(features["date"], utc=True)

    # Read all price Parquets to get the close column
    price_prefix = f"{PRICES_PREFIX}/{s3_key}/{interval}/"
    resp = s3.list_objects_v2(Bucket=bucket, Prefix=price_prefix)
    price_objects = resp.get("Contents", [])
    if not price_objects:
        raise ValueError(f"no price files found for {s3_key}/{interval}")

    price_frames = []
    for obj in price_objects:
        df = read_parquet(bucket, obj["Key"])
        if df is not None:
            price_frames.append(df[["date", "close"]])
    if not price_frames:
        raise ValueError(f"all price reads returned None for {s3_key}/{interval}")

    prices = pd.concat(price_frames, ignore_index=True)
    prices["date"] = pd.to_datetime(prices["date"], utc=True)

    # Inner join features + close on date
    merged = features.merge(prices, on="date", how="inner")
    merged = merged.drop_duplicates(subset=["date"]).sort_values("date").reset_index(drop=True)

    if merged.empty:
        raise ValueError(f"inner join produced empty DataFrame for {s3_key}/{interval}")

    # Apply pipeline row-by-row
    signal_rows = []
    for _, row in merged.iterrows():
        pipeline_out = _apply_pipeline(s3_key, row.to_dict())
        signal_row = {col: row[col] for col in ["date", "ema_20", "ema_50", "rsi_14", "macd", "macd_signal", "macd_hist", "atr_14"]}
        signal_row.update(pipeline_out)
        signal_rows.append(signal_row)

    signals_df = pd.DataFrame(signal_rows, columns=SIGNAL_COLUMNS)

    # Write one Parquet per calendar year
    for year, group in signals_df.groupby(signals_df["date"].dt.year):
        key = f"{SIGNALS_PREFIX}/{s3_key}/{interval}/{int(year)}.parquet"
        existing = read_parquet(bucket, key)
        if existing is not None:
            existing["date"] = pd.to_datetime(existing["date"], utc=True)
            combined = pd.concat([existing, group], ignore_index=True)
            combined["date"] = pd.to_datetime(combined["date"], utc=True)
            group = combined.drop_duplicates(subset=["date"]).sort_values("date").reset_index(drop=True)
        write_parquet(group, bucket, key)
        logger.info("%s/%s/%s signals: %d rows", s3_key, interval, year, len(group))


def run_signals(
    instruments: list[str] | None = None,
    intervals: list[str] | None = None,
) -> dict:
    """
    Compute rule-based signals for all instruments and intervals.

    Args:
        instruments: list of s3_key values (e.g. ["EURUSD"]). Defaults to all.
        intervals: list of interval strings (e.g. ["1d"]). Defaults to all.

    Returns:
        {"succeeded": [...], "failed": [...]}
    """
    bucket = os.environ["LIVEWELL_BUCKET"]
    targets = (
        [i for i in INSTRUMENTS if i["s3_key"] in instruments]
        if instruments
        else INSTRUMENTS
    )
    target_intervals = intervals if intervals else list(INTERVALS.keys())

    failed_pairs: list[tuple[str, str]] = []

    for instrument in targets:
        for interval in target_intervals:
            try:
                _signals_one(instrument, interval, bucket)
            except Exception as exc:
                logger.error(
                    "failed to compute signals %s/%s: %s",
                    instrument["s3_key"], interval, exc,
                )
                failed_pairs.append((instrument["s3_key"], interval))

    failed = list({s3_key for s3_key, _ in failed_pairs})
    succeeded = [i["s3_key"] for i in targets if i["s3_key"] not in failed]

    logger.info("signals complete — succeeded: %s, failed: %s", succeeded, failed)
    return {"succeeded": succeeded, "failed": failed}

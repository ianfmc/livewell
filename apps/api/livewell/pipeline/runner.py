from __future__ import annotations
import logging
import os
from datetime import datetime, timezone

import boto3
import pandas as pd

from livewell.ingestion.ingest import run_ingestion
from livewell.features.features import run_features
from livewell.signals.signals import run_signals
from livewell.signals.constants import SIGNAL_COLUMNS, SIGNALS_PREFIX
from livewell.ingestion.s3 import read_parquet
from livewell.models.inference import score_signal

logger = logging.getLogger(__name__)


def _read_latest_signal(s3_key: str, bucket: str) -> dict | None:
    """Read all signal Parquets for s3_key (1d interval) and return the most recent row."""
    s3 = boto3.client("s3")
    prefix = f"{SIGNALS_PREFIX}/{s3_key}/1d/"
    paginator = s3.get_paginator("list_objects_v2")
    objects = []
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        objects.extend(page.get("Contents", []))
    if not objects:
        return None

    frames = []
    for obj in sorted(objects, key=lambda o: o["Key"]):
        df = read_parquet(bucket, obj["Key"])
        if df is not None:
            frames.append(df)
    if not frames:
        return None

    combined = pd.concat(frames, ignore_index=True)
    combined["date"] = pd.to_datetime(combined["date"], utc=True)
    latest = combined.sort_values("date").iloc[-1]
    return latest.to_dict()


def run_instrument(s3_key: str, run_id: str, backfill: bool = False) -> dict:
    """
    Run ingestion → features → signals → inference for one instrument.
    Returns a DynamoDB signal record with score and model_version set.
    Raises on any stage failure — caller catches and records the error.
    """
    bucket = os.environ["LIVEWELL_BUCKET"]

    run_ingestion(instruments=[s3_key], backfill=backfill)
    run_features(instruments=[s3_key])
    run_signals(instruments=[s3_key])

    row = _read_latest_signal(s3_key, bucket)
    if row is None:
        raise ValueError(f"no signal row found after pipeline for {s3_key}")

    date_str = pd.Timestamp(row["date"]).strftime("%Y-%m-%d")
    record = {
        "signal_id": f"{s3_key}__{date_str}",
        "s3_key": s3_key,
        "run_id": run_id,
        "date": date_str,
        "ema_20": str(row.get("ema_20", "")),
        "ema_50": str(row.get("ema_50", "")),
        "rsi_14": str(row.get("rsi_14", "")),
        "macd": str(row.get("macd", "")),
        "macd_signal": str(row.get("macd_signal", "")),
        "macd_hist": str(row.get("macd_hist", "")),
        "atr_14": str(row.get("atr_14", "")),
        "trend_bias": str(row.get("trend_bias", "")),
        "session_quality": str(row.get("session_quality", "")),
        "strike_candidate": str(row.get("strike_candidate", "")),
        "signal_valid": bool(row.get("signal_valid", False)),
        "direction": str(row.get("direction", "none")),
        "reasoning": str(row.get("reasoning", "{}")),
        "timing_slot": str(row.get("timing_slot", "")),
        "timing_risk": str(row.get("timing_risk", "")),
        "score": None,
        "model_version": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    record = score_signal(record, s3_key)
    return record

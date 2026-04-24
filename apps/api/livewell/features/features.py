"""Core feature generation: read OHLCV from S3, compute indicators, write features to S3."""
from __future__ import annotations

import logging
import os

import boto3
import pandas as pd
import pandas_ta as ta

from livewell.ingestion.constants import INSTRUMENTS, INTERVALS
from livewell.ingestion.s3 import read_parquet, write_parquet
from livewell.features.constants import COLUMN_RENAMES, FEATURE_COLUMNS, FEATURES_PREFIX, PRICES_PREFIX

logger = logging.getLogger(__name__)


def _compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Compute all 5 indicators on a full-history OHLCV DataFrame. Returns feature DataFrame."""
    prices = df.copy()
    prices = prices.sort_values("date").reset_index(drop=True)

    prices.ta.ema(length=20, append=True)
    prices.ta.ema(length=50, append=True)
    prices.ta.rsi(length=14, append=True)
    prices.ta.macd(fast=12, slow=26, signal=9, append=True)
    prices.ta.atr(length=14, append=True)

    prices = prices.rename(columns=COLUMN_RENAMES)
    return prices[FEATURE_COLUMNS]


def _features_one(instrument: dict, interval: str, bucket: str) -> None:
    """Read all price years for one instrument+interval, compute features, write by year."""
    s3_key = instrument["s3_key"]

    s3 = boto3.client("s3")
    prefix = f"{PRICES_PREFIX}/{s3_key}/{interval}/"
    resp = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
    objects = resp.get("Contents", [])
    if not objects:
        logger.warning("no price files found for %s/%s", s3_key, interval)
        return

    frames = []
    for obj in objects:
        df = read_parquet(bucket, obj["Key"])
        if df is not None:
            frames.append(df)
    if not frames:
        return

    full_history = pd.concat(frames, ignore_index=True)
    full_history = full_history.drop_duplicates(subset=["date"]).sort_values("date").reset_index(drop=True)

    features = _compute_indicators(full_history)

    for year, group in features.groupby(features["date"].dt.year):
        key = f"{FEATURES_PREFIX}/{s3_key}/{interval}/{int(year)}.parquet"
        existing = read_parquet(bucket, key)
        if existing is not None:
            combined = pd.concat([existing, group], ignore_index=True)
            combined["date"] = pd.to_datetime(combined["date"])
            group = combined.drop_duplicates(subset=["date"]).sort_values("date").reset_index(drop=True)
        write_parquet(group, bucket, key)
        logger.info("%s/%s/%s features: %d rows", s3_key, interval, year, len(group))


def run_features(
    instruments: list[str] | None = None,
    intervals: list[str] | None = None,
) -> dict:
    """
    Compute technical indicators for all instruments and intervals.

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
                _features_one(instrument, interval, bucket)
            except Exception as exc:
                logger.error(
                    "failed to compute features %s/%s: %s",
                    instrument["s3_key"], interval, exc,
                )
                failed_pairs.append((instrument["s3_key"], interval))

    failed = list({s3_key for s3_key, _ in failed_pairs})
    succeeded = [i["s3_key"] for i in targets if i["s3_key"] not in failed]

    logger.info("features complete — succeeded: %s, failed: %s", succeeded, failed)
    return {"succeeded": succeeded, "failed": failed}

"""Core ingestion logic: fetch OHLCV from yfinance, merge, write to S3."""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone

import pandas as pd
import yfinance as yf

from livewell.ingestion.constants import INSTRUMENTS, INTERVALS, S3_PREFIX
from livewell.ingestion.s3 import read_parquet, write_parquet

logger = logging.getLogger(__name__)


def fetch_ohlcv(
    ticker: str,
    interval: str,
    lookback_days: int,
) -> pd.DataFrame | None:
    """Fetch OHLCV from yfinance for the last lookback_days. Returns None if empty."""
    end = datetime.now(timezone.utc).replace(tzinfo=None)
    start = end - timedelta(days=lookback_days)
    raw = yf.Ticker(ticker).history(start=start, end=end, interval=interval)
    if raw.empty:
        return None
    df = raw[["Open", "High", "Low", "Close", "Volume"]].copy()
    df.columns = ["open", "high", "low", "close", "volume"]
    df.index.name = "date"
    df = df.reset_index()
    df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)
    return df


def fetch_ohlcv_backfill(ticker: str, interval: str, years: int) -> pd.DataFrame | None:
    """Fetch full history up to `years` back. Used on first run."""
    return fetch_ohlcv(ticker, interval, lookback_days=years * 365)


def merge_and_dedup(
    existing: pd.DataFrame | None,
    new: pd.DataFrame,
) -> pd.DataFrame:
    """Concatenate existing and new rows, dedup on date, sort ascending."""
    if existing is None:
        combined = new
    else:
        combined = pd.concat([existing, new], ignore_index=True)
    combined["date"] = pd.to_datetime(combined["date"])
    combined = combined.drop_duplicates(subset=["date"]).sort_values("date").reset_index(drop=True)
    return combined


def _s3_key(s3_key: str, interval: str, year: int) -> str:
    return f"{S3_PREFIX}/{s3_key}/{interval}/{year}.parquet"


def _ingest_one(
    instrument: dict,
    interval: str,
    bucket: str,
    backfill: bool,
) -> None:
    ticker = instrument["ticker"]
    s3_key = instrument["s3_key"]
    cfg = INTERVALS[interval]

    if backfill:
        new_df = fetch_ohlcv_backfill(ticker, interval, years=cfg["backfill_years"])
    else:
        new_df = fetch_ohlcv(ticker, interval, lookback_days=cfg["lookback_days"])

    if new_df is None or new_df.empty:
        logger.warning("no data returned for %s %s", s3_key, interval)
        return

    for year, group in new_df.groupby(new_df["date"].dt.year):
        key = _s3_key(s3_key, interval, int(year))
        existing = read_parquet(bucket, key)
        merged = merge_and_dedup(existing, group)
        write_parquet(merged, bucket, key)
        logger.info("%s/%s/%s: %d rows", s3_key, interval, year, len(merged))


def run_ingestion(
    instruments: list[str] | None = None,
    backfill: bool = False,
) -> dict:
    """
    Run ingestion for all instruments and intervals.

    Args:
        instruments: list of s3_key values to process (e.g. ["EURUSD", "GBPUSD"]).
                     Defaults to all instruments in constants.INSTRUMENTS.
        backfill: if True, fetch full 2-year history regardless of existing data.

    Returns:
        {"succeeded": [...], "failed": [...]}
    """
    bucket = os.environ["LIVEWELL_BUCKET"]
    targets = (
        [i for i in INSTRUMENTS if i["s3_key"] in instruments]
        if instruments
        else INSTRUMENTS
    )

    failed_pairs: list[tuple[str, str]] = []

    for instrument in targets:
        for interval in INTERVALS:
            try:
                _ingest_one(instrument, interval, bucket, backfill)
            except Exception as exc:
                logger.error(
                    "failed to ingest %s/%s: %s",
                    instrument["s3_key"], interval, exc,
                )
                failed_pairs.append((instrument["s3_key"], interval))

    failed = list({s3_key for s3_key, _ in failed_pairs})
    succeeded = [i["s3_key"] for i in targets if i["s3_key"] not in failed]

    logger.info("ingestion complete — succeeded: %s, failed: %s", succeeded, failed)
    return {"succeeded": succeeded, "failed": failed}

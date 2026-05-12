from __future__ import annotations
import io
import logging
import os
from datetime import datetime, timezone

import boto3
import pandas as pd
from botocore.exceptions import ClientError

from livewell.ingestion.constants import INSTRUMENTS

logger = logging.getLogger(__name__)

_REPLAY_YEARS = list(range(2019, 2027))
_DIRECTION_MAP = {"buy": "call", "sell": "put"}


def _normalise_direction(d: str) -> str:
    return _DIRECTION_MAP.get(str(d), str(d))


def _load_existing_ids(table) -> set[str]:
    existing: set[str] = set()
    resp = table.scan(ProjectionExpression="signal_id")
    for item in resp.get("Items", []):
        existing.add(item["signal_id"])
    while "LastEvaluatedKey" in resp:
        resp = table.scan(
            ProjectionExpression="signal_id",
            ExclusiveStartKey=resp["LastEvaluatedKey"],
        )
        for item in resp.get("Items", []):
            existing.add(item["signal_id"])
    return existing


def _read_parquet(s3, bucket: str, key: str) -> pd.DataFrame | None:
    try:
        obj = s3.get_object(Bucket=bucket, Key=key)
        return pd.read_parquet(io.BytesIO(obj["Body"].read()))
    except ClientError as e:
        if e.response["Error"]["Code"] in ("NoSuchKey", "404"):
            return None
        raise


def replay_signals(
    instruments: list[str] | None = None,
    env: str = "prod",
    bucket: str = "livewell-data-prod",
    dry_run: bool = False,
) -> dict:
    """
    Read signal Parquets from S3 and batch-write to DynamoDB, skipping existing records.
    Returns {"written": N, "skipped": N, "failed": [signal_id, ...]}.
    """
    region = os.environ.get("AWS_DEFAULT_REGION", "us-west-1")
    s3 = boto3.client("s3", region_name=region)
    dynamodb = boto3.resource("dynamodb", region_name=region)
    table = dynamodb.Table(f"livewell-signals-{env}")

    targets = instruments or [i["s3_key"] for i in INSTRUMENTS]
    existing_ids = _load_existing_ids(table)

    written = 0
    skipped = 0
    failed: list[str] = []
    now = datetime.now(timezone.utc).isoformat()

    for s3_key in targets:
        batch: list[dict] = []

        for year in _REPLAY_YEARS:
            key = f"signals/{s3_key}/1d/{year}.parquet"
            df = _read_parquet(s3, bucket, key)
            if df is None:
                logger.warning("no parquet at %s — skipping year", key)
                continue
            if df.empty:
                continue

            df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)

            for _, row in df.iterrows():
                direction = _normalise_direction(row.get("direction", "none"))
                if direction == "none":
                    continue

                date_str = pd.Timestamp(row["date"]).strftime("%Y-%m-%d")
                signal_id = f"{s3_key}__{date_str}"

                if signal_id in existing_ids:
                    skipped += 1
                    continue

                record = {
                    "signal_id": signal_id,
                    "s3_key": s3_key,
                    "run_id": "replay",
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
                    "direction": direction,
                    "reasoning": str(row.get("reasoning", "{}")),
                    "timing_slot": str(row.get("timing_slot", "")),
                    "timing_risk": str(row.get("timing_risk", "")),
                    "score": None,
                    "model_version": None,
                    "created_at": now,
                }
                batch.append(record)

        if not dry_run and batch:
            try:
                with table.batch_writer() as bw:
                    for record in batch:
                        bw.put_item(Item=record)
                written += len(batch)
            except Exception as exc:
                logger.error("batch write failed for %s: %s", s3_key, exc)
                failed.extend(r["signal_id"] for r in batch)
        else:
            written += len(batch)

    return {"written": written, "skipped": skipped, "failed": failed}

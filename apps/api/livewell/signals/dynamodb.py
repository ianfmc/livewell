# apps/api/livewell/signals/dynamodb.py
from __future__ import annotations

import logging
import os

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from livewell.ingestion.constants import INSTRUMENTS

logger = logging.getLogger(__name__)

# GSI partitioned on s3_key (instrument) with date as the range key. Querying
# this index with Limit=1, newest-first, returns an instrument's latest signal
# in a single read — bounding the hot path to one query per instrument instead
# of an unbounded full-table scan (LW-208). Must match the index name in
# infra/lib/livewell-stack.ts.
GSI_LATEST = "by-instrument-date"


def _table():
    env = os.environ.get("LIVEWELL_ENV", "prod")
    return boto3.resource("dynamodb").Table(f"livewell-signals-{env}")


def _query_latest(table, s3_key: str) -> dict | None:
    """Return the most-recent signal for one instrument via the GSI, or None.

    Queries the `by-instrument-date` index for the single highest `date` (ISO
    YYYY-MM-DD sorts lexicographically). `ScanIndexForward=False` + `Limit=1`
    yields the true latest regardless of write order, so out-of-order backfill
    writes do not clobber the result.
    """
    resp = table.query(
        IndexName=GSI_LATEST,
        KeyConditionExpression=Key("s3_key").eq(s3_key),
        ScanIndexForward=False,
        Limit=1,
    )
    items = resp.get("Items", [])
    return items[0] if items else None


def get_latest_signals() -> list[dict]:
    """Return one record per instrument (the most recent by date).

    One bounded GSI query per instrument over the fixed INSTRUMENTS list, so the
    read cost is independent of history size. Instruments with no signals yet are
    absent from the result (same contract as the previous scan-and-reduce).
    """
    try:
        table = _table()
        latest: list[dict] = []
        for inst in INSTRUMENTS:
            record = _query_latest(table, inst["s3_key"])
            if record is not None:
                latest.append(record)
        return latest
    except ClientError as exc:
        logger.error("DynamoDB query failed: %s", exc)
        return []


def get_latest_signal(instrument: str) -> dict | None:
    """Return the most-recent signal for a single instrument (s3_key), or None."""
    try:
        return _query_latest(_table(), instrument)
    except ClientError as exc:
        logger.error("DynamoDB query failed: %s", exc)
        return None


def get_signal(instrument: str, date: str) -> dict | None:
    """Return the signal record for instrument on date, or None."""
    signal_id = f"{instrument}__{date}"
    try:
        table = _table()
        resp = table.get_item(Key={"signal_id": signal_id})
        return resp.get("Item")
    except ClientError as exc:
        logger.error("DynamoDB get_item failed: %s", exc)
        return None

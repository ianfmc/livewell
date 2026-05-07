# apps/api/livewell/signals/dynamodb.py
from __future__ import annotations
import logging
import os

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


def _table():
    env = os.environ.get("LIVEWELL_ENV", "prod")
    return boto3.resource("dynamodb").Table(f"livewell-signals-{env}")


def get_latest_signals() -> list[dict]:
    """Scan signals table; return one record per instrument (the most recent by date)."""
    try:
        table = _table()
        resp = table.scan()
        items: list[dict] = list(resp.get("Items", []))
        while "LastEvaluatedKey" in resp:
            resp = table.scan(ExclusiveStartKey=resp["LastEvaluatedKey"])
            items.extend(resp.get("Items", []))
    except ClientError as exc:
        logger.error("DynamoDB scan failed: %s", exc)
        return []

    # Keep only the most recent record per instrument (s3_key)
    latest: dict[str, dict] = {}
    for item in items:
        key = str(item.get("s3_key", ""))
        existing = latest.get(key)
        if existing is None or str(item.get("date", "")) > str(existing.get("date", "")):
            latest[key] = item
    return list(latest.values())


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

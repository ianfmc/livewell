from __future__ import annotations

import logging
import os

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


def _env() -> str:
    return os.environ.get("LIVEWELL_ENV", "prod")


def _table():
    return boto3.resource("dynamodb").Table(f"livewell-trades-{_env()}")


def create_trade(record: dict) -> None:
    _table().put_item(Item={k: v for k, v in record.items() if v is not None})


def list_trades(status: str | None = None, from_date: str | None = None, to_date: str | None = None) -> list[dict]:
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

    if status:
        items = [i for i in items if i.get("status") == status]
    if from_date:
        items = [i for i in items if str(i.get("expiry_time", "")) >= from_date]
    if to_date:
        items = [i for i in items if str(i.get("expiry_time", "")) <= to_date]

    return sorted(items, key=lambda i: str(i.get("expiry_time", "")), reverse=True)


def patch_trade(trade_id: str, status: str, outcome_price: str | None, outcome_source: str, resolved_at: str) -> None:
    _table().update_item(
        Key={"trade_id": trade_id},
        UpdateExpression="SET #s = :s, outcome_source = :os, resolved_at = :ra"
        + (", outcome_price = :op" if outcome_price else ""),
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={
            ":s": status,
            ":os": outcome_source,
            ":ra": resolved_at,
            **({":op": outcome_price} if outcome_price else {}),
        },
    )


def get_open_trades_due(as_of: str) -> list[dict]:
    """Return open trades whose expiry_time <= as_of."""
    all_open = list_trades(status="open")
    return [t for t in all_open if str(t.get("expiry_time", "")) <= as_of]

from __future__ import annotations
import os

import boto3
from boto3.dynamodb.conditions import Key


def _table():
    env = os.environ.get("LIVEWELL_ENV", "prod")
    dynamodb = boto3.resource("dynamodb")
    return dynamodb.Table(f"livewell-model-registry-{env}")


def get_active_model(model_name: str = "rf_tuned") -> dict:
    """
    Return the active registry record for model_name.
    Raises RuntimeError if no active record exists.
    Returns dict with keys: version, s3_path, features (and others).
    """
    table = _table()
    resp = table.query(
        KeyConditionExpression=Key("model_name").eq(model_name),
        FilterExpression="#st = :active",
        ExpressionAttributeNames={"#st": "status"},
        ExpressionAttributeValues={":active": "active"},
    )
    items = resp.get("Items", [])
    if not items:
        raise RuntimeError(f"no active model found for {model_name}")
    # If somehow multiple are active, take the most recent by version
    return max(items, key=lambda x: x["version"])


def register_model(
    model_name: str,
    version: str,
    s3_path: str,
    features: list[str],
    win_rate: float,
    ev: float,
    trained_at: str,
) -> None:
    """
    Write a new active registry record and retire any existing active records.
    """
    table = _table()

    # Retire existing active records
    existing = table.query(
        KeyConditionExpression=Key("model_name").eq(model_name),
        FilterExpression="#st = :active",
        ExpressionAttributeNames={"#st": "status"},
        ExpressionAttributeValues={":active": "active"},
    )
    for item in existing.get("Items", []):
        table.update_item(
            Key={"model_name": item["model_name"], "version": item["version"]},
            UpdateExpression="SET #st = :retired",
            ExpressionAttributeNames={"#st": "status"},
            ExpressionAttributeValues={":retired": "retired"},
        )

    # Write new active record
    table.put_item(Item={
        "model_name": model_name,
        "version": version,
        "s3_path": s3_path,
        "features": features,
        "win_rate": str(win_rate),
        "ev": str(ev),
        "trained_at": trained_at,
        "status": "active",
    })

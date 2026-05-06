from __future__ import annotations
import os
import boto3


def _env() -> str:
    return os.environ.get("LIVEWELL_ENV", "prod")


def _runs_table():
    return boto3.resource("dynamodb").Table(f"livewell-model-runs-{_env()}")


def _signals_table():
    return boto3.resource("dynamodb").Table(f"livewell-signals-{_env()}")


def create_run(run_id: str, started_at: str) -> None:
    _runs_table().put_item(Item={
        "run_id": run_id,
        "started_at": started_at,
        "status": "running",
        "instruments": [],
        "errors": [],
        "completed_at": None,
    })


def update_run(
    run_id: str,
    started_at: str,
    status: str,
    instruments: list[str],
    errors: list[dict],
    completed_at: str,
) -> None:
    _runs_table().update_item(
        Key={"run_id": run_id, "started_at": started_at},
        UpdateExpression=(
            "SET #s = :s, instruments = :i, errors = :e, completed_at = :c"
        ),
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={
            ":s": status,
            ":i": instruments,
            ":e": errors,
            ":c": completed_at,
        },
    )


def put_signal(record: dict) -> None:
    _signals_table().put_item(Item=record)

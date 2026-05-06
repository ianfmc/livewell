from __future__ import annotations
import json
import logging
import os
import uuid
from datetime import datetime, timezone

import boto3

from livewell.ingestion.constants import INSTRUMENTS
from livewell.pipeline.dynamodb import create_run, put_signal
from livewell.pipeline.runner import run_instrument

logger = logging.getLogger(__name__)

_lambda_client = boto3.client("lambda")


def handler(event: dict, context) -> dict:
    if "s3_key" in event:
        return _run_worker(event)
    return _run_coordinator(event)


def _run_coordinator(event: dict) -> dict:
    backfill = bool(event.get("backfill", False))
    run_id = str(uuid.uuid4())
    started_at = datetime.now(timezone.utc).isoformat()
    function_name = os.environ["AWS_LAMBDA_FUNCTION_NAME"]

    create_run(run_id, started_at)

    for instrument in INSTRUMENTS:
        payload = json.dumps({
            "s3_key": instrument["s3_key"],
            "run_id": run_id,
            "backfill": backfill,
        })
        _lambda_client.invoke(
            FunctionName=function_name,
            InvocationType="Event",
            Payload=payload,
        )
        logger.info("dispatched worker for %s (run %s)", instrument["s3_key"], run_id)

    logger.info("coordinator done — run_id=%s, backfill=%s", run_id, backfill)
    return {"run_id": run_id, "status": "running"}


def _run_worker(event: dict) -> dict:
    s3_key = event["s3_key"]
    run_id = event["run_id"]
    backfill = bool(event.get("backfill", False))

    record = run_instrument(s3_key, run_id, backfill=backfill)
    put_signal(record)
    logger.info("worker done — %s (run %s)", s3_key, run_id)
    return {"signal_id": record["signal_id"], "s3_key": s3_key}

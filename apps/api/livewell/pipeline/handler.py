from __future__ import annotations
import json
import logging
import os
import uuid
from datetime import datetime, timezone

import boto3

from livewell.ingestion.constants import INSTRUMENTS
from livewell.pipeline.dynamodb import create_run, update_run, put_signal
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

    dispatch_errors: list[dict] = []
    dispatched: list[str] = []

    for instrument in INSTRUMENTS:
        s3_key = instrument["s3_key"]
        payload = json.dumps({"s3_key": s3_key, "run_id": run_id, "backfill": backfill})
        try:
            resp = _lambda_client.invoke(
                FunctionName=function_name,
                InvocationType="Event",
                Payload=payload,
            )
            if resp.get("StatusCode") != 202:
                raise RuntimeError(f"unexpected StatusCode {resp.get('StatusCode')}")
            dispatched.append(s3_key)
            logger.info("dispatched worker for %s (run %s)", s3_key, run_id)
        except Exception as exc:
            logger.error("failed to dispatch %s: %s", s3_key, exc)
            dispatch_errors.append({"s3_key": s3_key, "error": str(exc)})

    n_total = len(INSTRUMENTS)
    n_err = len(dispatch_errors)
    if n_err == 0:
        status = "dispatched"
    elif n_err == n_total:
        status = "dispatch_failed"
    else:
        status = "dispatch_partial"

    completed_at = datetime.now(timezone.utc).isoformat()
    update_run(
        run_id=run_id,
        started_at=started_at,
        status=status,
        instruments=dispatched,
        errors=dispatch_errors,
        completed_at=completed_at,
    )

    logger.info("coordinator done — run_id=%s status=%s dispatched=%d errors=%d",
                run_id, status, len(dispatched), n_err)
    return {"run_id": run_id, "status": status}


def _run_worker(event: dict) -> dict:
    s3_key = event.get("s3_key")
    run_id = event.get("run_id")
    if not s3_key or not run_id:
        raise ValueError(f"worker event missing required fields s3_key/run_id: {event!r}")
    backfill = bool(event.get("backfill", False))
    logger.info("worker started — %s (run %s)", s3_key, run_id)

    record = run_instrument(s3_key, run_id, backfill=backfill)
    put_signal(record)
    logger.info("worker done — %s (run %s)", s3_key, run_id)
    return {"signal_id": record["signal_id"], "s3_key": s3_key}

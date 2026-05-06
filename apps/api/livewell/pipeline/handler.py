from __future__ import annotations
import logging
import uuid
from datetime import datetime, timezone

from livewell.ingestion.constants import INSTRUMENTS
from livewell.pipeline.dynamodb import create_run, update_run, put_signal
from livewell.pipeline.runner import run_instrument

logger = logging.getLogger(__name__)


def handler(event: dict, context) -> dict:
    run_id = str(uuid.uuid4())
    started_at = datetime.now(timezone.utc).isoformat()

    create_run(run_id, started_at)

    signals: list[dict] = []
    errors: list[dict] = []

    for instrument in INSTRUMENTS:
        s3_key = instrument["s3_key"]
        try:
            record = run_instrument(s3_key, run_id)
            signals.append(record)
        except Exception as exc:
            logger.error("instrument %s failed: %s", s3_key, exc)
            errors.append({"s3_key": s3_key, "error": str(exc)})

    n_total = len(INSTRUMENTS)
    n_err = len(errors)

    if n_err == 0:
        status = "completed"
    elif n_err == n_total:
        status = "failed"
    else:
        status = "completed_with_errors"

    completed_at = datetime.now(timezone.utc).isoformat()
    succeeded_keys = [s["s3_key"] for s in signals]

    update_run(
        run_id=run_id,
        started_at=started_at,
        status=status,
        instruments=succeeded_keys,
        errors=errors,
        completed_at=completed_at,
    )

    for record in signals:
        put_signal(record)

    logger.info("run %s %s: %d ok, %d errors", run_id, status, len(signals), n_err)
    return {"run_id": run_id, "status": status}

from __future__ import annotations

import logging
from datetime import UTC, datetime

from livewell.tracking.dynamodb import get_open_trades_due
from livewell.tracking.resolver import resolve_trade

logging.getLogger().setLevel(logging.INFO)
logger = logging.getLogger(__name__)


def handler(event: dict, context) -> dict:
    as_of = datetime.now(UTC).isoformat()
    trades = get_open_trades_due(as_of=as_of)
    logger.info("resolver found %d trade(s) due as of %s", len(trades), as_of)

    resolved = 0
    errors = 0
    for trade in trades:
        try:
            resolve_trade(trade, as_of=as_of)
            resolved += 1
        except Exception as exc:  # noqa: BLE001  # per-trade resilience: record and continue
            logger.error("failed to resolve trade %s: %s", trade.get("trade_id"), exc)
            errors += 1

    logger.info("resolver complete: resolved=%d errors=%d", resolved, errors)
    return {"resolved": resolved, "errors": errors}

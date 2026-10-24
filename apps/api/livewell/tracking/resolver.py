from __future__ import annotations

import logging
from datetime import datetime, timedelta

import yfinance as yf

from livewell.ingestion.constants import INSTRUMENTS
from livewell.tracking.dynamodb import patch_trade

logger = logging.getLogger(__name__)

_TICKER_BY_S3_KEY: dict[str, str] = {i["s3_key"]: i["ticker"] for i in INSTRUMENTS}


def resolve_outcome(direction: str, strike: str, close_price: float) -> str:
    s = float(strike)
    if direction == "buy":
        return "won" if close_price > s else "lost"
    else:  # sell
        return "won" if close_price < s else "lost"


def fetch_close_price(ticker: str, expiry_time: str) -> float | None:
    try:
        expiry_dt = datetime.fromisoformat(expiry_time.replace("Z", "+00:00"))
        start = (expiry_dt - timedelta(minutes=5)).strftime("%Y-%m-%d")
        end = (expiry_dt + timedelta(days=1)).strftime("%Y-%m-%d")
        df = yf.download(
            ticker, start=start, end=end, interval="1m", progress=False, auto_adjust=True, multi_level_index=False
        )
        if df.empty:
            return None
        df.index = df.index.tz_convert("UTC") if df.index.tzinfo else df.index.tz_localize("UTC")
        diffs = abs(df.index - expiry_dt)
        closest = diffs.argmin()
        return float(df["Close"].iloc[closest])
    except Exception as exc:  # noqa: BLE001  # price-fetch resilience: skip trade, don't crash batch
        logger.error("yfinance fetch failed for %s at %s: %s", ticker, expiry_time, exc)
        return None


def resolve_trade(trade: dict, as_of: str) -> None:
    trade_id = trade["trade_id"]
    s3_key = trade["s3_key"]
    ticker = _TICKER_BY_S3_KEY.get(s3_key)
    if not ticker:
        logger.error("no ticker for s3_key=%s, skipping trade %s", s3_key, trade_id)
        return

    close_price = fetch_close_price(ticker, trade["expiry_time"])
    if close_price is None:
        logger.warning("no price available for trade %s, skipping", trade_id)
        return

    outcome = resolve_outcome(trade["direction"], trade["strike"], close_price)
    patch_trade(
        trade_id=trade_id,
        status=outcome,
        outcome_price=str(round(close_price, 6)),
        outcome_source="auto",
        resolved_at=as_of,
    )
    logger.info("resolved trade %s: %s (close=%.5f strike=%s)", trade_id, outcome, close_price, trade["strike"])

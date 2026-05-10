from __future__ import annotations
import logging

import pandas as pd

logger = logging.getLogger(__name__)


def is_win(direction: str, strike: float, next_close: float) -> bool:
    """Return True if next_close beats strike in the predicted direction."""
    if direction == "call":
        return next_close > strike
    if direction == "put":
        return next_close < strike
    return False


def resolve_trade(signal_row: dict, price_df: pd.DataFrame) -> dict | None:
    """
    Find the next trading day's close after signal_row["date"] and determine outcome.

    Returns None if no next-day price exists (end of data or signal on last date).
    Returns a trade result dict on success.
    """
    signal_date = pd.Timestamp(str(signal_row.get("date", "")))
    later = price_df[price_df["date"] > signal_date].sort_values("date")
    if later.empty:
        logger.warning("No next-day price for signal %s — skipping", signal_row.get("signal_id"))
        return None

    next_row = later.iloc[0]
    next_close = float(next_row["close"])
    strike = float(signal_row.get("strike_candidate", 0))
    direction = str(signal_row.get("direction", "none"))
    won = is_win(direction, strike, next_close)

    return {
        "signal_id": str(signal_row.get("signal_id", "")),
        "date": str(signal_row.get("date", "")),
        "instrument": str(signal_row.get("s3_key", "")),
        "direction": direction,
        "strike": strike,
        "next_close": next_close,
        "win": won,
        "signal_valid": bool(signal_row.get("signal_valid", False)),
        "regime": str(signal_row.get("trend_bias", "")),
    }

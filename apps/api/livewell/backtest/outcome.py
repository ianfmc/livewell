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

    Returns None if:
    - "date" is missing or cannot be parsed
    - "strike_candidate" is missing or cannot be converted to float
    - "direction" is missing or "none" (no actionable signal)
    - no next-day price exists (end of data or signal on last date)

    Returns a trade result dict on success.
    """
    # Issue 1: guard against missing or unparseable date
    raw_date = signal_row.get("date")
    if raw_date is None:
        logger.warning("Signal %s has no date — skipping", signal_row.get("signal_id"))
        return None
    try:
        signal_date = pd.Timestamp(str(raw_date))
        # If price_df has tz-aware dates, make signal_date tz-aware too
        if not price_df.empty and price_df["date"].dt.tz is not None and signal_date.tz is None:
            signal_date = signal_date.tz_localize("UTC")
    except (ValueError, TypeError):
        logger.warning("Signal %s has invalid date %r — skipping", signal_row.get("signal_id"), raw_date)
        return None

    # Issue 3: guard against missing or unknown direction
    direction = str(signal_row.get("direction", "none"))
    if direction == "none":
        logger.warning("Signal %s has no actionable direction — skipping", signal_row.get("signal_id"))
        return None

    # Issue 2: guard against missing or unconvertible strike
    raw_strike = signal_row.get("strike_candidate")
    if raw_strike is None:
        logger.warning("Signal %s has no strike_candidate — skipping", signal_row.get("signal_id"))
        return None
    try:
        strike = float(raw_strike)
    except (ValueError, TypeError):
        logger.warning("Signal %s has invalid strike_candidate %r — skipping", signal_row.get("signal_id"), raw_strike)
        return None

    later = price_df[price_df["date"] > signal_date].sort_values("date")
    if later.empty:
        logger.warning("No next-day price for signal %s — skipping", signal_row.get("signal_id"))
        return None

    next_row = later.iloc[0]
    next_close = float(next_row["close"])
    won = is_win(direction, strike, next_close)

    return {
        "signal_id": str(signal_row.get("signal_id", "")),
        "date": str(raw_date),
        "instrument": str(signal_row.get("s3_key", "")),
        "direction": direction,
        "strike": strike,
        "next_close": next_close,
        "win": won,
        "signal_valid": bool(signal_row.get("signal_valid", False)),
        "regime": str(signal_row.get("trend_bias", "")),
    }

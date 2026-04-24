"""Signal generation pipeline: read features+prices from S3, apply 5-stage rules, write signals."""
from __future__ import annotations

import json
import logging
import math
import os

import boto3
import pandas as pd

from livewell.ingestion.constants import INSTRUMENTS, INTERVALS
from livewell.ingestion.s3 import read_parquet, write_parquet
from livewell.features.constants import FEATURES_PREFIX, PRICES_PREFIX
from livewell.signals.constants import (
    ATR_FEASIBILITY_MULTIPLIER,
    MIN_ATR_THRESHOLD,
    PIP_PRECISION,
    RSI_BEARISH_MAX,
    RSI_BULLISH_MIN,
    RSI_OVERBOUGHT,
    RSI_OVERSOLD,
    SESSION_CONFIG,
    SIGNAL_COLUMNS,
    SIGNALS_PREFIX,
)

logger = logging.getLogger(__name__)


def _session_quality(s3_key: str, ts: pd.Timestamp) -> str:
    """Return session quality string for an instrument at a given UTC timestamp."""
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    hour = ts.hour

    sessions = SESSION_CONFIG.get(s3_key, SESSION_CONFIG["EURUSD"])

    for start, end, quality in sessions:
        if start < end:
            if start <= hour < end:
                return quality
        else:
            # Crosses midnight (e.g. 23–07)
            if hour >= start or hour < end:
                return quality

    return "low"

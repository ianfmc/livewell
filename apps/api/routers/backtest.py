from __future__ import annotations
import json
import logging
import os

import boto3
from botocore.exceptions import ClientError
from fastapi import APIRouter, HTTPException

from schemas.backtest import BacktestSummary

logger = logging.getLogger(__name__)
router = APIRouter()

_SUMMARY_KEY = "backtest/summary.json"


@router.get("/backtest/summary", response_model=BacktestSummary)
def get_backtest_summary() -> BacktestSummary:
    bucket = os.environ.get("LIVEWELL_BUCKET", "")
    if not bucket:
        raise HTTPException(status_code=500, detail="LIVEWELL_BUCKET not configured")

    s3 = boto3.client("s3")
    try:
        obj = s3.get_object(Bucket=bucket, Key=_SUMMARY_KEY)
        data = json.loads(obj["Body"].read())
    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchKey":
            raise HTTPException(status_code=404, detail="Backtest has not been run yet")
        logger.exception("S3 error reading backtest summary: %s", e)
        raise HTTPException(status_code=500, detail="Failed to load backtest summary")

    return BacktestSummary(**data)

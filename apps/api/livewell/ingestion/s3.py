"""S3 read/write helpers for OHLCV Parquet files."""
from __future__ import annotations

import io
import logging

import boto3
import pandas as pd
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


def read_parquet(bucket: str, key: str) -> pd.DataFrame | None:
    """Return DataFrame from S3 Parquet, or None if the object does not exist."""
    s3 = boto3.client("s3")
    try:
        obj = s3.get_object(Bucket=bucket, Key=key)
        return pd.read_parquet(io.BytesIO(obj["Body"].read()))
    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchKey":
            return None
        raise


def write_parquet(df: pd.DataFrame, bucket: str, key: str) -> None:
    """Write DataFrame to S3 as Parquet, overwriting any existing object."""
    s3 = boto3.client("s3")
    buf = io.BytesIO()
    df.to_parquet(buf, index=False)
    buf.seek(0)
    s3.put_object(Bucket=bucket, Key=key, Body=buf.getvalue())
    logger.info("wrote %d rows to s3://%s/%s", len(df), bucket, key)

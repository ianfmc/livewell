from __future__ import annotations
import io
import logging
import os

import boto3
import pandas as pd
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

_PRICE_YEARS = list(range(2019, 2027))


def load_price_history(s3_key: str, bucket: str) -> pd.DataFrame:
    """
    Load all annual 1d Parquet files for s3_key from S3 and return a combined DataFrame.

    Columns include at minimum: date (datetime), close (float).
    Returns empty DataFrame if no files found.
    """
    s3 = boto3.client("s3")
    frames: list[pd.DataFrame] = []
    for year in _PRICE_YEARS:
        key = f"prices/{s3_key}/1d/{year}.parquet"
        try:
            obj = s3.get_object(Bucket=bucket, Key=key)
            df = pd.read_parquet(io.BytesIO(obj["Body"].read()))
            frames.append(df)
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                continue
            raise

    if not frames:
        logger.warning("No price history found for %s in s3://%s", s3_key, bucket)
        return pd.DataFrame(columns=["date", "close"])

    combined = pd.concat(frames, ignore_index=True)
    combined["date"] = pd.to_datetime(combined["date"], utc=True)
    combined = combined.sort_values("date").reset_index(drop=True)
    return combined


def load_all_signals(env: str = "prod") -> list[dict]:
    """
    Scan the livewell-signals-{env} DynamoDB table and return all records
    where direction != 'none'.
    """
    region = os.environ.get("AWS_DEFAULT_REGION", "us-west-1")
    table = boto3.resource("dynamodb", region_name=region).Table(f"livewell-signals-{env}")
    try:
        resp = table.scan()
        items: list[dict] = list(resp.get("Items", []))
        while "LastEvaluatedKey" in resp:
            resp = table.scan(ExclusiveStartKey=resp["LastEvaluatedKey"])
            items.extend(resp.get("Items", []))
    except ClientError as exc:
        logger.error("DynamoDB scan failed: %s", exc)
        return []

    return [i for i in items if str(i.get("direction", "none")) != "none"]

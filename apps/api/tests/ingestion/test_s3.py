import io
import os
import boto3
import pandas as pd
import pytest
from moto import mock_aws
from livewell.ingestion.s3 import read_parquet, write_parquet

BUCKET = "test-livewell"
KEY = "prices/EURUSD/1d/2026.parquet"


def make_df():
    return pd.DataFrame({
        "date":   pd.to_datetime(["2026-04-21", "2026-04-22"]),
        "open":   [1.08, 1.09],
        "high":   [1.09, 1.10],
        "low":    [1.07, 1.08],
        "close":  [1.085, 1.095],
        "volume": [1000.0, 1100.0],
    })


@pytest.fixture()
def s3_bucket():
    with mock_aws():
        conn = boto3.client("s3", region_name="us-east-1")
        conn.create_bucket(Bucket=BUCKET)
        yield conn


def test_write_then_read_roundtrip(s3_bucket):
    df = make_df()
    write_parquet(df, BUCKET, KEY)
    result = read_parquet(BUCKET, KEY)
    assert list(result.columns) == list(df.columns)
    assert len(result) == len(df)


def test_read_missing_returns_none(s3_bucket):
    result = read_parquet(BUCKET, "prices/EURUSD/1d/2099.parquet")
    assert result is None


def test_write_overwrites_existing(s3_bucket):
    df1 = make_df()
    write_parquet(df1, BUCKET, KEY)
    df2 = make_df().iloc[:1]
    write_parquet(df2, BUCKET, KEY)
    result = read_parquet(BUCKET, KEY)
    assert len(result) == 1

# utils_s3.py
"""S3 utility functions for Nadex recommendation system."""
from __future__ import annotations
import io
import csv
import datetime as dt
from typing import Iterable, Optional, Dict
import pandas as pd
import boto3
from botocore.exceptions import ClientError
from botocore import UNSIGNED
from botocore.config import Config

# ============================================================================
# S3 CLIENT CREATION
# ============================================================================

def create_s3_clients(
    profile: str = "default", 
    region: str = None
) -> Dict[str, boto3.client]:
    """
    Create S3 clients for public and private access.
    
    Parameters
    ----------
    profile : str, default "default"
        AWS profile name
    region : str, optional
        AWS region (e.g., 'us-west-2')
        
    Returns
    -------
    dict
        Dictionary with keys: 'public', 'private', 'resource'
    """
    session = boto3.Session(profile_name=profile, region_name=region)
    return {
        "public": session.client(
            "s3",
            config=Config(signature_version=UNSIGNED),
            region_name=region,
        ),
        "private": session.client("s3"),
        "resource": session.resource("s3"),
    }


def get_bucket(resource: boto3.resource, name: str):
    """
    Get S3 bucket from resource.
    
    Parameters
    ----------
    resource : boto3.resource
        S3 resource object
    name : str
        Bucket name
        
    Returns
    -------
    S3 Bucket object
    """
    return resource.Bucket(name)


# ============================================================================
# DATAFRAME UPLOAD FUNCTIONS
# ============================================================================

def upload_df_to_s3_with_validation(
    df: pd.DataFrame,
    bucket: str,
    key: str,
    region: str = None,
    index: bool = False
) -> None:
    """
    Uploads a DataFrame to S3 as CSV with bucket validation.
    
    This function verifies bucket existence before uploading and provides
    detailed error messages if upload fails.
    
    Parameters
    ----------
    df : pd.DataFrame
        DataFrame to upload
    bucket : str
        Name of the S3 bucket (leading/trailing spaces will be stripped)
    key : str
        S3 object key, e.g. "recommendations/20251120.csv"
    region : str, optional
        AWS region where the bucket resides
    index : bool, default False
        Whether to include DataFrame index in CSV
        
    Raises
    ------
    RuntimeError
        If bucket doesn't exist or upload fails
    """
    bucket = bucket.strip()
    s3 = boto3.client('s3', region_name=region)

    # Verify bucket exists
    try:
        s3.head_bucket(Bucket=bucket)
    except ClientError as e:
        code = e.response['Error']['Code']
        msg = e.response['Error']['Message']
        raise RuntimeError(
            f"Could not access bucket '{bucket}' (region={region}): {msg} (code {code})"
        ) from e

    # Upload DataFrame as CSV
    buffer = io.StringIO()
    df.to_csv(buffer, index=index)
    buffer.seek(0)

    try:
        s3.put_object(Bucket=bucket, Key=key, Body=buffer.getvalue())
        print(f"✅ Uploaded to s3://{bucket}/{key}")
    except ClientError as e:
        raise RuntimeError(
            f"Failed to upload CSV to s3://{bucket}/{key}: "
            f"{e.response['Error']['Message']}"
        ) from e


def save_dataframe_to_s3(
    s3_client, 
    df: pd.DataFrame, 
    bucket: str, 
    key: str, 
    *, 
    index: bool = False, 
    na_rep: str = ""
) -> None:
    """
    Save DataFrame to S3 as CSV (simple version, requires pre-created client).
    
    Parameters
    ----------
    s3_client : boto3.client
        S3 client object
    df : pd.DataFrame
        DataFrame to save
    bucket : str
        S3 bucket name
    key : str
        S3 object key
    index : bool, default False
        Whether to include index
    na_rep : str, default ""
        String representation of NaN values
    """
    csv_bytes = df.to_csv(index=index, na_rep=na_rep).encode("utf-8")
    s3_client.put_object(Bucket=bucket, Key=key, Body=csv_bytes, ContentType="text/csv")


# ============================================================================
# TEXT UPLOAD
# ============================================================================

def save_text_to_s3(
    s3_client, 
    text: str, 
    bucket: str, 
    key: str, 
    content_type: str = "text/plain; charset=utf-8"
) -> None:
    """
    Save text string to S3.
    
    Parameters
    ----------
    s3_client : boto3.client
        S3 client object
    text : str
        Text content to save
    bucket : str
        S3 bucket name
    key : str
        S3 object key
    content_type : str, default "text/plain; charset=utf-8"
        Content type header
    """
    s3_client.put_object(
        Bucket=bucket, 
        Key=key, 
        Body=text.encode("utf-8"), 
        ContentType=content_type
    )


# ============================================================================
# RUN LOG TRACKING
# ============================================================================

RUNLOG_FIELDS = [
    "date", "start_time", "end_time", "status",
    "files_processed", "files_skipped", "files_error",
    "run_id", "notes"
]


def append_runlog_s3(
    s3_client, 
    bucket: str, 
    key: str, 
    *, 
    start_time: Optional[dt.datetime] = None,
    status: str = "success", 
    files_processed: int = 0, 
    files_skipped: int = 0,
    files_error: int = 0, 
    run_id: str = "", 
    notes: str = ""
) -> None:
    """
    Append a row to the run log CSV in S3.
    
    This function fetches the existing log (if it exists), appends a new row,
    and writes it back to S3.
    
    Parameters
    ----------
    s3_client : boto3.client
        S3 client object
    bucket : str
        S3 bucket name
    key : str
        S3 object key for the run log
    start_time : datetime, optional
        Run start time (defaults to now)
    status : str, default "success"
        Run status
    files_processed : int, default 0
        Number of files processed
    files_skipped : int, default 0
        Number of files skipped
    files_error : int, default 0
        Number of files with errors
    run_id : str, default ""
        Unique run identifier
    notes : str, default ""
        Additional notes
    """
    now = dt.datetime.now()
    start = start_time or now
    
    row = {
        "date": now.date().isoformat(),
        "start_time": start if isinstance(start, str) else start.isoformat(timespec="seconds"),
        "end_time": now.isoformat(timespec="seconds"),
        "status": status,
        "files_processed": int(files_processed),
        "files_skipped": int(files_skipped),
        "files_error": int(files_error),
        "run_id": run_id,
        "notes": notes
    }
    
    # Fetch existing log (if present)
    buf = io.StringIO()
    need_header = False
    try:
        obj = s3_client.get_object(Bucket=bucket, Key=key)
        buf.write(obj["Body"].read().decode("utf-8"))
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code in ("NoSuchKey", "404", "NoSuchBucket"):
            need_header = True
        else:
            raise
    
    if buf.tell() == 0:
        need_header = True
    
    # Append new row
    writer = csv.DictWriter(buf, fieldnames=RUNLOG_FIELDS)
    if need_header:
        writer.writeheader()
    if buf.getvalue() and not buf.getvalue().endswith("\n"):
        buf.write("\n")
    writer.writerow(row)
    
    # Write back to S3
    s3_client.put_object(
        Bucket=bucket, 
        Key=key, 
        Body=buf.getvalue().encode("utf-8"), 
        ContentType="text/csv"
    )


# ============================================================================
# VALIDATION
# ============================================================================

def assert_allowed_bucket(bucket: str, allowed_buckets: Iterable[str]) -> None:
    """
    Verify bucket is in allowed list.
    
    Parameters
    ----------
    bucket : str
        Bucket name to validate
    allowed_buckets : iterable of str
        List of allowed bucket names
        
    Raises
    ------
    ValueError
        If bucket is not in allowed list
    """
    if bucket not in set(allowed_buckets or []):
        raise ValueError(
            f"Bucket '{bucket}' not in allowed set: {set(allowed_buckets or [])}"
        )

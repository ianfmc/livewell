# Comparison: utils_s3.py vs refactored_s3_code.py

## Current lib/utils_s3.py Functions

| Function | Signature | Notes |
|----------|-----------|-------|
| `append_runlog_s3` | `(s3_client, bucket, key, ...)` | ✅ Already exists, takes client as param |
| `save_dataframe_to_s3` | `(s3_client, df, bucket, key, ...)` | ✅ Already exists, simple version |
| `save_text_to_s3` | `(s3_client, text, bucket, key, ...)` | ✅ Already exists |
| `assert_allowed_bucket` | `(bucket, allowed_buckets)` | ✅ Already exists |

## Functions in refactored_s3_code.py (Notebook)

| Function | Signature | Status in utils_s3.py |
|----------|-----------|----------------------|
| `create_s3_clients` | `(profile, region)` → Dict | ❌ **MISSING - Need to add** |
| `get_bucket` | `(resource, name)` → Bucket | ❌ **MISSING - Need to add** |
| `upload_df_to_s3` | `(df, bucket, key, region)` | ⚠️ **Different pattern - need to reconcile** |

## Recommended Updates to lib/utils_s3.py

### 1. Add `create_s3_clients()`
```python
def create_s3_clients(
    profile: str = "default", 
    region: str = None
) -> dict:
    """
    Create S3 clients for public and private access.
    
    Parameters
    ----------
    profile : str
        AWS profile name
    region : str
        AWS region
        
    Returns
    -------
    dict with keys: 'public', 'private', 'resource'
    """
    from botocore import UNSIGNED
    from botocore.config import Config
    import boto3
    
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
```

### 2. Add `get_bucket()`
```python
def get_bucket(resource, name: str):
    """Get S3 bucket from resource."""
    return resource.Bucket(name)
```

### 3. Add `upload_df_to_s3_with_validation()`
New function that validates bucket before upload:
```python
def upload_df_to_s3_with_validation(
    df: pd.DataFrame,
    bucket: str,
    key: str,
    region: str = None,
    index: bool = False
) -> None:
    """
    Uploads a DataFrame to S3 as CSV with bucket validation.
    
    Parameters
    ----------
    df : pd.DataFrame
    bucket : str
        Name of the S3 bucket
    key : str
        S3 object key
    region : str, optional
        AWS region
    index : bool
        Whether to include index in CSV
    """
    import boto3
    
    bucket = bucket.strip()
    s3 = boto3.client('s3', region_name=region)

    try:
        s3.head_bucket(Bucket=bucket)
    except ClientError as e:
        code = e.response['Error']['Code']
        msg = e.response['Error']['Message']
        raise RuntimeError(
            f"Could not access bucket '{bucket}' (region={region}): {msg} (code {code})"
        ) from e

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
```

## Recommended Changes to nadex-recommendation.ipynb

### Current Structure (Delete from notebook):
```python
# DELETE these function definitions from notebook cells:
- def create_s3_clients(...)
- def get_bucket(...)
- def upload_df_to_s3(...)
```

### New Import Structure:
```python
# In "Load from configuration files" cell:
import sys
import yaml
from pathlib import Path

sys.path.append("../lib")

from strategy_rsi import generate_rsi_signals
from utils_s3 import (
    create_s3_clients,
    get_bucket,
    upload_df_to_s3_with_validation,
    append_runlog_s3,
    save_dataframe_to_s3,
    assert_allowed_bucket
)
```

### Updated Pipeline Function:
```python
def run_recommendation_pipeline(tickers: List,
                               bucket_name: str,
                               period: str,
                               interval: str,
                               mapping_file: str,
                               region: str = None) -> pd.DataFrame:
    """
    Fetch price, compute indicators, load strikes,
    and return a DataFrame of trade signals.
    """
    # Use imported function
    clients = create_s3_clients(region=region)
    public_s3 = clients["public"]
    private_s3 = clients["private"]
    s3_resource = clients["resource"]
    
    # Use imported function
    buckets = {
        "daily": get_bucket(s3_resource, bucket_name),
    }

    ticker_price_data = [
        (ticker, fetch_price(ticker, period, interval))
        for ticker in tickers
    ]

    processed = {
        ticker: (
            df
              .pipe(compute_macd)
              .pipe(compute_rsi)
              .pipe(compute_atr)
        )
        for ticker, df in ticker_price_data
    }
    strikes_df = load_strikes(mapping_file)
    signals_df = generate_detailed_signals(processed, strikes_df)

    today_str = date.today().strftime('%Y%m%d')
    s3_key = f"{RECS_PREFIX}/{today_str}.csv"
    
    # Use imported function
    upload_df_to_s3_with_validation(
        signals_df,
        bucket_name,
        s3_key,
        region=region
    )
    return signals_df
```

### Updated Run Log Cell:
```python
# DELETE the entire "Record in the Run Log" cell 
# The append_runlog_s3 function is now imported from utils_s3
```

## Summary of Changes

### Files to Update:

#### 1. `lib/utils_s3.py` - ADD these functions:
- ✅ `create_s3_clients(profile, region)`
- ✅ `get_bucket(resource, name)`
- ✅ `upload_df_to_s3_with_validation(df, bucket, key, region, index)`

#### 2. `notebooks/nadex-recommendation.ipynb` - MODIFICATIONS:
- ✅ DELETE cell: "Define a function to upload the recommendations to S3"
- ✅ DELETE cell: "Record in the Run Log"
- ✅ UPDATE cell: "Load from configuration files" - add imports
- ✅ UPDATE cell: "Define a function to run the Pipeline" - use imported functions

### Benefits:
1. ✅ All S3 code centralized in `lib/utils_s3.py`
2. ✅ Notebook becomes cleaner and focused on business logic
3. ✅ S3 functions can be reused across multiple notebooks
4. ✅ Easier to test and maintain
5. ✅ Consistent API across all S3 operations

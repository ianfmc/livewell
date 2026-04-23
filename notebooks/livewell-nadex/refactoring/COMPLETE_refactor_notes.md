# S3 Configuration Refactoring Notes

## Current State
Your notebook already loads `s3.yaml` in the "Load from configuration files" cell and sets:
- `BUCKET` = cfg['bucket'] = "nadex-daily-results"
- `REGION` = cfg.get('region') = "us-east-1"
- `RECS_PREFIX` = "historical"
- `MAPPING_FILE` = "contracts.csv"

## Issues to Fix

### 1. `create_s3_clients()` function (Cell: "Define a function to upload the recommendations to S3")
**Current:** Has hardcoded default `region: str = "us-west-2"`
**Fix:** Change to use the REGION from config

```python
def create_s3_clients(
    profile: str = "default", region: str = None  # Changed default
) -> Dict[str, boto3.client]:
    # Use the region from config if not provided
    if region is None:
        region = REGION  # Will use value from s3.yaml
    
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

### 2. `run_recommendation_pipeline()` function
**Current:** Calls `create_s3_clients()` without passing the region
**Fix:** Pass the region parameter

```python
def run_recommendation_pipeline(tickers: List,
                               bucket_name: str,
                               period: str,
                               interval: str,
                               mapping_file: str,
                               region: str = None) -> pd.DataFrame:  # Add region param
    """
    Fetch price, compute indicators, load strikes,
    and return a DataFrame of trade signals.
    """
    clients = create_s3_clients(region=region)  # Pass region
    # ... rest of function
```

### 3. Final execution cell
**Current:** Doesn't pass region to run_recommendation_pipeline
**Fix:** 

```python
successful_run = show_interesting_trades(
    run_recommendation_pipeline(
        tickers=TICKERS,
        period="90d",
        interval="1d",
        bucket_name=BUCKET,
        mapping_file=MAPPING_FILE,
        region=REGION  # Add this line
    )
)
```

### 4. `upload_df_to_s3()` function
**Current:** Already accepts region parameter - GOOD!
**Fix:** Just make sure it's being called with the region:

In `run_recommendation_pipeline`, update the upload call:
```python
upload_df_to_s3(
    signals_df,
    bucket_name,
    s3_key,
    region=region  # Add this line
)
```

## Summary of Changes Needed

1. ✅ Config loading is already done
2. ✅ `create_s3_clients()` - change default region and handle None case
3. ✅ `run_recommendation_pipeline()` - add region parameter and pass to functions
4. ✅ Final execution - pass REGION to run_recommendation_pipeline
5. ✅ `upload_df_to_s3()` call - pass region parameter

## Benefits
- All S3 configuration centralized in `s3.yaml`
- Easy to switch between environments (dev/prod)
- Region, bucket, and prefixes all configured in one place
- No hardcoded values scattered through code

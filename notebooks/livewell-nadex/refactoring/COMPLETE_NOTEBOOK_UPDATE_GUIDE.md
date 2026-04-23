# Notebook Update Guide: Moving S3 Code to lib/utils_s3.py

## Overview
This guide shows how to update `nadex-recommendation.ipynb` to use the centralized S3 functions from `lib/utils_s3.py`.

## Files Modified
1. ✅ `lib/utils_s3.py` - Already updated with new functions
2. ⏳ `notebooks/nadex-recommendation.ipynb` - Needs updates (see below)

---

## Step-by-Step Notebook Changes

### STEP 1: ❌ DELETE this entire cell: "Define a function to upload the recommendations to S3"

**Current cell contains:**
```python
import io
import boto3
import pandas as pd
from botocore.exceptions import ClientError
from botocore import UNSIGNED
from botocore.config import Config

from typing import Iterable, List, Dict

def create_s3_clients(...)
def get_bucket(...)
def upload_df_to_s3(...)
```

**Action: DELETE THE ENTIRE CELL** - These functions are now in `lib/utils_s3.py`

---

### STEP 2: ❌ DELETE this entire cell: "Record in the Run Log"

**Current cell contains:**
```python
import yaml
from pathlib import Path
with open('../configs/s3.yaml', 'r') as f:
    cfg = yaml.safe_load(f)
    
# Run log helper (append a row to S3 CSV)
import io, csv, datetime as dt
from botocore.exceptions import ClientError

RUNLOG_FIELDS = [...]

session = boto3.Session(region_name=cfg.get('region'))
private_s3 = session.client('s3')
public_s3 = session.client('s3', config=Config(signature_version=UNSIGNED))

def append_runlog_s3(...)
```

**Action: DELETE THE ENTIRE CELL** - This function is now in `lib/utils_s3.py`

---

### STEP 3: ✏️ UPDATE cell: "Load from configuration files"

**Replace the entire cell with:**
```python
# Load config (run from inside notebooks/)
import sys
import yaml
from pathlib import Path

sys.path.append("../lib")

# Import strategy functions
from strategy_rsi import generate_rsi_signals

# Import S3 utility functions
from utils_s3 import (
    create_s3_clients,
    get_bucket,
    upload_df_to_s3_with_validation,
    append_runlog_s3,
    save_dataframe_to_s3,
    assert_allowed_bucket
)

# Load s3 configuration
with open('../configs/s3.yaml', 'r') as f:
    cfg = yaml.safe_load(f)

# S3 targets / prefixes
BUCKET = cfg['bucket']
REGION = cfg.get('region')
RECS_PREFIX = cfg['prefixes'].get('recommendations', 'recommendations')
REPORTS_PREFIX = cfg['prefixes'].get('reports', 'reports')
RUNLOG_KEY = f"{cfg['prefixes'].get('logs','logs')}/run_log.csv"

print(f"✅ Loaded config:")
print(f"   Bucket: {BUCKET}")
print(f"   Region: {REGION}")
print(f"   Recommendations prefix: {RECS_PREFIX}")

# Optional mapping file
MAPPING_FILE = Path(cfg.get('mapping_file')).resolve() if cfg.get('mapping_file') else None

# Optional: guard to prevent accidental hard-coding at runtime
ALLOWED_BUCKETS = {BUCKET}

def assert_allowed_bucket_local(b):
    if b not in ALLOWED_BUCKETS:
        raise ValueError(
            f"Bucket '{b}' not allowed; use cfg['bucket'] from s3.yaml."
        )
```

---

### STEP 4: ✏️ UPDATE cell: "Define a function to run the Pipeline"

**Replace the entire cell with:**
```python
import pandas as pd
from datetime import date, datetime
from typing import List

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
    # Create S3 clients using imported function
    clients = create_s3_clients(region=region)
    public_s3 = clients["public"]
    private_s3 = clients["private"]
    s3_resource = clients["resource"]
    
    # Get bucket using imported function
    buckets = {
        "daily": get_bucket(s3_resource, bucket_name),
    }

    # Fetch price data for all tickers
    ticker_price_data = [
        (ticker, fetch_price(ticker, period, interval))
        for ticker in tickers
    ]

    # Compute technical indicators
    processed = {
        ticker: (
            df
              .pipe(compute_macd)
              .pipe(compute_rsi)
              .pipe(compute_atr)
        )
        for ticker, df in ticker_price_data
    }
    
    # Load strike prices and generate signals
    strikes_df = load_strikes(mapping_file)
    signals_df = generate_detailed_signals(processed, strikes_df)

    # Upload to S3 using imported function
    today_str = date.today().strftime('%Y%m%d')
    s3_key = f"{RECS_PREFIX}/{today_str}.csv"
    
    upload_df_to_s3_with_validation(
        signals_df,
        bucket_name,
        s3_key,
        region=region
    )
    
    return signals_df
```

---

### STEP 5: ✏️ UPDATE cell: "Run recommendation pipeline"

**Replace the entire cell with:**
```python
import datetime as dt

TICKERS = {
    'CL=F',
    'ES=F',
    'GC=F',
    'NQ=F',
    'RTY=F',
    'YM=F',
    'NG=F',
    'AUDUSD=X',
    'EURJPY=X',
    'EURUSD=X',
    'GBPJPY=X',
    'GBPUSD=X',
    'USDCAD=X',
    'USDCHF=X',
    'USDJPY=X'
}

# Track run start time
run_start = dt.datetime.now()
run_id = run_start.strftime("%Y%m%dT%H%M%S")

# Run the pipeline
successful_run = show_interesting_trades(
    run_recommendation_pipeline(
        tickers=TICKERS,
        period="90d",
        interval="1d",
        bucket_name=BUCKET,
        mapping_file=MAPPING_FILE,
        region=REGION
    )
)

# Create S3 client for logging
from utils_s3 import create_s3_clients
clients = create_s3_clients(region=REGION)
private_s3 = clients["private"]

# Append to run log using imported function
append_runlog_s3(
    private_s3,
    BUCKET, 
    RUNLOG_KEY,
    start_time=run_start,
    status=successful_run,
    files_processed=0,
    files_skipped=0,
    files_error=0,
    run_id=run_id,
    notes='Recommendation run'
)

print(f"\n✅ Run complete: {run_id}")
print(f"   Status: {successful_run}")
```

---

## Summary of Changes

### Cells to DELETE (2 cells):
1. ✅ "Define a function to upload the recommendations to S3"
2. ✅ "Record in the Run Log"

### Cells to UPDATE (3 cells):
1. ✏️ "Load from configuration files" - add imports from utils_s3
2. ✏️ "Define a function to run the Pipeline" - use imported functions
3. ✏️ "Run recommendation pipeline" - use imported functions

---

## Benefits After Refactoring

✅ **Cleaner Notebook**
- Removed ~100 lines of S3 boilerplate code
- Focus on business logic (pricing, indicators, signals)

✅ **Reusability**
- S3 functions can be used across multiple notebooks
- Consistent API for S3 operations

✅ **Maintainability**
- Single source of truth for S3 code
- Easier to test and debug

✅ **Configuration-Driven**
- All S3 settings in `configs/s3.yaml`
- No hardcoded values in notebook

---

## Testing the Changes

After making these changes, run the notebook cells in order:

1. Install packages
2. Define data fetching functions
3. Define technical indicator functions
4. Define strike loading function
5. Define signal generation functions
6. Define show_interesting_trades function
7. **Load configuration** (updated with imports)
8. **Run pipeline** (updated to use imported functions)

Expected output:
```
✅ Loaded config:
   Bucket: nadex-daily-results
   Region: us-west-2
   Recommendations prefix: recommendations
   
[... ticker processing ...]

✅ Uploaded to s3://nadex-daily-results/recommendations/20251120.csv

[... trade recommendations table ...]

✅ Run complete: 20251120T142535
   Status: Success
```

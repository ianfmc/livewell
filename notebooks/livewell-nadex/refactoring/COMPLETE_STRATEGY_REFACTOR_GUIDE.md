# Strategy Refactoring Guide: Use strategy.yaml and lib/strategy_rsi.py

## Problem Analysis

### Current Hardcoded Values in Notebook
| Location | Hardcoded Value | Should Come From |
|----------|-----------------|------------------|
| `compute_macd()` | `span=12, 26, 9` | `strategy.yaml` → `trend.macd_fast/slow/signal` |
| `compute_rsi()` | `window=14` | `strategy.yaml` → `rsi.period` |
| `momentum_check()` | `rsi > 50 / rsi < 50` | `strategy.yaml` → `rsi.centerline` |
| `signal_trigger()` | `rsi > 50 / rsi < 50` | `strategy.yaml` → `rsi.centerline` |
| `determine_trend()` | EMA12/EMA26 logic | `strategy.yaml` → `trend.type` + params |

### Available in strategy.yaml
```yaml
rsi:
  period: 14
  mode: centerline
  centerline: 50
  
trend:
  type: macd
  macd_fast: 12
  macd_slow: 26
  macd_signal: 9
```

### Available in lib/strategy_rsi.py
- `rsi_wilder(close, period)` - Configurable RSI
- `macd(close, fast, slow, signal)` - Configurable MACD  
- `generate_rsi_signals(close, cfg)` - Full signal generation using config
- `trend_ok(close, cfg)` - Trend filtering based on config

---

## Refactoring Steps

### STEP 1: Load strategy.yaml in Config Cell

**Update the "Load from configuration files" cell:**

```python
# Load config (run from inside notebooks/)
import sys
import yaml
from pathlib import Path

sys.path.append("../lib")

# Import strategy functions
from strategy_rsi import generate_rsi_signals, rsi_wilder, macd

# Import S3 utility functions
from utils_s3 import (
    create_s3_clients,
    get_bucket,
    upload_df_to_s3_with_validation,
    append_runlog_s3,
    save_dataframe_to_s3,
    assert_allowed_bucket
)

# Load S3 configuration
with open('../configs/s3.yaml', 'r') as f:
    s3_cfg = yaml.safe_load(f)

# Load STRATEGY configuration
with open('../configs/strategy.yaml', 'r') as f:
    strategy_cfg = yaml.safe_load(f)

# S3 targets / prefixes
BUCKET = s3_cfg['bucket']
REGION = s3_cfg.get('region')
RECS_PREFIX = s3_cfg['prefixes'].get('recommendations', 'recommendations')
REPORTS_PREFIX = s3_cfg['prefixes'].get('reports', 'reports')
RUNLOG_KEY = f"{s3_cfg['prefixes'].get('logs','logs')}/run_log.csv"

print(f"✅ Loaded S3 config:")
print(f"   Bucket: {BUCKET}")
print(f"   Region: {REGION}")

print(f"\n✅ Loaded Strategy config:")
print(f"   RSI Period: {strategy_cfg['rsi']['period']}")
print(f"   RSI Mode: {strategy_cfg['rsi']['mode']}")
print(f"   RSI Centerline: {strategy_cfg['rsi']['centerline']}")
print(f"   Trend Type: {strategy_cfg['trend']['type']}")
print(f"   MACD: {strategy_cfg['trend']['macd_fast']}/{strategy_cfg['trend']['macd_slow']}/{strategy_cfg['trend']['macd_signal']}")

# Mapping file
MAPPING_FILE = Path(s3_cfg.get('mapping_file')).resolve() if s3_cfg.get('mapping_file') else None

# Bucket validation
ALLOWED_BUCKETS = {BUCKET}
```

---

### STEP 2: Replace Technical Indicators Cell

**Replace the "Define a function to compute the technical indicators" cell:**

```python
import pandas as pd
from strategy_rsi import rsi_wilder, macd as macd_func

def compute_indicators(df: pd.DataFrame, strategy_cfg: dict) -> pd.DataFrame:
    """
    Compute technical indicators using strategy.yaml configuration.
    
    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with OHLC data
    strategy_cfg : dict
        Strategy configuration from strategy.yaml
        
    Returns
    -------
    pd.DataFrame with indicators added
    """
    df = df.copy()
    
    # Get config values
    rsi_period = strategy_cfg['rsi']['period']
    macd_fast = strategy_cfg['trend']['macd_fast']
    macd_slow = strategy_cfg['trend']['macd_slow']
    macd_signal = strategy_cfg['trend']['macd_signal']
    
    # Compute RSI using strategy_rsi.py function
    df['RSI'] = rsi_wilder(df['Close'], period=rsi_period)
    
    # Compute MACD using strategy_rsi.py function
    df['MACD'], df['Signal'], df['MACD_hist'] = macd_func(
        df['Close'], 
        fast=macd_fast, 
        slow=macd_slow, 
        signal=macd_signal
    )
    
    # Keep EMA calculations for compatibility
    df['EMA12'] = df['Close'].ewm(span=macd_fast, adjust=False).mean()
    df['EMA26'] = df['Close'].ewm(span=macd_slow, adjust=False).mean()
    
    # Compute ATR (not in strategy_rsi.py yet, keep custom)
    prev_close = df['Close'].shift(1)
    tr1 = df['High'] - df['Low']
    tr2 = (df['High'] - prev_close).abs()
    tr3 = (df['Low'] - prev_close).abs()
    df['ATR'] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1).rolling(window=14).mean()
    
    return df
```

---

### STEP 3: Update Signal Generation to Use Config

**Replace the "Define a function to determine the trading signal" cell:**

```python
import pandas as pd

def determine_trend(row, strategy_cfg):
    """
    Returns (trend_str, ema_diff) using config-based MACD parameters.
    """
    trend_type = strategy_cfg['trend']['type']
    
    if trend_type == 'macd':
        # Use MACD for trend determination
        diff = row.MACD - row.Signal
        if (row.MACD > row.Signal) and (row.Close > row.EMA12) and (row.Close > row.EMA26):
            trend = 'up'
        elif (row.MACD < row.Signal) and (row.Close < row.EMA12) and (row.Close < row.EMA26):
            trend = 'down'
        else:
            trend = 'sideways'
        return trend, diff
    else:
        # Fallback
        return 'sideways', 0

def momentum_check(row, trend, strategy_cfg):
    """
    Returns (ok, rsi) using config-based RSI parameters.
    """
    rsi = row.RSI
    centerline = strategy_cfg['rsi']['centerline']
    
    if trend == 'up':
        ok = (rsi > centerline) and ((row.MACD > row.Signal) or (row.MACD_hist > 0))
    elif trend == 'down':
        ok = (rsi < centerline) and ((row.MACD < row.Signal) or (row.MACD_hist < 0))
    else:
        ok = False
    return ok, rsi

def signal_trigger(row, trend, strategy_cfg):
    """
    Returns (ok, macd_diff) using config-based RSI centerline.
    """
    macd_diff = row.MACD - row.Signal
    centerline = strategy_cfg['rsi']['centerline']
    
    if trend == 'up':
        ok = (macd_diff > 0) and (row.RSI > centerline)
    elif trend == 'down':
        ok = (macd_diff < 0) and (row.RSI < centerline)
    else:
        ok = False
    return ok, macd_diff

def volatility_check(row, strike_diff):
    """
    Returns (ok, strike_diff) - ATR-based check.
    """
    ok = strike_diff <= 0.5 * row.ATR
    return ok, strike_diff

def signal_detail_for_row(row, per_ticker, strategy_cfg, expiry="EOD"):
    """
    Generate signal details for a single row, using strategy config.
    """
    df = per_ticker[row.ticker]
    last = df.iloc[-1]

    trend, trend_val = determine_trend(last, strategy_cfg)
    momentum_ok, momentum_val = momentum_check(last, trend, strategy_cfg)
    sig_ok, signal_val = signal_trigger(last, trend, strategy_cfg)
    strike_diff = abs(row.strike - last.Close)
    vol_ok, vol_val = volatility_check(last, strike_diff)

    # Build recommendation + contract price
    if (trend == 'sideways'
        or not momentum_ok
        or not sig_ok
        or not vol_ok
    ):
        rec = "No trade"
        price = pd.NA
    else:
        direction = "Buy" if trend == "up" else "Sell"
        price = 10 * (0.5 - (strike_diff / (2 * last.ATR)))
        rec = direction

    return pd.Series({
        "Date": pd.Timestamp.now().strftime("%d-%b-%y"),
        "Ticker": row.ticker,
        "Strike": row.strike,
        "EMA12": last.EMA12,
        "EMA26": last.EMA26,
        "MACD": last.MACD,
        "RSI": last.RSI,
        "ATR": last.ATR,
        "Recommendation": rec,
        "ContractPrice": price,
        "Trend": trend_val,
        "Momentum": momentum_val,
        "Signal": signal_val,
        "Volatility": vol_val
    })

def generate_detailed_signals(per_ticker: dict[str, pd.DataFrame],
                              strikes_df: pd.DataFrame,
                              strategy_cfg: dict) -> pd.DataFrame:
    """
    Applies signal_detail_for_row to every strike with strategy config.
    """
    return strikes_df.apply(
        lambda r: signal_detail_for_row(r, per_ticker, strategy_cfg),
        axis=1
    )
```

---

### STEP 4: Update Pipeline to Use Config-Based Functions

**Replace the "Define a function to run the Pipeline" cell:**

```python
import pandas as pd
from datetime import date, datetime
from typing import List

def run_recommendation_pipeline(tickers: List,
                               bucket_name: str,
                               period: str,
                               interval: str,
                               mapping_file: str,
                               strategy_cfg: dict,
                               region: str = None) -> pd.DataFrame:
    """
    Fetch price, compute indicators, load strikes,
    and return a DataFrame of trade signals.
    """
    # Create S3 clients
    clients = create_s3_clients(region=region)
    public_s3 = clients["public"]
    private_s3 = clients["private"]
    s3_resource = clients["resource"]
    buckets = {
        "daily": get_bucket(s3_resource, bucket_name),
    }

    # Fetch price data for all tickers
    ticker_price_data = [
        (ticker, fetch_price(ticker, period, interval))
        for ticker in tickers
    ]

    # Compute technical indicators using config
    processed = {
        ticker: compute_indicators(df, strategy_cfg)
        for ticker, df in ticker_price_data
    }
    
    # Load strike prices and generate signals
    strikes_df = load_strikes(mapping_file)
    signals_df = generate_detailed_signals(processed, strikes_df, strategy_cfg)

    # Upload to S3
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

### STEP 5: Update Run Cell to Pass Config

**Replace the "Run recommendation pipeline" cell:**

```python
import datetime as dt

TICKERS = {
    'CL=F', 'ES=F', 'GC=F', 'NQ=F', 'RTY=F', 'YM=F', 'NG=F',
    'AUDUSD=X', 'EURJPY=X', 'EURUSD=X', 'GBPJPY=X', 'GBPUSD=X',
    'USDCAD=X', 'USDCHF=X', 'USDJPY=X'
}

# Track run start time
run_start = dt.datetime.now()
run_id = run_start.strftime("%Y%m%dT%H%M%S")

# Run the pipeline WITH strategy config
successful_run = show_interesting_trades(
    run_recommendation_pipeline(
        tickers=TICKERS,
        period="90d",
        interval="1d",
        bucket_name=BUCKET,
        mapping_file=MAPPING_FILE,
        strategy_cfg=strategy_cfg,  # ← Pass strategy config
        region=REGION
    )
)

# Create S3 client and log result
clients = create_s3_clients(region=REGION)
private_s3 = clients["private"]

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
    notes=f'Recommendation run - RSI:{strategy_cfg["rsi"]["mode"]}'
)

print(f"\n✅ Run complete: {run_id}")
print(f"   Status: {successful_run}")
```

---

## Summary of Changes

### Files Modified
1. ✅ "Load from configuration files" - Load strategy.yaml
2. ✅ "Define a function to compute the technical indicators" - Use config values
3. ✅ "Define a function to determine the trading signal" - Use config values
4. ✅ "Define a function to run the Pipeline" - Pass strategy_cfg
5. ✅ "Run recommendation pipeline" - Pass strategy_cfg

### Hardcoded Values Eliminated
- ❌ MACD spans (12, 26, 9) → ✅ `strategy.yaml` values
- ❌ RSI period (14) → ✅ `strategy.yaml` value
- ❌ RSI centerline (50) → ✅ `strategy.yaml` value
- ❌ Trend logic → ✅ Uses `strategy.yaml` trend.type

### Benefits
1. ✅ **Configuration-driven** - Change strategy by editing YAML, not code
2. ✅ **Reusable** - Same config used across notebooks
3. ✅ **Testable** - Easy to backtest different configurations
4. ✅ **Maintainable** - Single source of truth for strategy parameters
5. ✅ **Professional** - Separates strategy logic from implementation

### Testing
After making changes, verify:
1. Config loads correctly with print statements
2. Indicators use config values (check RSI period, MACD params)
3. Signals use config centerline (50)
4. Results match previous runs (if config values match hardcoded ones)

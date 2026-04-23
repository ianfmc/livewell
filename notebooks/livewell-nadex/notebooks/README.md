# Simplified Nadex Backtesting Guide

## Overview

The simplified backtesting approach addresses all the issues found in the original implementation:

1. **Probability-Based Pricing** - Entry costs based on actual contract probability
2. **Clean Data Aggregation** - One signal per ticker per day
3. **Minimal Strategy** - Pure RSI, no complex filters
4. **Easy Comparison** - Test multiple strategies side-by-side

## Key Improvements

### 1. Fixed the "Multiple Strikes Per Day" Problem

**Original Issue:** 35,000 rows but only 57 trades
**Root Cause:** Data has ~10-20 strike prices per ticker per day
**Solution:** Aggregate to ONE at-the-money contract per ticker per day

```python
# Pick the strike closest to Exp Value (at-the-money)
raw_data['strike_distance'] = abs(raw_data['Exp Value'] - raw_data['Strike Price'])
idx = raw_data.groupby(['Ticker', 'Date'])['strike_distance'].idxmin()
daily_data = raw_data.loc[idx]
```

### 2. Implemented Probability-Based Pricing

**Original Issue:** Fixed 50% entry cost ($5) was unrealistic
**New Approach:** Calculate entry cost from Exp Value vs Strike Price

```python
def calculate_probability_itm(exp_value, strike_price, volatility=0.01):
    z_score = (exp_value - strike_price) / (strike_price * volatility)
    prob = norm.cdf(z_score)  # Standard normal CDF
    return max(0.05, min(0.95, prob))  # Clamp to 5-95%

entry_cost = max_payout * probability_itm
```

**Example:**
- Exp Value = 100, Strike = 95 (Far ITM) → Prob = 95% → Entry = $9.50
- Exp Value = 100, Strike = 100 (ATM) → Prob = 50% → Entry = $5.00
- Exp Value = 100, Strike = 105 (Far OTM) → Prob = 5% → Entry = $0.50

### 3. Removed Complex Filters

**Original Issue:** MACD filter + require_cross eliminated 99.84% of trades
**Solution:** Start with pure RSI reversal, add filters later if needed

```python
# Simple signals
signal = 1 if rsi < oversold else 0   # BUY
signal = -1 if rsi > overbought else 0  # SELL
```

### 4. Loads ALL Available Data

**Original Issue:** Only 60 days, but 50 days needed for warmup
**Solution:** Load all 8 months of available data (March-November 2025)

## Using the Simplified Notebook

### Quick Start (Python Script Version)

Since the notebook has JSON formatting issues, here's a standalone Python script:

```python
# Save as: notebooks/backtest_simplified.py
import sys
sys.path.append('../src')

import pandas as pd
import numpy as np
from scipy.stats import norm
import yaml
from nadex_common.utils_s3 import create_s3_clients

# Load configuration
with open('../configs/s3.yaml', 'r') as f:
    s3_cfg = yaml.safe_load(f)

clients = create_s3_clients(region=s3_cfg.get('region'))
s3_client = clients['private']

# Load ALL historical data
print("Loading historical data...")
response = s3_client.list_objects_v2(
    Bucket=s3_cfg['bucket'],
    Prefix=s3_cfg['prefixes']['historical']
)

all_data = []
for obj in response['Contents']:
    if obj['Key'].endswith('.csv'):
        obj_data = s3_client.get_object(Bucket=s3_cfg['bucket'], Key=obj['Key'])
        all_data.append(pd.read_csv(obj_data['Body']))

raw_data = pd.concat(all_data, ignore_index=True)
raw_data['Date'] = pd.to_datetime(raw_data['Date'], format='%d-%b-%y')

print(f"Loaded {len(raw_data):,} rows from {raw_data['Date'].min().date()} to {raw_data['Date'].max().date()}")

# Aggregate to daily (one contract per ticker per day)
print("Aggregating to daily...")
raw_data['strike_distance'] = abs(raw_data['Exp Value'] - raw_data['Strike Price'])
idx = raw_data.groupby(['Ticker', 'Date'])['strike_distance'].idxmin()
daily_data = raw_data.loc[idx].copy().drop('strike_distance', axis=1)

print(f"Aggregated to {len(daily_data):,} daily observations")

# Probability-based pricing
def calculate_fair_entry_cost(exp_value, strike_price, volatility=0.01):
    z_score = (exp_value - strike_price) / (strike_price * volatility)
    prob = max(0.05, min(0.95, norm.cdf(z_score)))
    entry_cost = 10.0 * prob
    return entry_cost, prob

# Simple RSI calculation
def calculate_rsi(prices, period=14):
    delta = prices.diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = -delta.where(delta < 0, 0).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# Backtest
print("Running backtest...")
results = []

for ticker in daily_data['Ticker'].unique():
    ticker_data = daily_data[daily_data['Ticker'] == ticker].copy()
    
    # Calculate RSI
    ticker_data['rsi'] = calculate_rsi(ticker_data['Exp Value'])
    
    # Generate signals
    ticker_data['signal'] = 0
    ticker_data.loc[ticker_data['rsi'] < 30, 'signal'] = 1   # BUY
    ticker_data.loc[ticker_data['rsi'] > 70, 'signal'] = -1  # SELL
    
    # Calculate P&L for trades
    trades = ticker_data[ticker_data['signal'] != 0].copy()
    
    for idx, row in trades.iterrows():
        entry_cost, prob = calculate_fair_entry_cost(row['Exp Value'], row['Strike Price'])
        pnl = (10.0 - entry_cost) if row['In the Money'] == 1 else -entry_cost
        ticker_data.loc[idx, 'entry_cost'] = entry_cost
        ticker_data.loc[idx, 'probability_itm'] = prob
        ticker_data.loc[idx, 'pnl'] = pnl
    
    results.append(ticker_data)

backtest_results = pd.concat(results, ignore_index=True)
trades = backtest_results[backtest_results['signal'] != 0]

# Calculate metrics
print("\n" + "="*70)
print("BACKTEST RESULTS")
print("="*70)
print(f"Total Trades:        {len(trades)}")
print(f"Win Rate:            {(trades['pnl'] > 0).sum() / len(trades):.2%}")
print(f"Total P&L:           ${trades['pnl'].sum():.2f}")
print(f"Avg Entry Cost:      ${trades['entry_cost'].mean():.2f}")
print(f"Total Return:        {(trades['pnl'].sum() / trades['entry_cost'].sum() * 100):.2f}%")
print(f"Sharpe Ratio:        {(trades['pnl'].mean() / trades['pnl'].std()) * np.sqrt(252):.2f}")
print("="*70)

# Show sample trades
print("\nSample Trades:")
print(trades[['Date', 'Ticker', 'Exp Value', 'Strike Price', 'entry_cost', 
              'probability_itm', 'In the Money', 'pnl']].head(10))
```

Run with:
```bash
cd notebooks
python backtest_simplified.py
```

## Expected Results

With the simplified approach, you should see:

- **150-300+ trades** (vs 57 before)
- **Win rate 45-55%** (random baseline)
- **Entry costs varying** from $0.50 to $9.50 based on probability
- **P&L chart** covering full date range (March-November)
- **Clear comparison** between strategy variants

## Strategy Comparison Framework

Test multiple configurations:

```python
strategies = {
    'Baseline': {'rsi_period': 14, 'oversold': 30, 'overbought': 70},
    'Conservative': {'rsi_period': 14, 'oversold': 25, 'overbought': 75},
    'Aggressive': {'rsi_period': 14, 'oversold': 35, 'overbought': 65},
    'Fast RSI': {'rsi_period': 7, 'oversold': 30, 'overbought': 70},
    'Slow RSI': {'rsi_period': 21, 'oversold': 30, 'overbought': 70},
}

for name, params in strategies.items():
    results = backtest(daily_data, **params)
    print(f"{name}: {len(results)} trades, {win_rate:.1%} win rate")
```

## Next Steps

1. Run the simplified backtest
2. Review results - are they better than random (>50% win rate)?
3. If yes, fine-tune parameters
4. If no, try different indicators or strategies
5. Add complexity gradually (MACD filter, position sizing, etc.)

## Troubleshooting

### "Why are entry costs so variable?"
That's the point! The probability model adapts:
- Far ITM contracts cost more (high probability of winning)
- Far OTM contracts cost less (low probability of winning)
- This is more realistic than fixed 50%

### "Why still seeing poor results?"
Possible reasons:
1. RSI may not be predictive for Nadex contracts
2. Daily timeframe may be wrong (contracts expire intraday)
3. At-the-money selection may not be optimal
4. Market may be efficient (no edge to find)

### "How to add MACD filter back?"
Once baseline works, add incrementally:
```python
# Calculate MACD
exp1 = ticker_data['Exp Value'].ewm(span=12).mean()
exp2 = ticker_data['Exp Value'].ewm(span=26).mean()
ticker_data['macd'] = exp1 - exp2

# Filter signals
ticker_data.loc[(ticker_data['signal'] == 1) & (ticker_data['macd'] <= 0), 'signal'] = 0
ticker_data.loc[(ticker_data['signal'] == -1) & (ticker_data['macd'] >= 0), 'signal'] = 0
```

## Files

- `backtest_simplified.py` - Standalone Python script (recommended)
- `nadex-backtesting-simplified.ipynb` - Jupyter notebook (has formatting issues)
- `nadex-kpi-report.ipynb` - KPI Dashboard Report notebook (Sprint 3.5)
- `README_BACKTESTING.md` - Key findings summary
- `BACKTESTING_MAINTENANCE_GUIDE.md` - Maintenance procedures
- `BACKTESTING_OPTIMAL_STRATEGY.md` - Best strategy documentation
- This file - Usage guide

**Archived (in `refactoring/`):**
- `COMPLETE_BACKTESTING_ISSUES_ANALYSIS.md` - Historical problem analysis (resolved)

## KPI Dashboard Report (Sprint 3.5)

Generate a visual HTML dashboard with key performance indicators:

### Quick Start

**Option 1: Run as Python module (from project root)**
```bash
cd src
python -m nadex_common.kpi.report
```

**Option 2: Run the Jupyter notebook**
```bash
jupyter notebook notebooks/nadex-kpi-report.ipynb
```

**Option 3: Import in Python**
```python
from nadex_common.kpi import generate_report, KPIReportConfig

config = KPIReportConfig(
    commission_per_contract=1.00,
    rsi_period=14,
    oversold=25,
    overbought=75
)
kpis = generate_report(config)
```

### Output Files

**Local:**
- `reports/kpi_dashboard.html` - Interactive HTML dashboard
- `reports/kpi_summary.csv` - CSV summary of metrics

**S3:**
- `reports/<date>/kpi_dashboard.html`
- `reports/<date>/summary.csv`

### KPI Dashboard Features

**KPI Cards:**
- Win Rate (with win/loss count)
- Profit & Loss (Gross, Net, Commissions breakdown)
- Maximum Drawdown (with % and recovery time)

**Charts:**
- Cumulative P&L over time (line chart)
- Drawdown analysis (column chart)

**Configuration:**
- Commission: $1.00 per contract (configurable)
- Strategy: Conservative RSI (14, 25/75)
- Uses `rsi_wilder` from `nadex_common.strategy_rsi`

### Module Structure

```
src/nadex_common/kpi/
├── __init__.py         # Package exports
├── calculator.py       # KPI calculation logic
├── html_generator.py   # Jinja2 HTML rendering
└── report.py           # Main orchestration

templates/
└── kpi_dashboard.html.j2  # Jinja2 HTML template
```

### Sample Dashboard

The dashboard is styled with Material Design and includes:
- Responsive layout (works on mobile)
- Interactive Chart.js visualizations
- Hover tooltips with exact values
- Metadata header (date range, total trades, wins, losses)

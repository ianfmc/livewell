# Configuration Files Usage Guide

## Quick Start: What to Do With Your Config Files

You have **two configuration files** to update with your backtesting results:

### 1. **configs/ticker_mappings.yaml** - Update `active` flag for poor performers
### 2. **configs/strategy.yaml** - Update backtesting metrics and parameters

**All configuration centralized in existing config files!** No separate files needed.

---

## Step-by-Step: Using ticker_mappings.yaml

### Step 1: Find Your Bottom 5 Tickers (Section 13 Output)

1. **Scroll to Section 13** in your notebook output
2. **Look for this heading:** "🔻 BOTTOM 5 TICKERS TO EXCLUDE:"
3. **You'll see something like:**
   ```
   1. US Tech 100: $-450.00 (1234 trades)
   2. Germany 40: $-320.00 (987 trades)
   3. Wall Street 30: $-280.00 (856 trades)
   4. US 500: $-190.00 (743 trades)
   5. China 50: $-150.00 (621 trades)
   ```

### Step 2: Map Display Names to Ticker Symbols

The Section 13 output shows display names, but you need the ticker symbols from `ticker_mappings.yaml`:

**Common Mappings:**
- "US Tech 100" or "USTECH" → `NQ=F`
- "US 500" or "US500" → `ES=F`
- "Wall Street 30" or "WALLST30" → `YM=F`
- "Gold" or "GOLD" → `GC=F`
- "Crude Oil" or "CRUDE" → `CL=F`
- "EUR-USD" → `EURUSD=X`
- "GBP-USD" → `GBPUSD=X`

### Step 3: Update ticker_mappings.yaml

**Set `active: false` for poor performers:**

```yaml
tickers:
  NQ=F:
    display_name: USTECH
    description: E-mini NASDAQ 100
    asset_class: Futures
    active: false        # ← Changed from true - Bottom performer in Dec 2025
    
  YM=F:
    display_name: WALLST30
    description: E-mini Dow Jones
    asset_class: Futures
    active: false        # ← Changed from true - Bottom performer in Dec 2025
```

**Add a comment explaining why:**
```yaml
# Updated: 2025-12-01
# Set active: false for bottom 5 performers from backtesting
# Review monthly and re-enable if performance improves
```

---

## Using ticker_mappings.yaml in Your Code

### Example 1: Filter to Active Tickers Only

```python
import yaml

# Load ticker mappings
with open('../configs/ticker_mappings.yaml', 'r') as f:
    config = yaml.safe_load(f)

# Get only active tickers
active_tickers = [
    ticker for ticker, info in config['tickers'].items() 
    if info.get('active', False)
]

print(f"Active tickers: {len(active_tickers)}")
print(active_tickers)

# Filter your data
filtered_data = data[data['Ticker'].isin(active_tickers)]
```

### Example 2: Get Display Names for Active Tickers

```python
import yaml

with open('../configs/ticker_mappings.yaml', 'r') as f:
    config = yaml.safe_load(f)

# Build mapping of ticker symbol → display name (active only)
active_display_names = {
    ticker: info['display_name']
    for ticker, info in config['tickers'].items()
    if info.get('active', False)
}

print("Active tickers for recommendations:")
for ticker, display in active_display_names.items():
    print(f"  {ticker:12} → {display}")
```

### Example 3: Filter Data by Active Flag

```python
import yaml
import pandas as pd

def load_active_tickers():
    """Load list of active tickers from config."""
    with open('../configs/ticker_mappings.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    return [
        ticker for ticker, info in config['tickers'].items()
        if info.get('active', False)
    ]

# Use in your backtesting
active = load_active_tickers()
filtered_data = data[data['Ticker'].isin(active)]

print(f"Filtered from {len(data):,} to {len(filtered_data):,} contracts")
```

### Example 4: Complete Trading Pipeline

```python
import yaml
import pandas as pd

# Load configs
with open('../configs/strategy.yaml', 'r') as f:
    strategy_config = yaml.safe_load(f)

with open('../configs/ticker_mappings.yaml', 'r') as f:
    ticker_config = yaml.safe_load(f)

# Get parameters
rsi_params = strategy_config['rsi']
strike_filter = strategy_config['strike_filter']
active_tickers = [
    t for t, info in ticker_config['tickers'].items() 
    if info.get('active', False)
]

def apply_optimal_strategy(data):
    # 1. Filter to active tickers only
    filtered = data[data['Ticker'].isin(active_tickers)].copy()
    
    # 2. Apply strike filter (±10% from Expected Value)
    if strike_filter['enabled']:
        filtered['distance_pct'] = abs(
            filtered['Strike Price'] - filtered['Exp Value']
        ) / filtered['Exp Value']
        filtered = filtered[filtered['distance_pct'] <= strike_filter['distance_pct']]
    
    # 3. Calculate RSI and generate signals
    # Use rsi_params['period'], rsi_params['oversold'], rsi_params['overbought']
    
    return filtered

# Use it
optimized_data = apply_optimal_strategy(raw_data)
print(f"Data after all filters: {len(optimized_data):,} contracts")
```

---

## Maintenance: When to Update ticker_mappings.yaml

### Monthly Updates (after running full backtest)

**Check Section 13 output:**

1. **Has the bottom 5 list changed?**
   - If 3+ new tickers appear: Update `active` flags
   - If 1-2 changed: Note for quarterly review
   
2. **Should any inactive tickers be reactivated?**
   - Check if previously disabled tickers now perform well
   - If consistent good performance for 1+ month: Set `active: true`

### Update Process

**To Disable a Poor Performer:**
```yaml
GC=F:
  display_name: GOLD
  description: Gold
  asset_class: Futures
  active: false        # Disabled 2025-12-01 - Bottom 5 performer
```

**To Re-enable an Improved Ticker:**
```yaml
GC=F:
  display_name: GOLD
  description: Gold  
  asset_class: Futures
  active: true         # Re-enabled 2026-01-15 - Performance improved
```

### What "Significant Change" Means

**Update ticker_mappings.yaml if:**
- 3 or more new tickers in bottom 5
- A previously disabled ticker shows consistent good performance (1+ month)
- New ticker added to Nadex platform

---

## Integration with Recommendation Notebook

### Current State
Your recommendation notebook should already be using the `active` flag:

```python
# In nadex-recommendation.ipynb
with open('../configs/ticker_mappings.yaml', 'r') as f:
    ticker_config = yaml.safe_load(f)

# Filter to active tickers
active_tickers = [
    t for t, info in ticker_config['tickers'].items()
    if info.get('active', True)  # Defaults to True if not specified
]

# Use only active tickers for recommendations
recommendations = generate_recommendations(data, active_tickers)
```

### Benefits of This Approach

✅ **Single Source of Truth** - One config file for all ticker info  
✅ **Easy to Maintain** - Just flip `active` flag  
✅ **Version Control Friendly** - Clear diffs when tickers change  
✅ **Consistent Across Notebooks** - Backtesting and recommendations use same config  
✅ **Documented** - Comments explain why tickers are disabled  

---

## File Organization

**Simplified structure (no separate ticker_exclusion.yaml needed):**
```
configs/
├── ticker_mappings.yaml          ← Update active flags here
├── strategy.yaml
├── s3.yaml
└── ...

notebooks/
├── nadex-backtesting.ipynb
├── nadex-recommendation.ipynb    ← Already uses active flag
├── optimal_strategy_config.yaml
├── BACKTESTING_MAINTENANCE_GUIDE.md
└── CONFIG_FILES_USAGE_GUIDE.md
```

**Version Control:**
```bash
# After monthly backtest and ticker updates
git add configs/ticker_mappings.yaml
git commit -m "Update active flags after Dec 2025 backtest - disable NQ=F, YM=F"
git push
```

---

## Updating configs/strategy.yaml

### Find Your Metrics from Section 15

**Scroll to the "🏆 WINNER" output:**
- Note metrics for "±10% + Bottom 5 Excluded"

**Update the backtesting section:**

```yaml
backtesting:
  last_run_date: "2025-12-01"              # ← Today's date
  data_period: "March 2025 to November 2025"  # ← From Section 1
  total_days: 180                          # ← From Section 1
  
  metrics:
    total_trades: 13522                    # ← From Section 15
    win_rate: 0.5671                       # ← From Section 15 (56.71%)
    total_pnl: 6945.00                     # ← From Section 15
    total_return_pct: 9.96                 # ← From Section 15
    capital_used: 69736.00                 # ← From Section 15
```

**Also verify RSI parameters match optimal strategy:**

```yaml
rsi:
  period: 14
  oversold: 25       # Conservative strategy
  overbought: 75     # Conservative strategy
```

---

## Quick Reference Card

**Files to Update:**
- `configs/ticker_mappings.yaml` - Set `active: false` for poor performers
- `configs/strategy.yaml` - Update backtesting metrics and parameters

**Update Frequency:**
- **Review:** Monthly
- **Update:** Only if 3+ tickers change or metrics change >5%

**Loading in Python:**
```python
import yaml

# Get active tickers
with open('../configs/ticker_mappings.yaml', 'r') as f:
    ticker_config = yaml.safe_load(f)
active = [t for t, i in ticker_config['tickers'].items() if i.get('active', False)]

# Load strategy params
with open('../configs/strategy.yaml', 'r') as f:
    strategy_config = yaml.safe_load(f)

# Access parameters
rsi_period = strategy_config['rsi']['period']
oversold = strategy_config['rsi']['oversold']
overbought = strategy_config['rsi']['overbought']
strike_filter = strategy_config['strike_filter']['distance_pct']
```

---

## Troubleshooting

**Q: How do I know which ticker symbol matches the display name?**  
A: Check ticker_mappings.yaml - it has both. Match the display_name to find the ticker symbol.

**Q: Should I set active to false or delete the ticker?**  
A: Always set `active: false`. Never delete - you might want to re-enable it later.

**Q: What if Section 13 shows a ticker not in ticker_mappings.yaml?**  
A: Add it to ticker_mappings.yaml with complete metadata before setting active flag.

**Q: Can I have all tickers active: false?**  
A: No, you need at least 5-10 active tickers for diversification and strategy effectiveness.

**Q: Does the recommendation notebook automatically use active flags?**  
A: Yes, if properly configured. Check that it filters by `active: true`.

---

## Example: Complete Monthly Update Workflow

### Step 1: Run Backtest
```
1. Run nadex-backtesting.ipynb Sections 1-16
2. Note bottom 5 tickers from Section 13
3. Note optimal strategy metrics from Section 15
```

### Step 2: Update ticker_mappings.yaml
```yaml
# Example: Disable poor performers
tickers:
  NQ=F:
    active: false  # Disabled 2025-12-01 - Bottom 5
  YM=F:
    active: false  # Disabled 2025-12-01 - Bottom 5
  
# Example: Re-enable improved ticker  
  GC=F:
    active: true   # Re-enabled 2025-12-01 - Performance improved
```

### Step 3: Update configs/strategy.yaml
```yaml
backtesting:
  last_run_date: "2025-12-01"
  metrics:
    total_trades: 13522         # From Section 15
    win_rate: 0.5671           # From Section 15
    total_pnl: 6945.00         # From Section 15
    total_return_pct: 9.96     # From Section 15
```

### Step 4: Commit Changes
```bash
git add configs/ticker_mappings.yaml configs/strategy.yaml
git commit -m "Monthly backtest Dec 2025: disable NQ=F, YM=F; metrics updated"
git push
```

---

## Summary

**Simplified Approach:**
1. ✅ Run monthly backtest (all sections)
2. ✅ Update `active` flags in ticker_mappings.yaml based on Section 13
3. ✅ Update backtesting metrics in strategy.yaml from Section 15
4. ✅ Commit changes to version control
5. ✅ All notebooks automatically use updated configs

**All configuration centralized!** Everything in existing config files:
- ticker_mappings.yaml for ticker active/inactive status
- strategy.yaml for RSI parameters and backtesting results

# Backtesting Maintenance Guide

**Purpose:** Guidelines for maintaining and updating your Nadex trading strategy over time.

## Backtesting Frequency Recommendations

### 1. **Monthly Full Backtest** (Recommended)

**When:** First weekend of each month  
**Why:** Balance between staying current and avoiding over-optimization

**What to Do:**
1. Re-run full notebook (Sections 1-16) with latest data
2. Compare new metrics to previous month
3. Check if bottom 5 tickers have changed
4. Verify ±10% strike filter still optimal
5. Update config files if parameters change significantly

**Triggers for Concern:**
- Win rate drops >5 percentage points
- Total return decreases >20%
- Bottom 5 list changes completely (3+ new tickers)
- Strategy starts losing money consistently

### 2. **Quarterly Deep Review** (Required)

**When:** End of each quarter (March, June, September, December)  
**Why:** Longer periods capture seasonal patterns and market regime changes

**What to Do:**
1. Full backtest with 90+ days of trailing data
2. Compare performance across quarters
3. Check for seasonal patterns
4. Evaluate if excluded tickers should be reconsidered
5. Test alternative RSI parameters (7, 14, 21)
6. Document performance trends

**Questions to Ask:**
- Is the strategy degrading over time?
- Are certain quarters consistently better/worse?
- Should any excluded tickers be given another chance?
- Is market volatility affecting performance?

### 3. **Event-Driven Backtests** (As Needed)

**Triggers:**
- Major market event (crash, regime change)
- Significant change in volatility
- New ticker added to Nadex platform
- Ticker removed from Nadex platform
- Strategy performance anomaly (3+ consecutive losing days)

**What to Do:**
- Run targeted backtest focusing on recent period
- Compare to historical norms
- Adjust position sizing if needed
- Consider temporary strategy pause if extreme conditions

### 4. **Weekly Spot Checks** (Optional but Helpful)

**When:** Every Monday morning  
**Why:** Quick health check without full re-optimization

**What to Monitor:**
- Last week's win rate vs. historical average
- Any excluded tickers showing improvement
- Position sizing working as expected
- No data quality issues

**Don't:**
- Over-react to single-week performance
- Change strategy parameters weekly
- Make decisions based on emotion

## What Changes Require Action

### 🔴 Critical - Act Immediately

1. **Win rate drops below 50%** for 2+ weeks
   - Action: Pause trading, run full backtest, investigate

2. **Excluded ticker performing well consistently**
   - Action: Re-evaluate exclusion after 1 month of good performance

3. **Data quality issues detected**
   - Action: Verify S3 data, check for missing files

4. **Capital drawdown >15%** from peak
   - Action: Review position sizing, consider reducing daily allocation

### 🟡 Important - Review at Next Monthly Backtest

1. **Win rate fluctuates ±3 percentage points**
   - Normal variance, document and monitor

2. **One excluded ticker showing marginal improvement**
   - Note for quarterly review

3. **Strike filter efficiency changes**
   - Compare ±5% vs ±10% at quarterly review

4. **New ticker added to trading universe**
   - Add to analysis in next backtest cycle

### 🟢 Informational - No Immediate Action

1. **Daily P&L variance within historical norms**
   - Expected, no action needed

2. **Single winning/losing day**
   - Normal occurrence, continue monitoring

3. **Minor parameter differences (<1% impact)**
   - Document, consider at quarterly review

## Config File Usage

### Using optimal_strategy_config.yaml

**In Production Code:**
```python
import yaml

# Load strategy config
with open('optimal_strategy_config.yaml', 'r') as f:
    config = yaml.safe_load(f)

# Extract parameters
rsi_period = config['strategy']['parameters']['rsi_period']
oversold = config['strategy']['parameters']['oversold_threshold']
overbought = config['strategy']['parameters']['overbought_threshold']
strike_filter = config['strategy']['parameters']['strike_filter_pct']

# Use in trading logic
if rsi < oversold:
    # Generate BUY signal
    pass
```

**After Monthly Backtest:**
1. Compare new metrics to config file
2. If significant changes (>5% impact), update config
3. Version control changes (git commit with date)
4. Test updated strategy before deploying

### Using ticker_exclusion.yaml

**Populate After Section 13:**
```yaml
ticker_exclusion:
  exclude_tickers:
    - "US Tech 100"      # Replace with actual tickers
    - "Germany 40"       # from Section 13 output
    - "Wall Street 30"
    - "US 500"
    - "China 50"
  last_updated: "2025-12-01"
  next_review: "2026-01-01"
```

**In Production Code:**
```python
# Load exclusions
with open('ticker_exclusion.yaml', 'r') as f:
    exclusions = yaml.safe_load(f)

excluded = exclusions['ticker_exclusion']['exclude_tickers']

# Filter data
filtered_data = data[~data['Ticker'].isin(excluded)]
```

**Monthly Update Process:**
1. Run Section 13 to identify current bottom 5
2. Compare to existing exclusion list
3. If 3+ tickers changed, update YAML file
4. If 1-2 changed, make note for quarterly review
5. Update `last_updated` date

## Performance Tracking

### Metrics to Track Over Time

**Create a tracking spreadsheet/file:**

| Date | Period | Total Trades | Win Rate | Total P&L | Return % | Sharpe | Bottom 5 Tickers |
|------|--------|--------------|----------|-----------|----------|--------|------------------|
| Dec 2025 | Monthly | 13,522 | 56.71% | $6,945 | 9.96% | TBD | List here |
| Jan 2026 | Monthly | ... | ... | ... | ... | ... | ... |

### Trend Analysis

**Plot these over time:**
1. Win rate trend (should stay 54-58% range)
2. Return % trend (should stay positive)
3. Sharpe ratio trend (higher is better)
4. Capital efficiency (return per dollar risked)

### Alert Thresholds

Set up automated alerts if:
- Win rate < 52% for 2 consecutive weeks
- Monthly return < 3%
- 3+ consecutive losing days
- Daily drawdown > 10%

## Strategy Evolution

### When to Consider Major Changes

**Only make significant changes if:**
1. Strategy consistently underperforms for 3+ months
2. Market structure fundamentally changes
3. Nadex platform rules change
4. Multiple quarters show degradation

**Don't change if:**
- Single bad week/month (variance is normal)
- Emotional reaction to losses
- Competitor claims better results
- Impatient with growth rate

### Change Process

1. **Hypothesis:** "I believe X will improve results because Y"
2. **Backtest:** Test hypothesis on historical data
3. **Compare:** New strategy vs current strategy (same period)
4. **Validate:** Out-of-sample testing (forward test)
5. **Document:** Record rationale and results
6. **Deploy:** Only if significant improvement (>10% better metrics)

## Checklist Template

### Monthly Backtest Checklist

- [ ] Re-run Section 1 (load latest data)
- [ ] Verify date range covers last 180+ days
- [ ] Run Sections 2-16 completely
- [ ] Record metrics in tracking spreadsheet
- [ ] Compare to previous month
- [ ] Check if bottom 5 tickers changed
- [ ] Update ticker_exclusion.yaml if needed
- [ ] Review any anomalies or concerns
- [ ] Update optimal_strategy_config.yaml if >5% metric change
- [ ] **Generate KPI Dashboard** (see below)
- [ ] Document any observations/notes

### KPI Dashboard Generation (Sprint 3.5)

After completing the monthly backtest, generate the KPI dashboard:

**Option 1: Python Script**
```bash
cd notebooks
python kpi_report_generator.py
```

**Option 2: Jupyter Notebook**
```bash
jupyter notebook nadex-kpi-report.ipynb
# Run all cells
```

**Output Files:**
- Local: `reports/kpi_dashboard.html` and `reports/kpi_summary.csv`
- S3: `reports/<date>/kpi_dashboard.html` and `reports/<date>/summary.csv`

**Dashboard includes:**
- Win Rate, Gross/Net P&L, Max Drawdown cards
- Cumulative P&L line chart
- Drawdown column chart
- Metadata (date range, total trades, wins/losses)

**Configuration:**
- Commission: $1.00 per contract (configurable in script)
- Uses `rsi_wilder` from `nadex_common.strategy_rsi` for consistency

### Quarterly Review Checklist

- [ ] Full monthly backtest steps above
- [ ] Compare last 3 months performance
- [ ] Check for seasonal patterns
- [ ] Review excluded tickers performance
- [ ] Test alternative RSI periods (7, 14, 21)
- [ ] Compare ±5% vs ±10% strike filter
- [ ] Evaluate position sizing effectiveness
- [ ] Check capital growth trajectory
- [ ] Update documentation
- [ ] Plan any strategy adjustments

## Best Practices

### Do's ✅

- ✅ Maintain consistent backtesting schedule
- ✅ Document all changes and rationale
- ✅ Use version control for config files
- ✅ Track metrics over time
- ✅ Be patient with strategy evolution
- ✅ Focus on process, not single outcomes
- ✅ Keep detailed notes on market conditions

### Don'ts ❌

- ❌ Over-optimize based on recent performance
- ❌ Change parameters after every losing day
- ❌ Ignore data quality issues
- ❌ Skip scheduled backtests
- ❌ Make emotional decisions
- ❌ Deploy untested changes
- ❌ Forget to version control configs

## Summary

**Minimum Viable Maintenance:**
- Monthly backtest with config updates
- Quarterly deep review
- Monitor weekly performance (no changes)

**Optimal Maintenance:**
- All of above, plus
- Detailed performance tracking
- Event-driven backtests when needed
- Continuous documentation

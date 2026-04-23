# Nadex Backtesting Analysis - Key Findings

## Executive Summary

This document summarizes the key findings from the V4 backtesting analysis with multiple strikes per signal.

## Multi-Strike Strategy Results (V4)

### Configuration
- **RSI Period**: 14
- **Oversold Threshold**: 30
- **Overbought Threshold**: 70
- **Pricing Model**: 3-tier ($7.50 ITM, $5.00 ATM, $2.50 OTM)

### Performance Metrics
- **Total Trades**: 37,708 (vs 690 in V3 = 54.6x multiplier)
- **Win Rate**: 53.40%
- **Total P&L**: $9,962.50
- **Average Win**: $4.20
- **Average Loss**: -$4.24
- **Total Return**: 5.21%
- **Sharpe Ratio**: 0.96

### Entry Cost Distribution
- **$2.50 (OTM)**: 5,311 trades (14.1%)
- **$5.00 (ATM)**: 25,947 trades (68.8%)
- **$7.50 (ITM)**: 6,450 trades (17.1%)
- **Average Entry Cost**: $5.08

## Strategy Comparison

Best performing strategies by metric:
- **Best Total P&L**: Aggressive (14, 35/65) - $13,290
- **Best Win Rate**: Conservative (14, 25/75) - 54%
- **Best Total Return**: Conservative (14, 25/75) - 6.25%
- **Best Sharpe Ratio**: Conservative (14, 25/75) - 1.16

### Conservative Strategy (RECOMMENDED)
- **Total Trades**: 20,602
- **Win Rate**: 54%
- **Total P&L**: $6,582.50
- **Total Return**: 6.25%
- **Sharpe Ratio**: 1.16

## Ticker Filtering Analysis

### Purpose
To determine if filtering out underperforming tickers improves returns.

### Key Questions
1. Which tickers consistently underperform?
2. What % of total P&L comes from top performers?
3. Does filtering bottom 25%/50% improve risk-adjusted returns?
4. What is the trade-off between P&L and trade count?

## Next Steps

1. **Complete Section 12**: Add ticker filtering backtest comparison
2. **Implement Filtering**: Test removing bottom 25% and 50% of tickers
3. **Compare Metrics**: Evaluate P&L, Sharpe ratio, and trade count changes
4. **Document Findings**: Update this file with filtering recommendations

## Technical Notes

### Data Coverage
- **Date Range**: March 3, 2025 to November 25, 2025
- **Total Files**: 190
- **Total Rows**: 157,498
- **Unique Tickers**: 19
- **Unique Dates**: 190

### Issues Addressed
- ✅ Multi-strike implementation working correctly
- ✅ 3-tier pricing model applied properly
- ✅ Strategy comparison framework functional
- ⏳ Ticker filtering analysis in progress

## Recommendations

Based on current analysis:
1. **Use Conservative Strategy**: RSI(14) with 25/75 thresholds provides best risk-adjusted returns
2. **Monitor Individual Tickers**: Some tickers show significantly better performance
3. **Consider Filtering**: Awaiting Section 12 analysis to determine optimal ticker filtering approach
4. **Generate KPI Dashboard**: Use `kpi_report_generator.py` or `nadex-kpi-report.ipynb` to visualize performance

## KPI Dashboard (Sprint 3.5)

A visual HTML dashboard for key performance indicators is available:

**Run:**
```bash
cd notebooks
python kpi_report_generator.py
```

**Output:**
- `reports/kpi_dashboard.html` - Interactive dashboard with:
  - Win Rate card
  - Profit & Loss card (Gross/Net/Commissions)
  - Max Drawdown card
  - Cumulative P&L chart
  - Drawdown column chart
- `reports/kpi_summary.csv` - CSV metrics export
- S3 upload: `reports/<date>/kpi_dashboard.html` and `reports/<date>/summary.csv`

**Configuration:**
- Commission: $1.00 per contract
- Uses `rsi_wilder` from `nadex_common.strategy_rsi`
- Material Design styling with responsive layout

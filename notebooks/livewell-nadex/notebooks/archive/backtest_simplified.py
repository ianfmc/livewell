#!/usr/bin/env python3
"""
Simplified Nadex Backtesting Script

Addresses all issues from the original implementation:
1. Probability-based pricing (not fixed 50%)
2. One signal per ticker per day (not per strike)
3. Minimal RSI strategy (no MACD filter initially)
4. Loads all available data (not just 60 days)
5. Easy strategy comparison
"""

import sys
sys.path.append('../src')

import pandas as pd
import numpy as np
from scipy.stats import norm
import yaml
from typing import Dict, Tuple
from nadex_common.utils_s3 import create_s3_clients

# ============================================================================
# CONFIGURATION
# ============================================================================

with open('../configs/s3.yaml', 'r') as f:
    s3_cfg = yaml.safe_load(f)

clients = create_s3_clients(region=s3_cfg.get('region'))
s3_client = clients['private']
BUCKET = s3_cfg['bucket']
PREFIX = s3_cfg['prefixes']['historical']

# ============================================================================
# DATA LOADING
# ============================================================================

def load_all_historical_data():
    """Load all available historical data from S3."""
    print("Loading historical data from S3...")
    
    response = s3_client.list_objects_v2(Bucket=BUCKET, Prefix=PREFIX)
    if 'Contents' not in response:
        print("No historical files found!")
        return pd.DataFrame()
    
    all_data = []
    file_count = 0
    
    for obj in response['Contents']:
        key = obj['Key']
        if not key.endswith('.csv'):
            continue
        try:
            obj_data = s3_client.get_object(Bucket=BUCKET, Key=key)
            df = pd.read_csv(obj_data['Body'])
            all_data.append(df)
            file_count += 1
        except Exception as e:
            print(f"Warning: Could not load {key}: {e}")
    
    if not all_data:
        return pd.DataFrame()
    
    combined = pd.concat(all_data, ignore_index=True)
    combined['Date'] = pd.to_datetime(combined['Date'], format='%d-%b-%y')
    
    print(f"✓ Loaded {file_count} files, {len(combined):,} total rows")
    print(f"✓ Date range: {combined['Date'].min().date()} to {combined['Date'].max().date()}")
    print(f"✓ Unique tickers: {combined['Ticker'].nunique()}")
    print(f"✓ Unique dates: {combined['Date'].nunique()}")
    
    return combined.sort_values('Date').reset_index(drop=True)


def aggregate_to_daily(raw_data: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate multiple strikes per day to single daily observation.
    Picks the at-the-money contract (closest to Exp Value).
    """
    print("\nAggregating to daily (one contract per ticker per day)...")
    
    raw_data['strike_distance'] = abs(raw_data['Exp Value'] - raw_data['Strike Price'])
    idx = raw_data.groupby(['Ticker', 'Date'])['strike_distance'].idxmin()
    daily_data = raw_data.loc[idx].copy().drop('strike_distance', axis=1)
    
    print(f"✓ Aggregated to {len(daily_data):,} daily observations")
    print(f"✓ Average {len(daily_data) / daily_data['Ticker'].nunique():.0f} days per ticker")
    
    return daily_data.sort_values(['Ticker', 'Date']).reset_index(drop=True)


# ============================================================================
# PROBABILITY-BASED PRICING MODEL
# ============================================================================

def calculate_probability_itm(exp_value: float, strike_price: float, 
                             volatility: float = 0.01) -> float:
    """
    Estimate probability contract will be In The Money using Black-Scholes logic.
    
    Parameters:
    -----------
    exp_value : float
        Expected value at expiration (current price)
    strike_price : float
        Strike price of the contract
    volatility : float
        Assumed daily volatility (default 1%)
    
    Returns:
    --------
    float : Probability between 0.05 and 0.95
    """
    if volatility <= 0:
        volatility = 0.01
    
    # Calculate z-score (standard deviations from strike)
    z_score = (exp_value - strike_price) / (strike_price * volatility)
    
    # Use normal CDF
    prob = norm.cdf(z_score)
    
    # Clamp to reasonable range
    return max(0.05, min(0.95, prob))


def calculate_fair_entry_cost(exp_value: float, strike_price: float,
                             max_payout: float = 10.0,
                             volatility: float = 0.01) -> Tuple[float, float]:
    """
    Calculate fair entry cost based on probability model.
    
    Returns:
    --------
    Tuple[float, float] : (entry_cost, probability_itm)
    """
    prob_itm = calculate_probability_itm(exp_value, strike_price, volatility)
    entry_cost = max_payout * prob_itm
    return entry_cost, prob_itm


# ============================================================================
# RSI STRATEGY
# ============================================================================

def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    """Calculate RSI indicator."""
    delta = prices.diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = -delta.where(delta < 0, 0).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def generate_rsi_signals(data: pd.DataFrame, period: int = 14,
                        oversold: float = 30, overbought: float = 70) -> pd.DataFrame:
    """Generate simple RSI reversal signals."""
    result = data.copy()
    result['rsi'] = calculate_rsi(result['Exp Value'], period)
    result['signal'] = 0
    result.loc[result['rsi'] < oversold, 'signal'] = 1   # BUY
    result.loc[result['rsi'] > overbought, 'signal'] = -1  # SELL
    return result


# ============================================================================
# BACKTESTING ENGINE
# ============================================================================

def backtest_strategy(data: pd.DataFrame, 
                     rsi_period: int = 14,
                     oversold: float = 30,
                     overbought: float = 70,
                     volatility: float = 0.01) -> pd.DataFrame:
    """
    Backtest simple RSI strategy with probability-based pricing.
    """
    all_results = []
    
    for ticker in data['Ticker'].unique():
        ticker_data = data[data['Ticker'] == ticker].copy()
        
        # Generate signals
        ticker_data = generate_rsi_signals(ticker_data, rsi_period, oversold, overbought)
        
        # Calculate P&L for trades
        trades = ticker_data[ticker_data['signal'] != 0].copy()
        
        for idx in trades.index:
            row = ticker_data.loc[idx]
            entry_cost, prob = calculate_fair_entry_cost(
                row['Exp Value'], row['Strike Price'], volatility=volatility
            )
            pnl = (10.0 - entry_cost) if row['In the Money'] == 1 else -entry_cost
            
            ticker_data.loc[idx, 'entry_cost'] = entry_cost
            ticker_data.loc[idx, 'probability_itm'] = prob
            ticker_data.loc[idx, 'pnl'] = pnl
        
        all_results.append(ticker_data)
    
    return pd.concat(all_results, ignore_index=True)


def calculate_metrics(backtest_results: pd.DataFrame) -> Dict:
    """Calculate performance metrics."""
    trades = backtest_results[backtest_results['signal'] != 0].copy()
    
    if len(trades) == 0:
        return {'total_trades': 0, 'win_rate': 0, 'total_pnl': 0}
    
    wins = trades[trades['pnl'] > 0]
    losses = trades[trades['pnl'] < 0]
    
    return {
        'total_trades': len(trades),
        'winning_trades': len(wins),
        'losing_trades': len(losses),
        'win_rate': len(wins) / len(trades),
        'total_pnl': trades['pnl'].sum(),
        'avg_win': wins['pnl'].mean() if len(wins) > 0 else 0,
        'avg_loss': losses['pnl'].mean() if len(losses) > 0 else 0,
        'avg_entry_cost': trades['entry_cost'].mean(),
        'total_capital': trades['entry_cost'].sum(),
        'total_return_pct': (trades['pnl'].sum() / trades['entry_cost'].sum() * 100) if trades['entry_cost'].sum() > 0 else 0,
        'sharpe_ratio': (trades['pnl'].mean() / trades['pnl'].std()) * np.sqrt(252) if len(trades) > 1 and trades['pnl'].std() > 0 else 0,
    }


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    print("="*70)
    print("SIMPLIFIED NADEX BACKTESTING")
    print("="*70)
    
    # Load and prepare data
    raw_data = load_all_historical_data()
    if raw_data.empty:
        print("No data loaded. Exiting.")
        return
    
    daily_data = aggregate_to_daily(raw_data)
    
    # Run baseline strategy
    print("\n" + "="*70)
    print("RUNNING BASELINE STRATEGY")
    print("Configuration: RSI(14), Oversold=30, Overbought=70")
    print("="*70)
    
    baseline_results = backtest_strategy(daily_data, rsi_period=14, oversold=30, overbought=70)
    baseline_metrics = calculate_metrics(baseline_results)
    
    print("\n📊 BASELINE RESULTS")
    print("="*70)
    print(f"Total Trades:           {baseline_metrics['total_trades']}")
    print(f"Winning Trades:         {baseline_metrics['winning_trades']}")
    print(f"Losing Trades:          {baseline_metrics['losing_trades']}")
    print(f"Win Rate:               {baseline_metrics['win_rate']:.2%}")
    print(f"\nTotal P&L:              ${baseline_metrics['total_pnl']:.2f}")
    print(f"Average Win:            ${baseline_metrics['avg_win']:.2f}")
    print(f"Average Loss:           ${baseline_metrics['avg_loss']:.2f}")
    print(f"\nAvg Entry Cost:         ${baseline_metrics['avg_entry_cost']:.2f}")
    print(f"Total Capital Used:     ${baseline_metrics['total_capital']:.2f}")
    print(f"Total Return:           {baseline_metrics['total_return_pct']:.2f}%")
    print(f"Sharpe Ratio:           {baseline_metrics['sharpe_ratio']:.2f}")
    print("="*70)
    
    # Show sample trades
    trades = baseline_results[baseline_results['signal'] != 0][
        ['Date', 'Ticker', 'Exp Value', 'Strike Price', 'rsi', 'entry_cost', 
         'probability_itm', 'In the Money', 'pnl']
    ].head(15)
    
    print("\nSample Trades:")
    print(trades.to_string(index=False))
    
    # Strategy comparison
    print("\n" + "="*70)
    print("STRATEGY COMPARISON")
    print("="*70)
    
    strategies = {
        'Baseline (14, 30/70)': {'rsi_period': 14, 'oversold': 30, 'overbought': 70},
        'Conservative (14, 25/75)': {'rsi_period': 14, 'oversold': 25, 'overbought': 75},
        'Aggressive (14, 35/65)': {'rsi_period': 14, 'oversold': 35, 'overbought': 65},
        'Fast RSI (7, 30/70)': {'rsi_period': 7, 'oversold': 30, 'overbought': 70},
        'Slow RSI (21, 30/70)': {'rsi_period': 21, 'oversold': 30, 'overbought': 70},
    }
    
    comparison_results = []
    for name, params in strategies.items():
        print(f"Testing: {name}...")
        results = backtest_strategy(daily_data, **params)
        metrics = calculate_metrics(results)
        metrics['strategy'] = name
        comparison_results.append(metrics)
    
    comparison_df = pd.DataFrame(comparison_results)
    comparison_df = comparison_df[['strategy', 'total_trades', 'win_rate', 'total_pnl', 
                                   'avg_entry_cost', 'total_return_pct', 'sharpe_ratio']]
    
    print("\n📊 STRATEGY COMPARISON")
    print("="*70)
    print(comparison_df.to_string(index=False))
    
    print("\n🏆 Best by Total P&L:")
    best_pnl = comparison_df.loc[comparison_df['total_pnl'].idxmax()]
    print(f"  {best_pnl['strategy']}: ${best_pnl['total_pnl']:.2f}")
    
    print("\n🏆 Best by Win Rate:")
    best_wr = comparison_df.loc[comparison_df['win_rate'].idxmax()]
    print(f"  {best_wr['strategy']}: {best_wr['win_rate']:.2%}")
    
    print("\n🏆 Best by Sharpe Ratio:")
    best_sharpe = comparison_df.loc[comparison_df['sharpe_ratio'].idxmax()]
    print(f"  {best_sharpe['strategy']}: {best_sharpe['sharpe_ratio']:.2f}")
    
    print("\n" + "="*70)
    print("Analysis complete! See README_SIMPLIFIED.md for next steps.")
    print("="*70)


if __name__ == '__main__':
    main()

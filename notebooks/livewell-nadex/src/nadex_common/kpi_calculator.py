# kpi_calculator.py
"""
KPI Calculation Module

Provides functions for calculating trading KPIs from backtest results.
"""

from typing import Dict, Any
import pandas as pd


def calculate_tier_entry_cost(exp_value: float, strike_price: float) -> float:
    """
    Calculate entry cost using 3-tier pricing model.
    
    Parameters
    ----------
    exp_value : float
        Expected value (underlying price)
    strike_price : float
        Strike price of the contract
        
    Returns
    -------
    float
        Entry cost: $7.50 (ITM), $5.00 (ATM), $2.50 (OTM)
    """
    threshold = strike_price * 0.01
    diff = exp_value - strike_price
    
    if diff > threshold:
        return 7.50  # Far ITM
    elif diff < -threshold:
        return 2.50  # Far OTM
    else:
        return 5.00  # ATM


def calculate_kpis(trades: pd.DataFrame, commission_per_contract: float = 1.00) -> Dict[str, Any]:
    """
    Calculate all KPIs from trades DataFrame.
    
    Parameters
    ----------
    trades : pd.DataFrame
        DataFrame with columns: Date, pnl, entry_cost, In the Money
    commission_per_contract : float, default=1.00
        Commission charged per contract
        
    Returns
    -------
    dict
        Dictionary containing:
        - win_rate: float (0.0 to 1.0)
        - total_trades: int
        - wins: int
        - losses: int
        - gross_pnl: float
        - commissions: float
        - net_pnl: float
        - max_drawdown: float
        - max_drawdown_pct: float
        - recovery_days: int
        - date_start: datetime
        - date_end: datetime
        - daily_data: DataFrame with cumulative P&L and drawdown
    """
    if trades.empty:
        return {
            'win_rate': 0.0,
            'total_trades': 0,
            'wins': 0,
            'losses': 0,
            'gross_pnl': 0.0,
            'commissions': 0.0,
            'net_pnl': 0.0,
            'max_drawdown': 0.0,
            'max_drawdown_pct': 0.0,
            'recovery_days': 0,
            'date_start': None,
            'date_end': None,
            'daily_data': pd.DataFrame()
        }
    
    # Basic stats
    wins = trades[trades['pnl'] > 0]
    losses = trades[trades['pnl'] <= 0]
    total_trades = len(trades)
    win_count = len(wins)
    loss_count = len(losses)
    win_rate = win_count / total_trades if total_trades > 0 else 0
    
    # P&L calculations
    gross_pnl = trades['pnl'].sum()
    commissions = total_trades * commission_per_contract
    net_pnl = gross_pnl - commissions
    
    # Date range
    date_start = trades['Date'].min()
    date_end = trades['Date'].max()
    
    # Daily aggregation for charts
    trades_by_date = trades.groupby('Date').agg({
        'pnl': 'sum',
        'entry_cost': 'sum'
    }).reset_index()
    trades_by_date = trades_by_date.sort_values('Date')
    trades_by_date['cumulative_pnl'] = trades_by_date['pnl'].cumsum()
    
    # Calculate drawdown
    trades_by_date['running_max'] = trades_by_date['cumulative_pnl'].cummax()
    trades_by_date['drawdown'] = trades_by_date['cumulative_pnl'] - trades_by_date['running_max']
    
    max_drawdown = trades_by_date['drawdown'].min()
    running_max = trades_by_date['running_max'].max()
    max_drawdown_pct = (max_drawdown / running_max * 100) if running_max > 0 else 0
    
    # Recovery time (days from max drawdown to recovery)
    max_dd_idx = trades_by_date['drawdown'].idxmin()
    recovery_days = 0
    if max_dd_idx is not None and not pd.isna(max_dd_idx):
        post_dd = trades_by_date.loc[max_dd_idx:]
        recovered = post_dd[post_dd['drawdown'] >= 0]
        if len(recovered) > 0:
            recovery_days = (recovered.iloc[0]['Date'] - trades_by_date.loc[max_dd_idx, 'Date']).days
    
    return {
        'win_rate': win_rate,
        'total_trades': total_trades,
        'wins': win_count,
        'losses': loss_count,
        'gross_pnl': gross_pnl,
        'commissions': commissions,
        'net_pnl': net_pnl,
        'max_drawdown': max_drawdown,
        'max_drawdown_pct': max_drawdown_pct,
        'recovery_days': recovery_days,
        'date_start': date_start,
        'date_end': date_end,
        'daily_data': trades_by_date
    }

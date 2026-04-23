# capital.py
"""
Capital Management Module

Implements fixed budget funding with daily constraints for backtesting.
Tracks capital allocation, risk limits, and provides skip reasons for unfunded trades.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum
import pandas as pd
import numpy as np


class SkipReason(Enum):
    """Reasons why a trade was not funded."""
    FUNDED = "funded"
    EXCEEDS_DAILY_BUDGET = "exceeds_daily_budget"
    EXCEEDS_DAILY_RISK = "exceeds_daily_risk"
    EXCEEDS_TRADE_LIMIT = "exceeds_trade_limit"
    EXCEEDS_MAX_LOSS = "exceeds_max_loss"
    INSUFFICIENT_SCORE = "insufficient_score"
    NO_CAPITAL = "no_capital"


@dataclass
class CapitalConfig:
    """Configuration for capital constraints."""
    daily_budget: float = 50.0           # Max $ to allocate per day
    daily_risk_budget: float = 25.0      # Max $ risk exposure per day
    max_trades_per_day: int = 5          # Max trades per day
    max_loss_per_trade: float = 7.50     # Max loss on any single trade
    rebalance_frequency: str = "daily"   # daily | weekly
    rebalance_day: int = 0               # 0 = Monday (for weekly)
    
    @classmethod
    def from_dict(cls, config: dict) -> 'CapitalConfig':
        """Create CapitalConfig from dictionary."""
        return cls(
            daily_budget=float(config.get('daily_budget', 50.0)),
            daily_risk_budget=float(config.get('daily_risk_budget', 25.0)),
            max_trades_per_day=int(config.get('max_trades_per_day', 5)),
            max_loss_per_trade=float(config.get('max_loss_per_trade', 7.50)),
            rebalance_frequency=config.get('rebalance_frequency', 'daily'),
            rebalance_day=int(config.get('rebalance_day', 0))
        )


@dataclass
class DailyCapitalState:
    """Track capital allocation state for a single day."""
    date: pd.Timestamp
    budget_remaining: float
    risk_remaining: float
    trades_remaining: int
    trades_funded: int = 0
    trades_skipped: int = 0
    capital_used: float = 0.0
    risk_used: float = 0.0
    
    def can_fund(self, entry_cost: float, risk_amount: float) -> Tuple[bool, SkipReason]:
        """
        Check if a trade can be funded given current state.
        
        Parameters
        ----------
        entry_cost : float
            Entry cost for the trade
        risk_amount : float
            Risk amount (max loss) for the trade
            
        Returns
        -------
        tuple of (can_fund, reason)
        """
        if self.trades_remaining <= 0:
            return False, SkipReason.EXCEEDS_TRADE_LIMIT
        
        if entry_cost > self.budget_remaining:
            return False, SkipReason.EXCEEDS_DAILY_BUDGET
        
        if risk_amount > self.risk_remaining:
            return False, SkipReason.EXCEEDS_DAILY_RISK
        
        return True, SkipReason.FUNDED
    
    def fund_trade(self, entry_cost: float, risk_amount: float) -> None:
        """Update state after funding a trade."""
        self.budget_remaining -= entry_cost
        self.risk_remaining -= risk_amount
        self.trades_remaining -= 1
        self.trades_funded += 1
        self.capital_used += entry_cost
        self.risk_used += risk_amount
    
    def skip_trade(self) -> None:
        """Update state after skipping a trade."""
        self.trades_skipped += 1


@dataclass
class FundingResult:
    """Result of applying capital constraints to trades."""
    funded_trades: pd.DataFrame
    skipped_trades: pd.DataFrame
    daily_states: List[DailyCapitalState]
    summary: Dict[str, any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Calculate summary statistics."""
        if not self.daily_states:
            return
            
        self.summary = {
            'total_days': len(self.daily_states),
            'total_funded': sum(s.trades_funded for s in self.daily_states),
            'total_skipped': sum(s.trades_skipped for s in self.daily_states),
            'total_capital_used': sum(s.capital_used for s in self.daily_states),
            'total_risk_used': sum(s.risk_used for s in self.daily_states),
            'avg_trades_per_day': np.mean([s.trades_funded for s in self.daily_states]),
            'avg_capital_per_day': np.mean([s.capital_used for s in self.daily_states]),
            'funding_rate': (
                sum(s.trades_funded for s in self.daily_states) / 
                max(1, sum(s.trades_funded + s.trades_skipped for s in self.daily_states))
            )
        }


def calculate_risk_amount(entry_cost: float, max_loss_per_trade: float) -> float:
    """
    Calculate risk amount for a trade.
    
    Risk is the maximum possible loss, which is the entry cost.
    
    Parameters
    ----------
    entry_cost : float
        Entry cost for the trade
    max_loss_per_trade : float
        Maximum allowed loss per trade (for filtering)
        
    Returns
    -------
    float
        Risk amount (capped at max_loss_per_trade)
    """
    # For binary options, max loss = entry cost
    return min(entry_cost, max_loss_per_trade)


def apply_capital_constraints(
    trades: pd.DataFrame,
    config: CapitalConfig
) -> FundingResult:
    """
    Apply capital constraints to a set of trades.
    
    Trades should be pre-sorted by priority (score descending).
    Funding is applied deterministically in order.
    
    Parameters
    ----------
    trades : pd.DataFrame
        Trades to fund. Must have columns: Date, entry_cost
        Should be sorted by priority (Date asc, score desc)
    config : CapitalConfig
        Capital constraint configuration
        
    Returns
    -------
    FundingResult
        Contains funded trades, skipped trades, and daily states
    """
    if trades.empty:
        return FundingResult(
            funded_trades=pd.DataFrame(),
            skipped_trades=pd.DataFrame(),
            daily_states=[]
        )
    
    df = trades.copy()
    
    # Ensure required columns
    if 'entry_cost' not in df.columns:
        raise ValueError("DataFrame must have 'entry_cost' column")
    
    if 'Date' not in df.columns:
        raise ValueError("DataFrame must have 'Date' column")
    
    # Initialize tracking
    funded_list = []
    skipped_list = []
    daily_states = []
    
    # Process by date
    current_state = None
    current_week = None
    
    for date, day_trades in df.groupby('Date', sort=True):
        # Determine if we need to reset budget
        week_number = date.isocalendar()[1]
        should_reset = (
            config.rebalance_frequency == 'daily' or
            current_state is None or
            (config.rebalance_frequency == 'weekly' and 
             (week_number != current_week or date.dayofweek == config.rebalance_day))
        )
        
        if should_reset:
            current_state = DailyCapitalState(
                date=date,
                budget_remaining=config.daily_budget,
                risk_remaining=config.daily_risk_budget,
                trades_remaining=config.max_trades_per_day
            )
            current_week = week_number
        else:
            # Carry forward remaining budget but reset for new day
            current_state = DailyCapitalState(
                date=date,
                budget_remaining=config.daily_budget,
                risk_remaining=config.daily_risk_budget,
                trades_remaining=config.max_trades_per_day
            )
        
        # Sort day trades by score if available (should already be sorted)
        if 'score' in day_trades.columns:
            day_trades = day_trades.sort_values('score', ascending=False)
        
        # Process each trade
        for idx, trade in day_trades.iterrows():
            entry_cost = trade['entry_cost']
            risk_amount = calculate_risk_amount(entry_cost, config.max_loss_per_trade)
            
            # Check if trade exceeds max loss constraint
            if entry_cost > config.max_loss_per_trade:
                trade_copy = trade.copy()
                trade_copy['funded'] = False
                trade_copy['skip_reason'] = SkipReason.EXCEEDS_MAX_LOSS.value
                skipped_list.append(trade_copy)
                current_state.skip_trade()
                continue
            
            # Check if trade can be funded
            can_fund, reason = current_state.can_fund(entry_cost, risk_amount)
            
            if can_fund:
                current_state.fund_trade(entry_cost, risk_amount)
                trade_copy = trade.copy()
                trade_copy['funded'] = True
                trade_copy['skip_reason'] = SkipReason.FUNDED.value
                funded_list.append(trade_copy)
            else:
                trade_copy = trade.copy()
                trade_copy['funded'] = False
                trade_copy['skip_reason'] = reason.value
                skipped_list.append(trade_copy)
                current_state.skip_trade()
        
        daily_states.append(current_state)
    
    # Create result DataFrames
    funded_df = pd.DataFrame(funded_list) if funded_list else pd.DataFrame()
    skipped_df = pd.DataFrame(skipped_list) if skipped_list else pd.DataFrame()
    
    return FundingResult(
        funded_trades=funded_df,
        skipped_trades=skipped_df,
        daily_states=daily_states
    )


def fund_trades(
    trades: pd.DataFrame,
    config: Optional[CapitalConfig] = None,
    daily_budget: float = 50.0,
    daily_risk_budget: float = 25.0,
    max_trades_per_day: int = 5,
    max_loss_per_trade: float = 7.50
) -> Tuple[pd.DataFrame, pd.DataFrame, Dict]:
    """
    Apply capital constraints to trades.
    
    Convenience function that creates config and applies constraints.
    
    Parameters
    ----------
    trades : pd.DataFrame
        Trades to fund (must have Date, entry_cost)
    config : CapitalConfig, optional
        Capital configuration (overrides other params if provided)
    daily_budget : float
        Max $ to allocate per day
    daily_risk_budget : float
        Max $ risk per day
    max_trades_per_day : int
        Max trades per day
    max_loss_per_trade : float
        Max loss per trade
        
    Returns
    -------
    tuple of (funded_trades, skipped_trades, summary_dict)
    """
    if config is None:
        config = CapitalConfig(
            daily_budget=daily_budget,
            daily_risk_budget=daily_risk_budget,
            max_trades_per_day=max_trades_per_day,
            max_loss_per_trade=max_loss_per_trade
        )
    
    result = apply_capital_constraints(trades, config)
    
    return result.funded_trades, result.skipped_trades, result.summary


def get_skip_reason_summary(skipped_trades: pd.DataFrame) -> Dict[str, int]:
    """
    Summarize skip reasons from skipped trades DataFrame.
    
    Parameters
    ----------
    skipped_trades : pd.DataFrame
        DataFrame with 'skip_reason' column
        
    Returns
    -------
    dict
        Count of each skip reason
    """
    if skipped_trades.empty or 'skip_reason' not in skipped_trades.columns:
        return {}
    
    return skipped_trades['skip_reason'].value_counts().to_dict()


def verify_funding_determinism(
    trades: pd.DataFrame,
    config: CapitalConfig,
    n_runs: int = 3
) -> bool:
    """
    Verify that funding is deterministic across multiple runs.
    
    Parameters
    ----------
    trades : pd.DataFrame
        Input trades
    config : CapitalConfig
        Capital configuration
    n_runs : int
        Number of runs to verify
        
    Returns
    -------
    bool
        True if all runs produce identical results
    """
    results = []
    
    for _ in range(n_runs):
        funded, skipped, _ = fund_trades(trades.copy(), config)
        # Create hashable representation
        if not funded.empty:
            key_cols = [c for c in ['Date', 'Ticker', 'entry_cost'] if c in funded.columns]
            if key_cols:
                result_hash = pd.util.hash_pandas_object(funded[key_cols]).sum()
            else:
                result_hash = len(funded)
        else:
            result_hash = 0
        results.append(result_hash)
    
    return len(set(results)) == 1


def simulate_capital_growth(
    trades: pd.DataFrame,
    config: CapitalConfig,
    starting_capital: float = 500.0
) -> pd.DataFrame:
    """
    Simulate capital growth over time with constraints.
    
    Parameters
    ----------
    trades : pd.DataFrame
        Trades with Date, entry_cost, pnl columns
    config : CapitalConfig
        Capital configuration
    starting_capital : float
        Initial capital
        
    Returns
    -------
    pd.DataFrame
        Daily capital tracking with columns:
        Date, starting_capital, trades_executed, daily_pnl, ending_capital
    """
    if trades.empty:
        return pd.DataFrame()
    
    # Apply capital constraints
    funded, skipped, _ = fund_trades(trades, config)
    
    if funded.empty:
        return pd.DataFrame()
    
    # Track capital by date
    capital = starting_capital
    daily_results = []
    
    for date, day_trades in funded.groupby('Date', sort=True):
        daily_pnl = day_trades['pnl'].sum() if 'pnl' in day_trades.columns else 0
        trades_executed = len(day_trades)
        capital_used = day_trades['entry_cost'].sum()
        
        starting_cap = capital
        capital += daily_pnl
        
        daily_results.append({
            'Date': date,
            'starting_capital': starting_cap,
            'trades_executed': trades_executed,
            'capital_used': capital_used,
            'daily_pnl': daily_pnl,
            'ending_capital': capital,
            'cumulative_pnl': capital - starting_capital
        })
    
    return pd.DataFrame(daily_results)

# selection.py
"""
Trade Selection Module

Provides deterministic scoring and top-k selection for trade opportunities.
Ensures reproducible selection based on signal strength and other metrics.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Tuple
import pandas as pd
import numpy as np


@dataclass
class SelectionConfig:
    """Configuration for trade selection."""
    score_by: str = "signal_strength"  # Primary scoring metric
    top_k: int = 5                      # Max trades to select per day
    tiebreaker: str = "ticker"          # Secondary sort for determinism
    min_score: float = 0.0              # Minimum score threshold
    
    @classmethod
    def from_dict(cls, config: dict) -> 'SelectionConfig':
        """Create SelectionConfig from dictionary."""
        return cls(
            score_by=config.get('score_by', 'signal_strength'),
            top_k=config.get('top_k', 5),
            tiebreaker=config.get('tiebreaker', 'ticker'),
            min_score=config.get('min_score', 0.0)
        )


def calculate_signal_strength(
    rsi: float,
    signal: int,
    rsi_mode: str = "reversal",
    oversold: float = 25,
    overbought: float = 75,
    centerline: float = 50,
    trend_side: int = 0
) -> float:
    """
    Calculate signal strength score from RSI and signal direction.
    
    Higher scores indicate stronger signals. Score is normalized to [0, 1].
    
    Parameters
    ----------
    rsi : float
        RSI value (0-100)
    signal : int
        Trade signal: 1 (buy), -1 (sell), 0 (no signal)
    rsi_mode : str
        RSI mode: "reversal" or "centerline"
    oversold : float
        Oversold threshold
    overbought : float
        Overbought threshold
    centerline : float
        Centerline threshold (for centerline mode)
    trend_side : int
        Trend direction: 1 (up), -1 (down), 0 (neutral)
        
    Returns
    -------
    float
        Signal strength score between 0.0 and 1.0
    """
    if signal == 0 or pd.isna(rsi):
        return 0.0
    
    score = 0.0
    
    if rsi_mode == "reversal":
        # For reversal mode: score based on RSI extremity
        if signal == 1:  # Buy signal (from oversold)
            # Stronger signal when RSI is further into oversold territory
            if rsi <= oversold:
                score = (oversold - rsi) / oversold
            else:
                # RSI crossed back above oversold - score based on recency
                score = max(0.3, 1.0 - (rsi - oversold) / 20.0)
        elif signal == -1:  # Sell signal (from overbought)
            # Stronger signal when RSI is further into overbought territory
            if rsi >= overbought:
                score = (rsi - overbought) / (100 - overbought)
            else:
                # RSI crossed back below overbought - score based on recency
                score = max(0.3, 1.0 - (overbought - rsi) / 20.0)
                
    elif rsi_mode == "centerline":
        # For centerline mode: score based on distance from centerline
        if signal == 1:  # Buy signal (above centerline)
            score = min((rsi - centerline) / 25.0, 1.0)
        elif signal == -1:  # Sell signal (below centerline)
            score = min((centerline - rsi) / 25.0, 1.0)
    
    # Apply trend alignment bonus/penalty
    if trend_side != 0:
        if signal * trend_side > 0:  # Aligned with trend
            score = min(score * 1.2, 1.0)
        elif signal * trend_side < 0:  # Against trend
            score = score * 0.7
    
    return max(0.0, min(1.0, score))


def calculate_ev_proxy(
    entry_cost: float,
    signal_strength: float,
    historical_win_rate: float = 0.55
) -> float:
    """
    Calculate expected value proxy score.
    
    TODO: Implement proper EV model based on historical performance.
    Currently uses a simple proxy combining entry cost and signal strength.
    
    Parameters
    ----------
    entry_cost : float
        Entry cost for the trade ($2.50, $5.00, or $7.50)
    signal_strength : float
        Signal strength score (0-1)
    historical_win_rate : float
        Historical win rate for similar trades
        
    Returns
    -------
    float
        EV proxy score (higher is better)
    """
    # TODO: Replace with proper EV calculation:
    # EV = (win_prob * win_payout) - (loss_prob * loss_amount)
    # where win_payout = 10.0 - entry_cost, loss_amount = entry_cost
    
    # Simple proxy: prefer lower entry costs with higher signal strength
    # Normalize entry cost: $2.50 -> 1.0, $5.00 -> 0.6, $7.50 -> 0.3
    entry_cost_score = max(0.0, 1.0 - (entry_cost - 2.50) / 7.50)
    
    # Combine with signal strength
    ev_proxy = (signal_strength * 0.6) + (entry_cost_score * 0.4)
    
    return ev_proxy


def score_opportunities(
    opportunities: pd.DataFrame,
    score_by: str = "signal_strength",
    rsi_mode: str = "reversal",
    oversold: float = 25,
    overbought: float = 75,
    centerline: float = 50
) -> pd.DataFrame:
    """
    Score all trading opportunities.
    
    Parameters
    ----------
    opportunities : pd.DataFrame
        DataFrame with columns: Date, Ticker, rsi, signal, entry_cost, etc.
    score_by : str
        Scoring method: "signal_strength" or "ev_proxy"
    rsi_mode : str
        RSI mode used for signal generation
    oversold : float
        Oversold threshold
    overbought : float
        Overbought threshold
    centerline : float
        Centerline threshold
        
    Returns
    -------
    pd.DataFrame
        Input DataFrame with added 'score' column
    """
    df = opportunities.copy()
    
    # Ensure required columns exist
    if 'signal' not in df.columns:
        raise ValueError("DataFrame must have 'signal' column")
    
    # Only score non-zero signals
    trade_mask = df['signal'] != 0
    
    if not trade_mask.any():
        df['score'] = 0.0
        return df
    
    # Calculate signal strength for all rows
    df['signal_strength'] = 0.0
    
    if 'rsi' in df.columns:
        trend_col = 'trend_side' if 'trend_side' in df.columns else None
        
        for idx in df[trade_mask].index:
            row = df.loc[idx]
            trend_side = row[trend_col] if trend_col else 0
            
            df.loc[idx, 'signal_strength'] = calculate_signal_strength(
                rsi=row['rsi'],
                signal=row['signal'],
                rsi_mode=rsi_mode,
                oversold=oversold,
                overbought=overbought,
                centerline=centerline,
                trend_side=int(trend_side) if not pd.isna(trend_side) else 0
            )
    
    # Calculate score based on scoring method
    if score_by == "signal_strength":
        df['score'] = df['signal_strength']
    elif score_by == "ev_proxy":
        df['score'] = 0.0
        if 'entry_cost' in df.columns:
            for idx in df[trade_mask].index:
                row = df.loc[idx]
                df.loc[idx, 'score'] = calculate_ev_proxy(
                    entry_cost=row['entry_cost'],
                    signal_strength=row['signal_strength']
                )
        else:
            # Fallback to signal strength if no entry_cost
            df['score'] = df['signal_strength']
    else:
        raise ValueError(f"Unknown scoring method: {score_by}")
    
    return df


def select_top_k(
    opportunities: pd.DataFrame,
    config: SelectionConfig
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Select top-k opportunities per day using deterministic scoring.
    
    Ensures deterministic selection by:
    1. Sorting primarily by score (descending)
    2. Using tiebreaker column for ties (ascending)
    3. Selecting top-k per group
    
    Parameters
    ----------
    opportunities : pd.DataFrame
        DataFrame with Date, signal, score, and tiebreaker columns
    config : SelectionConfig
        Selection configuration
        
    Returns
    -------
    tuple of (selected, rejected) DataFrames
        selected: Top-k opportunities per day
        rejected: Opportunities not selected
    """
    df = opportunities.copy()
    
    # Filter to actual signals only
    trade_mask = df['signal'] != 0
    non_trades = df[~trade_mask].copy()
    trades = df[trade_mask].copy()
    
    if trades.empty:
        return pd.DataFrame(), pd.DataFrame()
    
    # Ensure score column exists
    if 'score' not in trades.columns:
        raise ValueError("DataFrame must have 'score' column. Run score_opportunities first.")
    
    # Filter by minimum score
    if config.min_score > 0:
        trades = trades[trades['score'] >= config.min_score]
    
    if trades.empty:
        return pd.DataFrame(), df[trade_mask].copy()
    
    # Ensure tiebreaker column exists
    tiebreaker = config.tiebreaker
    if tiebreaker not in trades.columns:
        if 'Ticker' in trades.columns:
            tiebreaker = 'Ticker'
        else:
            # Add row index as tiebreaker
            trades['_tiebreaker'] = range(len(trades))
            tiebreaker = '_tiebreaker'
    
    # Sort deterministically: score (desc), tiebreaker (asc)
    trades = trades.sort_values(
        by=['Date', 'score', tiebreaker],
        ascending=[True, False, True]
    )
    
    # Select top-k per day
    selected_list = []
    rejected_list = []
    
    for date, day_trades in trades.groupby('Date', sort=False):
        # Maintain sort order within each day
        day_sorted = day_trades.sort_values(
            by=['score', tiebreaker],
            ascending=[False, True]
        )
        
        top_k = day_sorted.head(config.top_k)
        rejected = day_sorted.iloc[config.top_k:]
        
        selected_list.append(top_k)
        if len(rejected) > 0:
            rejected_list.append(rejected)
    
    selected = pd.concat(selected_list, ignore_index=True) if selected_list else pd.DataFrame()
    rejected = pd.concat(rejected_list, ignore_index=True) if rejected_list else pd.DataFrame()
    
    # Add selection metadata
    if not selected.empty:
        selected['selected'] = True
        selected['selection_reason'] = 'top_k'
    
    if not rejected.empty:
        rejected['selected'] = False
        rejected['selection_reason'] = 'exceeded_top_k'
    
    # Clean up temporary columns
    for col in ['_tiebreaker']:
        if col in selected.columns:
            selected = selected.drop(columns=[col])
        if col in rejected.columns:
            rejected = rejected.drop(columns=[col])
    
    return selected, rejected


def select_opportunities(
    opportunities: pd.DataFrame,
    config: Optional[SelectionConfig] = None,
    rsi_mode: str = "reversal",
    oversold: float = 25,
    overbought: float = 75,
    centerline: float = 50
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Score and select top opportunities per day.
    
    Convenience function that combines scoring and selection.
    
    Parameters
    ----------
    opportunities : pd.DataFrame
        Raw opportunities with Date, Ticker, rsi, signal columns
    config : SelectionConfig, optional
        Selection configuration (uses defaults if None)
    rsi_mode : str
        RSI mode for scoring
    oversold : float
        Oversold threshold
    overbought : float
        Overbought threshold
    centerline : float
        Centerline threshold
        
    Returns
    -------
    tuple of (selected, rejected) DataFrames
    """
    if config is None:
        config = SelectionConfig()
    
    # Score all opportunities
    scored = score_opportunities(
        opportunities=opportunities,
        score_by=config.score_by,
        rsi_mode=rsi_mode,
        oversold=oversold,
        overbought=overbought,
        centerline=centerline
    )
    
    # Select top-k
    selected, rejected = select_top_k(scored, config)
    
    return selected, rejected


def verify_selection_determinism(
    opportunities: pd.DataFrame,
    config: SelectionConfig,
    n_runs: int = 3
) -> bool:
    """
    Verify that selection is deterministic across multiple runs.
    
    Parameters
    ----------
    opportunities : pd.DataFrame
        Input opportunities
    config : SelectionConfig
        Selection configuration
    n_runs : int
        Number of runs to verify
        
    Returns
    -------
    bool
        True if all runs produce identical results
    """
    results = []
    
    for _ in range(n_runs):
        selected, _ = select_opportunities(opportunities.copy(), config)
        # Create hashable representation
        if not selected.empty:
            key_cols = ['Date', 'Ticker', 'score'] if 'Ticker' in selected.columns else ['Date', 'score']
            key_cols = [c for c in key_cols if c in selected.columns]
            result_hash = pd.util.hash_pandas_object(selected[key_cols]).sum()
        else:
            result_hash = 0
        results.append(result_hash)
    
    return len(set(results)) == 1

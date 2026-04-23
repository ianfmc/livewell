# experiments.py
"""
Experiment Runner Module

Loads experiment configurations from YAML, runs backtests with capital constraints,
computes standardized metrics, and saves artifacts to S3.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable
import json
import copy

import pandas as pd
import numpy as np
import yaml

from .selection import SelectionConfig, select_opportunities, score_opportunities
from .capital import CapitalConfig, fund_trades, apply_capital_constraints
from .kpi_calculator import calculate_kpis
from .backtest_results import BacktestResults


@dataclass
class ExperimentConfig:
    """Configuration for a single experiment."""
    exp_id: str
    name: str
    description: str
    enabled: bool = True
    tags: List[str] = field(default_factory=list)
    notes: str = ""
    
    # Merged configuration sections
    strategy: Dict[str, Any] = field(default_factory=dict)
    capital: Dict[str, Any] = field(default_factory=dict)
    selection: Dict[str, Any] = field(default_factory=dict)
    backtest: Dict[str, Any] = field(default_factory=dict)
    output: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_dict(cls, exp_id: str, config: dict, defaults: dict) -> 'ExperimentConfig':
        """Create ExperimentConfig by merging defaults with overrides."""
        # Deep merge defaults with overrides
        merged = deep_merge(copy.deepcopy(defaults), config.get('overrides', {}))
        
        return cls(
            exp_id=exp_id,
            name=config.get('name', exp_id),
            description=config.get('description', ''),
            enabled=config.get('enabled', True),
            tags=config.get('tags', []),
            notes=config.get('notes', ''),
            strategy=merged.get('strategy', {}),
            capital=merged.get('capital', {}),
            selection=merged.get('selection', {}),
            backtest=merged.get('backtest', {}),
            output=merged.get('output', {})
        )


@dataclass
class ExperimentResult:
    """Results from running a single experiment."""
    exp_id: str
    name: str
    config: ExperimentConfig
    
    # Trade data
    funded_trades: pd.DataFrame
    skipped_trades: pd.DataFrame
    
    # Metrics
    kpis: Dict[str, Any]
    daily_metrics: pd.DataFrame
    
    # Metadata
    run_timestamp: str
    s3_artifacts: Dict[str, str] = field(default_factory=dict)
    
    def to_summary_row(self) -> Dict[str, Any]:
        """Convert to summary row for DataFrame."""
        return {
            'exp_id': self.exp_id,
            'name': self.name,
            'total_trades': self.kpis.get('total_trades', 0),
            'funded_trades': len(self.funded_trades) if not self.funded_trades.empty else 0,
            'skipped_trades': len(self.skipped_trades) if not self.skipped_trades.empty else 0,
            'win_rate': self.kpis.get('win_rate', 0.0),
            'gross_pnl': self.kpis.get('gross_pnl', 0.0),
            'net_pnl': self.kpis.get('net_pnl', 0.0),
            'total_capital': self.kpis.get('total_capital_used', 0.0),
            'return_pct': self.kpis.get('return_pct', 0.0),
            'max_drawdown': self.kpis.get('max_drawdown', 0.0),
            'sharpe_ratio': self.kpis.get('sharpe_ratio', 0.0),
            'tags': ','.join(self.config.tags),
            'run_timestamp': self.run_timestamp
        }


def deep_merge(base: dict, override: dict) -> dict:
    """Deep merge override dict into base dict."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_experiments_config(
    config_path: str = 'configs/experiments.yaml'
) -> Dict[str, Any]:
    """
    Load experiments configuration from YAML file.
    
    Parameters
    ----------
    config_path : str
        Path to experiments.yaml
        
    Returns
    -------
    dict
        Parsed configuration with 'defaults', 'experiments', 'groups' keys
    """
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Experiments config not found: {config_path}")
    
    with open(path, 'r') as f:
        config = yaml.safe_load(f)
    
    return config


def get_experiment_configs(
    config_path: str = 'configs/experiments.yaml',
    experiment_ids: Optional[List[str]] = None,
    group: Optional[str] = None,
    enabled_only: bool = True
) -> List[ExperimentConfig]:
    """
    Get experiment configurations from YAML.
    
    Parameters
    ----------
    config_path : str
        Path to experiments.yaml
    experiment_ids : list of str, optional
        Specific experiment IDs to load (e.g., ['E1.0', 'E1.1'])
    group : str, optional
        Load all experiments in a group (e.g., 'baseline', 'capital_sweep')
    enabled_only : bool
        If True, only return enabled experiments
        
    Returns
    -------
    list of ExperimentConfig
    """
    config = load_experiments_config(config_path)
    defaults = config.get('defaults', {})
    experiments = config.get('experiments', {})
    groups = config.get('groups', {})
    
    # Determine which experiment IDs to load
    if experiment_ids is not None:
        ids_to_load = experiment_ids
    elif group is not None:
        if group not in groups:
            raise ValueError(f"Unknown group: {group}. Available: {list(groups.keys())}")
        ids_to_load = groups[group].get('experiments', [])
    else:
        # Load all experiments
        ids_to_load = list(experiments.keys())
    
    # Build ExperimentConfig objects
    configs = []
    for exp_id in ids_to_load:
        if exp_id not in experiments:
            print(f"Warning: Experiment {exp_id} not found in config")
            continue
        
        exp_config = ExperimentConfig.from_dict(exp_id, experiments[exp_id], defaults)
        
        if enabled_only and not exp_config.enabled:
            continue
        
        configs.append(exp_config)
    
    return configs


def run_backtest(
    data: pd.DataFrame,
    config: ExperimentConfig,
    backtest_fn: Optional[Callable] = None
) -> pd.DataFrame:
    """
    Run backtest on data with given configuration.
    
    Uses existing backtest logic if backtest_fn is provided,
    otherwise uses default RSI-based backtest.
    
    Parameters
    ----------
    data : pd.DataFrame
        Historical data with Ticker, Date, Exp Value, Strike Price, In the Money
    config : ExperimentConfig
        Experiment configuration
    backtest_fn : callable, optional
        Custom backtest function(data, **strategy_params) -> trades_df
        
    Returns
    -------
    pd.DataFrame
        Backtest results with signal, entry_cost, pnl columns
    """
    if backtest_fn is not None:
        # Use provided backtest function
        return backtest_fn(data, **config.strategy)
    
    # Default implementation using existing backtest logic
    from .strategy_rsi import rsi_wilder
    from .kpi_calculator import calculate_tier_entry_cost
    
    strategy = config.strategy
    rsi_period = strategy.get('rsi_period', 14)
    oversold = strategy.get('oversold', 25)
    overbought = strategy.get('overbought', 75)
    strike_filter_pct = strategy.get('strike_filter_pct', 0.10)
    
    all_results = []
    
    for ticker in data['Ticker'].unique():
        ticker_data = data[data['Ticker'] == ticker].copy()
        
        # Apply strike filter if configured
        if strike_filter_pct is not None and strike_filter_pct > 0:
            ticker_data['distance_pct'] = abs(
                ticker_data['Strike Price'] - ticker_data['Exp Value']
            ) / ticker_data['Exp Value']
            ticker_data = ticker_data[ticker_data['distance_pct'] <= strike_filter_pct].copy()
        
        if ticker_data.empty:
            continue
        
        # Get daily Exp Value (use mean across strikes for that day)
        daily_exp = ticker_data.groupby('Date')['Exp Value'].mean().reset_index()
        daily_exp = daily_exp.sort_values('Date').reset_index(drop=True)
        
        # Calculate RSI on daily Exp Value
        daily_exp['rsi'] = rsi_wilder(daily_exp['Exp Value'], rsi_period)
        
        # Generate signals
        daily_exp['signal'] = 0
        daily_exp.loc[daily_exp['rsi'] < oversold, 'signal'] = 1   # BUY
        daily_exp.loc[daily_exp['rsi'] > overbought, 'signal'] = -1  # SELL
        
        # Merge signals back to ALL strikes
        ticker_data = ticker_data.merge(
            daily_exp[['Date', 'rsi', 'signal']], 
            on='Date', 
            how='left'
        )
        
        # Calculate P&L for each strike that gets a signal
        trades = ticker_data[ticker_data['signal'] != 0].copy()
        for idx in trades.index:
            row = ticker_data.loc[idx]
            entry_cost = calculate_tier_entry_cost(row['Exp Value'], row['Strike Price'])
            pnl = (10.0 - entry_cost) if row['In the Money'] == 1 else -entry_cost
            ticker_data.loc[idx, 'entry_cost'] = entry_cost
            ticker_data.loc[idx, 'pnl'] = pnl
        
        all_results.append(ticker_data)
    
    if not all_results:
        return pd.DataFrame()
    
    return pd.concat(all_results, ignore_index=True)


def run_single_experiment(
    data: pd.DataFrame,
    config: ExperimentConfig,
    backtest_fn: Optional[Callable] = None,
    s3_client=None,
    s3_bucket: Optional[str] = None,
    save_artifacts: bool = True
) -> ExperimentResult:
    """
    Run a single experiment.
    
    Parameters
    ----------
    data : pd.DataFrame
        Historical data
    config : ExperimentConfig
        Experiment configuration
    backtest_fn : callable, optional
        Custom backtest function
    s3_client : boto3 client, optional
        S3 client for saving artifacts
    s3_bucket : str, optional
        S3 bucket name
    save_artifacts : bool
        Whether to save artifacts to S3
        
    Returns
    -------
    ExperimentResult
    """
    run_timestamp = datetime.now().isoformat()
    print(f"\n{'='*60}")
    print(f"Running Experiment: {config.exp_id} - {config.name}")
    print(f"{'='*60}")
    
    # Step 1: Run backtest
    print("  [1/4] Running backtest...")
    all_trades = run_backtest(data, config, backtest_fn)
    
    if all_trades.empty:
        print("  Warning: No trades generated from backtest")
        return ExperimentResult(
            exp_id=config.exp_id,
            name=config.name,
            config=config,
            funded_trades=pd.DataFrame(),
            skipped_trades=pd.DataFrame(),
            kpis={'total_trades': 0, 'win_rate': 0.0, 'gross_pnl': 0.0, 'net_pnl': 0.0},
            daily_metrics=pd.DataFrame(),
            run_timestamp=run_timestamp
        )
    
    # Filter to actual trades
    trades = all_trades[all_trades['signal'] != 0].copy()
    print(f"      Generated {len(trades):,} raw trade signals")
    
    # Step 2: Score and select opportunities
    print("  [2/4] Scoring and selecting opportunities...")
    selection_config = SelectionConfig.from_dict(config.selection)
    
    scored_trades = score_opportunities(
        opportunities=trades,
        score_by=selection_config.score_by,
        rsi_mode=config.strategy.get('rsi_mode', 'reversal'),
        oversold=config.strategy.get('oversold', 25),
        overbought=config.strategy.get('overbought', 75)
    )
    
    from .selection import select_top_k
    selected, selection_rejected = select_top_k(scored_trades, selection_config)
    print(f"      Selected {len(selected):,} opportunities (top-{selection_config.top_k}/day)")
    
    # Step 3: Apply capital constraints
    print("  [3/4] Applying capital constraints...")
    capital_config = CapitalConfig.from_dict(config.capital)
    
    funded_trades, capital_rejected, funding_summary = fund_trades(
        trades=selected,
        config=capital_config
    )
    print(f"      Funded {len(funded_trades):,} trades")
    print(f"      Skipped {len(capital_rejected):,} trades (capital constraints)")
    
    # Combine rejected trades
    all_skipped = pd.concat([selection_rejected, capital_rejected], ignore_index=True) if not selection_rejected.empty or not capital_rejected.empty else pd.DataFrame()
    
    # Step 4: Calculate KPIs
    print("  [4/4] Calculating KPIs...")
    commission = config.backtest.get('commission_per_contract', 0.10)
    
    if not funded_trades.empty:
        kpis = calculate_kpis(funded_trades, commission_per_contract=commission)
        daily_metrics = kpis.pop('daily_data', pd.DataFrame())
        
        # Add additional metrics
        total_capital = funded_trades['entry_cost'].sum() if 'entry_cost' in funded_trades.columns else 0
        kpis['total_capital_used'] = total_capital
        kpis['return_pct'] = (kpis['net_pnl'] / total_capital * 100) if total_capital > 0 else 0
        
        # Calculate Sharpe ratio
        if 'pnl' in funded_trades.columns and len(funded_trades) > 1:
            daily_pnl = funded_trades.groupby('Date')['pnl'].sum()
            if daily_pnl.std() > 0:
                kpis['sharpe_ratio'] = (daily_pnl.mean() / daily_pnl.std()) * np.sqrt(252)
            else:
                kpis['sharpe_ratio'] = 0.0
        else:
            kpis['sharpe_ratio'] = 0.0
    else:
        kpis = {
            'total_trades': 0,
            'wins': 0,
            'losses': 0,
            'win_rate': 0.0,
            'gross_pnl': 0.0,
            'commissions': 0.0,
            'net_pnl': 0.0,
            'max_drawdown': 0.0,
            'total_capital_used': 0.0,
            'return_pct': 0.0,
            'sharpe_ratio': 0.0
        }
        daily_metrics = pd.DataFrame()
    
    print(f"\n  Results for {config.exp_id}:")
    print(f"      Trades: {kpis.get('total_trades', 0):,}")
    print(f"      Win Rate: {kpis.get('win_rate', 0):.2%}")
    print(f"      Net P&L: ${kpis.get('net_pnl', 0):,.2f}")
    print(f"      Return: {kpis.get('return_pct', 0):.2f}%")
    
    # Create result
    result = ExperimentResult(
        exp_id=config.exp_id,
        name=config.name,
        config=config,
        funded_trades=funded_trades,
        skipped_trades=all_skipped,
        kpis=kpis,
        daily_metrics=daily_metrics,
        run_timestamp=run_timestamp
    )
    
    # Save artifacts to S3
    if save_artifacts and s3_client is not None and s3_bucket is not None:
        result.s3_artifacts = save_experiment_artifacts(
            result=result,
            s3_client=s3_client,
            bucket=s3_bucket,
            prefix=config.output.get('s3_prefix', 'experiments')
        )
    
    return result


def save_experiment_artifacts(
    result: ExperimentResult,
    s3_client,
    bucket: str,
    prefix: str = "experiments"
) -> Dict[str, str]:
    """
    Save experiment artifacts to S3.
    
    Parameters
    ----------
    result : ExperimentResult
        Experiment result to save
    s3_client : boto3 client
        S3 client
    bucket : str
        S3 bucket name
    prefix : str
        S3 prefix
        
    Returns
    -------
    dict
        S3 URIs for saved artifacts
    """
    saved_uris = {}
    exp_id = result.exp_id
    timestamp = datetime.now().strftime('%Y-%m-%d')
    
    base_path = f"{prefix}/{exp_id}/{timestamp}"
    
    try:
        # Save funded trades
        if not result.funded_trades.empty:
            trades_key = f"{base_path}/trades.csv"
            trades_csv = result.funded_trades.to_csv(index=False)
            s3_client.put_object(
                Bucket=bucket, Key=trades_key,
                Body=trades_csv.encode('utf-8'), ContentType='text/csv'
            )
            saved_uris['trades'] = f"s3://{bucket}/{trades_key}"
        
        # Save KPIs
        kpis_key = f"{base_path}/kpi_summary.json"
        kpis_json = json.dumps(result.kpis, indent=2, default=str)
        s3_client.put_object(
            Bucket=bucket, Key=kpis_key,
            Body=kpis_json.encode('utf-8'), ContentType='application/json'
        )
        saved_uris['kpis'] = f"s3://{bucket}/{kpis_key}"
        
        # Save daily metrics
        if not result.daily_metrics.empty:
            daily_key = f"{base_path}/daily_metrics.csv"
            daily_csv = result.daily_metrics.to_csv(index=False)
            s3_client.put_object(
                Bucket=bucket, Key=daily_key,
                Body=daily_csv.encode('utf-8'), ContentType='text/csv'
            )
            saved_uris['daily_metrics'] = f"s3://{bucket}/{daily_key}"
        
        # Save config
        config_key = f"{base_path}/config.json"
        config_dict = {
            'exp_id': result.config.exp_id,
            'name': result.config.name,
            'description': result.config.description,
            'tags': result.config.tags,
            'strategy': result.config.strategy,
            'capital': result.config.capital,
            'selection': result.config.selection,
            'backtest': result.config.backtest
        }
        config_json = json.dumps(config_dict, indent=2)
        s3_client.put_object(
            Bucket=bucket, Key=config_key,
            Body=config_json.encode('utf-8'), ContentType='application/json'
        )
        saved_uris['config'] = f"s3://{bucket}/{config_key}"
        
        print(f"  ✓ Saved artifacts to s3://{bucket}/{base_path}/")
        
    except Exception as e:
        print(f"  Warning: Failed to save artifacts: {e}")
    
    return saved_uris


def run_experiments(
    data: pd.DataFrame,
    config_path: str = 'configs/experiments.yaml',
    experiment_ids: Optional[List[str]] = None,
    group: Optional[str] = None,
    enabled_only: bool = True,
    backtest_fn: Optional[Callable] = None,
    s3_client=None,
    s3_bucket: Optional[str] = None,
    save_artifacts: bool = True
) -> pd.DataFrame:
    """
    Run multiple experiments and return summary DataFrame.
    
    This is the main entry point for the experiment runner.
    
    Parameters
    ----------
    data : pd.DataFrame
        Historical data for backtesting
    config_path : str
        Path to experiments.yaml
    experiment_ids : list of str, optional
        Specific experiment IDs to run
    group : str, optional
        Run all experiments in a group
    enabled_only : bool
        Only run enabled experiments
    backtest_fn : callable, optional
        Custom backtest function
    s3_client : boto3 client, optional
        S3 client for artifact storage
    s3_bucket : str, optional
        S3 bucket name
    save_artifacts : bool
        Whether to save artifacts to S3
        
    Returns
    -------
    pd.DataFrame
        Summary DataFrame with one row per experiment
    """
    print("="*60)
    print("EXPERIMENT RUNNER")
    print("="*60)
    
    # Load experiment configurations
    configs = get_experiment_configs(
        config_path=config_path,
        experiment_ids=experiment_ids,
        group=group,
        enabled_only=enabled_only
    )
    
    if not configs:
        print("No experiments to run!")
        return pd.DataFrame()
    
    print(f"Running {len(configs)} experiment(s)")
    if group:
        print(f"Group: {group}")
    print(f"Data shape: {data.shape}")
    
    # Run each experiment
    results = []
    for config in configs:
        result = run_single_experiment(
            data=data,
            config=config,
            backtest_fn=backtest_fn,
            s3_client=s3_client,
            s3_bucket=s3_bucket,
            save_artifacts=save_artifacts
        )
        results.append(result)
    
    # Create summary DataFrame
    summary_rows = [r.to_summary_row() for r in results]
    summary_df = pd.DataFrame(summary_rows)
    
    # Sort by net_pnl descending
    if 'net_pnl' in summary_df.columns:
        summary_df = summary_df.sort_values('net_pnl', ascending=False)
    
    print("\n" + "="*60)
    print("EXPERIMENT SUMMARY")
    print("="*60)
    
    return summary_df


def get_experiment_result_details(
    summary_df: pd.DataFrame,
    exp_id: str
) -> Optional[Dict[str, Any]]:
    """
    Get detailed results for a specific experiment from summary.
    
    Parameters
    ----------
    summary_df : pd.DataFrame
        Summary DataFrame from run_experiments
    exp_id : str
        Experiment ID to get details for
        
    Returns
    -------
    dict or None
        Experiment details if found
    """
    if summary_df.empty:
        return None
    
    row = summary_df[summary_df['exp_id'] == exp_id]
    if row.empty:
        return None
    
    return row.iloc[0].to_dict()

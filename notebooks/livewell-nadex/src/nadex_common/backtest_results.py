# backtest_results.py
"""
Backtest Results Module

Provides the BacktestResults class for saving and loading backtest results.
Uses the schema defined in configs/backtest_schema.yaml.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

import pandas as pd
import yaml


def load_backtest_schema(schema_path: str = '../configs/backtest_schema.yaml') -> Dict:
    """
    Load the backtest schema configuration.
    
    Parameters
    ----------
    schema_path : str
        Path to backtest_schema.yaml
        
    Returns
    -------
    dict
        Schema configuration
    """
    with open(schema_path, 'r') as f:
        return yaml.safe_load(f)


@dataclass
class BacktestResults:
    """
    Container for backtest results with S3 save/load capabilities.
    
    Attributes
    ----------
    trades : pd.DataFrame
        Individual trade data with columns: Date, Ticker, entry_cost, pnl, etc.
    kpis : dict
        Pre-calculated KPI metrics
    daily_metrics : pd.DataFrame
        Daily aggregated metrics for charts
    strategy_params : dict
        Strategy parameters used (RSI period, thresholds, etc.)
    generated_at : str
        ISO timestamp when results were generated
    """
    trades: pd.DataFrame
    kpis: Dict[str, Any]
    daily_metrics: pd.DataFrame
    strategy_params: Dict[str, Any] = field(default_factory=dict)
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def save_to_s3(
        self, 
        s3_client, 
        bucket: str, 
        date: Optional[str] = None,
        prefix: str = "backtest/results",
        save_latest: bool = True
    ) -> Dict[str, str]:
        """
        Save backtest results to S3.
        
        Parameters
        ----------
        s3_client : boto3 S3 client
            S3 client for uploads
        bucket : str
            S3 bucket name
        date : str, optional
            Date string (YYYY-MM-DD). Defaults to today.
        prefix : str
            S3 prefix for results
        save_latest : bool
            If True, also saves to {prefix}/latest/
            
        Returns
        -------
        dict
            S3 URIs for saved files
        """
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        saved_uris = {}
        kpis_serializable = self._prepare_kpis_for_json()
        
        paths = {f"{prefix}/{date}": True}
        if save_latest:
            paths[f"{prefix}/latest"] = True
        
        for folder_path in paths.keys():
            # Save trades.csv
            trades_key = f"{folder_path}/trades.csv"
            trades_csv = self.trades.to_csv(index=False)
            s3_client.put_object(
                Bucket=bucket, Key=trades_key,
                Body=trades_csv.encode('utf-8'), ContentType='text/csv'
            )
            saved_uris[f'trades_{folder_path}'] = f"s3://{bucket}/{trades_key}"
            
            # Save kpi_summary.json
            kpi_key = f"{folder_path}/kpi_summary.json"
            kpi_json = json.dumps(kpis_serializable, indent=2, default=str)
            s3_client.put_object(
                Bucket=bucket, Key=kpi_key,
                Body=kpi_json.encode('utf-8'), ContentType='application/json'
            )
            saved_uris[f'kpis_{folder_path}'] = f"s3://{bucket}/{kpi_key}"
            
            # Save daily_metrics.csv
            daily_key = f"{folder_path}/daily_metrics.csv"
            daily_csv = self.daily_metrics.to_csv(index=False)
            s3_client.put_object(
                Bucket=bucket, Key=daily_key,
                Body=daily_csv.encode('utf-8'), ContentType='text/csv'
            )
            saved_uris[f'daily_{folder_path}'] = f"s3://{bucket}/{daily_key}"
        
        print(f"✓ Saved backtest results to S3:")
        print(f"  - s3://{bucket}/{prefix}/{date}/")
        if save_latest:
            print(f"  - s3://{bucket}/{prefix}/latest/")
        
        return saved_uris
    
    def _prepare_kpis_for_json(self) -> Dict:
        """Prepare KPIs dict for JSON serialization."""
        kpis = self.kpis.copy()
        
        if 'date_start' in kpis and hasattr(kpis['date_start'], 'strftime'):
            kpis['date_start'] = kpis['date_start'].strftime('%Y-%m-%d')
        if 'date_end' in kpis and hasattr(kpis['date_end'], 'strftime'):
            kpis['date_end'] = kpis['date_end'].strftime('%Y-%m-%d')
        if 'daily_data' in kpis:
            del kpis['daily_data']
        
        kpis['generated_at'] = self.generated_at
        kpis['strategy_params'] = self.strategy_params
        return kpis
    
    @classmethod
    def load_from_s3(
        cls, 
        s3_client, 
        bucket: str,
        date: Optional[str] = None,
        prefix: str = "backtest/results"
    ) -> 'BacktestResults':
        """
        Load backtest results from S3.
        
        Parameters
        ----------
        s3_client : boto3 S3 client
            S3 client for downloads
        bucket : str
            S3 bucket name
        date : str, optional
            Date string (YYYY-MM-DD). If None, loads from 'latest'.
        prefix : str
            S3 prefix for results
            
        Returns
        -------
        BacktestResults
            Loaded backtest results
        """
        folder = date if date else "latest"
        folder_path = f"{prefix}/{folder}"
        
        print(f"Loading backtest results from s3://{bucket}/{folder_path}/")
        
        # Load trades.csv
        trades_key = f"{folder_path}/trades.csv"
        try:
            obj = s3_client.get_object(Bucket=bucket, Key=trades_key)
            trades = pd.read_csv(obj['Body'])
            trades['Date'] = pd.to_datetime(trades['Date'])
            print(f"  ✓ Loaded trades: {len(trades):,} rows")
        except Exception as e:
            raise FileNotFoundError(f"Could not load trades from {trades_key}: {e}")
        
        # Load kpi_summary.json
        kpi_key = f"{folder_path}/kpi_summary.json"
        try:
            obj = s3_client.get_object(Bucket=bucket, Key=kpi_key)
            kpis = json.loads(obj['Body'].read().decode('utf-8'))
            if 'date_start' in kpis and kpis['date_start']:
                kpis['date_start'] = pd.to_datetime(kpis['date_start'])
            if 'date_end' in kpis and kpis['date_end']:
                kpis['date_end'] = pd.to_datetime(kpis['date_end'])
            print(f"  ✓ Loaded KPIs: win_rate={kpis.get('win_rate', 0):.2%}")
        except Exception as e:
            raise FileNotFoundError(f"Could not load KPIs from {kpi_key}: {e}")
        
        # Load daily_metrics.csv
        daily_key = f"{folder_path}/daily_metrics.csv"
        try:
            obj = s3_client.get_object(Bucket=bucket, Key=daily_key)
            daily_metrics = pd.read_csv(obj['Body'])
            daily_metrics['Date'] = pd.to_datetime(daily_metrics['Date'])
            print(f"  ✓ Loaded daily metrics: {len(daily_metrics):,} rows")
        except Exception as e:
            raise FileNotFoundError(f"Could not load daily metrics from {daily_key}: {e}")
        
        kpis['daily_data'] = daily_metrics
        strategy_params = kpis.pop('strategy_params', {})
        generated_at = kpis.pop('generated_at', datetime.now().isoformat())
        
        return cls(
            trades=trades, kpis=kpis, daily_metrics=daily_metrics,
            strategy_params=strategy_params, generated_at=generated_at
        )
    
    def save_local(self, output_dir: str = 'reports') -> Dict[str, str]:
        """Save backtest results locally."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        saved_paths = {}
        
        trades_path = output_path / 'trades.csv'
        self.trades.to_csv(trades_path, index=False)
        saved_paths['trades'] = str(trades_path)
        
        kpi_path = output_path / 'kpi_summary.json'
        with open(kpi_path, 'w') as f:
            json.dump(self._prepare_kpis_for_json(), f, indent=2, default=str)
        saved_paths['kpis'] = str(kpi_path)
        
        daily_path = output_path / 'daily_metrics.csv'
        self.daily_metrics.to_csv(daily_path, index=False)
        saved_paths['daily_metrics'] = str(daily_path)
        
        print(f"✓ Saved backtest results locally to {output_dir}/")
        return saved_paths
    
    @classmethod
    def load_local(cls, input_dir: str = 'reports') -> 'BacktestResults':
        """Load backtest results from local files."""
        input_path = Path(input_dir)
        
        trades = pd.read_csv(input_path / 'trades.csv')
        trades['Date'] = pd.to_datetime(trades['Date'])
        
        with open(input_path / 'kpi_summary.json', 'r') as f:
            kpis = json.load(f)
        if 'date_start' in kpis and kpis['date_start']:
            kpis['date_start'] = pd.to_datetime(kpis['date_start'])
        if 'date_end' in kpis and kpis['date_end']:
            kpis['date_end'] = pd.to_datetime(kpis['date_end'])
        
        daily_metrics = pd.read_csv(input_path / 'daily_metrics.csv')
        daily_metrics['Date'] = pd.to_datetime(daily_metrics['Date'])
        kpis['daily_data'] = daily_metrics
        
        strategy_params = kpis.pop('strategy_params', {})
        generated_at = kpis.pop('generated_at', datetime.now().isoformat())
        
        return cls(
            trades=trades, kpis=kpis, daily_metrics=daily_metrics,
            strategy_params=strategy_params, generated_at=generated_at
        )
    
    def __repr__(self) -> str:
        return (
            f"BacktestResults(trades={len(self.trades):,}, "
            f"win_rate={self.kpis.get('win_rate', 0):.2%}, "
            f"net_pnl=${self.kpis.get('net_pnl', 0):,.2f})"
        )

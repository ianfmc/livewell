# kpi_html_generator.py
"""
HTML Report Generator Module

Uses Jinja2 templates to generate HTML KPI dashboards.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from jinja2 import Environment, FileSystemLoader


def get_template_path() -> Path:
    """
    Get the path to the templates directory.
    
    Returns
    -------
    Path
        Path to the templates directory
    """
    # Navigate from src/nadex_common/ to project root/templates/
    current_dir = Path(__file__).parent
    project_root = current_dir.parent.parent
    template_dir = project_root / 'templates'
    return template_dir


def generate_html_dashboard(
    kpis: Dict[str, Any],
    commission_per_contract: float = 1.00,
    template_name: str = 'kpi_dashboard.html.j2',
    template_dir: Optional[Path] = None
) -> str:
    """
    Generate HTML KPI dashboard using Jinja2 template.
    
    Parameters
    ----------
    kpis : dict
        KPI dictionary from calculate_kpis()
    commission_per_contract : float, default=1.00
        Commission per contract for display
    template_name : str, default='kpi_dashboard.html.j2'
        Name of the Jinja2 template file
    template_dir : Path, optional
        Path to templates directory. If None, uses default location.
        
    Returns
    -------
    str
        Rendered HTML content
    """
    if template_dir is None:
        template_dir = get_template_path()
    
    # Set up Jinja2 environment
    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=True
    )
    template = env.get_template(template_name)
    
    # Prepare data for template
    daily_data = kpis.get('daily_data')
    
    if daily_data is not None and not daily_data.empty:
        dates_json = json.dumps(daily_data['Date'].dt.strftime('%Y-%m-%d').tolist())
        cumulative_pnl_json = json.dumps(daily_data['cumulative_pnl'].round(2).tolist())
        drawdown_json = json.dumps(daily_data['drawdown'].round(2).tolist())
    else:
        dates_json = '[]'
        cumulative_pnl_json = '[]'
        drawdown_json = '[]'
    
    # Format dates
    date_start = kpis.get('date_start')
    date_end = kpis.get('date_end')
    date_start_str = date_start.strftime('%b %d, %Y') if date_start else 'N/A'
    date_end_str = date_end.strftime('%b %d, %Y') if date_end else 'N/A'
    generated_time = datetime.now().strftime('%m/%d/%Y, %I:%M:%S %p')
    
    # Determine CSS classes based on values
    win_rate = kpis.get('win_rate', 0)
    net_pnl = kpis.get('net_pnl', 0)
    gross_pnl = kpis.get('gross_pnl', 0)
    
    win_rate_class = 'positive' if win_rate >= 0.5 else 'negative'
    net_pnl_class = 'positive' if net_pnl >= 0 else 'negative'
    gross_pnl_class = 'positive' if gross_pnl >= 0 else 'negative'
    
    # Render template
    html_content = template.render(
        # KPI values
        win_rate=win_rate,
        total_trades=kpis.get('total_trades', 0),
        wins=kpis.get('wins', 0),
        losses=kpis.get('losses', 0),
        gross_pnl=gross_pnl,
        commissions=kpis.get('commissions', 0),
        net_pnl=net_pnl,
        max_drawdown=kpis.get('max_drawdown', 0),
        max_drawdown_pct=kpis.get('max_drawdown_pct', 0),
        recovery_days=kpis.get('recovery_days', 0),
        
        # Date strings
        date_start=date_start_str,
        date_end=date_end_str,
        generated_time=generated_time,
        
        # CSS classes
        win_rate_class=win_rate_class,
        net_pnl_class=net_pnl_class,
        gross_pnl_class=gross_pnl_class,
        
        # Chart data (JSON)
        dates_json=dates_json,
        cumulative_pnl_json=cumulative_pnl_json,
        drawdown_json=drawdown_json,
        
        # Configuration
        commission_per_contract=commission_per_contract
    )
    
    return html_content

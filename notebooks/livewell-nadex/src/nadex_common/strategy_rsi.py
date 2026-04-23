# strategy_rsi.py
from __future__ import annotations
import numpy as np
import pandas as pd

def rsi_wilder(close: pd.Series, period: int = 14) -> pd.Series:
    close = pd.Series(close).astype(float)
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1/period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False, min_periods=period).mean()
    
    # Handle edge cases:
    # - If avg_loss is 0 (no losses), RSI should be 100 (maximum overbought)
    # - If avg_gain is 0 (no gains), RSI should be 0 (maximum oversold)
    rs = avg_gain / avg_loss.replace(0.0, 1e-10)  # Use tiny value instead of NaN
    rsi = 100.0 - (100.0 / (1.0 + rs))
    
    # Set RSI to 100 when there are gains but no losses
    rsi = rsi.where(avg_loss > 0, 100.0)
    # Set RSI to 0 when there are losses but no gains  
    rsi = rsi.where(avg_gain > 0, 0.0)
    
    return rsi

def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    close = pd.Series(close).astype(float)
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    line = ema_fast - ema_slow
    sig = line.ewm(span=signal, adjust=False).mean()
    hist = line - sig
    return line, sig, hist

def sma(close: pd.Series, window: int = 50) -> pd.Series:
    return pd.Series(close).astype(float).rolling(window).mean()

def _cross_up(series: pd.Series, level: float) -> pd.Series:
    s = pd.Series(series)
    return (s.shift(1) <= level) & (s > level)

def _cross_down(series: pd.Series, level: float) -> pd.Series:
    s = pd.Series(series)
    return (s.shift(1) >= level) & (s < level)

def trend_ok(close: pd.Series, cfg: dict) -> pd.Series:
    trend_cfg = (cfg.get("trend") or {})
    t = str(trend_cfg.get("type", "none")).lower()
    if t == "macd":
        line, sig, _ = macd(close,
                            fast=trend_cfg.get("macd_fast", 12),
                            slow=trend_cfg.get("macd_slow", 26),
                            signal=trend_cfg.get("macd_signal", 9))
        return pd.Series(np.where(line >= sig, 1, -1), index=pd.Series(close).index)
    if t == "sma":
        ma = sma(close, trend_cfg.get("sma_window", 50))
        return pd.Series(np.where(pd.Series(close) >= ma, 1, -1), index=pd.Series(close).index)
    return pd.Series(0, index=pd.Series(close).index)

def generate_rsi_signals(close: pd.Series, cfg: dict) -> pd.DataFrame:
    r = cfg.get("rsi", {})
    mode = str(r.get("mode", "centerline")).lower()
    period = int(r.get("period", 14))
    rsi = rsi_wilder(close, period)
    tside = trend_ok(close, cfg)
    sig = pd.Series(0, index=pd.Series(close).index)
    if mode == "centerline":
        cl = float(r.get("centerline", 50))
        buy  = (rsi > cl) & (tside >= 0)  # >= 0 instead of == 1
        sell = (rsi < cl) & (tside <= 0)  # <= 0 instead of == -1
        sig = np.select([buy, sell], [1, -1], default=0)  # ← ADD THIS LINE
    elif mode == "reversal":
        ob = float(r.get("overbought", 70))
        os = float(r.get("oversold", 30))
        if bool(r.get("require_cross", True)):
            buy  = _cross_up(rsi, os)
            sell = _cross_down(rsi, ob)
        else:
            buy  = (rsi <= os)
            sell = (rsi >= ob)
        sig = np.select([buy, sell], [1, -1], default=0)
    else:
        raise ValueError(f"Unknown RSI mode: {mode}")
    return pd.DataFrame({
        "close": pd.Series(close).astype(float),
        "rsi": rsi.astype(float),
        "trend_side": tside.astype(int),
        "signal": pd.Series(sig, index=pd.Series(close).index, dtype=int)
    })

def calculate_signal_confidence(rsi: float, trend_side: int, signal: int,
                                rsi_mode: str = "centerline",
                                rsi_centerline: float = 50,
                                rsi_oversold: float = 30,
                                rsi_overbought: float = 70) -> float:
    """
    Calculate confidence score for a trading signal based on RSI and trend alignment.
    
    Parameters
    ----------
    rsi : float
        RSI value (0-100)
    trend_side : int
        Trend direction: 1 (up), -1 (down), 0 (neutral)
    signal : int
        Trading signal: 1 (buy), -1 (sell), 0 (no trade)
    rsi_mode : str, default="centerline"
        RSI mode: "centerline" or "reversal"
    rsi_centerline : float, default=50
        Centerline threshold for centerline mode
    rsi_oversold : float, default=30
        Oversold threshold for reversal mode
    rsi_overbought : float, default=70
        Overbought threshold for reversal mode
        
    Returns
    -------
    float
        Confidence score between 0.0 and 1.0
    """
    if signal == 0:
        return 0.0
    
    confidence = 0.0
    
    if rsi_mode == "centerline":
        # For centerline mode: confidence based on distance from centerline
        # Adjusted divisor from 50 to 25 for more reasonable confidence scores
        if signal == 1:  # Buy signal
            # Higher confidence when RSI is well above centerline
            confidence = min((rsi - rsi_centerline) / 25.0, 1.0)
        elif signal == -1:  # Sell signal
            # Higher confidence when RSI is well below centerline
            confidence = min((rsi_centerline - rsi) / 25.0, 1.0)
    
    elif rsi_mode == "reversal":
        # For reversal mode: confidence based on distance from extreme
        if signal == 1:  # Buy signal (from oversold)
            # Higher confidence when close to oversold level
            distance_from_oversold = abs(rsi - rsi_oversold)
            confidence = max(1.0 - (distance_from_oversold / 30.0), 0.0)
        elif signal == -1:  # Sell signal (from overbought)
            # Higher confidence when close to overbought level
            distance_from_overbought = abs(rsi - rsi_overbought)
            confidence = max(1.0 - (distance_from_overbought / 30.0), 0.0)
    
    # Bonus confidence if signal aligns with trend
    if signal * trend_side > 0:  # Signal and trend in same direction
        confidence = min(confidence * 1.2, 1.0)
    elif signal * trend_side < 0:  # Signal and trend opposed
        confidence = confidence * 0.5
    
    return max(min(confidence, 1.0), 0.0)  # Ensure 0.0 <= confidence <= 1.0

def apply_guardrails(df: pd.DataFrame, cfg: dict, 
                    signal_col: str = "signal",
                    confidence_col: str = None) -> pd.DataFrame:
    """
    Apply guardrails to filter and limit trading signals.
    
    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with trading signals
    cfg : dict
        Strategy configuration with 'guardrails' section
    signal_col : str, default="signal"
        Name of column containing signal values (1=buy, -1=sell, 0=no trade)
    confidence_col : str, optional
        Name of column containing confidence scores (0.0-1.0)
        If None, no confidence filtering is applied
        
    Returns
    -------
    pd.DataFrame
        Filtered DataFrame respecting guardrails
    """
    guardrails = cfg.get("guardrails", {})
    
    # Make a copy to avoid modifying original
    result = df.copy()
    
    # Filter to only actual trade signals (non-zero)
    if signal_col in result.columns:
        trade_mask = result[signal_col] != 0
        trade_signals = result[trade_mask].copy()
        no_trade_signals = result[~trade_mask].copy()
    else:
        return result
    
    if trade_signals.empty:
        return result
    
    # Apply confidence threshold if confidence column exists
    if confidence_col and confidence_col in trade_signals.columns:
        confidence_threshold = float(guardrails.get("confidence_threshold", 0.6))
        trade_signals = trade_signals[
            trade_signals[confidence_col] >= confidence_threshold
        ]
    
    # Limit positions per day
    max_positions = int(guardrails.get("max_positions_per_day", 3))
    if confidence_col and confidence_col in trade_signals.columns:
        # Sort by confidence and keep top N
        trade_signals = trade_signals.nlargest(max_positions, confidence_col, keep="first")
    else:
        # Just take first N
        trade_signals = trade_signals.head(max_positions)
    
    # Combine back filtered trades with no-trade signals
    result = pd.concat([trade_signals, no_trade_signals], ignore_index=True)
    
    return result

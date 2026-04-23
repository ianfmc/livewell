"""
Unit tests for strategy_rsi.py

Tests each function with fixed test data and validates expected outcomes.
Run with: pytest tests/test_strategy_rsi.py -v
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))

import unittest
import numpy as np
import pandas as pd
from strategy_rsi import (
    rsi_wilder,
    macd,
    sma,
    trend_ok,
    generate_rsi_signals,
    calculate_signal_confidence,
    apply_guardrails
)


class TestRSIWilder(unittest.TestCase):
    """Test RSI calculation using Wilder's smoothing method."""
    
    def test_rsi_simple_uptrend(self):
        """Test RSI in a clear uptrend."""
        # Create realistic uptrend with some noise (50 points to ensure sufficient data)
        base = 100
        trend = [base + i*0.8 + np.random.uniform(-0.3, 0.3) for i in range(50)]
        prices = pd.Series(trend)
        rsi = rsi_wilder(prices, period=14)
        
        # RSI should be high (>50) in uptrend after warm-up
        # Check that RSI is valid (not NaN) and in expected range
        assert not pd.isna(rsi.iloc[-1]), f"RSI should not be NaN, got {rsi.iloc[-1]}"
        assert rsi.iloc[-1] > 50, f"Expected RSI > 50 in uptrend, got {rsi.iloc[-1]:.2f}"
        assert rsi.iloc[-1] <= 100, "RSI should be <= 100 (can be exactly 100 if no losses)"
    
    def test_rsi_simple_downtrend(self):
        """Test RSI in a clear downtrend."""
        # Create realistic downtrend with some noise (50 points to ensure sufficient data)
        base = 100
        trend = [base - i*0.8 + np.random.uniform(-0.3, 0.3) for i in range(50)]
        prices = pd.Series(trend)
        rsi = rsi_wilder(prices, period=14)
        
        # RSI should be low (<50) in downtrend
        # Check that RSI is valid (not NaN) and in expected range
        assert not pd.isna(rsi.iloc[-1]), f"RSI should not be NaN, got {rsi.iloc[-1]}"
        assert rsi.iloc[-1] < 50, f"Expected RSI < 50 in downtrend, got {rsi.iloc[-1]:.2f}"
        assert rsi.iloc[-1] >= 0, "RSI should be >= 0"
    
    def test_rsi_sideways(self):
        """Test RSI in sideways market."""
        # Prices oscillating around 100 with equal ups and downs
        # Create a more balanced pattern: up 1, down 1, repeated
        prices = pd.Series([100, 101, 100, 99, 100, 101, 100, 99, 100, 101, 
                           100, 99, 100, 101, 100, 99, 100, 101, 100, 99,
                           100, 101, 100, 99, 100, 101, 100, 99, 100, 101])
        rsi = rsi_wilder(prices, period=14)
        
        # RSI should be near 50 in sideways market (allow wider range)
        assert 40 < rsi.iloc[-1] < 60, f"Expected RSI near 50 in sideways market, got {rsi.iloc[-1]:.2f}"
    
    def test_rsi_length_matches_input(self):
        """Test that RSI output has same length as input."""
        prices = pd.Series(range(100, 150))
        rsi = rsi_wilder(prices, period=14)
        assert len(rsi) == len(prices), "RSI length should match price length"


class TestMACD(unittest.TestCase):
    """Test MACD calculation."""
    
    def test_macd_uptrend(self):
        """Test MACD in uptrend shows positive values."""
        # Strong uptrend
        prices = pd.Series([100 + i*2 for i in range(50)])
        line, signal, hist = macd(prices, fast=12, slow=26, signal=9)
        
        # In uptrend, MACD line should be above signal line
        assert line.iloc[-1] > signal.iloc[-1], "MACD line should be above signal in uptrend"
        assert hist.iloc[-1] > 0, "MACD histogram should be positive in uptrend"
    
    def test_macd_downtrend(self):
        """Test MACD in downtrend shows negative values."""
        # Strong downtrend
        prices = pd.Series([100 - i*2 for i in range(50)])
        line, signal, hist = macd(prices, fast=12, slow=26, signal=9)
        
        # In downtrend, MACD line should be below signal line
        assert line.iloc[-1] < signal.iloc[-1], "MACD line should be below signal in downtrend"
        assert hist.iloc[-1] < 0, "MACD histogram should be negative in downtrend"
    
    def test_macd_length_matches_input(self):
        """Test that MACD outputs have same length as input."""
        prices = pd.Series(range(100, 150))
        line, signal, hist = macd(prices)
        assert len(line) == len(prices), "MACD line length should match price length"
        assert len(signal) == len(prices), "MACD signal length should match price length"
        assert len(hist) == len(prices), "MACD histogram length should match price length"


class TestTrendOk(unittest.TestCase):
    """Test trend detection logic."""
    
    def test_trend_none(self):
        """Test that trend='none' returns all zeros."""
        prices = pd.Series(range(100, 150))
        cfg = {"trend": {"type": "none"}}
        trend = trend_ok(prices, cfg)
        
        assert all(trend == 0), "Trend should be 0 when type='none'"
    
    def test_trend_macd_uptrend(self):
        """Test MACD trend detection in uptrend."""
        # Strong uptrend
        prices = pd.Series([100 + i*2 for i in range(50)])
        cfg = {
            "trend": {
                "type": "macd",
                "macd_fast": 12,
                "macd_slow": 26,
                "macd_signal": 9
            }
        }
        trend = trend_ok(prices, cfg)
        
        # Should show uptrend (1) at the end
        assert trend.iloc[-1] == 1, f"Expected uptrend (1), got {trend.iloc[-1]}"
    
    def test_trend_macd_downtrend(self):
        """Test MACD trend detection in downtrend."""
        # Strong downtrend
        prices = pd.Series([100 - i*2 for i in range(50)])
        cfg = {
            "trend": {
                "type": "macd",
                "macd_fast": 12,
                "macd_slow": 26,
                "macd_signal": 9
            }
        }
        trend = trend_ok(prices, cfg)
        
        # Should show downtrend (-1) at the end
        assert trend.iloc[-1] == -1, f"Expected downtrend (-1), got {trend.iloc[-1]}"
    
    def test_trend_sma_uptrend(self):
        """Test SMA trend detection in uptrend."""
        # Strong uptrend
        prices = pd.Series([100 + i for i in range(60)])
        cfg = {
            "trend": {
                "type": "sma",
                "sma_window": 50
            }
        }
        trend = trend_ok(prices, cfg)
        
        # Should show uptrend (1) at the end
        assert trend.iloc[-1] == 1, f"Expected uptrend (1), got {trend.iloc[-1]}"


class TestGenerateRSISignals(unittest.TestCase):
    """Test signal generation in both centerline and reversal modes."""
    
    def test_centerline_mode_buy_signal(self):
        """Test buy signal in centerline mode with uptrend."""
        # Create strong consistent uptrend (+2 per day for 50 days)
        prices = pd.Series([100 + i*2.0 for i in range(50)])
        cfg = {
            "rsi": {"mode": "centerline", "period": 14, "centerline": 50},
            "trend": {"type": "macd", "macd_fast": 12, "macd_slow": 26, "macd_signal": 9}
        }
        
        signals = generate_rsi_signals(prices, cfg)
        
        # Debug: Print last few rows to see what's happening
        print("\n=== DEBUG: test_centerline_mode_buy_signal ===")
        print(f"Last price: {prices.iloc[-1]}")
        print(f"Last 5 signals:\n{signals.tail()}")
        print(f"RSI last: {signals['rsi'].iloc[-1]}")
        print(f"Trend side last: {signals['trend_side'].iloc[-1]}")
        print(f"Signal last: {signals['signal'].iloc[-1]}")
        
        # Should generate buy signal (1) at the end
        assert signals['signal'].iloc[-1] == 1, f"Expected buy signal (1), got {signals['signal'].iloc[-1]}"
        assert signals['rsi'].iloc[-1] > 50, "RSI should be > 50 for buy signal"
        assert signals['trend_side'].iloc[-1] == 1, "Trend should be up (1)"
    
    def test_centerline_mode_sell_signal(self):
        """Test sell signal in centerline mode with downtrend."""
        # Create downtrend with RSI < 50
        prices = pd.Series([100 - i*0.5 for i in range(50)])
        cfg = {
            "rsi": {"mode": "centerline", "period": 14, "centerline": 50},
            "trend": {"type": "macd", "macd_fast": 12, "macd_slow": 26, "macd_signal": 9}
        }
        
        signals = generate_rsi_signals(prices, cfg)
        
        # Should generate sell signal (-1) at the end
        assert signals['signal'].iloc[-1] == -1, f"Expected sell signal (-1), got {signals['signal'].iloc[-1]}"
        assert signals['rsi'].iloc[-1] < 50, "RSI should be < 50 for sell signal"
        assert signals['trend_side'].iloc[-1] == -1, "Trend should be down (-1)"
    
    def test_reversal_mode_oversold_buy(self):
        """Test buy signal in reversal mode from oversold."""
        # Create price drop then recovery
        prices = pd.Series(
            [100] * 10 + [95 - i for i in range(10)] + [85 + i*0.5 for i in range(10)]
        )
        cfg = {
            "rsi": {
                "mode": "reversal",
                "period": 14,
                "oversold": 30,
                "overbought": 70,
                "require_cross": True
            },
            "trend": {"type": "none"}
        }
        
        signals = generate_rsi_signals(prices, cfg)
        
        # Should have at least one buy signal when crossing above oversold
        buy_signals = signals[signals['signal'] == 1]
        assert len(buy_signals) > 0, "Should generate buy signal when crossing above oversold"
    
    def test_signal_dataframe_structure(self):
        """Test that signal DataFrame has correct structure."""
        prices = pd.Series(range(100, 150))
        cfg = {
            "rsi": {"mode": "centerline", "period": 14, "centerline": 50},
            "trend": {"type": "none"}
        }
        
        signals = generate_rsi_signals(prices, cfg)
        
        assert 'close' in signals.columns, "Should have 'close' column"
        assert 'rsi' in signals.columns, "Should have 'rsi' column"
        assert 'trend_side' in signals.columns, "Should have 'trend_side' column"
        assert 'signal' in signals.columns, "Should have 'signal' column"
        assert len(signals) == len(prices), "Signal length should match price length"


class TestCalculateSignalConfidence(unittest.TestCase):
    """Test confidence score calculation."""
    
    def test_no_signal_zero_confidence(self):
        """Test that no signal (0) returns 0 confidence."""
        confidence = calculate_signal_confidence(
            rsi=50, trend_side=0, signal=0, rsi_mode="centerline"
        )
        assert confidence == 0.0, "No signal should have 0 confidence"
    
    def test_centerline_buy_strong_confidence(self):
        """Test high confidence for strong buy signal in centerline mode."""
        # RSI 75 (25 points above centerline 50), buy signal, aligned with uptrend
        confidence = calculate_signal_confidence(
            rsi=75.0,
            trend_side=1,
            signal=1,
            rsi_mode="centerline",
            rsi_centerline=50
        )
        
        # Base: (75-50)/25 = 1.0, with trend bonus: 1.0 * 1.2 = 1.2, capped at 1.0
        assert confidence == 1.0, f"Expected confidence 1.0, got {confidence:.2f}"
    
    def test_centerline_buy_moderate_confidence(self):
        """Test moderate confidence for buy signal in centerline mode."""
        # RSI 57.5 (7.5 points above centerline 50), buy signal, aligned with uptrend
        confidence = calculate_signal_confidence(
            rsi=57.5,
            trend_side=1,
            signal=1,
            rsi_mode="centerline",
            rsi_centerline=50
        )
        
        # Base: (57.5-50)/25 = 0.3, with trend bonus: 0.3 * 1.2 = 0.36
        expected = 0.3 * 1.2
        assert abs(confidence - expected) < 0.01, f"Expected confidence ~{expected:.2f}, got {confidence:.2f}"
    
    def test_centerline_buy_against_trend(self):
        """Test reduced confidence when signal opposes trend."""
        # RSI 60, buy signal, but downtrend
        confidence = calculate_signal_confidence(
            rsi=60.0,
            trend_side=-1,
            signal=1,
            rsi_mode="centerline",
            rsi_centerline=50
        )
        
        # Base: (60-50)/25 = 0.4, against trend: 0.4 * 0.5 = 0.2
        expected = 0.4 * 0.5
        assert abs(confidence - expected) < 0.01, f"Expected confidence ~{expected:.2f}, got {confidence:.2f}"
    
    def test_centerline_sell_confidence(self):
        """Test confidence for sell signal in centerline mode."""
        # RSI 40 (10 points below centerline 50), sell signal, aligned with downtrend
        confidence = calculate_signal_confidence(
            rsi=40.0,
            trend_side=-1,
            signal=-1,
            rsi_mode="centerline",
            rsi_centerline=50
        )
        
        # Base: (50-40)/25 = 0.4, with trend bonus: 0.4 * 1.2 = 0.48
        expected = 0.4 * 1.2
        assert abs(confidence - expected) < 0.01, f"Expected confidence ~{expected:.2f}, got {confidence:.2f}"
    
    def test_reversal_mode_oversold_buy(self):
        """Test confidence for buy from oversold in reversal mode."""
        # RSI just above oversold level (32), should have high confidence
        confidence = calculate_signal_confidence(
            rsi=32.0,
            trend_side=0,
            signal=1,
            rsi_mode="reversal",
            rsi_oversold=30,
            rsi_overbought=70
        )
        
        # Distance from oversold: |32-30| = 2, confidence: 1 - (2/30) = 0.933
        expected = 1.0 - (2.0 / 30.0)
        assert abs(confidence - expected) < 0.01, f"Expected confidence ~{expected:.2f}, got {confidence:.2f}"
    
    def test_confidence_bounds(self):
        """Test that confidence is always between 0 and 1."""
        # Test extreme values
        for rsi in [0, 25, 50, 75, 100]:
            for trend in [-1, 0, 1]:
                for sig in [-1, 1]:
                    confidence = calculate_signal_confidence(
                        rsi=float(rsi),
                        trend_side=trend,
                        signal=sig,
                        rsi_mode="centerline"
                    )
                    assert 0.0 <= confidence <= 1.0, \
                        f"Confidence {confidence} out of bounds for RSI={rsi}, trend={trend}, signal={sig}"


class TestApplyGuardrails(unittest.TestCase):
    """Test guardrail filtering logic."""
    
    def test_confidence_threshold_filtering(self):
        """Test that signals below confidence threshold are filtered."""
        df = pd.DataFrame({
            'signal': [1, 1, -1, 1, 0],
            'Confidence': [0.5, 0.25, 0.4, 0.35, 0.0],
            'Ticker': ['A', 'B', 'C', 'D', 'E']
        })
        cfg = {
            'guardrails': {
                'confidence_threshold': 0.3,
                'max_positions_per_day': 10
            }
        }
        
        result = apply_guardrails(df, cfg, signal_col='signal', confidence_col='Confidence')
        
        # Should keep signals with confidence >= 0.3 (A, C, D)
        trades = result[result['signal'] != 0]
        assert len(trades) == 3, f"Expected 3 signals above threshold, got {len(trades)}"
        assert all(trades['Confidence'] >= 0.3), "All kept signals should have confidence >= 0.3"
    
    def test_max_positions_limiting(self):
        """Test that max positions per day is enforced."""
        df = pd.DataFrame({
            'signal': [1, 1, 1, 1, 1],
            'Confidence': [0.9, 0.8, 0.7, 0.6, 0.5],
            'Ticker': ['A', 'B', 'C', 'D', 'E']
        })
        cfg = {
            'guardrails': {
                'confidence_threshold': 0.3,
                'max_positions_per_day': 3
            }
        }
        
        result = apply_guardrails(df, cfg, signal_col='signal', confidence_col='Confidence')
        
        # Should keep only top 3 by confidence
        trades = result[result['signal'] != 0]
        assert len(trades) == 3, f"Expected max 3 positions, got {len(trades)}"
        assert list(trades['Ticker']) == ['A', 'B', 'C'], "Should keep top 3 by confidence"
    
    def test_combined_filtering(self):
        """Test confidence threshold + max positions together."""
        df = pd.DataFrame({
            'signal': [1, 1, 1, 1, 1, 0],
            'Confidence': [0.9, 0.5, 0.25, 0.35, 0.8, 0.0],
            'Ticker': ['A', 'B', 'C', 'D', 'E', 'F']
        })
        cfg = {
            'guardrails': {
                'confidence_threshold': 0.3,
                'max_positions_per_day': 2
            }
        }
        
        result = apply_guardrails(df, cfg, signal_col='signal', confidence_col='Confidence')
        
        # Should filter to confidence >= 0.3 (A, B, D, E), then keep top 2 (A, E)
        trades = result[result['signal'] != 0]
        assert len(trades) == 2, f"Expected 2 positions after filtering, got {len(trades)}"
        assert list(trades['Ticker']) == ['A', 'E'], "Should keep top 2 by confidence above threshold"
    
    def test_preserves_no_trade_signals(self):
        """Test that signals with value 0 are preserved."""
        df = pd.DataFrame({
            'signal': [1, 0, 0, 1],
            'Confidence': [0.5, 0.0, 0.0, 0.4],
            'Ticker': ['A', 'B', 'C', 'D']
        })
        cfg = {
            'guardrails': {
                'confidence_threshold': 0.3,
                'max_positions_per_day': 5
            }
        }
        
        result = apply_guardrails(df, cfg, signal_col='signal', confidence_col='Confidence')
        
        # Should have 2 no-trade signals preserved
        no_trades = result[result['signal'] == 0]
        assert len(no_trades) == 2, "Should preserve no-trade signals"


class TestIntegration(unittest.TestCase):
    """Integration tests using complete workflow."""
    
    def test_full_workflow_uptrend(self):
        """Test complete workflow with uptrending data."""
        # Create strong uptrending price data (1.0 per day for consistent uptrend)
        prices = pd.Series([100 + i*1.0 for i in range(100)])
        
        cfg = {
            "rsi": {"mode": "centerline", "period": 14, "centerline": 50},
            "trend": {"type": "macd", "macd_fast": 12, "macd_slow": 26, "macd_signal": 9},
            "guardrails": {"confidence_threshold": 0.3, "max_positions_per_day": 3}
        }
        
        # Generate signals
        signals = generate_rsi_signals(prices, cfg)
        
        # Calculate confidence for last signal
        last = signals.iloc[-1]
        confidence = calculate_signal_confidence(
            rsi=float(last['rsi']),
            trend_side=int(last['trend_side']),
            signal=int(last['signal']),
            rsi_mode=cfg['rsi']['mode'],
            rsi_centerline=cfg['rsi']['centerline']
        )
        
        # Verify expectations
        assert last['signal'] == 1, "Should generate buy signal in uptrend"
        assert last['rsi'] > 50, "RSI should be above centerline"
        assert last['trend_side'] == 1, "Trend should be up"
        assert confidence >= 0.3, f"Confidence should be >= 0.3, got {confidence:.2f}"
    
    def test_full_workflow_downtrend(self):
        """Test complete workflow with downtrending data."""
        # Create downtrending price data
        prices = pd.Series([100 - i*0.3 for i in range(60)])
        
        cfg = {
            "rsi": {"mode": "centerline", "period": 14, "centerline": 50},
            "trend": {"type": "macd", "macd_fast": 12, "macd_slow": 26, "macd_signal": 9},
            "guardrails": {"confidence_threshold": 0.3, "max_positions_per_day": 3}
        }
        
        # Generate signals
        signals = generate_rsi_signals(prices, cfg)
        
        # Calculate confidence for last signal
        last = signals.iloc[-1]
        confidence = calculate_signal_confidence(
            rsi=float(last['rsi']),
            trend_side=int(last['trend_side']),
            signal=int(last['signal']),
            rsi_mode=cfg['rsi']['mode'],
            rsi_centerline=cfg['rsi']['centerline']
        )
        
        # Verify expectations
        assert last['signal'] == -1, "Should generate sell signal in downtrend"
        assert last['rsi'] < 50, "RSI should be below centerline"
        assert last['trend_side'] == -1, "Trend should be down"
        assert confidence >= 0.3, f"Confidence should be >= 0.3, got {confidence:.2f}"


if __name__ == "__main__":
    # Run tests with pytest if available, otherwise basic runner
    try:
        import pytest
        pytest.main([__file__, "-v", "--tb=short"])
    except ImportError:
        print("pytest not installed. Install with: pip install pytest")
        print("Running basic tests...")
        
        # Basic test runner
        import unittest
        loader = unittest.TestLoader()
        suite = loader.loadTestsFromModule(sys.modules[__name__])
        runner = unittest.TextTestRunner(verbosity=2)
        runner.run(suite)

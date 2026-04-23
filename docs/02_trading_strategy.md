# 02 Trading Strategy

## Purpose

This document defines the production trading logic for LIVEWELL. It converts raw market context into candidate trade setups through deterministic technical analysis rules, feasibility filters, and session-aware gating. Machine learning may later refine probabilities, but this strategy layer defines what a technically valid setup looks like before any model-based ranking occurs.

## Strategy Philosophy

The strategy is built on a simple principle:

> Trade only when trend, momentum, volatility, and timing align.

That means:
- do not trade based on a single indicator,
- do not ignore broader trend,
- do not recommend strikes that require unrealistic moves,
- do not treat every bullish signal as equally tradable.

The strategy uses four main indicator families:
- EMAs for direction,
- MACD for trend confirmation and momentum shift,
- RSI for timing and momentum bias,
- ATR for volatility feasibility.

## Indicator Set

## 1. Exponential Moving Averages (EMA)

EMAs define trend direction and structural bias.

### Formula

For period `N`:

```text
EMA_today = α * Price_today + (1 - α) * EMA_yesterday
α = 2 / (N + 1)
```

Because EMAs weight recent prices more heavily than SMAs, they are better suited for shorter-horizon tactical trading.

### Role in LIVEWELL

Use a fast EMA and a slow EMA to define directional bias.

Suggested starting configurations:
- intraday tactical view: 7 / 26 or 10 / 30
- development may tune this later by pair and timeframe

### Trend interpretation

Bullish:
- EMA_fast > EMA_slow
- preferably price above both

Bearish:
- EMA_fast < EMA_slow
- preferably price below both

### Production use

EMA is not a standalone trade trigger. It is the trend filter that determines whether the system should even consider:
- buy-side binaries,
- sell-side binaries,
- or no trade.

## 2. MACD

MACD adds both trend confirmation and momentum transition logic.

### Standard construction

```text
MACD line = EMA(12) - EMA(26)
Signal line = EMA(9) of MACD line
Histogram = MACD line - Signal line
```

### Interpretation

Bullish:
- MACD line crosses above signal line,
- histogram turns positive or begins rising,
- MACD above zero indicates stronger trend alignment.

Bearish:
- MACD line crosses below signal line,
- histogram turns negative or begins falling,
- MACD below zero indicates stronger downtrend alignment.

### Production role

MACD is used for:
- confirming trend continuation,
- detecting momentum shift after a pullback,
- filtering false EMA-only setups,
- measuring whether the move is accelerating or fading.

## 3. RSI

RSI is used to assess momentum bias and entry timing.

### Standard formula

```text
RSI = 100 - 100 / (1 + RS)
RS = average_gain / average_loss
```

Usually calculated over 14 periods.

### Interpretation

- RSI > 50: bullish momentum bias
- RSI < 50: bearish momentum bias
- RSI > 70: overbought / potentially extended
- RSI < 30: oversold / potentially extended

### Production role

RSI helps answer:
- is momentum aligned with direction?
- is the setup already overextended?
- is a pullback ending and trend resuming?

LIVEWELL should especially value:
- RSI rising back above 50 in an uptrend,
- RSI falling back below 50 in a downtrend,
- recovery from oversold within bullish context,
- rollover from overbought within bearish context.

## 4. ATR

ATR is used for feasibility, not direction.

### Construction

True Range for each bar is:

```text
max(
    high - low,
    abs(high - previous_close),
    abs(low - previous_close)
)
```

ATR is the moving average of true range, commonly over 14 periods.

### Production role

ATR answers:
- how far is the market likely to move over the recommendation horizon?
- is the strike realistically reachable?
- is current volatility too low to justify a directional binary?

This is critical in NADEX because a contract can be “correct directionally” but still poorly chosen if the strike is too far away.

## Core Signal Architecture

The production strategy should use a staged pipeline rather than a single “if” statement.

### Stage 1: Trend filter

Determine whether the market is:
- bullish,
- bearish,
- neutral / noisy.

Suggested logic:

Bullish trend:
- EMA_fast > EMA_slow
- price >= EMA_fast
- slope of EMA_fast non-negative

Bearish trend:
- EMA_fast < EMA_slow
- price <= EMA_fast
- slope of EMA_fast non-positive

Neutral:
- frequent crossovers,
- flat EMA spread,
- inconsistent momentum.

Neutral markets should usually be filtered out.

### Stage 2: Momentum confirmation

In bullish trend:
- RSI > 50 or rising through 50
- MACD histogram rising
- MACD line crossing up or already above signal line

In bearish trend:
- RSI < 50 or falling through 50
- MACD histogram falling
- MACD line crossing down or already below signal line

### Stage 3: Overextension check

Reject or down-rank entries where:
- bullish setup but RSI is already extremely high and flattening,
- bearish setup but RSI is already extremely low and flattening,
- momentum appears exhausted rather than beginning.

### Stage 4: ATR feasibility check

Before recommending a strike:
- compute expected move envelope using ATR and time horizon,
- reject strikes requiring outsized move relative to normal range,
- prefer near-the-money or modestly out-of-the-money strikes that are reachable.

### Stage 5: Session and event filter

Reject or defer signals when:
- liquidity is low,
- spread is likely wide,
- major scheduled release is imminent,
- price behavior is unstable in a way that invalidates technical setup quality.

## Canonical Production Setup Rules

## Bullish setup

A long / buy-side candidate is valid when all of the following are true:

1. `EMA_fast > EMA_slow`
2. price is at or above the fast EMA
3. `RSI > 50` or just crossed upward through 50
4. MACD histogram is increasing
5. MACD line is above signal line, or crossing above it
6. chosen strike is within ATR-based feasible range
7. market is in an acceptable session / not inside a no-trade macro window

Optional stronger bullish variant:
- MACD near or above zero,
- recent pullback has already stabilized,
- price has resumed trend.

## Bearish setup

A short / sell-side candidate is valid when all of the following are true:

1. `EMA_fast < EMA_slow`
2. price is at or below the fast EMA
3. `RSI < 50` or just crossed downward through 50
4. MACD histogram is decreasing
5. MACD line is below signal line, or crossing below it
6. strike is reachable within ATR logic
7. acceptable time-of-day and macro conditions

## Mean-reversion-with-trend logic

The design also supports a useful pattern:
- market is in established trend,
- RSI temporarily moves against that trend,
- then momentum snaps back in trend direction.

Examples:
- uptrend + RSI dips into weak zone + recovers = buy pullback
- downtrend + RSI rallies temporarily + rolls over = sell rally

This often produces better entries than chasing already-extended moves.

## Strike Selection Logic

A good signal still fails if paired with a poor strike.

### Production strike rules

For a bullish recommendation:
- choose the first plausible strike above current price or near ATM,
- avoid strikes materially beyond expected daily move unless momentum is exceptional.

For a bearish recommendation:
- choose the first plausible strike below current price or near ATM,
- avoid distant downside strikes unless volatility justifies them.

### ATR-guided heuristic

Examples:
- if daily ATR implies roughly 50 pips expected movement, avoid recommending a strike 100 pips away for ordinary daily setup,
- if intraday ATR is compressed, prefer nearer strikes or no trade.

## Ranking Logic

When multiple valid setups exist, rank them by a composite score such as:

```text
signal_score =
    trend_strength_score
    + momentum_alignment_score
    + volatility_feasibility_score
    + session_quality_score
    - overextension_penalty
```

Later, model probability can replace or augment this ranking.

## No-Trade Conditions

Production-grade systems need explicit no-trade logic. LIVEWELL should reject setups when any of the following hold:

- EMA structure is flat or noisy,
- MACD and RSI disagree sharply,
- ATR too low for strike feasibility,
- contract spread too wide,
- major news imminent,
- signal occurs in poor liquidity window,
- expected value negative even though technicals look decent,
- insufficient data quality.

A robust “no trade” decision is a feature, not a failure.

## Suggested Deterministic Signal Schema

Each candidate should be represented in structured form:

```json
{
  "pair": "EUR/USD",
  "timestamp": "2026-04-22T08:00:00Z",
  "trend_bias": "bullish",
  "ema_fast": 1.1021,
  "ema_slow": 1.1008,
  "rsi_14": 56.3,
  "macd_line": 0.0008,
  "macd_signal": 0.0005,
  "macd_hist": 0.0003,
  "atr_14": 0.0047,
  "session_quality": "high",
  "macro_window_blocked": false,
  "strike_candidate": 1.1040,
  "technical_valid": true,
  "technical_reasoning": [
    "EMA fast above EMA slow",
    "RSI above 50",
    "MACD histogram rising",
    "Strike within ATR-adjusted range"
  ]
}
```

## Reference Implementation Sketch

```python
def bullish_setup(features: dict) -> bool:
    return (
        features["ema_fast"] > features["ema_slow"]
        and features["price"] >= features["ema_fast"]
        and features["rsi_14"] > 50
        and features["macd_hist"] > 0
        and features["macd_line"] >= features["macd_signal"]
        and features["atr_feasible"]
        and features["session_ok"]
        and not features["macro_blocked"]
    )
```

A symmetrical bearish function should also exist.

## Relationship to Machine Learning

This strategy layer should remain useful even when ML is added.

Recommended production approach:
- rules define valid setup universe,
- ML estimates outcome probability within that universe,
- expected value and market price determine final recommendation.

That is stronger than allowing an unconstrained model to recommend trades in technically incoherent conditions.

## Bottom Line

The strategy layer is where LIVEWELL earns discipline.

Its production role is to make sure recommendations are:
- technically coherent,
- volatility-aware,
- session-aware,
- strike-aware,
- and capable of being explained.

Machine learning can improve ranking and calibration, but it should sit on top of this logic, not replace it prematurely.

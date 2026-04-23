# 01 Market Model

## Purpose

This document defines the market semantics that LIVEWELL must respect when generating NADEX forex binary recommendations. It is the foundational layer of the system because every later decision depends on understanding how contract price, probability, risk, reward, and time-to-expiry interact.

## NADEX Binary Options: Core Mechanics

NADEX binary options settle at either 0 or 100. That simple settlement structure is the reason they can be modeled cleanly as probability instruments.

### Buy-side payoff

If a trader buys a binary contract at price `P`:

- maximum risk = `P`
- maximum profit = `100 - P`

Example:
- buy at 49
- max risk = 49
- max profit = 51

### Sell-side payoff

If a trader sells a binary contract at price `P`:

- maximum profit = `P`
- maximum loss = `100 - P`

Example:
- sell at 30
- max profit = 30
- max loss = 70

These hard caps make risk and reward knowable in advance. LIVEWELL should preserve that property by making every recommendation explicit about expected entry price, max loss, and max profit.

## Price as Implied Probability

The most important modeling concept is that NADEX contract price approximates the market-implied probability of the event occurring.

Examples:
- price 50 ≈ 50% implied probability
- price 30 ≈ 30% implied probability
- price 80 ≈ 80% implied probability

In practice, the midpoint of bid and ask is usually the best quick estimate of market-implied probability.

Example:
- bid = 30
- ask = 32
- midpoint = 31
- implied probability ≈ 31%

From the seller’s perspective, the implied probability of being correct is roughly `100 - 31 = 69%`.

## Why this matters for LIVEWELL

LIVEWELL must not merely forecast direction. It must compare:

- **model-estimated probability**
- **market-implied probability**

A recommendation is only attractive when the system believes the true probability is materially better than the price implies.

### Decision rule concept

If:

```text
model_probability > market_implied_probability + required_edge
```

then the contract may be worth buying.

If:

```text
model_probability < market_implied_probability - required_edge
```

then the contract may be worth selling or avoiding on the buy side.

The required edge should absorb:
- model uncertainty,
- fees,
- slippage,
- calibration error.

## Expected Value Framing

A production recommendation engine should evaluate expected value, not raw directional conviction.

For a buy recommendation:

```text
EV_buy = p_model * (100 - entry_price) - (1 - p_model) * entry_price - fees
```

For a sell recommendation:

```text
EV_sell = (1 - p_model) * entry_price - p_model * (100 - entry_price) - fees
```

Where:
- `p_model` is model-estimated probability the condition finishes in the money for the buy side,
- `entry_price` is the chosen execution price or midpoint,
- `fees` are exchange and operational costs.

The system should reject trades where EV is non-positive or where the edge is too thin to trust.

## Risk/Reward Trade-off

Low-priced contracts offer high ROI if correct, but low probability of success.
High-priced contracts offer high probability of success, but low reward relative to risk.

### Low-price example

Buy at 20:
- risk 20
- reward 80
- high ROI if correct
- lower probability of success

### High-price example

Buy at 80:
- risk 80
- reward 20
- safer in probability terms
- poor reward-to-risk balance

LIVEWELL must therefore avoid both extremes unless the data strongly supports them.

Operationally, this means:
- avoid very cheap binaries unless momentum and volatility justify a large move,
- avoid very expensive binaries unless the probability edge is overwhelming.

## At-the-money and near-the-money interpretation

An at-the-money binary typically trades near 50 because the event is approximately 50/50.
Near-the-money or modestly out-of-the-money binaries are often the best candidates for a recommendation engine because:
- they offer enough payoff asymmetry to matter,
- they remain plausible within normal daily range.

This ties directly into ATR-based strike selection.

## Time and Market Session Considerations

The forex market trades nearly 24 hours during the work week, but not all hours are equally suitable for binary trading.

### Major sessions

Typical high-level session windows in Eastern Time:

- London: roughly 03:00–12:00 ET
- New York: roughly 08:00–17:00 ET
- Tokyo: roughly 19:00–04:00 ET
- Sydney: roughly 17:00–02:00 ET

### Most important overlap

The London / New York overlap, approximately 08:00–12:00 ET, is usually the most attractive window for major pairs such as EUR/USD and GBP/USD because:
- liquidity is highest,
- spreads are often tighter,
- price movement is more meaningful,
- major macro releases often occur around this window.

### Pair-specific timing

- EUR/USD and GBP/USD: strongest during London/New York overlap
- USD/JPY, EUR/JPY, GBP/JPY: Asian-to-European transition and U.S. morning can matter
- AUD/USD and NZD/USD: Asian session and Sydney/Tokyo overlap are more relevant

## Production filters based on session logic

LIVEWELL should include time-of-day gating, such as:

- prefer recommendation generation for active periods,
- down-rank or reject signals from low-liquidity periods,
- avoid recommendations immediately before major scheduled macro releases unless explicitly using a post-news strategy.

## News-awareness requirement

The original design identifies economic releases as a major source of abrupt volatility. Production-grade logic should therefore include at least a basic macro-event awareness layer.

The system does not need full news trading on day one, but it should know:
- when major scheduled releases occur,
- whether a recommendation is being generated too close to a known volatility event,
- whether spreads or expected noise likely invalidate an otherwise decent technical setup.

At minimum, maintain a calendar filter such as:
- reject new recommendations inside a configurable window before high-impact releases,
- optionally allow recommendations after volatility normalizes.

## Practical contract selection rules

A sound production system should not evaluate probabilities in the abstract only. It should also enforce contract selection rules such as:

1. use midpoint price as implied probability anchor,
2. reject strikes too far from current spot relative to ATR and time remaining,
3. prefer strikes that are within feasible daily range,
4. prefer contracts with adequate liquidity and tolerable spread.

## Market Model Requirements for Implementation

The code implementation should expose the following reusable functions:

### 1. Implied probability from price

```python
def implied_probability(price: float) -> float:
    return price / 100.0
```

### 2. Buy-side expected value

```python
def expected_value_buy(p_model: float, entry_price: float, fees: float = 0.0) -> float:
    return p_model * (100.0 - entry_price) - (1.0 - p_model) * entry_price - fees
```

### 3. Sell-side expected value

```python
def expected_value_sell(p_model: float, entry_price: float, fees: float = 0.0) -> float:
    return (1.0 - p_model) * entry_price - p_model * (100.0 - entry_price) - fees
```

### 4. Edge against market

```python
def probability_edge(p_model: float, market_price: float) -> float:
    return p_model - (market_price / 100.0)
```

## Production Design Implications

The market model imposes several non-negotiable constraints on LIVEWELL:

- every recommendation must include a price-aware probability comparison,
- every recommendation must include capped risk and capped reward,
- strike feasibility must be checked against expected move and time left,
- session timing must be part of validity logic,
- macro event awareness must exist, even if simple at first.

## Bottom Line

The market model is the governing logic of the entire system.

LIVEWELL should never emit a recommendation simply because “the model thinks price goes up.” It should emit a recommendation only when:
- the event is sufficiently likely,
- the contract price undervalues that likelihood,
- the strike is feasible within expected volatility,
- and market conditions are suitable for the trade to work before expiry.

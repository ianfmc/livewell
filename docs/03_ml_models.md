# 03 Machine Learning Models

## Purpose

This document defines how LIVEWELL should use machine learning to estimate binary option outcome probabilities in a way that is rigorous, explainable, and production-safe.

The core requirement is not “AI for its own sake.” The requirement is:

> estimate whether a candidate NADEX binary is mispriced relative to the true probability of the event occurring.

That makes this a supervised probabilistic classification problem.

## Problem Definition

Given:
- a forex pair,
- a timestamp,
- a candidate strike,
- an expiry horizon,
- a set of market and technical features,

predict:

```text
P(event finishes in the money)
```

Examples:
- probability that EUR/USD finishes above strike X by end of day,
- probability that GBP/USD settles below strike Y by a given intraday expiry.

The output of the model should therefore be a probability, not merely a class label.

## Role of ML in LIVEWELL

Machine learning is not the whole system. It is one layer in the recommendation process.

Recommended production sequence:
1. deterministic technical rules identify valid candidate setups,
2. ML estimates probability of success for each candidate,
3. market price provides implied probability,
4. expected value and edge determine whether to recommend.

This preserves interpretability and reduces the risk of unconstrained pattern fitting.

## Candidate Model Families

## 1. Logistic Regression

### Why it matters

Logistic regression is the best baseline model because it is:
- fast,
- interpretable,
- inherently probabilistic,
- less likely to overfit than more flexible methods on limited data.

### Strengths

- coefficients are human-readable,
- easy to train and recalibrate,
- supports probability output directly,
- works well when features are informative and relationships are roughly monotonic or linear in log-odds space.

### Weaknesses

- limited ability to capture non-linear interactions,
- may underfit if the true relationship is more complex,
- requires explicit interaction terms if those matter.

### Production use

Use logistic regression as:
- baseline benchmark,
- calibration reference,
- initial production model candidate.

If a more complex model does not materially outperform it out of sample, prefer logistic.

## 2. Random Forest

### Why it matters

Random forest is an excellent next-step model because it can capture:
- non-linear thresholds,
- interactions between features,
- conditional structures that hand-written rules may miss.

### Strengths

- stronger than logistic when interactions matter,
- relatively robust,
- moderate interpretability via feature importance and local explanation tools,
- strong performance on structured/tabular data.

### Weaknesses

- less interpretable than logistic,
- raw probabilities may require calibration,
- can overfit if trees are too deep,
- harder to reason about globally.

### Production use

Random forest is the leading candidate for a stronger production model after logistic regression. It is especially appropriate because LIVEWELL’s inputs are tabular engineered features rather than unstructured text or images.

## 3. LSTM

### Why it matters

LSTM introduces temporal sequence modeling. It can, in theory, capture richer sequential behavior across recent market history.

### Strengths

- models temporal dependencies,
- can ingest sequences of prior observations,
- may detect patterns not obvious in static features.

### Weaknesses

- requires more data,
- higher overfitting risk,
- much harder to interpret,
- significantly more tuning burden,
- often not worth the operational complexity unless it clearly outperforms simpler models.

### Production use

Do not use LSTM in the first production iteration unless testing shows a clear, durable advantage.
Treat it as an advanced-phase research path, not the default architecture.

## Feature Design

The best model will only be as good as the features. LIVEWELL should begin with structured, explainable features.

## Core technical features

- EMA fast
- EMA slow
- EMA spread
- EMA slope
- MACD line
- MACD signal
- MACD histogram
- RSI
- ATR
- normalized ATR
- price distance from strike
- price distance from EMA bands
- recent return measures
- session label / time-of-day bucket

## Contextual features

- day of week
- hours to expiry
- macro event proximity
- spread / liquidity proxy if available

## Optional sentiment features

Only add if validated:
- average news sentiment score,
- count of relevant headlines,
- sentiment dispersion,
- positioning / crowd sentiment.

## Label Construction

A production label must match the actual decision problem.

### Example label for buy-side binary

```text
y = 1 if final_spot > strike_at_expiry else 0
```

### Example label for sell-side binary

Depending on framing, either:
- invert the buy-side outcome,
- or keep one canonical event and interpret sell-side later through expected value logic.

Use one consistent event framing across the system so that probability comparisons remain clean.

## Recommended Modeling Targets

Two practical options exist.

### Option A: Pair-direction model

Predict whether the pair goes up or down over the horizon.

Pros:
- simpler,
- easier dataset construction.

Cons:
- less directly aligned to binary strike logic.

### Option B: Strike-specific event model

Predict probability that spot finishes beyond a strike at expiry.

Pros:
- directly aligned to NADEX contract decision,
- cleaner mapping to expected value.

Cons:
- more complex training data construction.

Production recommendation:
- start with pair-direction baseline if needed,
- move quickly toward strike-aware labeling because that is the actual business problem.

## Evaluation Framework

## Time-aware validation only

Never random-shuffle time series for model evaluation.

Use:
- rolling validation,
- walk-forward validation,
- expanding-window evaluation.

Example:
- train on early history,
- validate on later contiguous block,
- test on most recent unseen block.

## Metrics

Accuracy alone is not enough.

Recommended evaluation stack:
- Brier score for probability quality,
- log loss for calibration-aware classification quality,
- AUC for ranking quality,
- precision/recall at actionable threshold,
- simulated trade expected value,
- net P&L after fees,
- calibration plots.

A model that is slightly less accurate but much better calibrated may be more valuable for pricing decisions.

## Calibration

This is especially important for LIVEWELL because output probabilities are used directly against market prices.

Even if the classification model is good, the raw probability distribution may be poorly calibrated.
Therefore, production pipeline should consider:
- Platt scaling,
- isotonic regression,
- reliability diagrams.

A calibrated 0.62 needs to mean something close to 62%.

## Hyperparameter Tuning

Use constrained, disciplined tuning.

### Logistic regression
Tune:
- regularization strength,
- penalty type if applicable.

### Random forest
Tune:
- number of trees,
- max depth,
- min samples split / leaf,
- max features.

### LSTM
Tune sparingly:
- sequence length,
- hidden units,
- dropout,
- learning rate,
- batch size.

Avoid massive search spaces. Smaller, sensible searches reduce both compute cost and overfitting to the validation scheme.

## Model Selection Philosophy

Prefer:

```text
robust + explainable + calibrated > slightly better but fragile
```

Decision hierarchy:
1. if logistic is nearly as good as RF, choose logistic;
2. if RF is materially better and stable, choose RF;
3. only choose LSTM if it clearly wins and holds up over time-aware validation.

## Suggested Production Stack

### Phase 1
- rule-based signal generation only,
- no ML or minimal scoring.

### Phase 2
- logistic regression probability model,
- calibration step,
- side-by-side benchmark with deterministic rules.

### Phase 3
- random forest benchmark and possible promotion,
- full walk-forward comparison.

### Phase 4
- optional sequence models if justified.

## Training / Inference Separation

This is non-negotiable in production.

### Training pipeline responsibilities
- pull historical data,
- compute features,
- construct labels,
- run walk-forward evaluation,
- train candidate models,
- calibrate probabilities,
- persist artifacts and metrics.

### Inference pipeline responsibilities
- load latest approved model,
- compute current features,
- generate candidate probabilities,
- compare to live or stored market prices,
- emit recommendations.

The inference pipeline must not retrain models.

## Artifact Requirements

Persist the following:
- feature schema version,
- training date range,
- model type,
- hyperparameters,
- calibration method,
- validation metrics,
- serialized model,
- serialized scaler / transformer objects,
- recommendation thresholds used.

This supports reproducibility and rollback.

## Example Minimal Baseline Code

```python
from sklearn.linear_model import LogisticRegression

model = LogisticRegression(max_iter=1000)
model.fit(X_train, y_train)
p_hat = model.predict_proba(X_valid)[:, 1]
```

## Example Random Forest Baseline

```python
from sklearn.ensemble import RandomForestClassifier

model = RandomForestClassifier(
    n_estimators=200,
    max_depth=5,
    random_state=42,
)
model.fit(X_train, y_train)
p_hat = model.predict_proba(X_valid)[:, 1]
```

## Production Decision Thresholding

The model should not emit trades directly. Final recommendation logic should use:

```text
recommend if:
technical_valid
and calibrated_probability - market_implied_probability >= edge_threshold
and expected_value > 0
and risk filters pass
```

This architecture prevents models from being used in an operational vacuum.

## Bottom Line

For LIVEWELL, ML should serve three functions:
- estimate probability,
- improve ranking,
- calibrate confidence.

It should not replace the market model or strategy logic. The production path should begin with logistic regression, benchmark against random forest, and treat deeper sequence models as optional research until proven necessary.

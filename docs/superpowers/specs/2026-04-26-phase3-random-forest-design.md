# Phase 3 — Random Forest Benchmark Design

## Goal

Benchmark a random forest classifier against the Phase 2 logistic regression baseline (84% win rate, +0.51 EV per $1 risked) using an expanded feature set and the same walk-forward fold structure. Promote random forest to Phase 4 only if it beats logistic regression on both win rate and expected value.

## Scope

Research notebooks only. No production inference pipeline — that is Phase 4. No changes to existing Phase 2 notebooks.

## Architecture

One new notebook: `notebooks/livewell-nadex/notebooks/phase2/05_random_forest.ipynb`.

It loads the existing labeled dataset and fold assignments from Phase 2, builds an expanded feature matrix, trains default and tuned random forest models per fold, and produces a head-to-head comparison table and feature importance chart.

## Data and Features

**Source:** `../../../data/phase2/labeled_signals.parquet` — same file as notebook 02. Rows with `label=NaN` are dropped.

**Fold structure:** Same 6-month train / 1-month test walk-forward windows as Phase 2. Fold assignments are recomputed using the same `assign_walk_forward_folds` logic from notebook 02 (no dependency on notebook 02's output file — recompute in notebook 05 for self-containment).

**Feature matrix (11 features):**

| Feature | Source | Notes |
|---|---|---|
| `ema_ratio` | existing | ema_20 / ema_50 |
| `rsi_14` | existing | |
| `macd_hist` | existing | |
| `atr_14` | existing | |
| `session_quality_enc` | existing | label-encoded |
| `direction_enc` | existing | label-encoded |
| `signal_valid_enc` | existing | 0/1 |
| `ema_20` | new | raw value |
| `ema_50` | new | raw value |
| `macd` | new | raw value |
| `macd_signal` | new | raw value |
| `instrument_enc` | new | s3_key label-encoded 0–18 |

## Model Training

Two passes per fold, both using `sklearn.ensemble.RandomForestClassifier`:

**Pass 1 — Default RF**
- `n_estimators=100`, all other sklearn defaults
- Establishes an untuned baseline

**Pass 2 — Tuned RF**
- Grid search over train split only (no test data leakage):
  - `n_estimators`: [100, 300]
  - `max_depth`: [None, 10, 20]
  - `min_samples_leaf`: [1, 5, 10]
- Cross-validation on train split to select best params
- Best estimator applied to test split for final `prob_itm` predictions
- Feature importances recorded per fold

## Evaluation

**Per-fold metrics** (same as notebook 04):
- Top-50% by `prob_itm` selected as trades
- Win rate, Brier score, EV per $1 risked

**Summary outputs:**

1. **Head-to-head comparison table** — three rows (Logistic Regression, RF Default, RF Tuned), four columns (Trades selected, Win Rate, Brier Score, EV per $1). Logistic regression numbers taken from notebook 04 output (hardcoded as reference, not re-run).

2. **Feature importance chart** — bar chart of mean importance across all folds for the tuned RF, sorted descending. Shows which features the model relies on and whether new features add value.

## Promotion Rule

RF Tuned is considered for Phase 4 promotion only if it beats logistic regression on **both**:
- Win rate > 0.840
- EV per $1 > +0.512

If only one criterion is met, the result is noted in the notebook output and logistic regression remains the candidate for Phase 4.

## Files

- Create: `notebooks/livewell-nadex/notebooks/phase2/05_random_forest.ipynb`
- No changes to notebooks 01–04
- No changes to `apps/api`

## Out of Scope

- Window size experimentation (clean follow-on after promotion decision)
- Gradient boosting or other model types
- Production inference infrastructure
- Changes to the logistic regression model

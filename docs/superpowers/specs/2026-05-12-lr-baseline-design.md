# Phase 2 Logistic Regression Baseline — Design Spec

**Date:** 2026-05-12
**Status:** Approved

---

## Goal

Build the Phase 2 ML baseline: a logistic regression model trained on labeled historical signal data, registered in the model registry, and comparable against the existing rules-only system (18.8% win rate, 15,048 trades). Logistic regression is chosen first because its coefficients reveal which features are actually predictive before adding model complexity.

---

## Scope

Two sub-tasks, delivered in order:

1. **Label construction** — join backtest outcomes to signal features, write labeled Parquet to S3
2. **LR training** — train logistic regression with walk-forward validation, register artifact, print coefficients

---

## Architecture

```
notebooks/livewell-nadex/build_labels.ipynb
    └── reads s3://livewell-data-prod/backtest/summary.json  (trades list: signal_id + win)
    └── batch-fetches signal records from DynamoDB by signal_id
    └── joins on signal_id → adds label (1=win, 0=loss)
    └── writes s3://livewell-data-prod/labeled/signals_labeled.parquet

apps/api/livewell/models/train_lr.py
    └── run_lr_training() → (model, metrics, coef_df)
            └── loads labeled/*.parquet via existing _load_labeled_data()
            └── builds feature matrix via existing build_feature_vector()
            └── walk-forward validation via existing _walk_forward_split()
            └── trains LogisticRegression(C=1.0, class_weight="balanced", max_iter=1000)
            └── evaluates: win_rate, brier_score, ev per fold + final fold
            └── uploads joblib artifact to s3://.../models/lr_baseline/v{timestamp}.joblib
            └── registers under model_name="lr_baseline" in DynamoDB registry

notebooks/livewell-nadex/train_lr.ipynb
    └── calls run_lr_training()
    └── prints walk-forward metrics table
    └── prints feature coefficient table (sorted by abs value)
```

---

## Label Construction (`build_labels.ipynb`)

### Source

- `s3://livewell-data-prod/backtest/summary.json` — contains `trades` list produced by the most recent backtest run
- Each trade: `{signal_id, date, instrument, direction, strike, next_close, win, signal_valid, regime}`

### DynamoDB fetch

- Batch-get signal records from `livewell-signals-prod` by `signal_id` (25 per request, boto3 `batch_get_item`)
- Fields needed: `signal_id`, `s3_key`, `date`, `ema_20`, `ema_50`, `rsi_14`, `macd`, `macd_signal`, `macd_hist`, `atr_14`, `session_quality`, `direction`, `signal_valid`

### Output schema

Parquet written to `s3://livewell-data-prod/labeled/signals_labeled.parquet`:

| Column | Type | Source |
|--------|------|--------|
| `signal_id` | string | join key |
| `s3_key` | string | DynamoDB |
| `date` | string | DynamoDB |
| `ema_20` | float | DynamoDB |
| `ema_50` | float | DynamoDB |
| `rsi_14` | float | DynamoDB |
| `macd` | float | DynamoDB |
| `macd_signal` | float | DynamoDB |
| `macd_hist` | float | DynamoDB |
| `atr_14` | float | DynamoDB |
| `session_quality` | string | DynamoDB |
| `direction` | string | DynamoDB (call/put — must map back to buy/sell for feature encoding) |
| `signal_valid` | bool | DynamoDB |
| `label` | int | backtest `win`: True→1, False→0 |

### Direction mapping

The replay records store `direction` as `"call"` or `"put"`. `build_feature_vector()` expects `"buy"` or `"sell"` (the `_DIRECTION_ENC` dict). Label construction must map: `"call"` → `"buy"`, `"put"` → `"sell"` before writing the Parquet, so `train_lr.py` (and `train.py`) work without modification.

### Expected output

~15,048 rows, ~19% label=1, ~81% label=0.

---

## Logistic Regression Training (`train_lr.py`)

### Location

`apps/api/livewell/models/train_lr.py`

### Reused from `train.py`

- `_load_labeled_data()` — reads all Parquets from `s3://.../labeled/`
- `_build_xy()` — builds feature matrix via `build_feature_vector()`
- `_walk_forward_split()` — 6-month train, 1-month test sliding window
- `_upload_artifact()` — serialises joblib to S3 (path: `models/lr_baseline/v{timestamp}.joblib`)
- `register_model()` from `registry.py`

### Model

```python
LogisticRegression(
    C=1.0,
    class_weight="balanced",
    max_iter=1000,
    solver="lbfgs",
    random_state=42,
)
```

No `GridSearchCV` — C=1.0 is the baseline. Regularisation tuning is Phase 3 work.

### Walk-forward evaluation

Same fold structure as `train.py`: 6-month train, 1-month test, advancing 1 month at a time. Metrics per fold: win_rate (accuracy), Brier score, EV (top-half predicted probability vs actual win rate).

Final production model trained on **all** labeled data, not just the last fold.

### Coefficient output

After training, extract `model.coef_[0]` paired with `FEATURE_NAMES` and sort by absolute value. This is the primary interpretability output — tells you which features the model weighted.

### Registration

```python
register_model(
    model_name="lr_baseline",
    version=timestamp,
    s3_path="models/lr_baseline/v{timestamp}.joblib",
    features=FEATURE_NAMES,
    win_rate=final_fold_win_rate,
    ev=final_fold_ev,
    trained_at=now.isoformat(),
)
```

Registered under `"lr_baseline"` — separate from `"rf_tuned"` so both can coexist in the registry.

---

## Training Notebook (`train_lr.ipynb`)

3 cells:

**Cell 1 — Setup:**
```python
import sys, os
sys.path.insert(0, os.path.abspath("../../apps/api"))
import logging
logging.basicConfig(level=logging.INFO)
os.environ["LIVEWELL_BUCKET"] = "livewell-data-prod"
from livewell.models.train_lr import run_lr_training
```

**Cell 2 — Train:**
```python
model, metrics, coef_df = run_lr_training()
print(f"Final fold — win_rate: {metrics['win_rate']:.3f}, brier: {metrics['brier_score']:.3f}, ev: {metrics['ev']:.3f}")
```

**Cell 3 — Coefficients:**
```python
print(coef_df.to_string(index=False))
```

---

## Files

**Create:**
- `apps/api/livewell/models/train_lr.py`
- `apps/api/tests/models/test_train_lr.py`
- `notebooks/livewell-nadex/build_labels.ipynb`
- `notebooks/livewell-nadex/train_lr.ipynb`

**Unchanged:**
- `apps/api/livewell/models/train.py` (RF, untouched)
- `apps/api/livewell/models/features.py`
- `apps/api/livewell/models/inference.py`
- `apps/api/livewell/models/registry.py`

---

## Tests (`test_train_lr.py`)

All tests use moto + in-memory data. No live AWS calls.

- `test_run_lr_training_returns_model_and_metrics` — returns (model, dict, DataFrame) with expected keys
- `test_coef_df_has_all_feature_names` — coefficient DataFrame has one row per feature name
- `test_model_registered_in_dynamodb` — after training, registry has an `"lr_baseline"` record with status `"active"`
- `test_walk_forward_produces_multiple_folds` — with 18 months of data, at least 6 folds are evaluated

---

## Success Criteria

- Labeled Parquet written to S3 with ~15,048 rows
- `run_lr_training()` completes without error
- Coefficient table printed — at least one feature with meaningful weight (|coef| > 0.1)
- Model registered as `"lr_baseline"` in DynamoDB
- Win rate on final fold reported (no target — this is an honest baseline)
- Brier score < 0.25 (a random classifier scores ~0.155 at 19% base rate; lower is better)

# Phase 3 — Random Forest Benchmark Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `05_random_forest.ipynb` — a walk-forward benchmark of default and tuned random forest classifiers against the Phase 2 logistic regression baseline (84% win rate, +0.512 EV), using an expanded 12-feature matrix including instrument identity, raw EMA values, and full MACD components.

**Architecture:** Single new notebook in `notebooks/livewell-nadex/notebooks/phase2/`. Loads `labeled_signals.parquet`, recomputes fold assignments (self-contained, no dependency on notebook 02 output), builds expanded features, trains RF per fold, and produces a head-to-head comparison table and feature importance chart. No changes to notebooks 01–04 or `apps/api`.

**Tech Stack:** Python 3.12, pandas, scikit-learn (`RandomForestClassifier`, `GridSearchCV`), matplotlib, Jupyter (livewell-api kernel).

---

## File Structure

**Create:**
- `notebooks/livewell-nadex/notebooks/phase2/05_random_forest.ipynb`

**Read (reference, no changes):**
- `notebooks/livewell-nadex/notebooks/phase2/02_feature_prep.ipynb` — `encode_features` and `assign_walk_forward_folds` patterns
- `notebooks/livewell-nadex/notebooks/phase2/03_walk_forward_validation.ipynb` — `run_walk_forward` pattern
- `notebooks/livewell-nadex/notebooks/phase2/04_calibration_analysis.ipynb` — `summarise_metrics` pattern

---

## Task 1: Create notebook with imports, config, and feature prep

**Files:**
- Create: `notebooks/livewell-nadex/notebooks/phase2/05_random_forest.ipynb`

- [ ] **Step 1: Create notebook cell 1 — imports and config**

Create the notebook with its first cell containing all imports and constants:

```python
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import GridSearchCV

INPUT_PATH = "../../../data/phase2/labeled_signals.parquet"

# Phase 2 logistic regression baseline (from notebook 04)
LR_TRADES    = 444
LR_WIN_RATE  = 0.840
LR_BRIER     = 0.1440
LR_EV        = 0.5122

NADEX_WIN_PAYOUT = 0.80
NADEX_LOSS_COST  = 1.00

EXISTING_FEATURES = [
    "ema_ratio", "rsi_14", "macd_hist", "atr_14",
    "session_quality_enc", "direction_enc", "signal_valid_enc",
]
NEW_FEATURES = ["ema_20", "ema_50", "macd", "macd_signal", "instrument_enc"]
FEATURE_COLS = EXISTING_FEATURES + NEW_FEATURES
LABEL_COL = "label"
META_COLS = ["date", "s3_key", "fold", "split"]
```

- [ ] **Step 2: Create notebook cell 2 — feature encoding and fold assignment**

Add a second cell with the feature prep functions (self-contained — no import from notebook 02):

```python
def encode_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add derived and encoded columns. Returns new DataFrame."""
    out = df.copy()
    out["ema_ratio"]           = out["ema_20"] / out["ema_50"]
    out["session_quality_enc"] = out["session_quality"].map({"high": 2, "medium": 1, "low": 0})
    out["direction_enc"]       = out["direction"].map({"buy": 1, "sell": -1, "none": 0})
    out["signal_valid_enc"]    = out["signal_valid"].astype(int)
    le = LabelEncoder()
    out["instrument_enc"]      = le.fit_transform(out["s3_key"])
    return out


def assign_walk_forward_folds(
    df: pd.DataFrame,
    train_months: int = 6,
    test_months: int = 1,
) -> pd.DataFrame:
    """
    Assign walk-forward fold metadata to each row.

    For each fold N:
      - test:  rows where date falls in [fold_start + train_months,
                                         fold_start + train_months + test_months)
      - train: rows where date falls in [fold_start, fold_start + train_months)
               AND the row is not already assigned to a test split

    Rows that don't fall into any fold's test window get fold=-1, split="unused".
    """
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df["fold"]  = -1
    df["split"] = "unused"

    min_date = df["date"].min().to_period("M")
    max_date = df["date"].max().to_period("M")
    month_period = df["date"].dt.to_period("M")

    fold_idx = 0
    cursor = min_date
    fold_windows = []
    while True:
        train_start = cursor
        train_end   = cursor + train_months
        test_start  = train_end
        test_end    = train_end + test_months
        if test_end > max_date + 1:
            break
        fold_windows.append((fold_idx, train_start, train_end, test_start, test_end))
        test_mask = (month_period >= test_start) & (month_period < test_end)
        df.loc[test_mask, "fold"]  = fold_idx
        df.loc[test_mask, "split"] = "test"
        fold_idx += 1
        cursor += test_months

    for fold_idx, train_start, train_end, test_start, test_end in fold_windows:
        train_mask = (
            (month_period >= train_start) &
            (month_period <  train_end) &
            (df["split"] != "test")
        )
        df.loc[train_mask, "fold"]  = fold_idx
        df.loc[train_mask, "split"] = "train"

    return df


def prepare_features(df: pd.DataFrame) -> pd.DataFrame:
    """Drop NaN labels, encode features, assign folds. Returns model-ready DataFrame."""
    df = df[df["label"].notna()].copy()
    df = encode_features(df)
    df = assign_walk_forward_folds(df)
    keep = META_COLS + FEATURE_COLS + [LABEL_COL]
    return df[keep].reset_index(drop=True)
```

- [ ] **Step 3: Create notebook cell 3 — load and prep data**

```python
raw = pd.read_parquet(INPUT_PATH)
prepped = prepare_features(raw)

print(f"Total rows after dropping direction=none: {len(prepped)}")
print(f"Feature columns ({len(FEATURE_COLS)}): {FEATURE_COLS}")
print(f"\nAny NaN in features: {prepped[FEATURE_COLS].isna().any().any()}")
print(f"\nLabel distribution:\n{prepped[LABEL_COL].value_counts()}")
print(f"\nFolds with train+test: {prepped[prepped['split']=='train']['fold'].nunique()}")
```

Expected output:
```
Total rows after dropping direction=none: 13761
Feature columns (12): ['ema_ratio', 'rsi_14', 'macd_hist', 'atr_14', 'session_quality_enc', 'direction_enc', 'signal_valid_enc', 'ema_20', 'ema_50', 'macd', 'macd_signal', 'instrument_enc']
Any NaN in features: False
Label distribution:
label
0.0    7734
1.0    6027
```

- [ ] **Step 4: Commit the notebook skeleton**

```bash
git add notebooks/livewell-nadex/notebooks/phase2/05_random_forest.ipynb
git commit -m "feat: add phase3 notebook skeleton with feature prep"
```

---

## Task 2: Implement walk-forward training for default and tuned RF

**Files:**
- Modify: `notebooks/livewell-nadex/notebooks/phase2/05_random_forest.ipynb`

- [ ] **Step 1: Add cell 4 — metric helper functions**

```python
def win_rate(labels: pd.Series) -> float:
    return float(labels.mean())


def brier_score(labels: pd.Series, probs: pd.Series) -> float:
    return float(((probs - labels) ** 2).mean())


def expected_value(wr: float) -> float:
    return wr * NADEX_WIN_PAYOUT - (1 - wr) * NADEX_LOSS_COST


def summarise(labels: pd.Series, probs: pd.Series) -> dict:
    """Compute win rate, brier, EV for top-50% by prob_itm."""
    threshold = probs.quantile(0.50)
    selected = labels[probs >= threshold]
    selected_probs = probs[probs >= threshold]
    wr = win_rate(selected)
    return {
        "n_trades":  len(selected),
        "win_rate":  wr,
        "brier":     brier_score(selected, selected_probs),
        "ev":        expected_value(wr),
    }
```

- [ ] **Step 2: Add cell 5 — walk-forward training loop**

```python
def run_rf_walk_forward(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Run walk-forward validation with two RF models per fold.

    Returns:
        results_df: DataFrame with columns date, s3_key, fold, label,
                    prob_default, prob_tuned
        importance_df: DataFrame with columns fold, feature, importance
                       (from tuned model only)
    """
    folds = sorted(df[df["split"] == "test"]["fold"].unique())
    results = []
    importances = []

    param_grid = {
        "n_estimators": [100, 300],
        "max_depth":    [None, 10, 20],
        "min_samples_leaf": [1, 5, 10],
    }

    for fold_idx in folds:
        train = df[(df["fold"] == fold_idx) & (df["split"] == "train")]
        test  = df[(df["fold"] == fold_idx) & (df["split"] == "test")]

        if len(train) < 10:
            print(f"Fold {fold_idx}: skipping — only {len(train)} train rows")
            continue
        if len(test) == 0:
            print(f"Fold {fold_idx}: skipping — no test rows")
            continue

        X_train = train[FEATURE_COLS].values
        y_train = train[LABEL_COL].values
        X_test  = test[FEATURE_COLS].values

        # Pass 1: default RF
        rf_default = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
        rf_default.fit(X_train, y_train)
        prob_default = rf_default.predict_proba(X_test)[:, 1]

        # Pass 2: tuned RF via grid search on train split only
        rf_base = RandomForestClassifier(random_state=42, n_jobs=-1)
        gs = GridSearchCV(rf_base, param_grid, cv=3, scoring="roc_auc", n_jobs=-1)
        gs.fit(X_train, y_train)
        prob_tuned = gs.best_estimator_.predict_proba(X_test)[:, 1]

        # Record feature importances from tuned model
        for feat, imp in zip(FEATURE_COLS, gs.best_estimator_.feature_importances_):
            importances.append({"fold": fold_idx, "feature": feat, "importance": imp})

        fold_results = test[["date", "s3_key", "fold", LABEL_COL]].copy()
        fold_results["prob_default"] = prob_default
        fold_results["prob_tuned"]   = prob_tuned

        print(f"Fold {fold_idx}: train={len(train)}, test={len(test)}, best_params={gs.best_params_}")
        results.append(fold_results)

    if not results:
        raise RuntimeError("No folds produced results.")

    return pd.concat(results, ignore_index=True), pd.DataFrame(importances)
```

- [ ] **Step 3: Add cell 6 — run the walk-forward loop**

```python
print("Running walk-forward RF benchmark (this may take several minutes)...")
results_df, importance_df = run_rf_walk_forward(prepped)

print(f"\nTotal test predictions: {len(results_df)}")
print(f"prob_tuned range: {results_df['prob_tuned'].min():.3f} – {results_df['prob_tuned'].max():.3f}")
print(f"Label distribution in test set:\n{results_df[LABEL_COL].value_counts()}")
```

Expected output (approximate):
```
Running walk-forward RF benchmark (this may take several minutes)...
Fold 0: train=114, test=140, best_params={...}
Fold 1: train=175, test=161, best_params={...}
...
Total test predictions: 888
```

- [ ] **Step 4: Commit**

```bash
git add notebooks/livewell-nadex/notebooks/phase2/05_random_forest.ipynb
git commit -m "feat: add rf walk-forward training loop with default and tuned models"
```

---

## Task 3: Add comparison table and feature importance chart

**Files:**
- Modify: `notebooks/livewell-nadex/notebooks/phase2/05_random_forest.ipynb`

- [ ] **Step 1: Add cell 7 — head-to-head comparison table**

```python
default_metrics = summarise(results_df[LABEL_COL], results_df["prob_default"])
tuned_metrics   = summarise(results_df[LABEL_COL], results_df["prob_tuned"])

comparison = pd.DataFrame([
    {
        "Model":    "Logistic Regression (Phase 2)",
        "Trades":   LR_TRADES,
        "Win Rate": LR_WIN_RATE,
        "Brier":    LR_BRIER,
        "EV/$1":    LR_EV,
    },
    {
        "Model":    "RF Default (n=100)",
        "Trades":   default_metrics["n_trades"],
        "Win Rate": round(default_metrics["win_rate"], 3),
        "Brier":    round(default_metrics["brier"], 4),
        "EV/$1":    round(default_metrics["ev"], 4),
    },
    {
        "Model":    "RF Tuned (GridSearchCV)",
        "Trades":   tuned_metrics["n_trades"],
        "Win Rate": round(tuned_metrics["win_rate"], 3),
        "Brier":    round(tuned_metrics["brier"], 4),
        "EV/$1":    round(tuned_metrics["ev"], 4),
    },
])

print("=" * 65)
print("HEAD-TO-HEAD COMPARISON")
print("=" * 65)
print(comparison.to_string(index=False))
print("=" * 65)

# Promotion decision
promoted = (
    tuned_metrics["win_rate"] > LR_WIN_RATE and
    tuned_metrics["ev"]       > LR_EV
)
if promoted:
    print("\n✅ RF Tuned BEATS logistic regression on both win rate and EV.")
    print("   Candidate for Phase 4 promotion.")
else:
    print("\n❌ RF Tuned does NOT beat logistic regression on both criteria.")
    print("   Logistic regression remains the Phase 4 candidate.")
    if tuned_metrics["win_rate"] > LR_WIN_RATE:
        print("   (Win rate improved but EV did not.)")
    elif tuned_metrics["ev"] > LR_EV:
        print("   (EV improved but win rate did not.)")
```

- [ ] **Step 2: Add cell 8 — feature importance chart**

```python
mean_importance = (
    importance_df.groupby("feature")["importance"]
    .mean()
    .sort_values(ascending=True)
)

fig, ax = plt.subplots(figsize=(8, 6))
mean_importance.plot(kind="barh", ax=ax, color="steelblue")
ax.set_xlabel("Mean Feature Importance (across folds)")
ax.set_title("RF Tuned — Feature Importance")
ax.axvline(1 / len(FEATURE_COLS), color="red", linestyle="--", alpha=0.5,
           label=f"Uniform baseline (1/{len(FEATURE_COLS)})")
ax.legend()
plt.tight_layout()
plt.show()

print("\nFeature importances (sorted):")
print(mean_importance.sort_values(ascending=False).round(4).to_string())
```

- [ ] **Step 3: Run all cells — Restart & Run All in Jupyter (livewell-api kernel)**

Expected: comparison table printed, promotion decision printed, feature importance chart displayed. No errors.

- [ ] **Step 4: Commit with saved output**

```bash
git add notebooks/livewell-nadex/notebooks/phase2/05_random_forest.ipynb
git commit -m "feat: complete phase3 random forest benchmark with comparison table and feature importance"
```

---

## Self-Review

### Spec coverage

| Spec requirement | Covered in |
|---|---|
| Load `labeled_signals.parquet` | Task 1 cell 3 |
| Drop NaN labels | Task 1 cell 2 (`prepare_features`) |
| Recompute fold assignments (self-contained) | Task 1 cell 2 (`assign_walk_forward_folds`) |
| 12 expanded features including instrument_enc, ema_20, ema_50, macd, macd_signal | Task 1 cells 1–2 |
| Default RF pass (n_estimators=100) | Task 2 cell 5 |
| Tuned RF pass (GridSearchCV on train only) | Task 2 cell 5 |
| Grid search params: n_estimators [100,300], max_depth [None,10,20], min_samples_leaf [1,5,10] | Task 2 cell 5 |
| Feature importances recorded per fold | Task 2 cell 5 |
| Top-50% threshold for trade selection | Task 2 cell 4 (`summarise`) |
| Win rate, Brier score, EV metrics | Task 2 cell 4 |
| Head-to-head comparison table (3 rows × 4 cols) | Task 3 cell 7 |
| LR baseline hardcoded as reference | Task 3 cell 7 |
| Promotion decision printed | Task 3 cell 7 |
| Feature importance bar chart | Task 3 cell 8 |
| No changes to notebooks 01–04 | ✓ (only new notebook created) |
| No changes to apps/api | ✓ |

### Placeholder scan

No TBDs or incomplete steps.

### Type consistency

- `FEATURE_COLS` defined in cell 1, used in cells 2, 5 consistently.
- `summarise()` returns dict with keys `n_trades`, `win_rate`, `brier`, `ev` — all accessed by those exact keys in cell 7.
- `run_rf_walk_forward` returns `(results_df, importance_df)` — destructured correctly in cell 6, both used in cells 7–8.
- `LR_WIN_RATE`, `LR_EV` defined in cell 1, referenced in cell 7 promotion check.

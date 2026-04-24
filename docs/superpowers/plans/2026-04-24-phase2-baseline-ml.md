# Phase 2 — Baseline ML Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Validate whether logistic regression adds measurable signal-ranking value over the existing rule-based pipeline, using four sequential Jupyter notebooks that produce reusable, production-ready functions.

**Architecture:** Four notebooks in `notebooks/livewell-nadex/notebooks/phase2/`, each writing an intermediate Parquet to `notebooks/livewell-nadex/data/phase2/` (git-ignored). Core logic in each notebook lives in named functions — not inline cell code — so the handoff to `apps/api/livewell/ml/` is a lift-and-test operation. Rolling 6-month train / 1-month test walk-forward validation. Label = binary ITM outcome derived from D+1 daily close vs `strike_candidate`.

**Tech Stack:** Python 3.12, pandas, scikit-learn (logistic regression, StandardScaler, calibration), matplotlib, Jupyter, S3 via boto3.

---

## File Structure

**New files:**
- `notebooks/livewell-nadex/notebooks/phase2/01_label_construction.ipynb` — reads signals+prices from S3, computes D+1 close, derives ITM label
- `notebooks/livewell-nadex/notebooks/phase2/02_feature_prep.ipynb` — selects and encodes features, assigns walk-forward fold metadata
- `notebooks/livewell-nadex/notebooks/phase2/03_walk_forward_validation.ipynb` — trains logistic regression per fold, records per-fold predictions
- `notebooks/livewell-nadex/notebooks/phase2/04_calibration_analysis.ipynb` — computes win rate / Brier score / EV, plots calibration curve, compares rules-only vs model

**Modified files:**
- `apps/api/pyproject.toml` — add scikit-learn dependency
- `notebooks/livewell-nadex/notebooks/phase2/` — new directory (create via mkdir)

**Data files (git-ignored, written at runtime):**
- `notebooks/livewell-nadex/data/phase2/labeled_signals.parquet`
- `notebooks/livewell-nadex/data/phase2/features_for_model.parquet`
- `notebooks/livewell-nadex/data/phase2/validation_results.parquet`
- `notebooks/livewell-nadex/data/phase2/metrics_summary.parquet`

---

## Task 1: Environment Setup

**Files:**
- Modify: `apps/api/pyproject.toml`

- [ ] **Step 1: Add scikit-learn to the API dependencies**

```bash
cd apps/api && uv add scikit-learn
```

Expected: `pyproject.toml` updated with `scikit-learn>=...` and `uv.lock` updated.

- [ ] **Step 2: Verify scikit-learn imports**

```bash
cd apps/api && uv run python -c "from sklearn.linear_model import LogisticRegression; from sklearn.preprocessing import StandardScaler; from sklearn.calibration import calibration_curve; print('OK')"
```

Expected: prints `OK`.

- [ ] **Step 3: Create the phase2 notebook and data directories**

```bash
mkdir -p notebooks/livewell-nadex/notebooks/phase2
mkdir -p notebooks/livewell-nadex/data/phase2
```

- [ ] **Step 4: Ensure data/phase2 is git-ignored**

Check if `notebooks/livewell-nadex/data/` is already in `.gitignore`:

```bash
grep -r "data/" notebooks/livewell-nadex/.gitignore 2>/dev/null || grep -r "data/" .gitignore 2>/dev/null || echo "not found"
```

If not found, add to `notebooks/livewell-nadex/.gitignore` (create if needed):

```
data/
```

- [ ] **Step 5: Commit**

```bash
git add apps/api/pyproject.toml apps/api/uv.lock notebooks/livewell-nadex/.gitignore
git commit -m "feat: add scikit-learn dependency and phase2 notebook scaffold"
```

---

## Task 2: Label Construction Notebook

**Files:**
- Create: `notebooks/livewell-nadex/notebooks/phase2/01_label_construction.ipynb`

This notebook reads all signals Parquets and prices Parquets from S3, joins them on `date` and `s3_key`, then derives the binary ITM label using the D+1 daily close vs `strike_candidate`. Includes all rows regardless of `signal_valid`.

- [ ] **Step 1: Create the notebook**

Create `notebooks/livewell-nadex/notebooks/phase2/01_label_construction.ipynb` with the following cells in order.

**Cell 1 — Imports and config (code):**
```python
import os
import sys
import boto3
import pandas as pd

# Allow importing from apps/api
sys.path.insert(0, os.path.abspath("../../../../apps/api"))

from livewell.ingestion.s3 import read_parquet, write_parquet
from livewell.ingestion.constants import INSTRUMENTS, INTERVALS

BUCKET = os.environ["LIVEWELL_BUCKET"]
SIGNALS_PREFIX = "signals"
PRICES_PREFIX = "prices"
OUTPUT_PATH = "../../../data/phase2/labeled_signals.parquet"
INTERVAL = "1d"  # label construction uses daily bars only
```

**Cell 2 — Core functions (code):**
```python
def load_all_parquets(bucket: str, prefix: str) -> pd.DataFrame:
    """List all Parquet objects under prefix and concat into one DataFrame."""
    s3 = boto3.client("s3")
    resp = s3.list_objects_v2(Bucket=bucket, Prefix=prefix + "/")
    objects = resp.get("Contents", [])
    frames = []
    for obj in objects:
        df = read_parquet(bucket, obj["Key"])
        if df is not None:
            frames.append(df)
    if not frames:
        raise ValueError(f"No Parquet files found under s3://{bucket}/{prefix}/")
    return pd.concat(frames, ignore_index=True)


def load_signals(bucket: str, s3_key: str, interval: str) -> pd.DataFrame:
    """Load all signal Parquets for one instrument+interval, add s3_key column."""
    prefix = f"{SIGNALS_PREFIX}/{s3_key}/{interval}"
    df = load_all_parquets(bucket, prefix)
    df["s3_key"] = s3_key
    df["date"] = pd.to_datetime(df["date"], utc=True)
    return df


def load_prices(bucket: str, s3_key: str, interval: str) -> pd.DataFrame:
    """Load all price Parquets for one instrument+interval, return date+close only."""
    prefix = f"{PRICES_PREFIX}/{s3_key}/{interval}"
    df = load_all_parquets(bucket, prefix)
    df["date"] = pd.to_datetime(df["date"], utc=True)
    return df[["date", "close"]].rename(columns={"close": "close_d"})


def derive_label(signals: pd.DataFrame, prices: pd.DataFrame) -> pd.DataFrame:
    """
    For each signal on day D, find the D+1 close (close_d1) and derive
    binary ITM label:
      - direction=="buy":  label=1 if close_d1 >= strike_candidate else 0
      - direction=="sell": label=1 if close_d1 <= strike_candidate else 0
      - direction=="none": label=NaN (excluded from training)

    Args:
        signals: DataFrame with columns [date, direction, strike_candidate, ...]
        prices:  DataFrame with columns [date, close_d] sorted ascending

    Returns:
        signals with added columns: close_d1, label
    """
    prices_sorted = prices.sort_values("date").reset_index(drop=True)
    # Map each date to the NEXT available price date
    prices_sorted["date_d"] = prices_sorted["date"]
    prices_sorted["close_d1"] = prices_sorted["close_d"].shift(-1)

    merged = signals.merge(
        prices_sorted[["date_d", "close_d1"]].rename(columns={"date_d": "date"}),
        on="date",
        how="left",
    )

    def _label(row):
        if row["direction"] == "buy":
            return int(row["close_d1"] >= row["strike_candidate"])
        elif row["direction"] == "sell":
            return int(row["close_d1"] <= row["strike_candidate"])
        else:
            return float("nan")

    merged["label"] = merged.apply(_label, axis=1)
    return merged


def build_labeled_dataset(bucket: str, interval: str) -> pd.DataFrame:
    """
    Load signals and prices for all instruments, derive labels, return combined DataFrame.
    Rows with direction=="none" are included but label=NaN — callers decide how to handle.
    """
    all_frames = []
    for inst in INSTRUMENTS:
        s3_key = inst["s3_key"]
        try:
            signals = load_signals(bucket, s3_key, interval)
            prices = load_prices(bucket, s3_key, interval)
            labeled = derive_label(signals, prices)
            all_frames.append(labeled)
            print(f"{s3_key}: {len(labeled)} rows, {labeled['label'].notna().sum()} labeled")
        except Exception as exc:
            print(f"WARNING: {s3_key} failed — {exc}")
    if not all_frames:
        raise RuntimeError("No instruments produced labeled data.")
    return pd.concat(all_frames, ignore_index=True)
```

**Cell 3 — Run and save (code):**
```python
labeled = build_labeled_dataset(BUCKET, INTERVAL)
print(f"\nTotal rows: {len(labeled)}")
print(f"Labeled (direction != none): {labeled['label'].notna().sum()}")
print(f"Label distribution:\n{labeled['label'].value_counts(dropna=True)}")
os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
labeled.to_parquet(OUTPUT_PATH, index=False)
print(f"\nSaved to {OUTPUT_PATH}")
```

**Cell 4 — Spot-check (code):**
```python
df = pd.read_parquet(OUTPUT_PATH)
print(df[["date", "s3_key", "direction", "strike_candidate", "close_d1", "label", "signal_valid"]].head(20).to_string())
```

- [ ] **Step 2: Commit**

```bash
git add notebooks/livewell-nadex/notebooks/phase2/01_label_construction.ipynb
git commit -m "feat: add phase2 label construction notebook"
```

---

## Task 3: Feature Preparation Notebook

**Files:**
- Create: `notebooks/livewell-nadex/notebooks/phase2/02_feature_prep.ipynb`

This notebook reads `labeled_signals.parquet`, selects and encodes features for logistic regression, assigns walk-forward fold metadata (6-month train / 1-month test rolling), and writes `features_for_model.parquet`. Rows where `label` is NaN (`direction=="none"`) are dropped. All rows (including `signal_valid=False`) are retained so the model sees the full distribution.

The feature set:
- `ema_ratio` = ema_20 / ema_50 (captures trend strength, avoids scale issues)
- `rsi_14` (as-is)
- `macd_hist` (as-is)
- `atr_14` (as-is)
- `session_quality_enc` = {"high": 2, "medium": 1, "low": 0}
- `direction_enc` = {"buy": 1, "sell": -1, "none": 0}
- `signal_valid_enc` = signal_valid.astype(int) (0 or 1 — the rule system's vote)

- [ ] **Step 1: Create the notebook**

Create `notebooks/livewell-nadex/notebooks/phase2/02_feature_prep.ipynb` with the following cells.

**Cell 1 — Imports and config (code):**
```python
import os
import pandas as pd
import numpy as np

INPUT_PATH  = "../../../data/phase2/labeled_signals.parquet"
OUTPUT_PATH = "../../../data/phase2/features_for_model.parquet"

FEATURE_COLS = [
    "ema_ratio", "rsi_14", "macd_hist", "atr_14",
    "session_quality_enc", "direction_enc", "signal_valid_enc",
]
LABEL_COL = "label"
META_COLS = ["date", "s3_key", "fold", "split"]
```

**Cell 2 — Core functions (code):**
```python
def encode_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add derived and encoded columns to df. Returns a new DataFrame.
    Input df must contain: ema_20, ema_50, rsi_14, macd_hist, atr_14,
    session_quality, direction, signal_valid, label.
    """
    out = df.copy()
    out["ema_ratio"]          = out["ema_20"] / out["ema_50"]
    out["session_quality_enc"] = out["session_quality"].map({"high": 2, "medium": 1, "low": 0})
    out["direction_enc"]       = out["direction"].map({"buy": 1, "sell": -1, "none": 0})
    out["signal_valid_enc"]    = out["signal_valid"].astype(int)
    return out


def assign_walk_forward_folds(
    df: pd.DataFrame,
    train_months: int = 6,
    test_months: int = 1,
) -> pd.DataFrame:
    """
    Assign walk-forward fold metadata to each row.

    For each fold N:
      - train: rows where date falls in [fold_start, fold_start + train_months)
      - test:  rows where date falls in [fold_start + train_months,
                                         fold_start + train_months + test_months)

    Rows that don't fall into any fold's test window (e.g., the last
    train_months of data with no following test period) get fold=-1, split="unused".

    Args:
        df: DataFrame with a "date" column (tz-aware or tz-naive datetime).
        train_months: size of training window in calendar months.
        test_months: size of test window in calendar months.

    Returns:
        df with added columns: fold (int), split ("train" | "test" | "unused")
    """
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df["fold"]  = -1
    df["split"] = "unused"

    min_date = df["date"].min().to_period("M")
    max_date = df["date"].max().to_period("M")

    fold_idx = 0
    cursor = min_date
    while True:
        train_start = cursor
        train_end   = cursor + train_months          # exclusive
        test_start  = train_end
        test_end    = train_end + test_months        # exclusive

        if test_end > max_date + 1:
            break

        train_mask = (
            (df["date"].dt.to_period("M") >= train_start) &
            (df["date"].dt.to_period("M") <  train_end)
        )
        test_mask = (
            (df["date"].dt.to_period("M") >= test_start) &
            (df["date"].dt.to_period("M") <  test_end)
        )

        df.loc[train_mask, "fold"]  = fold_idx
        df.loc[train_mask, "split"] = "train"
        df.loc[test_mask,  "fold"]  = fold_idx
        df.loc[test_mask,  "split"] = "test"

        fold_idx += 1
        cursor += test_months

    return df


def prepare_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Full feature prep pipeline:
    1. Drop rows with NaN label (direction=="none")
    2. Encode features
    3. Assign walk-forward folds
    4. Return DataFrame with META_COLS + FEATURE_COLS + LABEL_COL

    Does NOT scale features — scaling happens inside each fold during training
    to prevent leakage.
    """
    df = df[df["label"].notna()].copy()
    df = encode_features(df)
    df = assign_walk_forward_folds(df)
    keep = META_COLS + FEATURE_COLS + [LABEL_COL]
    return df[keep].reset_index(drop=True)
```

**Cell 3 — Run and save (code):**
```python
raw = pd.read_parquet(INPUT_PATH)
prepped = prepare_features(raw)

print(f"Total rows after dropping direction=none: {len(prepped)}")
print(f"\nFold distribution:")
print(prepped.groupby(["fold", "split"]).size().to_string())
print(f"\nLabel distribution:\n{prepped['label'].value_counts()}")

os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
prepped.to_parquet(OUTPUT_PATH, index=False)
print(f"\nSaved to {OUTPUT_PATH}")
```

**Cell 4 — Spot-check (code):**
```python
df = pd.read_parquet(OUTPUT_PATH)
print(df[META_COLS + FEATURE_COLS + [LABEL_COL]].head(10).to_string())
print(f"\nFeature dtypes:\n{df[FEATURE_COLS].dtypes}")
print(f"\nAny NaN in features: {df[FEATURE_COLS].isna().any().any()}")
```

- [ ] **Step 2: Commit**

```bash
git add notebooks/livewell-nadex/notebooks/phase2/02_feature_prep.ipynb
git commit -m "feat: add phase2 feature preparation notebook"
```

---

## Task 4: Walk-Forward Validation Notebook

**Files:**
- Create: `notebooks/livewell-nadex/notebooks/phase2/03_walk_forward_validation.ipynb`

This notebook reads `features_for_model.parquet`, iterates each fold, fits a logistic regression on the training split (with per-fold StandardScaler to prevent leakage), predicts probabilities on the test split, and writes per-fold predictions to `validation_results.parquet`.

- [ ] **Step 1: Create the notebook**

Create `notebooks/livewell-nadex/notebooks/phase2/03_walk_forward_validation.ipynb` with the following cells.

**Cell 1 — Imports and config (code):**
```python
import os
import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

INPUT_PATH  = "../../../data/phase2/features_for_model.parquet"
OUTPUT_PATH = "../../../data/phase2/validation_results.parquet"

FEATURE_COLS = [
    "ema_ratio", "rsi_14", "macd_hist", "atr_14",
    "session_quality_enc", "direction_enc", "signal_valid_enc",
]
LABEL_COL = "label"
```

**Cell 2 — Core functions (code):**
```python
def train_fold(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_test: pd.DataFrame,
) -> tuple[np.ndarray, StandardScaler, LogisticRegression]:
    """
    Fit StandardScaler + LogisticRegression on training data.
    Return (predicted_probabilities_for_test, fitted_scaler, fitted_model).

    Scaler is fit only on X_train to prevent data leakage.
    LogisticRegression uses C=1.0, max_iter=1000, solver='lbfgs'.
    Returns probabilities for the positive class (label=1).
    """
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled  = scaler.transform(X_test)

    model = LogisticRegression(C=1.0, max_iter=1000, solver="lbfgs", random_state=42)
    model.fit(X_train_scaled, y_train)

    proba = model.predict_proba(X_test_scaled)[:, 1]  # P(label=1)
    return proba, scaler, model


def run_walk_forward(df: pd.DataFrame) -> pd.DataFrame:
    """
    Run walk-forward validation across all folds.

    For each fold N:
      1. Filter train rows (fold==N, split=="train")
      2. Filter test rows  (fold==N, split=="test")
      3. Call train_fold
      4. Append test rows + predicted probability to results

    Returns DataFrame with columns:
      date, s3_key, fold, label, prob_itm, signal_valid_enc, direction_enc
    """
    folds = sorted(df[df["split"] == "test"]["fold"].unique())
    results = []

    for fold_idx in folds:
        train = df[(df["fold"] == fold_idx) & (df["split"] == "train")]
        test  = df[(df["fold"] == fold_idx) & (df["split"] == "test")]

        if len(train) < 10:
            print(f"Fold {fold_idx}: skipping — only {len(train)} train rows")
            continue
        if len(test) == 0:
            print(f"Fold {fold_idx}: skipping — no test rows")
            continue

        X_train = train[FEATURE_COLS]
        y_train = train[LABEL_COL]
        X_test  = test[FEATURE_COLS]

        proba, _, model = train_fold(X_train, y_train, X_test)

        fold_results = test[["date", "s3_key", "fold", LABEL_COL, "signal_valid_enc", "direction_enc"]].copy()
        fold_results["prob_itm"] = proba

        n_pos = int((y_train == 1).sum())
        n_neg = int((y_train == 0).sum())
        print(f"Fold {fold_idx}: train={len(train)} (pos={n_pos}, neg={n_neg}), test={len(test)}, coef={model.coef_[0].round(3)}")
        results.append(fold_results)

    if not results:
        raise RuntimeError("No folds produced results.")
    return pd.concat(results, ignore_index=True)
```

**Cell 3 — Run and save (code):**
```python
df = pd.read_parquet(INPUT_PATH)
results = run_walk_forward(df)

print(f"\nTotal test predictions: {len(results)}")
print(f"prob_itm range: {results['prob_itm'].min():.3f} – {results['prob_itm'].max():.3f}")
print(f"Label distribution in test set:\n{results['label'].value_counts()}")

os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
results.to_parquet(OUTPUT_PATH, index=False)
print(f"\nSaved to {OUTPUT_PATH}")
```

**Cell 4 — Spot-check (code):**
```python
df = pd.read_parquet(OUTPUT_PATH)
print(df[["date", "s3_key", "fold", "label", "prob_itm"]].head(20).to_string())
```

- [ ] **Step 2: Commit**

```bash
git add notebooks/livewell-nadex/notebooks/phase2/03_walk_forward_validation.ipynb
git commit -m "feat: add phase2 walk-forward validation notebook"
```

---

## Task 5: Calibration Analysis Notebook

**Files:**
- Create: `notebooks/livewell-nadex/notebooks/phase2/04_calibration_analysis.ipynb`

This notebook reads `validation_results.parquet` and computes three metrics for both the rules-only baseline and the logistic regression model, then plots a calibration curve.

**Metrics:**
- **Win rate** = count(label==1) / count(label in {0,1}) for selected trades
- **Brier score** = mean((prob_itm − label)²) — lower is better; 0.25 is a coin flip
- **Expected value** = (win_rate × 0.80) − (loss_rate × 1.00)
  (NADEX standard: win pays ~$80 on a $100 contract, loss costs $100 — adjust if different)

**Rules-only baseline:** all rows treated as equally probable (prob_itm = win_rate of the full dataset — a naive constant baseline). Filtered to `signal_valid_enc==1` rows only.

**Model:** all rows, ranked by `prob_itm`. Top-50% by probability selected as "take this trade."

- [ ] **Step 1: Create the notebook**

Create `notebooks/livewell-nadex/notebooks/phase2/04_calibration_analysis.ipynb` with the following cells.

**Cell 1 — Imports and config (code):**
```python
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.calibration import calibration_curve

INPUT_PATH  = "../../../data/phase2/validation_results.parquet"
OUTPUT_PATH = "../../../data/phase2/metrics_summary.parquet"

# NADEX standard payout assumptions — adjust if your contracts differ
NADEX_WIN_PAYOUT  = 0.80   # net gain per $1 risked on a win
NADEX_LOSS_COST   = 1.00   # net loss per $1 risked on a loss
```

**Cell 2 — Core functions (code):**
```python
def win_rate(labels: pd.Series) -> float:
    """Fraction of trades that expired ITM."""
    return float(labels.mean())


def brier_score(labels: pd.Series, probs: pd.Series) -> float:
    """Mean squared error between predicted probability and binary outcome."""
    return float(((probs - labels) ** 2).mean())


def expected_value(wr: float, win_payout: float = NADEX_WIN_PAYOUT,
                   loss_cost: float = NADEX_LOSS_COST) -> float:
    """EV per $1 risked: wr * win_payout - (1 - wr) * loss_cost."""
    return wr * win_payout - (1 - wr) * loss_cost


def summarise_metrics(
    results: pd.DataFrame,
    label_col: str = "label",
    prob_col: str = "prob_itm",
) -> dict:
    """
    Compute all three metrics for both rules-only and model selections.

    Rules-only baseline:
      - Uses rows where signal_valid_enc == 1
      - Assigns constant probability = overall win rate (naive baseline)

    Model selection:
      - Uses all rows, sorted by prob_itm descending
      - Selects top 50% by probability as "take this trade"

    Returns dict with keys:
      rules_win_rate, rules_brier, rules_ev,
      model_win_rate, model_brier, model_ev,
      n_rules_trades, n_model_trades
    """
    rules_rows = results[results["signal_valid_enc"] == 1].copy()
    overall_wr = win_rate(results[label_col])
    rules_rows["const_prob"] = overall_wr

    model_threshold = results[prob_col].quantile(0.50)
    model_rows = results[results[prob_col] >= model_threshold].copy()

    return {
        "rules_win_rate":   win_rate(rules_rows[label_col]),
        "rules_brier":      brier_score(rules_rows[label_col], rules_rows["const_prob"]),
        "rules_ev":         expected_value(win_rate(rules_rows[label_col])),
        "n_rules_trades":   len(rules_rows),
        "model_win_rate":   win_rate(model_rows[label_col]),
        "model_brier":      brier_score(model_rows[label_col], model_rows[prob_col]),
        "model_ev":         expected_value(win_rate(model_rows[label_col])),
        "n_model_trades":   len(model_rows),
    }


def plot_calibration(results: pd.DataFrame, label_col: str = "label",
                     prob_col: str = "prob_itm") -> None:
    """
    Plot calibration curve: fraction of positives vs mean predicted probability.
    A perfectly calibrated model lies on the diagonal.
    """
    fraction_of_positives, mean_predicted = calibration_curve(
        results[label_col], results[prob_col], n_bins=10, strategy="uniform"
    )
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.plot([0, 1], [0, 1], "k--", label="Perfect calibration")
    ax.plot(mean_predicted, fraction_of_positives, "s-", label="Logistic regression")
    ax.set_xlabel("Mean predicted probability")
    ax.set_ylabel("Fraction of positives (actual win rate)")
    ax.set_title("Calibration Curve — Logistic Regression")
    ax.legend()
    plt.tight_layout()
    plt.show()
```

**Cell 3 — Run metrics (code):**
```python
results = pd.read_parquet(INPUT_PATH)
metrics = summarise_metrics(results)

print("=" * 50)
print("RULES-ONLY BASELINE")
print(f"  Trades selected:  {metrics['n_rules_trades']}")
print(f"  Win rate:         {metrics['rules_win_rate']:.3f}")
print(f"  Brier score:      {metrics['rules_brier']:.4f}")
print(f"  Expected value:   {metrics['rules_ev']:+.4f} per $1 risked")

print("\nMODEL (top-50% by prob_itm)")
print(f"  Trades selected:  {metrics['n_model_trades']}")
print(f"  Win rate:         {metrics['model_win_rate']:.3f}")
print(f"  Brier score:      {metrics['model_brier']:.4f}")
print(f"  Expected value:   {metrics['model_ev']:+.4f} per $1 risked")
print("=" * 50)
```

**Cell 4 — Calibration plot (code):**
```python
plot_calibration(results)
```

**Cell 5 — Per-fold breakdown (code):**
```python
fold_metrics = []
for fold_idx in sorted(results["fold"].unique()):
    fold = results[results["fold"] == fold_idx]
    m = summarise_metrics(fold)
    m["fold"] = fold_idx
    fold_metrics.append(m)

fold_df = pd.DataFrame(fold_metrics).set_index("fold")
print(fold_df[["rules_win_rate", "model_win_rate", "rules_ev", "model_ev",
               "rules_brier", "model_brier"]].round(4).to_string())
```

**Cell 6 — Save metrics summary (code):**
```python
summary_df = pd.DataFrame([metrics])
os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
summary_df.to_parquet(OUTPUT_PATH, index=False)
print(f"\nSaved metrics summary to {OUTPUT_PATH}")
```

- [ ] **Step 2: Commit**

```bash
git add notebooks/livewell-nadex/notebooks/phase2/04_calibration_analysis.ipynb
git commit -m "feat: add phase2 calibration analysis notebook"
```

---

## Self-Review

### Spec coverage

| Spec requirement | Covered in |
|---|---|
| Label construction (binary ITM from D+1 close) | Task 2 |
| All rows including signal_valid=False | Task 3 (`prepare_features` drops NaN label only) |
| Feature selection from signals Parquet | Task 3 |
| EMA ratio, RSI, MACD hist, ATR, session quality, direction, signal_valid | Task 3 `encode_features` |
| Rolling 6-month train / 1-month test walk-forward | Task 3 `assign_walk_forward_folds`, Task 4 `run_walk_forward` |
| Logistic regression with StandardScaler (per-fold, no leakage) | Task 4 `train_fold` |
| Win rate metric | Task 5 `win_rate` |
| Brier score metric | Task 5 `brier_score` |
| Expected value metric | Task 5 `expected_value` |
| Rules-only vs model comparison | Task 5 `summarise_metrics` |
| Calibration curve plot | Task 5 `plot_calibration` |
| Named functions (production handoff ready) | All notebooks — core logic in functions, cell is runner |
| scikit-learn dependency | Task 1 |
| Intermediate Parquet files between notebooks | Tasks 2–5 |
| Per-fold breakdown | Task 5 Cell 5 |
| Intraday data noted as future enhancement | Design doc |

### Placeholder scan

No TBDs, TODOs, or "implement later" references. All steps include complete code.

### Type consistency

- `derive_label(signals, prices) -> pd.DataFrame` — defined Task 2, returns df with `label` column read by Task 3 ✓
- `encode_features(df) -> pd.DataFrame` — adds `ema_ratio`, `session_quality_enc`, `direction_enc`, `signal_valid_enc` ✓
- `FEATURE_COLS` list defined in Task 3 Cell 1 and re-declared identically in Task 4 Cell 1 ✓
- `train_fold(X_train, y_train, X_test) -> tuple[ndarray, scaler, model]` — defined and called in Task 4 ✓
- `summarise_metrics` reads `signal_valid_enc` and `prob_itm` — both produced by Task 4 ✓
- `label` column: float in Task 2 (NaN for direction=none), dropna'd to int-compatible float in Task 3 ✓

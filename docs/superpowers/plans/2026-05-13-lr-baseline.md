# Phase 2 LR Baseline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Phase 2 logistic regression baseline: construct labeled training data from backtest outcomes + DynamoDB signals, train LR with walk-forward validation, register the model artifact, and print feature coefficients.

**Architecture:** Two sequential deliverables — (1) `build_labels.ipynb` reads `backtest/summary.json` from S3, batch-fetches matching signal records from DynamoDB, joins on `signal_id`, maps `call/put` → `buy/sell`, and writes `labeled/signals_labeled.parquet` to S3. (2) `train_lr.py` reuses `_load_labeled_data`, `_build_xy`, `_walk_forward_split`, and `_upload_artifact` from `train.py` (with the LR-specific S3 path), trains `LogisticRegression`, evaluates walk-forward metrics, uploads artifact, registers under `"lr_baseline"`, and returns `(model, metrics, coef_df)`. A `train_lr.ipynb` orchestrates it.

**Tech Stack:** Python 3.12, scikit-learn `LogisticRegression`, boto3, pandas, joblib, moto (tests), uv/pytest

---

## Pre-existing test failures (do not fix in this plan)

`tests/models/test_train.py` has 3 failing tests due to a `KeyError: 'label'` — the synthetic fixture uses `"outcome"` but `_build_xy` expects `"label"`. `tests/explain/test_router.py` has 4 failures. These are pre-existing and unrelated to this work. Do not touch `train.py` or `test_train.py`.

---

### Task 1: `train_lr.py` — logistic regression trainer

**Files:**
- Create: `apps/api/livewell/models/train_lr.py`
- Test: `apps/api/tests/models/test_train_lr.py`

**Context:** `train.py` lives at `apps/api/livewell/models/train.py` and exports `_load_labeled_data`, `_build_xy`, `_walk_forward_split`. These are private helpers — import them directly. `_upload_artifact` in `train.py` is hardcoded to `models/rf_tuned/` — do NOT reuse it; write a new `_upload_lr_artifact` that uses `models/lr_baseline/`. `register_model` is imported from `livewell.models.registry`. `FEATURE_NAMES` is imported from `livewell.models.features`. The `LIVEWELL_BUCKET` env var holds the S3 bucket name.

Run tests from `apps/api/` with: `uv run pytest tests/models/test_train_lr.py -v`

- [ ] **Step 1: Create `tests/models/test_train_lr.py` with the four failing tests**

```python
from __future__ import annotations
import io
from unittest.mock import patch, MagicMock
import numpy as np
import pandas as pd
import pytest


@pytest.fixture(autouse=True)
def env(monkeypatch):
    monkeypatch.setenv("LIVEWELL_BUCKET", "test-bucket")
    monkeypatch.setenv("LIVEWELL_ENV", "test")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")


def _synthetic_df(n: int = 60) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    return pd.DataFrame({
        "signal_id": [f"EURUSD__2026-01-{i+1:02d}" for i in range(n)],
        "s3_key": ["EURUSD"] * n,
        "date": pd.date_range("2026-01-01", periods=n, freq="D"),
        "ema_20": rng.uniform(1.05, 1.15, n),
        "ema_50": rng.uniform(1.04, 1.14, n),
        "rsi_14": rng.uniform(30, 70, n),
        "macd": rng.uniform(-0.002, 0.002, n),
        "macd_signal": rng.uniform(-0.002, 0.002, n),
        "macd_hist": rng.uniform(-0.001, 0.001, n),
        "atr_14": rng.uniform(0.003, 0.01, n),
        "session_quality": rng.choice(["high", "medium", "low"], n),
        "direction": rng.choice(["buy", "sell", "none"], n),
        "signal_valid": rng.choice([True, False], n),
        "label": rng.integers(0, 2, n),
    })


def test_run_lr_training_returns_model_and_metrics():
    df = _synthetic_df()
    with patch("livewell.models.train_lr._load_labeled_data", return_value=df), \
         patch("livewell.models.train_lr._upload_lr_artifact", return_value="models/lr_baseline/vTEST.joblib"), \
         patch("livewell.models.train_lr.register_model"):
        from livewell.models.train_lr import run_lr_training
        model, metrics, coef_df = run_lr_training()
    assert hasattr(model, "predict_proba")
    assert {"win_rate", "brier_score", "ev"}.issubset(metrics.keys())
    assert isinstance(coef_df, pd.DataFrame)


def test_coef_df_has_all_feature_names():
    from livewell.models.features import FEATURE_NAMES
    df = _synthetic_df()
    with patch("livewell.models.train_lr._load_labeled_data", return_value=df), \
         patch("livewell.models.train_lr._upload_lr_artifact", return_value="models/lr_baseline/vTEST.joblib"), \
         patch("livewell.models.train_lr.register_model"):
        from livewell.models.train_lr import run_lr_training
        _, _, coef_df = run_lr_training()
    assert set(coef_df["feature"].tolist()) == set(FEATURE_NAMES)


def test_model_registered_as_lr_baseline():
    df = _synthetic_df()
    with patch("livewell.models.train_lr._load_labeled_data", return_value=df), \
         patch("livewell.models.train_lr._upload_lr_artifact", return_value="models/lr_baseline/vTEST.joblib"), \
         patch("livewell.models.train_lr.register_model") as mock_register:
        from livewell.models.train_lr import run_lr_training
        run_lr_training()
    mock_register.assert_called_once()
    kwargs = mock_register.call_args.kwargs
    assert kwargs["model_name"] == "lr_baseline"
    assert "version" in kwargs
    assert "win_rate" in kwargs
    assert "ev" in kwargs


def test_walk_forward_produces_multiple_folds():
    # 18 months of daily data → at least 6 folds (6-month train, 1-month test, 1-month slide)
    rng = np.random.default_rng(0)
    n = 540  # ~18 months of daily rows
    df = pd.DataFrame({
        "signal_id": [f"EURUSD__2026-01-{i}" for i in range(n)],
        "s3_key": ["EURUSD"] * n,
        "date": pd.date_range("2025-01-01", periods=n, freq="D"),
        "ema_20": rng.uniform(1.05, 1.15, n),
        "ema_50": rng.uniform(1.04, 1.14, n),
        "rsi_14": rng.uniform(30, 70, n),
        "macd": rng.uniform(-0.002, 0.002, n),
        "macd_signal": rng.uniform(-0.002, 0.002, n),
        "macd_hist": rng.uniform(-0.001, 0.001, n),
        "atr_14": rng.uniform(0.003, 0.01, n),
        "session_quality": rng.choice(["high", "medium", "low"], n),
        "direction": rng.choice(["buy", "sell", "none"], n),
        "signal_valid": rng.choice([True, False], n),
        "label": rng.integers(0, 2, n),
    })
    with patch("livewell.models.train_lr._load_labeled_data", return_value=df), \
         patch("livewell.models.train_lr._upload_lr_artifact", return_value="models/lr_baseline/vTEST.joblib"), \
         patch("livewell.models.train_lr.register_model"):
        from livewell.models.train_lr import run_lr_training
        run_lr_training()
    from livewell.models.train import _walk_forward_split
    folds = list(_walk_forward_split(df))
    assert len(folds) >= 6
```

- [ ] **Step 2: Run tests — verify they all fail (ImportError or ModuleNotFoundError)**

```bash
cd apps/api && uv run pytest tests/models/test_train_lr.py -v
```

Expected: 4 failures with `ModuleNotFoundError: No module named 'livewell.models.train_lr'`

- [ ] **Step 3: Create `apps/api/livewell/models/train_lr.py`**

```python
from __future__ import annotations
import io
import logging
import os
from datetime import datetime, timezone

import boto3
import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss

from livewell.models.features import build_feature_vector, FEATURE_NAMES
from livewell.models.registry import register_model
from livewell.models.train import _load_labeled_data, _build_xy, _walk_forward_split

logger = logging.getLogger(__name__)


def _upload_lr_artifact(model, version: str) -> str:
    bucket = os.environ["LIVEWELL_BUCKET"]
    s3_path = f"models/lr_baseline/v{version}.joblib"
    buf = io.BytesIO()
    joblib.dump(model, buf)
    buf.seek(0)
    boto3.client("s3").put_object(Bucket=bucket, Key=s3_path, Body=buf.read())
    logger.info("uploaded LR artifact to s3://%s/%s", bucket, s3_path)
    return s3_path


def run_lr_training() -> tuple:
    """Train LogisticRegression on labeled signals. Return (model, metrics, coef_df)."""
    df = _load_labeled_data()
    logger.info("loaded %d labeled rows", len(df))

    df = df[df["label"].notna()].reset_index(drop=True)
    logger.info("labeled rows after dropping NaN: %d", len(df))

    X, y = _build_xy(df)
    logger.info("built feature matrix: %s rows, %s features", X.shape[0], X.shape[1])

    model = LogisticRegression(
        C=1.0,
        class_weight="balanced",
        max_iter=1000,
        solver="lbfgs",
        random_state=42,
    )

    folds = list(_walk_forward_split(df))
    fold_metrics = []
    for train_idx, test_idx in folds:
        X_train, y_train = X[train_idx], y[train_idx]
        X_test, y_test = X[test_idx], y[test_idx]
        fold_model = LogisticRegression(
            C=1.0, class_weight="balanced", max_iter=1000,
            solver="lbfgs", random_state=42,
        )
        fold_model.fit(X_train, y_train)
        proba = fold_model.predict_proba(X_test)[:, 1]
        preds = (proba >= 0.5).astype(int)
        win_rate = float(np.mean(preds == y_test)) if len(y_test) > 0 else 0.0
        brier = float(brier_score_loss(y_test, proba)) if len(y_test) > 0 else float("nan")
        top_half = proba >= np.median(proba)
        ev = float(np.mean(y_test[top_half]) * 2 - 1) if top_half.any() else float("nan")
        fold_metrics.append({"win_rate": win_rate, "brier_score": brier, "ev": ev})
        logger.info("fold metrics: win_rate=%.3f brier=%.3f ev=%.3f", win_rate, brier, ev)

    if folds:
        metrics = fold_metrics[-1]
    else:
        n = len(X)
        split = max(1, int(n * 0.8))
        test_idx = list(range(split, n))
        X_test, y_test = X[test_idx], y[test_idx]
        tmp = LogisticRegression(C=1.0, class_weight="balanced", max_iter=1000, solver="lbfgs", random_state=42)
        tmp.fit(X, y)
        proba = tmp.predict_proba(X_test)[:, 1]
        preds = (proba >= 0.5).astype(int)
        win_rate = float(np.mean(preds == y_test)) if len(y_test) > 0 else 0.0
        brier = float(brier_score_loss(y_test, proba)) if len(y_test) > 0 else float("nan")
        top_half = proba >= np.median(proba)
        ev = float(np.mean(y_test[top_half]) * 2 - 1) if top_half.any() else float("nan")
        metrics = {"win_rate": win_rate, "brier_score": brier, "ev": ev}

    # Train final model on all data
    model.fit(X, y)
    logger.info("final model trained on all %d rows", len(X))

    coefs = model.coef_[0]
    coef_df = pd.DataFrame({"feature": FEATURE_NAMES, "coefficient": coefs})
    coef_df["abs_coef"] = coef_df["coefficient"].abs()
    coef_df = coef_df.sort_values("abs_coef", ascending=False).drop(columns="abs_coef").reset_index(drop=True)

    now = datetime.now(timezone.utc)
    version = now.strftime("%Y%m%dT%H%M%S")
    s3_path = _upload_lr_artifact(model, version)
    register_model(
        model_name="lr_baseline",
        version=version,
        s3_path=s3_path,
        features=FEATURE_NAMES,
        win_rate=metrics["win_rate"],
        ev=metrics["ev"],
        trained_at=now.isoformat(),
    )
    logger.info("final metrics: %s", metrics)
    return model, metrics, coef_df


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    model, metrics, coef_df = run_lr_training()
    print(f"Final fold — win_rate: {metrics['win_rate']:.3f}, brier: {metrics['brier_score']:.3f}, ev: {metrics['ev']:.3f}")
    print(coef_df.to_string(index=False))
```

- [ ] **Step 4: Run tests — verify all 4 pass**

```bash
cd apps/api && uv run pytest tests/models/test_train_lr.py -v
```

Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add apps/api/livewell/models/train_lr.py apps/api/tests/models/test_train_lr.py
git commit -m "feat: add logistic regression trainer (train_lr.py) with walk-forward validation"
```

---

### Task 2: `build_labels.ipynb` — label construction notebook

**Files:**
- Create: `notebooks/livewell-nadex/build_labels.ipynb`

**Context:** This notebook reads `s3://livewell-data-prod/backtest/summary.json`, batch-fetches signal records from DynamoDB table `livewell-signals-prod` (25 per request via `batch_get_item`), joins on `signal_id`, maps `direction` from `"call"/"put"` → `"buy"/"sell"`, and writes the labeled Parquet to `s3://livewell-data-prod/labeled/signals_labeled.parquet`.

The backtest `summary.json` has a `trades` list. Each trade has at minimum: `signal_id`, `win` (bool). The DynamoDB signal record has: `signal_id`, `s3_key`, `date`, `ema_20`, `ema_50`, `rsi_14`, `macd`, `macd_signal`, `macd_hist`, `atr_14`, `session_quality`, `direction` (stored as `"call"` or `"put"`), `signal_valid`.

Direction mapping: `"call"` → `"buy"`, `"put"` → `"sell"`. Any other value stays as-is.

This is a notebook — it has no unit tests. Correctness is verified by checking the output shape and label distribution in the notebook itself.

- [ ] **Step 1: Create `notebooks/livewell-nadex/build_labels.ipynb`**

Create a Jupyter notebook with 5 cells:

**Cell 1 — Setup:**
```python
import boto3
import io
import json
import pandas as pd

BUCKET = "livewell-data-prod"
TABLE = "livewell-signals-prod"
REGION = "us-east-1"

s3 = boto3.client("s3", region_name=REGION)
dynamo = boto3.resource("dynamodb", region_name=REGION)
table = dynamo.Table(TABLE)
```

**Cell 2 — Load backtest trades:**
```python
body = s3.get_object(Bucket=BUCKET, Key="backtest/summary.json")["Body"].read()
summary = json.loads(body)
trades = summary["trades"]
print(f"Loaded {len(trades)} trades from backtest summary")

# Build signal_id → win lookup
win_map = {t["signal_id"]: t["win"] for t in trades}
signal_ids = list(win_map.keys())
print(f"Unique signal_ids: {len(signal_ids)}")
```

**Cell 3 — Batch-fetch from DynamoDB (25 per request):**
```python
from boto3.dynamodb.conditions import Key

def batch_get_signals(signal_ids: list[str]) -> list[dict]:
    records = []
    chunk_size = 25
    for i in range(0, len(signal_ids), chunk_size):
        chunk = signal_ids[i:i + chunk_size]
        keys = [{"signal_id": sid} for sid in chunk]
        response = boto3.client("dynamodb", region_name=REGION).batch_get_item(
            RequestItems={
                TABLE: {
                    "Keys": [{"signal_id": {"S": sid}} for sid in chunk],
                    "ProjectionExpression": "signal_id, s3_key, #d, ema_20, ema_50, rsi_14, macd, macd_signal, macd_hist, atr_14, session_quality, direction, signal_valid",
                    "ExpressionAttributeNames": {"#d": "date"},
                }
            }
        )
        for item in response["Responses"].get(TABLE, []):
            # Deserialize DynamoDB typed values
            record = {k: list(v.values())[0] for k, v in item.items()}
            records.append(record)
        # Handle unprocessed keys (rare but possible)
        unprocessed = response.get("UnprocessedKeys", {})
        if unprocessed:
            print(f"Warning: {len(unprocessed)} unprocessed keys in chunk {i//chunk_size}")
    return records

raw_records = batch_get_signals(signal_ids)
print(f"Fetched {len(raw_records)} signal records from DynamoDB")
```

**Cell 4 — Join and write Parquet:**
```python
_DIR_MAP = {"call": "buy", "put": "sell"}

rows = []
missing = 0
for rec in raw_records:
    sid = rec.get("signal_id")
    if sid not in win_map:
        missing += 1
        continue
    direction = rec.get("direction", "none")
    rows.append({
        "signal_id": sid,
        "s3_key": rec.get("s3_key", ""),
        "date": rec.get("date", ""),
        "ema_20": float(rec.get("ema_20", 0) or 0),
        "ema_50": float(rec.get("ema_50", 0) or 0),
        "rsi_14": float(rec.get("rsi_14", 50) or 50),
        "macd": float(rec.get("macd", 0) or 0),
        "macd_signal": float(rec.get("macd_signal", 0) or 0),
        "macd_hist": float(rec.get("macd_hist", 0) or 0),
        "atr_14": float(rec.get("atr_14", 0) or 0),
        "session_quality": rec.get("session_quality", "medium"),
        "direction": _DIR_MAP.get(direction, direction),
        "signal_valid": str(rec.get("signal_valid", "False")).lower() == "true",
        "label": int(bool(win_map[sid])),
    })

labeled_df = pd.DataFrame(rows)
print(f"Labeled rows: {len(labeled_df)}")
print(f"Missing from win_map: {missing}")
print(f"Label distribution:\n{labeled_df['label'].value_counts()}")

buf = io.BytesIO()
labeled_df.to_parquet(buf, index=False)
buf.seek(0)
s3.put_object(Bucket=BUCKET, Key="labeled/signals_labeled.parquet", Body=buf.read())
print(f"Written to s3://{BUCKET}/labeled/signals_labeled.parquet")
```

**Cell 5 — Verify:**
```python
verify_body = s3.get_object(Bucket=BUCKET, Key="labeled/signals_labeled.parquet")["Body"].read()
verify_df = pd.read_parquet(io.BytesIO(verify_body))
print(f"Verified: {len(verify_df)} rows, columns: {list(verify_df.columns)}")
print(f"Label=1: {verify_df['label'].sum()} ({verify_df['label'].mean():.1%})")
print(f"Label=0: {(verify_df['label'] == 0).sum()}")
```

- [ ] **Step 2: Commit**

```bash
git add notebooks/livewell-nadex/build_labels.ipynb
git commit -m "feat: add build_labels notebook to join backtest outcomes with DynamoDB signals"
```

---

### Task 3: `train_lr.ipynb` — training notebook

**Files:**
- Create: `notebooks/livewell-nadex/train_lr.ipynb`

**Context:** This notebook calls `run_lr_training()` from `apps/api/livewell/models/train_lr.py`. It needs to add `apps/api` to `sys.path` so the import works. The `LIVEWELL_BUCKET` env var must be set to `"livewell-data-prod"`. No unit tests — correctness verified by the printed output.

- [ ] **Step 1: Create `notebooks/livewell-nadex/train_lr.ipynb`**

Create a Jupyter notebook with 3 cells:

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

- [ ] **Step 2: Commit**

```bash
git add notebooks/livewell-nadex/train_lr.ipynb
git commit -m "feat: add train_lr notebook to run LR baseline training and print coefficients"
```

---

## Self-Review Notes

- `_upload_lr_artifact` is separate from `train.py`'s `_upload_artifact` — correct, the S3 paths differ (`lr_baseline` vs `rf_tuned`).
- `_load_labeled_data`, `_build_xy`, `_walk_forward_split` are imported directly from `train.py` — no duplication.
- `_build_xy` in `train.py` reads `record["label"]` (not `record["outcome"]`) — the synthetic fixture in `test_train_lr.py` uses `"label"` to match.
- Direction mapping (`call→buy`, `put→sell`) happens in `build_labels.ipynb` at write time so `build_feature_vector` receives the expected values.
- The 3 pre-existing `test_train.py` failures and 4 `test_router.py` failures are not introduced by this plan.

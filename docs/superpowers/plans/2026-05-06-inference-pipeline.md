# Inference Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire the validated RF tuned model (75.8% win rate, +0.364 EV) into the production worker Lambda so every signal record is scored with `prob_itm` at write time.

**Architecture:** Inference runs as a fourth step inside `runner.py` after `run_signals()`. A separate manual CLI trains and registers a new model artifact when needed. The daily Lambda loads the currently-active model from DynamoDB, downloads the artifact from S3 to `/tmp` (cached across warm invocations), builds a 12-feature vector from the signal record, and writes `score` and `model_version` back onto the record before it is persisted to DynamoDB.

**Tech Stack:** Python 3.12, scikit-learn (RandomForestClassifier), joblib, boto3, pytest, uv.

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `apps/api/livewell/models/__init__.py` | Create | Empty package marker |
| `apps/api/livewell/models/features.py` | Create | `build_feature_vector(record, s3_key)` — signal dict → 12-feature list. Fixed `INSTRUMENT_ENC` mapping. Shared by training and inference. |
| `apps/api/livewell/models/registry.py` | Create | `get_active_model()` — DynamoDB query for active record; `register_model()` — write new record + retire old. |
| `apps/api/livewell/models/inference.py` | Create | `score_signal(record, s3_key)` — load model (with `/tmp` cache), score, return updated record. |
| `apps/api/livewell/models/train.py` | Create | CLI entry point: load labeled data from S3, train RF tuned, evaluate, upload artifact, call `register_model()`. |
| `apps/api/livewell/pipeline/runner.py` | Modify | Import and call `score_signal(record, s3_key)` after `run_signals()`, before returning. |
| `apps/api/tests/models/__init__.py` | Create | Empty package marker |
| `apps/api/tests/models/test_features.py` | Create | Unit tests for `build_feature_vector()`. |
| `apps/api/tests/models/test_inference.py` | Create | Unit tests for `score_signal()` with mocked registry and S3. |
| `apps/api/tests/models/test_train.py` | Create | Integration test for training pipeline on synthetic data. |
| `apps/api/tests/pipeline/test_runner.py` | Modify | Assert `score` and `model_version` are set on the returned record (mock `score_signal`). |

---

## Task 1: Feature encoding

**Files:**
- Create: `apps/api/livewell/models/__init__.py`
- Create: `apps/api/livewell/models/features.py`
- Create: `apps/api/tests/models/__init__.py`
- Create: `apps/api/tests/models/test_features.py`

### Feature set (12 features, in order)

| # | Name | Derivation |
|---|---|---|
| 0 | `ema_ratio` | `float(record["ema_20"]) / float(record["ema_50"])` |
| 1 | `rsi_14` | `float(record["rsi_14"])` |
| 2 | `macd_hist` | `float(record["macd_hist"])` |
| 3 | `atr_14` | `float(record["atr_14"])` |
| 4 | `session_quality_enc` | `{"high": 2, "medium": 1, "low": 0}[record["session_quality"]]` |
| 5 | `direction_enc` | `{"buy": 1, "sell": -1, "none": 0}[record["direction"]]` |
| 6 | `signal_valid_enc` | `int(bool(record["signal_valid"]))` |
| 7 | `ema_20` | `float(record["ema_20"])` |
| 8 | `ema_50` | `float(record["ema_50"])` |
| 9 | `macd` | `float(record["macd"])` |
| 10 | `macd_signal` | `float(record["macd_signal"])` |
| 11 | `instrument_enc` | Fixed mapping from `s3_key` string to int (see below) |

### Fixed instrument encoding

```python
INSTRUMENT_ENC = {
    "EURUSD": 0, "GBPUSD": 1, "USDJPY": 2, "XAUUSD": 3, "US500": 4,
    "CL": 5, "NG": 6, "NQ": 7, "RTY": 8, "YM": 9, "NKD": 10,
    "AUDUSD": 11, "AUDJPY": 12, "EURJPY": 13, "EURGBP": 14,
    "GBPJPY": 15, "USDCAD": 16, "USDCHF": 17, "USDMXN": 18,
}
```

This mapping is fixed at definition time — never fitted — to prevent train/inference drift. Any s3_key not in the mapping raises `KeyError`.

- [ ] **Step 1: Write the failing tests**

Create `apps/api/tests/models/__init__.py` (empty) and `apps/api/tests/models/test_features.py`:

```python
from __future__ import annotations
import pytest
from livewell.models.features import build_feature_vector, INSTRUMENT_ENC


RECORD = {
    "ema_20": "1.08",
    "ema_50": "1.07",
    "rsi_14": "55.0",
    "macd": "0.001",
    "macd_signal": "0.0009",
    "macd_hist": "0.0001",
    "atr_14": "0.005",
    "session_quality": "high",
    "direction": "buy",
    "signal_valid": True,
}


def test_returns_12_features():
    vec = build_feature_vector(RECORD, "EURUSD")
    assert len(vec) == 12


def test_ema_ratio():
    vec = build_feature_vector(RECORD, "EURUSD")
    assert abs(vec[0] - (1.08 / 1.07)) < 1e-9


def test_direction_enc_buy():
    vec = build_feature_vector(RECORD, "EURUSD")
    assert vec[5] == 1


def test_direction_enc_sell():
    r = {**RECORD, "direction": "sell"}
    assert build_feature_vector(r, "EURUSD")[5] == -1


def test_direction_enc_none():
    r = {**RECORD, "direction": "none"}
    assert build_feature_vector(r, "EURUSD")[5] == 0


def test_session_quality_enc_high():
    vec = build_feature_vector(RECORD, "EURUSD")
    assert vec[4] == 2


def test_session_quality_enc_medium():
    r = {**RECORD, "session_quality": "medium"}
    assert build_feature_vector(r, "EURUSD")[4] == 1


def test_session_quality_enc_low():
    r = {**RECORD, "session_quality": "low"}
    assert build_feature_vector(r, "EURUSD")[4] == 0


def test_signal_valid_enc_true():
    vec = build_feature_vector(RECORD, "EURUSD")
    assert vec[6] == 1


def test_signal_valid_enc_false():
    r = {**RECORD, "signal_valid": False}
    assert build_feature_vector(r, "EURUSD")[6] == 0


def test_instrument_enc_eurusd():
    vec = build_feature_vector(RECORD, "EURUSD")
    assert vec[11] == 0


def test_instrument_enc_usdmxn():
    vec = build_feature_vector(RECORD, "USDMXN")
    assert vec[11] == 18


def test_instrument_enc_unknown_raises():
    with pytest.raises(KeyError):
        build_feature_vector(RECORD, "UNKNOWN")


def test_all_values_are_float_or_int():
    vec = build_feature_vector(RECORD, "EURUSD")
    for v in vec:
        assert isinstance(v, (int, float))
```

- [ ] **Step 2: Run to confirm they fail**

```bash
cd apps/api && uv run pytest tests/models/test_features.py -v
```

Expected: `ModuleNotFoundError: No module named 'livewell.models'`

- [ ] **Step 3: Create the package and implement features.py**

Create `apps/api/livewell/models/__init__.py` (empty).

Create `apps/api/livewell/models/features.py`:

```python
from __future__ import annotations

INSTRUMENT_ENC: dict[str, int] = {
    "EURUSD": 0, "GBPUSD": 1, "USDJPY": 2, "XAUUSD": 3, "US500": 4,
    "CL": 5, "NG": 6, "NQ": 7, "RTY": 8, "YM": 9, "NKD": 10,
    "AUDUSD": 11, "AUDJPY": 12, "EURJPY": 13, "EURGBP": 14,
    "GBPJPY": 15, "USDCAD": 16, "USDCHF": 17, "USDMXN": 18,
}

_SESSION_QUALITY_ENC = {"high": 2, "medium": 1, "low": 0}
_DIRECTION_ENC = {"buy": 1, "sell": -1, "none": 0}

FEATURE_NAMES = [
    "ema_ratio", "rsi_14", "macd_hist", "atr_14",
    "session_quality_enc", "direction_enc", "signal_valid_enc",
    "ema_20", "ema_50", "macd", "macd_signal", "instrument_enc",
]


def build_feature_vector(record: dict, s3_key: str) -> list[float]:
    """Return a 12-element feature vector for a signal record."""
    ema_20 = float(record["ema_20"])
    ema_50 = float(record["ema_50"])
    return [
        ema_20 / ema_50,
        float(record["rsi_14"]),
        float(record["macd_hist"]),
        float(record["atr_14"]),
        _SESSION_QUALITY_ENC[record["session_quality"]],
        _DIRECTION_ENC[record["direction"]],
        int(bool(record["signal_valid"])),
        ema_20,
        ema_50,
        float(record["macd"]),
        float(record["macd_signal"]),
        INSTRUMENT_ENC[s3_key],
    ]
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
cd apps/api && uv run pytest tests/models/test_features.py -v
```

Expected: 14 passed.

- [ ] **Step 5: Commit**

```bash
git add apps/api/livewell/models/__init__.py apps/api/livewell/models/features.py apps/api/tests/models/__init__.py apps/api/tests/models/test_features.py
git commit -m "feat: add feature encoding for inference pipeline"
```

---

## Task 2: Model registry

**Files:**
- Create: `apps/api/livewell/models/registry.py`

No new test file — registry is tested indirectly through `test_inference.py` (Task 3) and `test_train.py` (Task 5). Registry is a thin DynamoDB wrapper; the integration is what matters.

- [ ] **Step 1: Create registry.py**

```python
from __future__ import annotations
import os

import boto3
from boto3.dynamodb.conditions import Key


def _table():
    env = os.environ.get("LIVEWELL_ENV", "prod")
    dynamodb = boto3.resource("dynamodb")
    return dynamodb.Table(f"livewell-model-registry-{env}")


def get_active_model(model_name: str = "rf_tuned") -> dict:
    """
    Return the active registry record for model_name.
    Raises RuntimeError if no active record exists.
    Returns dict with keys: version, s3_path, features (and others).
    """
    table = _table()
    resp = table.query(
        KeyConditionExpression=Key("model_name").eq(model_name),
        FilterExpression="#st = :active",
        ExpressionAttributeNames={"#st": "status"},
        ExpressionAttributeValues={":active": "active"},
    )
    items = resp.get("Items", [])
    if not items:
        raise RuntimeError(f"no active model found for {model_name}")
    # If somehow multiple are active, take the most recent by version
    return max(items, key=lambda x: x["version"])


def register_model(
    model_name: str,
    version: str,
    s3_path: str,
    features: list[str],
    win_rate: float,
    ev: float,
    trained_at: str,
) -> None:
    """
    Write a new active registry record and retire any existing active records.
    """
    table = _table()

    # Retire existing active records
    existing = table.query(
        KeyConditionExpression=Key("model_name").eq(model_name),
        FilterExpression="#st = :active",
        ExpressionAttributeNames={"#st": "status"},
        ExpressionAttributeValues={":active": "active"},
    )
    for item in existing.get("Items", []):
        table.update_item(
            Key={"model_name": item["model_name"], "version": item["version"]},
            UpdateExpression="SET #st = :retired",
            ExpressionAttributeNames={"#st": "status"},
            ExpressionAttributeValues={":retired": "retired"},
        )

    # Write new active record
    table.put_item(Item={
        "model_name": model_name,
        "version": version,
        "s3_path": s3_path,
        "features": features,
        "win_rate": str(win_rate),
        "ev": str(ev),
        "trained_at": trained_at,
        "status": "active",
    })
```

- [ ] **Step 2: Commit**

```bash
git add apps/api/livewell/models/registry.py
git commit -m "feat: add model registry read/write"
```

---

## Task 3: Inference — score_signal

**Files:**
- Create: `apps/api/livewell/models/inference.py`
- Create: `apps/api/tests/models/test_inference.py`

- [ ] **Step 1: Write the failing tests**

Create `apps/api/tests/models/test_inference.py`:

```python
from __future__ import annotations
import os
import pickle
import tempfile
from unittest.mock import patch, MagicMock
import pytest
import numpy as np


@pytest.fixture(autouse=True)
def env(monkeypatch):
    monkeypatch.setenv("LIVEWELL_BUCKET", "test-bucket")
    monkeypatch.setenv("LIVEWELL_ENV", "test")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")


RECORD = {
    "ema_20": "1.08",
    "ema_50": "1.07",
    "rsi_14": "55.0",
    "macd": "0.001",
    "macd_signal": "0.0009",
    "macd_hist": "0.0001",
    "atr_14": "0.005",
    "session_quality": "high",
    "direction": "buy",
    "signal_valid": True,
    "score": None,
    "model_version": None,
}

ACTIVE_MODEL = {
    "version": "20260506T142000",
    "s3_path": "models/rf_tuned/v20260506T142000.joblib",
    "features": [
        "ema_ratio", "rsi_14", "macd_hist", "atr_14",
        "session_quality_enc", "direction_enc", "signal_valid_enc",
        "ema_20", "ema_50", "macd", "macd_signal", "instrument_enc",
    ],
}


def _make_mock_model():
    """Return a mock sklearn-like model that returns prob_itm=0.734."""
    model = MagicMock()
    model.predict_proba.return_value = np.array([[0.266, 0.734]])
    return model


def test_score_is_set_on_returned_record(tmp_path, monkeypatch):
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    mock_model = _make_mock_model()
    with patch("livewell.models.inference.get_active_model", return_value=ACTIVE_MODEL), \
         patch("livewell.models.inference._load_model", return_value=mock_model):
        from livewell.models.inference import score_signal
        result = score_signal(dict(RECORD), "EURUSD")
    assert abs(result["score"] - 0.734) < 1e-6
    assert result["model_version"] == "20260506T142000"


def test_original_record_fields_preserved(tmp_path, monkeypatch):
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    mock_model = _make_mock_model()
    with patch("livewell.models.inference.get_active_model", return_value=ACTIVE_MODEL), \
         patch("livewell.models.inference._load_model", return_value=mock_model):
        from livewell.models.inference import score_signal
        result = score_signal(dict(RECORD), "EURUSD")
    assert result["ema_20"] == "1.08"
    assert result["direction"] == "buy"


def test_raises_when_no_active_model(tmp_path, monkeypatch):
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    with patch("livewell.models.inference.get_active_model",
               side_effect=RuntimeError("no active model found for rf_tuned")):
        from livewell.models.inference import score_signal
        with pytest.raises(RuntimeError, match="no active model found"):
            score_signal(dict(RECORD), "EURUSD")


def test_s3_download_called_on_cache_miss(tmp_path, monkeypatch):
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    mock_model = _make_mock_model()
    with patch("livewell.models.inference.get_active_model", return_value=ACTIVE_MODEL), \
         patch("livewell.models.inference._download_model", return_value=mock_model) as mock_dl:
        from livewell.models.inference import score_signal
        score_signal(dict(RECORD), "EURUSD")
    mock_dl.assert_called_once()


def test_s3_download_not_called_on_cache_hit(tmp_path, monkeypatch):
    import joblib
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    mock_model = _make_mock_model()
    # Pre-populate the /tmp cache file
    cache_path = tmp_path / "livewell_model_20260506T142000.joblib"
    joblib.dump(mock_model, str(cache_path))

    with patch("livewell.models.inference.get_active_model", return_value=ACTIVE_MODEL), \
         patch("livewell.models.inference._download_model") as mock_dl:
        from livewell.models.inference import score_signal
        score_signal(dict(RECORD), "EURUSD")
    mock_dl.assert_not_called()
```

- [ ] **Step 2: Run to confirm they fail**

```bash
cd apps/api && uv run pytest tests/models/test_inference.py -v
```

Expected: `ModuleNotFoundError: No module named 'livewell.models.inference'`

- [ ] **Step 3: Implement inference.py**

Create `apps/api/livewell/models/inference.py`:

```python
from __future__ import annotations
import os
import logging

import boto3
import joblib

from livewell.models.features import build_feature_vector
from livewell.models.registry import get_active_model

logger = logging.getLogger(__name__)


def _cache_path(version: str) -> str:
    tmp = os.environ.get("TMPDIR", "/tmp")
    return os.path.join(tmp, f"livewell_model_{version}.joblib")


def _download_model(s3_path: str, dest: str):
    bucket = os.environ["LIVEWELL_BUCKET"]
    s3 = boto3.client("s3")
    s3.download_file(bucket, s3_path, dest)
    return joblib.load(dest)


def _load_model(version: str, s3_path: str):
    path = _cache_path(version)
    if os.path.exists(path):
        logger.info("loading model %s from cache", version)
        return joblib.load(path)
    logger.info("downloading model %s from s3", version)
    return _download_model(s3_path, path)


def score_signal(record: dict, s3_key: str) -> dict:
    """
    Score a signal record using the active model.
    Sets record["score"] = float prob_itm and record["model_version"] = version string.
    Raises on any failure (no active model, download error, encoding error).
    """
    active = get_active_model()
    version = active["version"]
    s3_path = active["s3_path"]

    model = _load_model(version, s3_path)
    features = build_feature_vector(record, s3_key)
    prob_itm = float(model.predict_proba([features])[:, 1][0])

    record["score"] = prob_itm
    record["model_version"] = version
    return record
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
cd apps/api && uv run pytest tests/models/test_inference.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add apps/api/livewell/models/inference.py apps/api/tests/models/test_inference.py
git commit -m "feat: add score_signal inference with tmp cache"
```

---

## Task 4: Training CLI

**Files:**
- Create: `apps/api/livewell/models/train.py`
- Create: `apps/api/tests/models/test_train.py`

- [ ] **Step 1: Check that scikit-learn and joblib are available**

```bash
cd apps/api && uv run python -c "import sklearn, joblib; print('ok')"
```

If this fails, add the dependencies:

```bash
cd apps/api && uv add scikit-learn joblib
```

- [ ] **Step 2: Write the failing test**

Create `apps/api/tests/models/test_train.py`:

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
        "outcome": rng.integers(0, 2, n),
    })


def test_train_produces_model_with_predict_proba(tmp_path):
    df = _synthetic_df()
    with patch("livewell.models.train._load_labeled_data", return_value=df), \
         patch("livewell.models.train._upload_artifact") as mock_upload, \
         patch("livewell.models.train.register_model") as mock_register:
        from livewell.models.train import run_training
        model, metrics = run_training()
    assert hasattr(model, "predict_proba")
    proba = model.predict_proba([[1.0, 55.0, 0.0001, 0.005, 2, 1, 1, 1.08, 1.07, 0.001, 0.0009, 0]])
    assert proba.shape == (1, 2)


def test_train_calls_register_model(tmp_path):
    df = _synthetic_df()
    with patch("livewell.models.train._load_labeled_data", return_value=df), \
         patch("livewell.models.train._upload_artifact", return_value="models/rf_tuned/vTEST.joblib"), \
         patch("livewell.models.train.register_model") as mock_register:
        from livewell.models.train import run_training
        run_training()
    mock_register.assert_called_once()
    call_kwargs = mock_register.call_args.kwargs
    assert call_kwargs["model_name"] == "rf_tuned"
    assert "version" in call_kwargs
    assert "win_rate" in call_kwargs
    assert "ev" in call_kwargs


def test_train_metrics_are_reasonable(tmp_path):
    df = _synthetic_df(n=120)
    with patch("livewell.models.train._load_labeled_data", return_value=df), \
         patch("livewell.models.train._upload_artifact"), \
         patch("livewell.models.train.register_model"):
        from livewell.models.train import run_training
        _, metrics = run_training()
    assert 0.0 <= metrics["win_rate"] <= 1.0
    assert isinstance(metrics["brier_score"], float)
```

- [ ] **Step 3: Run to confirm they fail**

```bash
cd apps/api && uv run pytest tests/models/test_train.py -v
```

Expected: `ModuleNotFoundError: No module named 'livewell.models.train'`

- [ ] **Step 4: Implement train.py**

Create `apps/api/livewell/models/train.py`:

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
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import brier_score_loss
from sklearn.model_selection import GridSearchCV

from livewell.models.features import build_feature_vector, FEATURE_NAMES
from livewell.models.registry import register_model

logger = logging.getLogger(__name__)

_PARAM_GRID = {
    "n_estimators": [100, 200],
    "max_depth": [4, 6, None],
    "min_samples_leaf": [5, 10],
}
_LABELED_S3_PREFIX = "labeled"


def _load_labeled_data() -> pd.DataFrame:
    bucket = os.environ["LIVEWELL_BUCKET"]
    s3 = boto3.client("s3")
    paginator = s3.get_paginator("list_objects_v2")
    frames = []
    for page in paginator.paginate(Bucket=bucket, Prefix=_LABELED_S3_PREFIX):
        for obj in page.get("Contents", []):
            body = s3.get_object(Bucket=bucket, Key=obj["Key"])["Body"].read()
            frames.append(pd.read_parquet(io.BytesIO(body)))
    if not frames:
        raise RuntimeError(f"no labeled data found under s3://{bucket}/{_LABELED_S3_PREFIX}/")
    return pd.concat(frames, ignore_index=True)


def _build_xy(df: pd.DataFrame):
    X, y = [], []
    for _, row in df.iterrows():
        record = row.to_dict()
        for col in ["ema_20", "ema_50", "rsi_14", "macd", "macd_signal",
                    "macd_hist", "atr_14"]:
            record[col] = str(record[col])
        try:
            vec = build_feature_vector(record, str(record["s3_key"]))
            X.append(vec)
            y.append(int(record["outcome"]))
        except (KeyError, ValueError, ZeroDivisionError):
            continue
    return np.array(X, dtype=float), np.array(y, dtype=int)


def _walk_forward_split(df: pd.DataFrame, train_months: int = 6, test_months: int = 1):
    """Yield (train_idx, test_idx) for walk-forward folds."""
    df = df.copy()
    df["_date"] = pd.to_datetime(df["date"], utc=True)
    df = df.sort_values("_date").reset_index(drop=True)
    start = df["_date"].min()
    end = df["_date"].max()
    fold_start = start
    while True:
        train_end = fold_start + pd.DateOffset(months=train_months)
        test_end = train_end + pd.DateOffset(months=test_months)
        if test_end > end:
            break
        train_idx = df.index[(df["_date"] >= fold_start) & (df["_date"] < train_end)].tolist()
        test_idx = df.index[(df["_date"] >= train_end) & (df["_date"] < test_end)].tolist()
        if train_idx and test_idx:
            yield train_idx, test_idx
        fold_start += pd.DateOffset(months=test_months)


def _upload_artifact(model, version: str) -> str:
    bucket = os.environ["LIVEWELL_BUCKET"]
    s3_path = f"models/rf_tuned/v{version}.joblib"
    buf = io.BytesIO()
    joblib.dump(model, buf)
    buf.seek(0)
    boto3.client("s3").put_object(Bucket=bucket, Key=s3_path, Body=buf.read())
    logger.info("uploaded model artifact to s3://%s/%s", bucket, s3_path)
    return s3_path


def run_training() -> tuple:
    """Train RF tuned on full labeled dataset. Return (model, metrics)."""
    df = _load_labeled_data()
    logger.info("loaded %d labeled rows", len(df))

    X, y = _build_xy(df)
    logger.info("built feature matrix: %s rows, %s features", X.shape[0], X.shape[1])

    # Evaluate on the final walk-forward fold
    folds = list(_walk_forward_split(df))
    if not folds:
        raise RuntimeError("not enough data for walk-forward split (need 7+ months)")
    _, test_idx = folds[-1]
    X_test, y_test = X[test_idx], y[test_idx]

    # Train on all data for the production artifact
    gs = GridSearchCV(
        RandomForestClassifier(random_state=42, class_weight="balanced"),
        _PARAM_GRID,
        cv=3,
        scoring="roc_auc",
        n_jobs=-1,
    )
    gs.fit(X, y)
    model = gs.best_estimator_
    logger.info("best params: %s", gs.best_params_)

    # Evaluate on final fold
    proba = model.predict_proba(X_test)[:, 1]
    preds = (proba >= 0.5).astype(int)
    win_rate = float(np.mean(preds == y_test)) if len(y_test) > 0 else 0.0
    brier = float(brier_score_loss(y_test, proba)) if len(y_test) > 0 else float("nan")
    top_half = proba >= np.median(proba)
    ev = float(np.mean(y_test[top_half]) * 2 - 1) if top_half.any() else float("nan")
    metrics = {"win_rate": win_rate, "brier_score": brier, "ev": ev}
    logger.info("final fold metrics: %s", metrics)

    version = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    s3_path = _upload_artifact(model, version)
    register_model(
        model_name="rf_tuned",
        version=version,
        s3_path=s3_path,
        features=FEATURE_NAMES,
        win_rate=win_rate,
        ev=ev,
        trained_at=datetime.now(timezone.utc).isoformat(),
    )
    return model, metrics


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    _, metrics = run_training()
    print(f"Training complete. Metrics: {metrics}")
```

- [ ] **Step 5: Run tests to confirm they pass**

```bash
cd apps/api && uv run pytest tests/models/test_train.py -v
```

Expected: 3 passed.

- [ ] **Step 6: Commit**

```bash
git add apps/api/livewell/models/train.py apps/api/tests/models/test_train.py
git commit -m "feat: add manual retrain CLI for RF tuned model"
```

---

## Task 5: Wire score_signal into runner.py

**Files:**
- Modify: `apps/api/livewell/pipeline/runner.py`
- Modify: `apps/api/tests/pipeline/test_runner.py`

- [ ] **Step 1: Update the runner test first**

Open `apps/api/tests/pipeline/test_runner.py` and replace the existing `test_run_instrument_returns_signal_record` test with one that also mocks `score_signal` and asserts the score fields are set:

```python
def test_run_instrument_returns_signal_record():
    with patch("livewell.pipeline.runner.run_ingestion") as mock_ingest, \
         patch("livewell.pipeline.runner.run_features") as mock_features, \
         patch("livewell.pipeline.runner.run_signals") as mock_signals, \
         patch("livewell.pipeline.runner._read_latest_signal", return_value=MOCK_SIGNAL_ROW), \
         patch("livewell.pipeline.runner.score_signal",
               side_effect=lambda rec, key: {**rec, "score": 0.734, "model_version": "v1"}) as mock_score:

        mock_ingest.return_value = {"succeeded": ["EURUSD"], "failed": []}
        mock_features.return_value = {"succeeded": ["EURUSD"], "failed": []}
        mock_signals.return_value = {"succeeded": ["EURUSD"], "failed": []}

        from livewell.pipeline.runner import run_instrument
        result = run_instrument("EURUSD", "run-123")

    assert result["signal_id"] == "EURUSD__2026-05-05"
    assert result["s3_key"] == "EURUSD"
    assert result["run_id"] == "run-123"
    assert result["direction"] == "buy"
    assert result["score"] == 0.734
    assert result["model_version"] == "v1"
    assert "created_at" in result
    mock_score.assert_called_once_with(result, "EURUSD")
```

- [ ] **Step 2: Run the updated test to confirm it fails**

```bash
cd apps/api && uv run pytest tests/pipeline/test_runner.py::test_run_instrument_returns_signal_record -v
```

Expected: FAIL — `score_signal` import not in runner, and `result["score"]` is `None`.

- [ ] **Step 3: Update runner.py**

Add the import at the top of `apps/api/livewell/pipeline/runner.py` (after the existing imports):

```python
from livewell.models.inference import score_signal
```

Replace the `run_instrument` function body — specifically the block after `run_signals()` and before the `_read_latest_signal` call — to add the `score_signal` call. The full updated `run_instrument` function:

```python
def run_instrument(s3_key: str, run_id: str, backfill: bool = False) -> dict:
    """
    Run ingestion → features → signals → inference for one instrument.
    Returns a DynamoDB signal record with score and model_version set.
    Raises on any stage failure — caller catches and records the error.
    """
    bucket = os.environ["LIVEWELL_BUCKET"]

    run_ingestion(instruments=[s3_key], backfill=backfill)
    run_features(instruments=[s3_key])
    run_signals(instruments=[s3_key])

    row = _read_latest_signal(s3_key, bucket)
    if row is None:
        raise ValueError(f"no signal row found after pipeline for {s3_key}")

    date_str = pd.Timestamp(row["date"]).strftime("%Y-%m-%d")
    record = {
        "signal_id": f"{s3_key}__{date_str}",
        "s3_key": s3_key,
        "run_id": run_id,
        "date": date_str,
        "ema_20": str(row.get("ema_20", "")),
        "ema_50": str(row.get("ema_50", "")),
        "rsi_14": str(row.get("rsi_14", "")),
        "macd": str(row.get("macd", "")),
        "macd_signal": str(row.get("macd_signal", "")),
        "macd_hist": str(row.get("macd_hist", "")),
        "atr_14": str(row.get("atr_14", "")),
        "trend_bias": str(row.get("trend_bias", "")),
        "session_quality": str(row.get("session_quality", "")),
        "strike_candidate": str(row.get("strike_candidate", "")),
        "signal_valid": bool(row.get("signal_valid", False)),
        "direction": str(row.get("direction", "none")),
        "reasoning": str(row.get("reasoning", "{}")),
        "timing_slot": str(row.get("timing_slot", "")),
        "timing_risk": str(row.get("timing_risk", "")),
        "score": None,
        "model_version": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    record = score_signal(record, s3_key)
    return record
```

- [ ] **Step 4: Run the runner tests**

```bash
cd apps/api && uv run pytest tests/pipeline/test_runner.py -v
```

Expected: both tests pass.

- [ ] **Step 5: Run the full test suite**

```bash
cd apps/api && uv run pytest -v
```

Expected: all tests pass (no regressions).

- [ ] **Step 6: Commit**

```bash
git add apps/api/livewell/pipeline/runner.py apps/api/tests/pipeline/test_runner.py
git commit -m "feat: wire score_signal into pipeline runner"
```

---

## Task 6: Full suite check and push

- [ ] **Step 1: Run the complete test suite one final time**

```bash
cd apps/api && uv run pytest -v
```

Expected: all tests pass including the new `tests/models/` suite.

- [ ] **Step 2: Push**

```bash
git push
```

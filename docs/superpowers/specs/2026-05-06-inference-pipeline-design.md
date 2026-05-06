# Inference Pipeline Design

**Date:** 2026-05-06
**Status:** Approved

## Problem

The daily pipeline writes signal records to DynamoDB with `score=None` and `model_version=None`. Phase 2/3 notebook work is complete — a tuned Random Forest model (75.8% win rate, +0.364 EV/$1) has been validated via walk-forward validation across 76 folds. This design operationalizes that model into the production pipeline.

## Approach

Inference runs inside the existing worker Lambda as a fourth pipeline step, after signals are generated. A separate manual retrain script trains, evaluates, and registers a new model artifact when needed. The daily Lambda loads whatever model is currently registered as active.

## Architecture

### New files

| File | Responsibility |
|---|---|
| `apps/api/livewell/models/features.py` | Feature encoding: signal record → 12-feature vector. Shared by training and inference. |
| `apps/api/livewell/models/inference.py` | Load active model from registry, score one signal record, return updated record with `score` and `model_version` set. |
| `apps/api/livewell/models/registry.py` | `get_active_model()` and `register_model()` — DynamoDB registry read/write. |
| `apps/api/livewell/models/train.py` | Manual retrain CLI: load labeled data from S3, train RF tuned, evaluate, upload artifact to S3, register in DynamoDB. |
| `apps/api/tests/models/test_features.py` | Unit tests for feature encoding. |
| `apps/api/tests/models/test_inference.py` | Unit tests for `score_signal()` with mocked registry and S3. |
| `apps/api/tests/models/test_train.py` | Light integration test for training pipeline on synthetic data. |

### Modified files

| File | Change |
|---|---|
| `apps/api/livewell/pipeline/runner.py` | Add `score_signal(record)` call after `run_signals()`, before returning the record. |

---

## Section 1: Model Artifact Management

### Training (manual)

Run from local machine when retraining is needed:

```bash
cd apps/api && LIVEWELL_BUCKET=livewell-data-prod uv run python -m livewell.models.train
```

The script:
1. Reads labeled signals from `s3://livewell-data-prod/` (same source as notebooks)
2. Encodes features via `features.py` (shared with inference)
3. Assigns walk-forward folds (6-month train, 1-month test)
4. Trains RF tuned model using `GridSearchCV` on the full labeled dataset
5. Evaluates on the final fold — computes win rate, Brier score, EV
6. Serializes with `joblib` → uploads to `s3://livewell-data-prod/models/rf_tuned/v<timestamp>.joblib`
7. Writes registry record to `livewell-model-registry-prod` DynamoDB table with `status="active"`
8. Sets any previous `status="active"` record to `status="retired"`

### S3 artifact layout

```
s3://livewell-data-prod/
  models/
    rf_tuned/
      v20260506T142000.joblib
      v20260507T090000.joblib   ← future retrains
```

### Model registry record schema

```
model_name:  "rf_tuned"          ← partition key
version:     "20260506T142000"   ← sort key
s3_path:     "models/rf_tuned/v20260506T142000.joblib"
features:    ["ema_ratio", "rsi_14", "macd_hist", "atr_14",
              "session_quality_enc", "direction_enc", "signal_valid_enc",
              "ema_20", "ema_50", "macd", "macd_signal", "instrument_enc"]
win_rate:    0.758
ev:          0.364
trained_at:  "2026-05-06T14:20:00Z"
status:      "active"            ← "active" | "retired"
```

### Rollback

To roll back to a previous version: manually update the current `status="active"` record to `status="retired"` and the target version to `status="active"` in DynamoDB. No code change required.

---

## Section 2: Inference in the Worker

### Worker flow (updated)

```
run_instrument(s3_key, run_id, backfill)
  → run_ingestion()
  → run_features()
  → run_signals()
  → score_signal(record)         ← new step
  → put_signal(record)
```

### `score_signal(record)` — `livewell/models/inference.py`

1. Call `get_active_model()` → returns `{version, s3_path, features}`
2. Check `/tmp/livewell_model_<version>.joblib`:
   - Present: load from disk (warm Lambda cache)
   - Absent: download from S3, save to `/tmp`
3. Build feature vector from signal record using `features.py`
4. Call `model.predict_proba([[...]])[:, 1]` → `prob_itm`
5. Set `record["score"] = float(prob_itm)` and `record["model_version"] = version`
6. Return updated record

### Feature set (12 features)

| Feature | Source | Encoding |
|---|---|---|
| `ema_ratio` | `ema_20 / ema_50` | float |
| `rsi_14` | signal field | float |
| `macd_hist` | signal field | float |
| `atr_14` | signal field | float |
| `session_quality_enc` | `session_quality` → `{high:2, medium:1, low:0}` | int |
| `direction_enc` | `direction` → `{buy:1, sell:-1, none:0}` | int |
| `signal_valid_enc` | `signal_valid` → int | int |
| `ema_20` | signal field | float |
| `ema_50` | signal field | float |
| `macd` | signal field | float |
| `macd_signal` | signal field | float |
| `instrument_enc` | `s3_key` → label-encoded int (fixed mapping) | int |

**Critical:** `instrument_enc` uses a fixed mapping (not `sklearn.LabelEncoder` fit at inference time) to avoid train/inference drift. The mapping is defined in `features.py` and shared by both train and inference.

---

## Section 3: Data Flow and Storage

### DynamoDB signal record (updated fields)

```
score:         0.734          ← prob_itm, was None
model_version: "20260506T142000"   ← was None
```

No schema changes — both fields already exist in the record structure.

### S3 artifact caching in Lambda

`/tmp` persists across warm invocations of the same Lambda container. The worker checks for the model file by version-stamped filename before downloading, so each container downloads the artifact at most once per cold start.

---

## Section 4: Error Handling

`score_signal()` raises on any failure — model not in registry, S3 download error, feature encoding error, shape mismatch. The worker does not catch these; they propagate to Lambda's async retry mechanism (2 retries, then DLQ → CloudWatch alarm → SNS alert).

`get_active_model()` raises `RuntimeError("no active model found for rf_tuned")` if the registry has no active record, making the "model not yet trained" case immediately visible rather than silently writing `score=None`.

---

## Section 5: Testing

### `tests/models/test_features.py`
- Given a complete signal record dict, verify `build_feature_vector()` returns a list of 12 floats in the correct order
- Verify `ema_ratio = ema_20 / ema_50`
- Verify `direction_enc` maps `buy→1`, `sell→-1`, `none→0`
- Verify `session_quality_enc` maps `high→2`, `medium→1`, `low→0`
- Verify `instrument_enc` returns correct fixed integer for known s3_keys

### `tests/models/test_inference.py`
- Mock `get_active_model()` returning a version and s3_path; mock S3 download; verify `score` and `model_version` are set on the returned record
- Verify `/tmp` cache is used on second call (S3 download not called twice)
- Verify `score_signal()` raises when `get_active_model()` raises

### `tests/models/test_train.py`
- Build a synthetic labeled DataFrame (50 rows, all 12 features, binary label)
- Run training pipeline end-to-end
- Verify resulting model has `predict_proba` method and produces output of correct shape
- Verify `register_model()` is called with correct fields (mock DynamoDB and S3)

---

## Phase 5 note

Automated weekly retraining (preferred long-term) is deferred to Phase 5 per the roadmap. The manual train script is designed so the Phase 5 automated version is a thin wrapper around it.

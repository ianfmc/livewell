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
            # s3_key in labeled data is a bare instrument symbol (e.g. "EURUSD"), not an S3 path
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
    if folds:
        _, test_idx = folds[-1]
    else:
        # Fallback for small datasets (training or testing): use last 20% as test
        n = len(X)
        split = max(1, int(n * 0.8))
        test_idx = list(range(split, n))
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

    now = datetime.now(timezone.utc)
    version = now.strftime("%Y%m%dT%H%M%S")
    s3_path = _upload_artifact(model, version)
    register_model(
        model_name="rf_tuned",
        version=version,
        s3_path=s3_path,
        features=FEATURE_NAMES,
        win_rate=win_rate,
        ev=ev,
        trained_at=now.isoformat(),
    )
    return model, metrics


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    _, metrics = run_training()
    print(f"Training complete. Metrics: {metrics}")

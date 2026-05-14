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
        X_train_fb, y_train_fb = X[:split], y[:split]
        X_test, y_test = X[test_idx], y[test_idx]
        tmp = LogisticRegression(C=1.0, class_weight="balanced", max_iter=1000, solver="lbfgs", random_state=42)
        tmp.fit(X_train_fb, y_train_fb)
        proba = tmp.predict_proba(X_test)[:, 1]
        preds = (proba >= 0.5).astype(int)
        win_rate = float(np.mean(preds == y_test)) if len(y_test) > 0 else 0.0
        brier = float(brier_score_loss(y_test, proba)) if len(y_test) > 0 else float("nan")
        top_half = proba >= np.median(proba)
        ev = float(np.mean(y_test[top_half]) * 2 - 1) if top_half.any() else float("nan")
        metrics = {"win_rate": win_rate, "brier_score": brier, "ev": ev}

    # Train final model on all data
    model = LogisticRegression(
        C=1.0,
        class_weight="balanced",
        max_iter=1000,
        solver="lbfgs",
        random_state=42,
    )
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

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


def score_signal(record: dict, instrument: str) -> dict:
    """
    Score a signal record using the active model.
    Sets record["score"] = float prob_itm and record["model_version"] = version string.
    Raises on any failure (no active model, download error, encoding error).
    """
    active = get_active_model()
    version = active["version"]
    s3_path = active["s3_path"]

    model = _load_model(version, s3_path)
    features = build_feature_vector(record, instrument)
    prob_itm = float(model.predict_proba([features])[:, 1][0])

    record["score"] = prob_itm
    record["model_version"] = version
    return record

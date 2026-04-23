from __future__ import annotations
from typing import Literal
from pydantic import BaseModel


class FeatureStatus(BaseModel):
    name: str
    status: Literal['Available', 'Stale', 'Missing']


class DriftWarning(BaseModel):
    feature: str
    description: str


class ModelHealth(BaseModel):
    overallStatus: Literal['Healthy', 'Warning', 'Degraded']
    trainingDate: str
    dataFreshness: str
    calibrationError: float
    validationAccuracy: float
    features: list[FeatureStatus]
    driftWarnings: list[DriftWarning]

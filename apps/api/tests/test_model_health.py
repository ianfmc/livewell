from decimal import Decimal
from unittest.mock import patch

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def _mock_registry_record(win_rate: float = 0.64, trained_at: str = "2026-04-18") -> dict:
    return {
        "model_name": "rf_tuned",
        "version": "20260418T120000",
        "s3_path": "s3://bucket/model.pkl",
        "features": ["EMA-20", "RSI-14"],
        "win_rate": Decimal(str(win_rate)),
        "ev": Decimal("0.12"),
        "trained_at": trained_at,
        "status": "active",
    }


def test_model_health_returns_200():
    with patch("routers.model_health.get_active_model", return_value=_mock_registry_record()):
        response = client.get("/api/model/health")
    assert response.status_code == 200


def test_model_health_healthy_when_win_rate_high():
    with patch("routers.model_health.get_active_model", return_value=_mock_registry_record(win_rate=0.65)):
        response = client.get("/api/model/health")
    data = response.json()
    assert data["overallStatus"] == "Healthy"
    assert data["trainingDate"] == "2026-04-18"
    assert len(data["features"]) == 8
    assert all(f["status"] == "Available" for f in data["features"])
    assert data["driftWarnings"] == []


def test_model_health_warning_when_win_rate_low():
    with patch("routers.model_health.get_active_model", return_value=_mock_registry_record(win_rate=0.55)):
        response = client.get("/api/model/health")
    data = response.json()
    assert data["overallStatus"] == "Warning"


def test_model_health_degraded_when_no_active_model():
    with patch("routers.model_health.get_active_model", side_effect=RuntimeError("no active model")):
        response = client.get("/api/model/health")
    data = response.json()
    assert data["overallStatus"] == "Degraded"
    assert data["trainingDate"] == "unknown"
    assert data["dataFreshness"] == "Stale"
    assert len(data["features"]) == 8
    assert all(f["status"] == "Missing" for f in data["features"])
    assert len(data["driftWarnings"]) == 1
    assert data["driftWarnings"][0]["feature"] == "All"

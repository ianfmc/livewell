from __future__ import annotations

import json
from pathlib import Path

import pytest
from livewell.backtest.aggregator import build_summary
from schemas.backtest import BacktestSummary

FIXTURE = Path(__file__).parent / "fixtures" / "frozen_trades.json"


@pytest.fixture(scope="module")
def frozen() -> dict:
    """Load the sanitized frozen trades fixture (synthetic data, not production)."""
    return json.loads(FIXTURE.read_text())


@pytest.fixture(scope="module")
def summary(frozen: dict) -> dict:
    """build_summary over the frozen trades — the artifact the route serves."""
    return build_summary(frozen["trades"])


class TestContractShape:
    """The LW-605 gap: validate build_summary output against the real schema."""

    def test_summary_validates_against_schema(self, summary: dict):
        # Raises ValidationError if the aggregator drifts from the contract.
        model = BacktestSummary.model_validate(summary)
        assert isinstance(model, BacktestSummary)

    def test_schema_roundtrips_without_dropping_fields(self, summary: dict):
        # Re-dumping the validated model must preserve every contract key.
        model = BacktestSummary.model_validate(summary)
        dumped = model.model_dump()
        for key in (
            "totalTrades", "winRate", "avgEdge", "maxDrawdown",
            "equityCurve", "rows", "signalValidSplit",
        ):
            assert key in dumped

    def test_rows_carry_default_expiry_window(self, summary: dict):
        model = BacktestSummary.model_validate(summary)
        assert model.rows, "fixture should produce at least one row"
        assert all(r.expiryWindow == "Daily" for r in model.rows)


class TestHeadlineFigures:
    """Deterministic figures hand-computed in the fixture's `expected` block."""

    def test_total_trades(self, summary: dict, frozen: dict):
        assert summary["totalTrades"] == frozen["expected"]["totalTrades"]

    def test_win_rate(self, summary: dict, frozen: dict):
        assert summary["winRate"] == pytest.approx(frozen["expected"]["winRate"])

    def test_avg_edge(self, summary: dict, frozen: dict):
        assert summary["avgEdge"] == pytest.approx(frozen["expected"]["avgEdge"])

    def test_max_drawdown(self, summary: dict, frozen: dict):
        assert summary["maxDrawdown"] == pytest.approx(
            frozen["expected"]["maxDrawdown"], abs=1e-4
        )

    def test_equity_curve_values(self, summary: dict, frozen: dict):
        values = [p["value"] for p in summary["equityCurve"]]
        assert values == pytest.approx(frozen["expected"]["equityCurveValues"])


class TestSplitFromFixture:
    """valid/invalid split reflects the fixture's signal_valid flags."""

    def test_split_counts(self, summary: dict):
        split = summary["signalValidSplit"]
        # 3 valid trades, 1 invalid in the fixture.
        assert split["valid"]["trades"] == 3
        assert split["invalid"]["trades"] == 1


class TestDeterminism:
    def test_build_summary_is_deterministic(self, frozen: dict):
        a = build_summary(frozen["trades"])
        b = build_summary(frozen["trades"])
        assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)

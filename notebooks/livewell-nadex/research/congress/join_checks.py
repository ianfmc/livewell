#!/usr/bin/env python
"""LW-108 — leakage-safe-join checks over invented fixtures.

Research-prep ONLY. Fabricated records + an invented price series. No real
disclosure acquisition, no production integration, NO model training and NO
ablation run (that is LW-206). Reuses LW-106 aggregation and the LW-107 clock
(eng-review Q1 — one source of truth for timing).

Defines the point-in-time left-join that attaches cng_* columns to the existing
feature spine, per
docs/superpowers/specs/2026-10-16-join-ablation-protocol-design.md.

Run:  python join_checks.py
"""
from __future__ import annotations

import re
import unittest
from datetime import timezone
from pathlib import Path

from normalization_checks import load_records, _parse_ts, is_eligible, resolve_asset, TICKER_TO_INSTRUMENT
from aggregation_checks import (
    agg_ticker, agg_sector, agg_consensus, agg_imbalance, agg_market_factor,
    contributing, _dir, _amendment_resolved, T_ALL, T_PRE_AMEND,
)

def _find_repo_root(start: Path) -> Path:
    p = start.resolve()
    for parent in [p, *p.parents]:
        if (parent / "docs/superpowers/specs").is_dir():
            return parent
    return start


_REPO = _find_repo_root(Path(__file__))
SPEC = _REPO / "docs/superpowers/specs/2026-10-16-join-ablation-protocol-design.md"

# ---- invented price series (T1) — US500 proxy, clearly fake --------------
# (date, close). Fabricated; used only to exercise cng_unrealized point-in-time.
PRICES_US500 = [
    ("2026-01-20", 5000.0),  # ~ transaction_date of demo:0006
    ("2026-02-19", 5050.0),  # original availability
    ("2026-03-15", 5120.0),  # T_PRE_AMEND
    ("2026-04-20", 5200.0),  # amendment availability
    ("2026-05-01", 5260.0),  # T_ALL
]


def _prices_asof(series, t):
    """Prices with price_ts <= t ONLY (A4a hard leakage guard)."""
    out = []
    for d, c in series:
        if _parse_ts(d + "T00:00:00Z") <= t:
            out.append((d, c))
    return out


def cng_unrealized(records, t, instrument, price_series) -> float:
    """Fenced candidate column: attenuate signal if the expected move already
    happened by t, using ONLY prices with price_ts <= t. (Design stub for the
    leakage-safety check; the realization test/threshold is an LW-206 tunable.)"""
    E = contributing(records, t, instrument)
    if not E:
        return 0.0
    net = sum(_dir(r["tx_type"]) for r in E)
    prices = _prices_asof(price_series, t)
    if len(prices) < 2 or net == 0:
        return float(net)
    moved = prices[-1][1] - prices[0][1]           # realized move so far (<= t)
    # if the market already moved in the signal's direction, attenuate toward 0
    if (net > 0 and moved > 0) or (net < 0 and moved < 0):
        return float(net) * 0.5
    return float(net)


def join_row(records, t, instrument, price_series) -> dict:
    """Point-in-time left-join: build the cng_* columns for one (instrument,date) row."""
    E = contributing(records, t, instrument)
    present = len(E) > 0
    tick = agg_ticker(records, t, instrument)
    sect = agg_sector(records, t, instrument)
    cons = agg_consensus(records, t, instrument)
    imb = agg_imbalance(records, t, instrument)
    return {
        "cng_ticker": tick["value"],
        "cng_sector": sect["value"],
        "cng_consensus": cons["value"],
        "cng_imbalance": imb["value"],
        "cng_imbalance_u": imb["uncertainty"],
        "cng_present": present,
        "cng_unrealized": cng_unrealized(records, t, instrument, price_series),
    }


# =============================================================================
class TestJoinContract(unittest.TestCase):
    def test_left_join_attaches_cng_columns(self):
        row = join_row(_amendment_resolved(load_records(), T_ALL), T_ALL, "US500", PRICES_US500)
        for col in ("cng_ticker", "cng_sector", "cng_consensus", "cng_imbalance",
                    "cng_present", "cng_unrealized"):
            self.assertIn(col, row)

    def test_point_in_time_per_row(self):
        recs = load_records()
        pre = join_row(_amendment_resolved(recs, T_PRE_AMEND), T_PRE_AMEND, "US500", PRICES_US500)
        post = join_row(_amendment_resolved(recs, T_ALL), T_ALL, "US500", PRICES_US500)
        # amendment flips one buy->sale: imbalance strictly lower after
        self.assertLess(post["cng_imbalance"], pre["cng_imbalance"])

    def test_absence_sets_present_false_and_zero(self):
        early = _parse_ts("2026-01-01T00:00:00Z")      # nothing available yet
        row = join_row(load_records(), early, "US500", PRICES_US500)
        self.assertFalse(row["cng_present"])
        self.assertEqual(row["cng_ticker"], 0.0)
        self.assertEqual(row["cng_imbalance"], 0.0)

    def test_unmapped_instrument_absent(self):
        row = join_row(load_records(), T_ALL, "RUT", PRICES_US500)   # WIDG only, unmapped
        self.assertFalse(row["cng_present"])


class TestUnrealizedLeakageGuard(unittest.TestCase):
    def test_only_uses_prices_at_or_before_t(self):
        asof = _prices_asof(PRICES_US500, T_PRE_AMEND)
        latest = max(d for d, _ in asof)
        self.assertLessEqual(_parse_ts(latest + "T00:00:00Z"), T_PRE_AMEND)
        # a future bar (2026-05-01) must NOT appear in the <= T_PRE_AMEND set
        self.assertNotIn("2026-05-01", [d for d, _ in asof])

    def test_attenuates_when_move_already_realized(self):
        recs = _amendment_resolved(load_records(), T_PRE_AMEND)
        raw_net = sum(_dir(r["tx_type"]) for r in contributing(recs, T_PRE_AMEND, "US500"))
        val = cng_unrealized(recs, T_PRE_AMEND, "US500", PRICES_US500)
        # pre-amend net is buy (+), price rose by T_PRE_AMEND -> attenuated toward 0
        if raw_net > 0:
            self.assertLess(abs(val), abs(raw_net))


class TestDeterminism(unittest.TestCase):
    def test_join_deterministic(self):
        recs = _amendment_resolved(load_records(), T_ALL)
        a = join_row(recs, T_ALL, "US500", PRICES_US500)
        b = join_row(recs, T_ALL, "US500", PRICES_US500)
        self.assertEqual(a, b)


class TestAblationProtocolCompleteness(unittest.TestCase):
    """T2 — structural check only. NO model trained, NO edge computed."""
    def setUp(self):
        self.text = SPEC.read_text() if SPEC.exists() else ""

    def test_spec_present(self):
        self.assertTrue(self.text, f"spec not found at {SPEC}")

    def test_names_frozen_baseline(self):
        self.assertIn("baseline-v1", self.text)

    def test_names_model_and_folds(self):
        self.assertRegex(self.text, r"rf_tuned")
        self.assertIn("walk-forward", self.text)

    def test_pre_registered_metrics_and_rule(self):
        self.assertRegex(self.text, r"[Pp]re-register")
        self.assertRegex(self.text, r"win rate")
        self.assertRegex(self.text, r"[Dd]ecision rule")

    def test_declares_no_run_here(self):
        self.assertRegex(self.text, r"[Nn]o model train|No ablation run|run in LW-206|runs the ablation")


if __name__ == "__main__":
    unittest.main(verbosity=2)

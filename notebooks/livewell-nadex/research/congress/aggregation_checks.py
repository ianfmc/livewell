#!/usr/bin/env python
"""LW-106 — aggregation experiments checks over invented disclosure records.

Research-prep ONLY. Operates exclusively on the fabricated records in
sample_disclosures.json (no real disclosure acquisition, no production
integration). Reuses the LW-107 clock and LW-105 resolver from
normalization_checks.py (eng-review Q1 — one source of truth for timing).

Defines the five aggregation axes (ticker, sector, market-factor,
cross-filer consensus, purchase/sale imbalance) as pure functions over the
shared eligible + recency-weighted contributing set, per
docs/superpowers/specs/2026-10-16-aggregation-experiments-design.md.

Run:  python aggregation_checks.py
"""
from __future__ import annotations

import unittest
from datetime import timezone

from normalization_checks import (
    load_records, _parse_ts, available_at, is_eligible,
    resolve_asset, TICKER_TO_INSTRUMENT,
)

# ---- shared core (LW-106 §2/§3) ---------------------------------------------
H_DAYS = 21.0            # recency half-life (named param, ablation-tunable)
EPS = 1e-9

# invented factor-bucket + direction maps (would live in the curated map)
TICKER_BUCKET = {"DEMO": "large_cap"}
BUCKET_TO_INSTRUMENT = {"large_cap": "US500", "small_cap": "RUT"}


def _dir(tx_type: str) -> int:
    if tx_type == "purchase":
        return +1
    if tx_type in ("sale", "sale_partial", "sale_full"):
        return -1
    return 0


def _midpoint_uncert(record: dict) -> tuple[float, float]:
    m = (record["amount_min"] + record["amount_max"]) / 2
    u = (record["amount_max"] - record["amount_min"]) / 2
    return m, u


def _weight(record: dict, t) -> float:
    # Decay on TRANSACTION age (Ian's hypothesis): the economic signal ages from
    # the trade date. Leakage-safe because eligibility is gated on
    # public_availability_at upstream (LW-107 C1); transaction_date is used here
    # only as a descriptive field (LW-107 C1a permits this), never as the clock.
    txn = _parse_ts(record["transaction_date"] + "T00:00:00Z")
    age_days = (t - txn).total_seconds() / 86400.0
    age_days = max(age_days, 0.0)
    return 0.5 ** (age_days / H_DAYS)


def contributing(records: list[dict], t, instrument: str) -> list[dict]:
    """Eligible (LW-107) + contributing (LW-105 R1) + mapped to `instrument`."""
    out = []
    for r in records:
        if not is_eligible(r, t):
            continue
        res = resolve_asset(r)
        if res["resolved_ticker"] is None or res["needs_manual_review"]:
            continue
        if TICKER_TO_INSTRUMENT.get(res["resolved_ticker"]) != instrument:
            continue
        out.append(r)
    return out


# ---- the five axes (LW-106 §5) ----------------------------------------------
def agg_ticker(records, t, instrument) -> dict:
    E = contributing(records, t, instrument)
    if not E:
        return {"value": 0.0, "uncertainty": None, "n": 0}
    return {"value": sum(_weight(r, t) * _dir(r["tx_type"]) for r in E),
            "uncertainty": None, "n": len(E)}


def agg_sector(records, t, instrument) -> dict:
    # same reduction as ticker in this invented set (DEMO -> US500 via sector)
    return agg_ticker(records, t, instrument)


def agg_market_factor(records, t) -> dict:
    """Factor-bucket rollup over mapped equities only (A4=A). Macro proxy deferred."""
    out: dict[str, float] = {}
    for inst in set(TICKER_TO_INSTRUMENT.values()):
        for r in contributing(records, t, inst):
            res = resolve_asset(r)
            bucket = TICKER_BUCKET.get(res["resolved_ticker"], "other")
            out[bucket] = out.get(bucket, 0.0) + _weight(r, t) * _dir(r["tx_type"])
    return out


def agg_consensus(records, t, instrument) -> dict:
    """Distinct-filer agreement in [-1,1]; each filer once; dedup by content_hash."""
    seen_hashes = set()
    net_by_filer: dict[str, int] = {}
    for r in contributing(records, t, instrument):
        if r["content_hash"] in seen_hashes:
            continue                       # duplicate re-pull -> ignore
        seen_hashes.add(r["content_hash"])
        net_by_filer[r["filer_name"]] = net_by_filer.get(r["filer_name"], 0) + _dir(r["tx_type"])
    f_plus = sum(1 for v in net_by_filer.values() if v > 0)
    f_minus = sum(1 for v in net_by_filer.values() if v < 0)
    denom = max(1, f_plus + f_minus)
    return {"value": (f_plus - f_minus) / denom, "f_plus": f_plus, "f_minus": f_minus}


def agg_imbalance(records, t, instrument) -> dict:
    E = contributing(records, t, instrument)
    buy = sell = u_tot = 0.0
    for r in E:
        w = _weight(r, t)
        m, u = _midpoint_uncert(r)
        d = _dir(r["tx_type"])
        if d > 0:
            buy += w * m
        elif d < 0:
            sell += w * m
        u_tot += w * u
    value = (buy - sell) / max(EPS, buy + sell) if (buy + sell) > 0 else 0.0
    return {"value": value, "uncertainty": (u_tot or None)}


# =============================================================================
T_ALL = _parse_ts("2026-05-01T23:59:59Z")        # after everything is available
T_PRE_AMEND = _parse_ts("2026-03-15T23:59:59Z")  # before demo:0007 (04-20)


def _amendment_resolved(records, t):
    """Apply point-in-time supersedence for the demo:0006/0007 pair at t."""
    out = []
    amend = next((r for r in records if r["record_id"] == "demo:0007"), None)
    for r in records:
        if r["record_id"] == "demo:0006" and amend and is_eligible(amend, t):
            continue                      # superseded once amendment is public
        if r["record_id"] == "demo:0007" and not is_eligible(amend, t):
            continue                      # amendment not yet public
        out.append(r)
    return out


class TestAxesContract(unittest.TestCase):
    def setUp(self):
        self.recs = load_records()

    def test_ticker_per_instrument_grain(self):
        r = agg_ticker(self.recs, T_ALL, "US500")
        self.assertIn("value", r)
        self.assertIsInstance(r["n"], int)

    def test_unmapped_contributes_zero(self):
        # WIDG (demo:0005) maps to no instrument -> never in any instrument's set
        self.assertEqual(agg_ticker(self.recs, T_ALL, "RUT")["n"], 0)

    def test_sparse_period_neutral(self):
        early = _parse_ts("2026-01-01T00:00:00Z")   # nothing available yet
        self.assertEqual(agg_ticker(self.recs, early, "US500"),
                         {"value": 0.0, "uncertainty": None, "n": 0})
        self.assertEqual(agg_imbalance(self.recs, early, "US500")["value"], 0.0)


class TestConsensus(unittest.TestCase):
    def setUp(self):
        self.recs = load_records()

    def test_distinct_filers_counted_once_each(self):
        # At T_PRE_AMEND: Jane(buy), Alex(buy, pre-amend), Morgan(buy) -> all buy.
        recs = _amendment_resolved(self.recs, T_PRE_AMEND)
        c = agg_consensus(recs, T_PRE_AMEND, "US500")
        self.assertEqual(c["f_plus"], 3)
        self.assertEqual(c["f_minus"], 0)
        self.assertEqual(c["value"], 1.0)

    def test_duplicate_not_double_counted(self):
        # demo:0008 duplicates demo:0001 (same content_hash) -> Jane still counts once
        recs = _amendment_resolved(self.recs, T_PRE_AMEND)
        c = agg_consensus(recs, T_PRE_AMEND, "US500")
        self.assertEqual(c["f_plus"], 3)   # not 4


class TestImbalancePointInTime(unittest.TestCase):
    def setUp(self):
        self.recs = load_records()

    def test_pre_amendment_buy_dominant(self):
        recs = _amendment_resolved(self.recs, T_PRE_AMEND)
        self.assertGreater(agg_imbalance(recs, T_PRE_AMEND, "US500")["value"], 0.0)

    def test_post_amendment_shifts_toward_sale(self):
        pre = agg_imbalance(_amendment_resolved(self.recs, T_PRE_AMEND), T_PRE_AMEND, "US500")["value"]
        post = agg_imbalance(_amendment_resolved(self.recs, T_ALL), T_ALL, "US500")["value"]
        self.assertLess(post, pre)   # amendment flips one buy -> sale

    def test_value_range_uses_bracket_not_point(self):
        r = agg_imbalance(_amendment_resolved(self.recs, T_ALL), T_ALL, "US500")
        self.assertIsNotNone(r["uncertainty"])   # uncertainty carried, not dropped


class TestMarketFactor(unittest.TestCase):
    def test_factor_bucket_rollup(self):
        buckets = agg_market_factor(load_records(), T_ALL)
        self.assertIn("large_cap", buckets)   # DEMO -> large_cap bucket


class TestDeterminism(unittest.TestCase):
    def test_aggregation_deterministic(self):
        recs = _amendment_resolved(load_records(), T_ALL)
        a = agg_imbalance(recs, T_ALL, "US500")
        b = agg_imbalance(recs, T_ALL, "US500")
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main(verbosity=2)

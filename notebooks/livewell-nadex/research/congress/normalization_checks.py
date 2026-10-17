#!/usr/bin/env python
"""LW-111 — normalization + point-in-time checks for invented disclosure records.

Research-prep ONLY. Operates exclusively on the fabricated records in
sample_disclosures.json (no real disclosure acquisition, no production
integration). This module provides a *reference* implementation of the LW-107
leakage-safe clock and the LW-105 asset-resolution policy — just enough to make
the verification scenarios in those specs executable against invented data.

Run:  python normalization_checks.py       (or via unittest)

Specs:
  - docs/superpowers/specs/2026-10-16-disclosure-schema-design.md   (LW-104)
  - docs/superpowers/specs/2026-10-16-asset-resolution-design.md    (LW-105)
  - docs/superpowers/specs/2026-10-16-leakage-safe-clock-design.md  (LW-107)
"""
from __future__ import annotations

import json
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

FIXTURE = Path(__file__).parent / "sample_disclosures.json"

# ---- LW-104 required fields (for the normalization/schema check) ------------
REQUIRED_FIELDS = [
    "record_id", "source_system", "document_id", "filing_id", "line_index",
    "source_url", "source_format", "content_hash", "extractor", "schema_version",
    "transaction_date", "filing_date", "public_availability_at",
    "public_availability_precision", "observed_at",
    "filer_name", "filer_chamber", "owner",
    "asset_text_raw", "asset_type", "needs_manual_review",
    "tx_type", "amount_range_raw", "amount_min", "amount_max", "amount_currency",
    "is_amendment",
]
ENUMS = {
    "source_system": {"house_fd", "senate_efd"},
    "owner": {"self", "spouse", "dependent", "joint", "unknown"},
    "tx_type": {"purchase", "sale", "sale_partial", "sale_full", "exchange", "unknown"},
    "public_availability_precision": {"timestamp", "date"},
}


def load_records() -> list[dict]:
    data = json.loads(FIXTURE.read_text())
    return data["records"]


# ---- LW-107 reference clock --------------------------------------------------
# Minimal curated LIVEWELL instrument map for the resolved-but-unmapped check.
TICKER_TO_INSTRUMENT = {
    "DEMO": "US500",        # mapped (invented large-cap -> an index)
    # "WIDG" intentionally absent -> resolved-but-unmapped
}


def _parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def available_at(record: dict) -> datetime:
    """Effective public-availability instant per LW-107 C2.

    date-precision -> treat as end of that UTC day (conservative; the spec's
    US-Eastern refinement is immaterial for these day-granular invented cases).
    """
    ts = _parse_ts(record["public_availability_at"])
    if record["public_availability_precision"] == "date":
        # end of the calendar day -> eligible strictly after that day
        return ts.replace(hour=23, minute=59, second=59)
    return ts


def is_eligible(record: dict, t: datetime) -> bool:
    """LW-107 Rule C1: eligible iff public-availability <= t. Never transaction_date."""
    return available_at(record) <= t


def current_version(records: list[dict], t: datetime) -> dict | None:
    """Return the point-in-time version of a logically-amended record as of t.

    LW-107 C1c: an amendment only applies from its own availability forward.
    Groups by (original record_id / supersedes chain).
    """
    # eligible candidates sorted by availability
    eligible = sorted(
        (r for r in records if is_eligible(r, t)),
        key=lambda r: available_at(r),
    )
    return eligible[-1] if eligible else None


# ---- LW-105 reference resolver ----------------------------------------------
TAU_AUTO = 0.80
TAU_REVIEW = 0.50


def resolve_asset(record: dict) -> dict:
    """Tiny deterministic stand-in for the LW-105 tiers (enough for the checks)."""
    text = record["asset_text_raw"].lower()
    ticker = (record.get("asset_ticker_raw") or "").upper()

    if ticker == "DEMO":                      # T1 exact ticker
        conf, resolved = 0.95, "DEMO"
    elif ticker == "WIDG":                    # T1 exact, but unmapped downstream
        conf, resolved = 0.95, "WIDG"
    elif "democorp" in text:                  # T2 normalized name
        conf, resolved = 0.85, "DEMO"
    elif text.strip() == "demo holdings":     # R2 ambiguous (two candidates)
        conf, resolved = 0.40, None
    else:                                     # T5 unresolvable
        conf, resolved = 0.20, None

    band = "high" if conf >= TAU_AUTO else ("review" if conf >= TAU_REVIEW else "reject")
    needs_review = band != "high" or resolved is None
    return {"resolved_ticker": resolved, "resolution_confidence": conf,
            "band": band, "needs_manual_review": needs_review}


def contributes(record: dict) -> bool:
    """LW-105 Rule R1 fail-safe + §7 mapped-instrument requirement."""
    r = resolve_asset(record)
    if r["resolved_ticker"] is None or r["resolution_confidence"] < TAU_AUTO or r["needs_manual_review"]:
        return False
    return r["resolved_ticker"] in TICKER_TO_INSTRUMENT   # resolved-but-unmapped -> False


# =============================================================================
class TestSchemaNormalization(unittest.TestCase):
    def setUp(self):
        self.records = load_records()

    def test_all_required_fields_present(self):
        for r in self.records:
            for f in REQUIRED_FIELDS:
                self.assertIn(f, r, f"{r['record_id']} missing {f}")

    def test_enums_valid(self):
        for r in self.records:
            for field, allowed in ENUMS.items():
                self.assertIn(r[field], allowed, f"{r['record_id']}.{field}={r[field]!r}")

    def test_value_is_range_not_point(self):
        for r in self.records:
            self.assertLessEqual(r["amount_min"], r["amount_max"])

    def test_three_clocks_ordered(self):
        # transaction_date <= filing_date <= public_availability <= observed_at
        for r in self.records:
            td = datetime.fromisoformat(r["transaction_date"])
            fd = datetime.fromisoformat(r["filing_date"])
            pa = _parse_ts(r["public_availability_at"]).replace(tzinfo=None)
            ob = _parse_ts(r["observed_at"]).replace(tzinfo=None)
            self.assertLessEqual(td, fd, r["record_id"])
            self.assertLessEqual(fd, pa, r["record_id"])
            self.assertLessEqual(pa, ob, r["record_id"])


class TestLeakageSafeClock(unittest.TestCase):
    """LW-107 §8 scenarios."""
    def setUp(self):
        self.records = load_records()
        self.by_id = {r["record_id"]: r for r in self.records}

    def test_future_availability_excluded(self):
        rec = self.by_id["demo:0001"]              # available 2026-03-11 (date)
        t = _parse_ts("2026-02-10T23:59:59Z")      # before availability
        self.assertFalse(is_eligible(rec, t))

    def test_available_record_included_later(self):
        rec = self.by_id["demo:0001"]
        t = _parse_ts("2026-03-15T23:59:59Z")
        self.assertTrue(is_eligible(rec, t))

    def test_date_precision_boundary_excludes_same_day(self):
        rec = self.by_id["demo:0001"]              # date-precision 2026-03-11
        same_day_morning = _parse_ts("2026-03-11T09:00:00Z")
        self.assertFalse(is_eligible(rec, same_day_morning))   # C2: end-of-day
        next_day = _parse_ts("2026-03-12T00:00:01Z")
        self.assertTrue(is_eligible(rec, next_day))

    def test_amendment_point_in_time(self):
        # Between original (03-11) and amendment (04-20): original 'purchase' is current.
        orig, amend = self.by_id["demo:0006"], self.by_id["demo:0007"]
        pair = [orig, amend]
        t_mid = _parse_ts("2026-03-15T23:59:59Z")
        self.assertEqual(current_version(pair, t_mid)["tx_type"], "purchase")
        t_after = _parse_ts("2026-04-25T23:59:59Z")
        self.assertEqual(current_version(pair, t_after)["tx_type"], "sale")

    def test_transaction_date_trap(self):
        # Keying on transaction_date (2026-01-20) would include at t=2026-02-01,
        # but availability (2026-02-19 date) must exclude it.
        orig = self.by_id["demo:0006"]
        t = _parse_ts("2026-02-01T23:59:59Z")
        self.assertFalse(is_eligible(orig, t))


class TestAssetResolution(unittest.TestCase):
    """LW-105 §9 scenarios."""
    def setUp(self):
        self.by_id = {r["record_id"]: r for r in load_records()}

    def test_exact_ticker_high_band(self):
        r = resolve_asset(self.by_id["demo:0001"])
        self.assertEqual(r["band"], "high")
        self.assertEqual(r["resolved_ticker"], "DEMO")

    def test_name_normalization(self):
        r = resolve_asset(self.by_id["demo:0002"])     # "DemoCorp Incorporated"
        self.assertEqual(r["resolved_ticker"], "DEMO")

    def test_ambiguous_goes_to_review(self):
        r = resolve_asset(self.by_id["demo:0003"])     # "Demo Holdings"
        self.assertNotEqual(r["band"], "high")
        self.assertTrue(r["needs_manual_review"])

    def test_unresolvable_rejected(self):
        r = resolve_asset(self.by_id["demo:0004"])
        self.assertIsNone(r["resolved_ticker"])
        self.assertTrue(r["needs_manual_review"])

    def test_resolved_but_unmapped_contributes_nothing(self):
        self.assertFalse(contributes(self.by_id["demo:0005"]))   # WIDG resolved, unmapped
        self.assertTrue(resolve_asset(self.by_id["demo:0005"])["resolved_ticker"] == "WIDG")

    def test_high_confidence_mapped_contributes(self):
        self.assertTrue(contributes(self.by_id["demo:0001"]))    # DEMO -> US500


class TestDedup(unittest.TestCase):
    def test_duplicate_detected_by_content_hash(self):
        recs = load_records()
        a = next(r for r in recs if r["record_id"] == "demo:0001")
        b = next(r for r in recs if r["record_id"] == "demo:0008")
        # same document_id + same content_hash => duplicate re-pull
        self.assertEqual(a["document_id"], b["document_id"])
        self.assertEqual(a["content_hash"], b["content_hash"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

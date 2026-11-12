"""Integrity checks for the archived Nov 12 source audit (not accuracy tests)."""
from __future__ import annotations

import csv
import importlib.util
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "research_audit/stage1a_gate_adj_nli_30_2026-11-12/audit_123_segments.csv"
ORIGINAL = ROOT / "data/processed/reviews.jsonl"
SCRIPT = ROOT / "scripts/stage1a_gate_adj_nli_30.py"
spec = importlib.util.spec_from_file_location("stage1a_gate_archive_source", SCRIPT)
model = importlib.util.module_from_spec(spec)
spec.loader.exec_module(model)


def test_canonical_frozen_segments_match_original_run():
    # The raw-file hash from a Windows checkout differs from the checkout on
    # GitHub Actions due to line endings. Verify the ACTUAL parsed experimental
    # units instead; no original segment content may change.
    reviews = model.choose_reviews(model.load_real_reviews(ORIGINAL, 0), 30, 42)
    units = model.make_segments(reviews)
    assert model.sha(units) == (
        "0dfa1e791f9f34e72e500ed79875eaf6bb5a17dc232997cc6d67d87e0966e036"
    )


def test_all_123_audit_rows_align_with_real_source_segments():
    reviews = model.choose_reviews(model.load_real_reviews(ORIGINAL, 0), 30, 42)
    units = model.make_segments(reviews)
    with AUDIT.open(encoding="utf-8-sig", newline="") as f:
        records = list(csv.DictReader(f))
    assert len(units) == len(records) == 123
    assert len({u["review_id"] for u in units}) == 30
    for i, (unit, record) in enumerate(zip(units, records)):
        assert record["index"] == str(i)
        assert record["review_id"] == unit["review_id"]
        assert int(record["segment_id"]) == unit["segment_id"]
        assert record["segment"] == unit["segment"]
        assert record["full_review"] == unit["full_review"]
        assert unit["full_review"][unit["start"]:unit["end"]] == record["segment"]
        assert record["screen_class"] in ("D", "I", "G", "X")
        for category in ("cal", "inv", "safe"):
            assert record[f"reference_{category}"] in ("S", "O", "N", "U")
        for checkpoint in ("bart", "deberta", "modernbert"):
            value = float(record[f"nli_{checkpoint}_mean"])
            assert 0 <= value <= 1


def test_single_reviewer_provisional_labels_preserved_without_accuracy_claims():
    with AUDIT.open(encoding="utf-8-sig", newline="") as f:
        records = list(csv.DictReader(f))
    assert Counter(r["screen_class"] for r in records) == {
        "D": 33, "I": 48, "G": 19, "X": 23,
    }
    assert sum(r[f"reference_{c}"] == "U" for r in records
               for c in ("cal", "inv", "safe")) == 87
    assert sum(r["adjective"].lower() == "true" for r in records) == 91

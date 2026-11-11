"""Offline mechanics checks for the direction-only pilot (no Ollama calls)."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import stage1a_direction_2 as trial
from stage1a_panel_pilot import load_real_reviews, prepare


def _supply_original_annotations(tmp_path):
    """Create only test-side archived annotation rows from actual source text."""
    config = json.loads((ROOT / "configs/stage1a_direction_2_cases.json").read_text())
    corpus = {(r["place_id"], r["review_index"]): prepare([r])[0]
              for r in load_real_reviews(ROOT / "data/processed/reviews.jsonl", 0)}
    spans = {
        (1, "calm"): "makes this place a dirty, chaotic mess",
        (3, "safe"): "the sides extremely slippery",
        (4, "safe"): "slip and hit their head",
        (11, "inviting"): "Maintenance of the park is also quite poor",
        (2, "safe"): "The spongy hardtop material forms a nice hill",
        (0, "safe"): "without worrying for the car drivers and crowd roads",
        (1, "calm"): "quiet times",
        (1, "inviting"): "I loved that place and wish to visit it again",
    }
    values = []
    for case in config["cases"]:
        original = corpus[(case["place_id"], case["review_index"])]
        unit = original["units"][case["unit_id"]]
        span = spans[(case["unit_id"], case["emotion"])]
        assert span in unit["text"], (case, unit["text"])
        values.append({**case, "clause": unit["text"],
                       "source_sha256": original["source_sha256"],
                       "evidence_span": span,
                       "rationale": "Previous extraction output",
                       "relevance": case["expected_prior_label"],
                       "model": case["source_model"]})
    p = tmp_path / "annotations.jsonl"
    p.write_text("".join(json.dumps(r) + "\n" for r in values), encoding="utf-8")
    return p


def test_eight_frozen_cases_original_text_and_existing_spans(tmp_path):
    prior = _supply_original_annotations(tmp_path)
    items = trial.build_items(ROOT / "data/processed/reviews.jsonl",
                              prior, ROOT / "configs/stage1a_direction_2_cases.json")
    assert len(items) == 8
    assert len({x["place_id"] for x in items}) == 2
    assert all(x["review_index"] == 0 and x["evidence_span"] in x["clause"] for x in items)
    assert set(x["emotion"] for x in items) == {"calm", "inviting", "safe"}


def test_prior_provenance_failure_blocks_model_calls(tmp_path):
    prior = _supply_original_annotations(tmp_path)
    rows = [json.loads(x) for x in prior.read_text().splitlines()]
    rows[0]["source_sha256"] = "wrong"
    prior.write_text("".join(json.dumps(r) + "\n" for r in rows))
    with pytest.raises(ValueError, match="does not match"):
        trial.build_items(ROOT / "data/processed/reviews.jsonl",
                          prior, ROOT / "configs/stage1a_direction_2_cases.json")


def test_direction_schema_and_labels():
    assert list(trial.SCHEMA["properties"]) == ["reason", "direction"]
    assert trial.validate_result({"reason": "Hazard raises injury risk", "direction": "opposes"})
    assert trial.validate_result({"reason": "Amenities only", "direction": "neither"})
    with pytest.raises(ValueError):
        trial.validate_result({"reason": "Bad label", "direction": "not_relevant"})

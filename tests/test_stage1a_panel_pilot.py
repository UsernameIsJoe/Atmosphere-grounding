"""Offline checks of the NEW pilot's mechanics, not semantic-label accuracy.

Short strings are test inputs for source-offset/invariant tests, NEVER research reviews.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

MODULE = Path(__file__).resolve().parents[1] / "scripts" / "stage1a_panel_pilot.py"
spec = importlib.util.spec_from_file_location("stage1a_panel_pilot", MODULE)
pilot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pilot)


def annotation(unit_id=0, emotion="calm", relevance="supports", quote="peaceful"):
    return {
        "unit_id": unit_id, "emotion": emotion, "relevance": relevance,
        "strength": "weak" if relevance in ("supports", "opposes", "mixed") else None,
        "type": "explicit" if relevance in ("supports", "opposes", "mixed") else None,
        "condition": "", "evidence_span": quote if relevance in ("supports", "opposes", "mixed") else "",
        "attribution": "first_person", "rationale": "source-grounded",
        "evidence_records": [],
    }


def test_clause_offsets_and_contrast():
    text = "A peaceful park in the morning, but crowded at night. I liked the trees."
    units = pilot.segment_review(text)
    assert len(units) == 3
    assert [x["unit_id"] for x in units] == [0, 1, 2]
    assert all(text[x["start"]:x["end"]] == x["text"] for x in units)
    assert "peaceful" in units[0]["text"]
    assert "crowded" in units[1]["text"]


def test_quote_exactness_and_offset_provenance():
    unit = pilot.segment_review("A peaceful park.")[0]
    result = pilot.validate_label(annotation(), unit)
    assert result["span_offsets"] == [{"start": 2, "end": 10}]
    with pytest.raises(ValueError):
        pilot.validate_label(annotation(quote="Peaceful"), unit)


def test_requires_all_unit_category_votes():
    units = pilot.segment_review("A peaceful park.")
    labels = [annotation(emotion="calm"),
              annotation(emotion="inviting", relevance="not_relevant"),
              annotation(emotion="safe", relevance="not_relevant")]
    assert len(pilot.validate_response({"labels": labels}, units)) == 3
    with pytest.raises(ValueError):
        pilot.validate_response({"labels": labels[:2]}, units)
    with pytest.raises(ValueError):
        pilot.validate_response({"labels": labels + [labels[0]]}, units)


def test_consensus_full_distribution_not_probability_of_truth():
    votes = [
        pilot.validate_label(annotation(), pilot.segment_review("A peaceful park.")[0]),
        pilot.validate_label(annotation(), pilot.segment_review("A peaceful park.")[0]),
        pilot.validate_label(annotation(relevance="not_relevant"), pilot.segment_review("A peaceful park.")[0]),
    ]
    out = pilot.aggregate(votes)
    assert out["label"] == "supports"
    assert out["distribution"]["supports"] == pytest.approx(2 / 3)
    assert out["distribution"]["not_relevant"] == pytest.approx(1 / 3)
    assert sum(out["distribution"].values()) == pytest.approx(1)


def test_three_way_disagreement_is_contested():
    unit = pilot.segment_review("A peaceful park.")[0]
    votes = [
        pilot.validate_label(annotation(), unit),
        pilot.validate_label(annotation(relevance="not_relevant"), unit),
        pilot.validate_label(annotation(relevance="uncertain"), unit),
    ]
    assert pilot.aggregate(votes)["label"] == "contested"


def test_fixture_rejected(tmp_path):
    fixture = tmp_path / "fixtures" / "reviews.jsonl"
    fixture.parent.mkdir()
    fixture.write_text(json.dumps({
        "place_id": "fixture_cambridge_common", "review_index": 0,
        "text": "A peaceful park.", "publish_time": "2026-01-01T00:00:00Z"}) + "\n")
    with pytest.raises(ValueError):
        pilot.load_real_reviews(fixture, 0)


def test_real_corpus_format_and_no_fixture_ids():
    corpus = Path(__file__).resolve().parents[1] / "data" / "processed" / "reviews.jsonl"
    if not corpus.exists():
        pytest.skip("Repository corpus not available in checkout")
    rows = pilot.load_real_reviews(corpus, 0)
    assert len(rows) == 214
    assert len({x["place_id"] for x in rows}) == 43
    assert all(not x["place_id"].startswith("fixture_") for x in rows)


def test_saved_call_validation_and_partial_consensus():
    unit = pilot.segment_review("A peaceful park.")[0]
    review = {"place_id": "ChIJ_testcase", "review_index": 0,
              "text": "A peaceful park.", "source_sha256": pilot.sha256("A peaceful park."),
              "units": [unit]}
    rows = []
    for model in ("qwen3:8b", "gemma3:4b", "llama3.2:3b"):
        for prompt in ("A", "B"):
            if model == "gemma3:4b" and prompt == "A":
                continue
            for emotion in pilot.PILOT:
                verdict = "supports" if emotion == "calm" else "not_relevant"
                item = pilot.validate_label(
                    annotation(emotion=emotion, relevance=verdict), unit)
                rows.append({**item, "place_id": review["place_id"],
                             "review_index": review["review_index"],
                             "source_sha256": review["source_sha256"],
                             "model": model, "prompt": prompt})
    done = pilot.completed_model_calls(rows, [review],
                                       ["qwen3:8b", "gemma3:4b", "llama3.2:3b"])
    assert len(done) == 5
    assert ("ChIJ_testcase", 0, "gemma3:4b", "A") not in done
    report = pilot.summarize(rows, allow_incomplete=True)
    assert report["n_items"] == 0
    assert report["n_incomplete_units"] == 3
    with pytest.raises(ValueError):
        pilot.summarize(rows)
    # Single bad saved original-text provenance must block unsafe reuse.
    rows[0]["source_sha256"] = "tampered"
    with pytest.raises(ValueError):
        pilot.completed_model_calls(rows, [review],
                                    ["qwen3:8b", "gemma3:4b", "llama3.2:3b"])


def test_partial_consensus_excludes_only_incomplete_key():
    unit = pilot.segment_review("A peaceful park.")[0]
    rows = []
    for emotion in pilot.PILOT:
        for model in ("qwen", "gemma", "llama"):
            if emotion == "safe" and model == "gemma":
                continue
            item = pilot.validate_label(annotation(
                emotion=emotion, relevance="supports" if emotion == "calm" else "not_relevant"), unit)
            rows.append({**item, "place_id": "ChIJ_testcase", "review_index": 0,
                         "model": model, "prompt": "A"})
    report = pilot.summarize(rows, allow_incomplete=True)
    assert report["n_items"] == 2
    assert report["n_incomplete_units"] == 1


def test_resume_accepts_saved_nested_offsets_and_rejects_tampering():
    """Stored outputs include enriched offsets absent from the model's JSON schema."""
    unit = pilot.segment_review("A peaceful park.")[0]
    review = {"place_id": "ChIJ_testcase", "review_index": 0,
              "text": "A peaceful park.", "source_sha256": pilot.sha256("A peaceful park."),
              "units": [unit]}
    rows = []
    for model in ("qwen3:8b", "gemma3:4b", "llama3.2:3b"):
        for prompt in ("A", "B"):
            for emotion in pilot.PILOT:
                base = annotation(emotion=emotion, relevance="supports")
                base["evidence_records"] = [{
                    "relevance": "supports", "evidence_span": "peaceful",
                    "strength": "weak", "type": "explicit", "condition": ""
                }]
                saved = pilot.validate_label(base, unit)
                rows.append({**saved, "place_id": review["place_id"],
                             "review_index": review["review_index"],
                             "source_sha256": review["source_sha256"],
                             "model": model, "prompt": prompt})
    completed = pilot.completed_model_calls(rows, [review],
                                           ["qwen3:8b", "gemma3:4b", "llama3.2:3b"])
    assert len(completed) == 6
    rows[0]["evidence_records"][0]["span_offsets"] = [{"start": 0, "end": 8}]
    with pytest.raises(ValueError, match="sub-evidence offsets mismatch"):
        pilot.completed_model_calls(rows, [review],
                                    ["qwen3:8b", "gemma3:4b", "llama3.2:3b"])


def test_prompt_c_is_distinct_and_summary_selectable():
    assert "C" in pilot.PROMPTS
    assert pilot.PROMPTS["C"] != pilot.PROMPTS["A"]
    assert "DIRECT INDICATOR" in pilot.PROMPTS["C"]
    unit = pilot.segment_review("A peaceful park.")[0]
    rows = []
    for model in ("qwen3:8b", "gemma3:4b", "llama3.2:3b"):
        for emotion in pilot.PILOT:
            item = pilot.validate_label(annotation(
                emotion=emotion, relevance="not_relevant"), unit)
            rows.append({**item, "place_id": "ChIJ_trial", "review_index": 0,
                         "model": model, "prompt": "C"})
    report = pilot.summarize(rows, allow_incomplete=True, prompt_id="C")
    assert report["n_items"] == 3
    assert report["n_incomplete_units"] == 0


def test_selected_places_use_first_review_not_last():
    """Regression: original A/B diverse mode used the first row per place."""
    rows = [
        {"place_id": "ChIJ_one", "review_index": 0, "text": "Original"},
        {"place_id": "ChIJ_two", "review_index": 0, "text": "Original two"},
        {"place_id": "ChIJ_one", "review_index": 4, "text": "Other review"},
        {"place_id": "ChIJ_two", "review_index": 4, "text": "Other review two"},
    ]
    chosen = pilot.select_first_reviews_for_places(rows, ["ChIJ_two", "ChIJ_one"])
    assert [(r["place_id"], r["review_index"], r["text"]) for r in chosen] == [
        ("ChIJ_two", 0, "Original two"),
        ("ChIJ_one", 0, "Original")]
    with pytest.raises(ValueError, match="missing"):
        pilot.select_first_reviews_for_places(rows, ["ChIJ_absent"])

"""Offline tests for targeted segment-only recovery. No generated texts used as evaluation data."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/stage1a_gate_rescue_segment_only.py"
spec = importlib.util.spec_from_file_location("stage1a_gate_rescue_segment_only", SCRIPT)
rescue = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rescue)

from stage1a_gate_adj_nli_30 import (
    load_real_reviews, choose_reviews, make_segments, append_jsonl, key, read_jsonl,
)

CORPUS = ROOT / "data/processed/reviews.jsonl"


def sample(tmp_path, count=3):
    reviews = choose_reviews(load_real_reviews(CORPUS, 0), count, 42)
    units = [make_segments([r])[0] for r in reviews]
    assert len(units) == count
    assert len({u["place_id"] for u in units}) == count
    root = tmp_path / "experiment"
    for unit in units:
        append_jsonl(root / "input/segments.jsonl", unit)
    return root, units


def model_row(u):
    return {"key": key(u), "ratings": [
        {"category": c, "verdict": "none", "quote": "",
         "attribution": "place", "reason": "no category information"}
        for c in rescue.CATEGORIES
    ]}


def valid_response():
    return json.dumps({"ratings": [
        {"category": c, "verdict": "none", "attribution": "place",
         "reason": "segment does not establish this category"}
        for c in rescue.CATEGORIES
    ]})


def config(root, *, limit=0, retry=False):
    return SimpleNamespace(root=root, output=None, base="http://127.0.0.1:11434",
                           timeout=10, limit=limit, retry_errors=retry)


def test_prompt_contains_only_target_not_full_review():
    segment = {"segment": "A little park."}
    req = rescue.payload(segment)
    assert req["model"] == "gemma3:4b"
    assert len(req["messages"]) == 2
    assert json.loads(req["messages"][1]["content"]) == {"target_segment": "A little park."}
    assert "full_review" not in json.dumps(req)
    assert "quote" not in req["format"]["properties"]["ratings"]["items"]["properties"]
    assert req["options"]["temperature"] == 0


def test_classifier_requires_exactly_three_rows_and_valid_verdicts():
    accepted = rescue.validate(json.loads(valid_response()))
    assert [x["category"] for x in accepted] == list(rescue.CATEGORIES)
    invalid = json.loads(valid_response())
    invalid["ratings"][1]["category"] = "calm"
    with pytest.raises(ValueError, match="Missing/duplicate"):
        rescue.validate(invalid)
    invalid = json.loads(valid_response())
    invalid["ratings"][0]["verdict"] = "certain"
    with pytest.raises(ValueError, match="Invalid verdict"):
        rescue.validate(invalid)


def test_rescue_only_missing_segments_preserves_previous_model_results(tmp_path, monkeypatch):
    root, units = sample(tmp_path, 3)
    qwen = root / "llm_v2/qwen3_8b/ratings.jsonl"
    gemma = root / "llm_v2/gemma3_4b/ratings.jsonl"
    for u in units:
        append_jsonl(qwen, model_row(u))
    append_jsonl(gemma, model_row(units[0]))
    before = (qwen.read_bytes(), gemma.read_bytes())
    monkeypatch.setattr(rescue, "check_gemma", lambda *args: "digest")
    requests = []

    def fake_call(base, data, timeout):
        requests.append(data)
        assert data["messages"][1]["content"].count("target_segment") == 1
        assert "full_original_review" not in json.dumps(data)
        return valid_response(), {"done_reason": "stop"}

    monkeypatch.setattr(rescue, "ollama_call", fake_call)
    summary = rescue.run(config(root))
    assert len(requests) == 2
    assert (qwen.read_bytes(), gemma.read_bytes()) == before
    assert summary["qwen_v2_valid"] == 3
    assert summary["gemma_v2_valid"] == 1
    assert summary["gemma_segment_only_recovered"] == 2
    assert summary["gemma_still_unresolved"] == 0
    assert summary["same_protocol_Qwen_Gemma_comparisons"] == 1
    saved = read_jsonl(root / "llm_segment_only_rescue_gemma_v1/ratings.jsonl")
    assert len(saved) == 2
    assert all(s["extracted_phrases"] == "not_requested" for s in saved)
    assert all(s["source_offsets"] == {"start": u["start"], "end": u["end"]}
               for s, u in zip(saved, units[1:]))
    csv_data = (root / "llm_segment_only_rescue_gemma_v1/comparison_with_recovery.csv").read_text(encoding="utf-8-sig")
    assert "segment_only_rescue" in csv_data
    assert "v2_full_review" in csv_data

    # Resume without re-inference, even though original V2 gaps remain.
    def should_not_call(*args):
        raise AssertionError("Model should not be called for completed rescue records")
    monkeypatch.setattr(rescue, "ollama_call", should_not_call)
    repeated = rescue.run(config(root))
    assert repeated["gemma_total_available_mixed_protocol"] == 3


def test_invalid_generation_logged_without_unbounded_retries(tmp_path, monkeypatch):
    root, units = sample(tmp_path, 1)
    monkeypatch.setattr(rescue, "check_gemma", lambda *args: "digest")
    calls = []

    def bad_call(*args):
        calls.append(1)
        return "not JSON", {"done_reason": "stop"}
    monkeypatch.setattr(rescue, "ollama_call", bad_call)
    first = rescue.run(config(root))
    assert first["gemma_still_unresolved"] == 1
    assert len(calls) == 2
    output = root / "llm_segment_only_rescue_gemma_v1"
    assert len(read_jsonl(output / "errors.jsonl")) == 1
    assert len(read_jsonl(output / "raw_responses.jsonl")) == 2

    # Don't repeat the same failure on every rerun unless explicitly requested.
    second = rescue.run(config(root))
    assert second["gemma_still_unresolved"] == 1
    assert len(calls) == 2
    rescue.run(config(root, retry=True))
    assert len(calls) == 4


def test_read_only_report_requires_no_ollama_or_input_rewrite(tmp_path, monkeypatch):
    root, units = sample(tmp_path, 2)
    rescue.output_status(root, root / "llm_segment_only_rescue_gemma_v1")
    assert (root / "llm_segment_only_rescue_gemma_v1/summary.json").exists()
    assert len(read_jsonl(root / "input/segments.jsonl")) == 2

"""Offline mechanics only. Real stored reviews; no synthetic research/accuracy results."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/stage1a_dual_channel_50.py"
SPEC = importlib.util.spec_from_file_location("stage1a_dual_channel_50", SCRIPT)
dual = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(dual)
CORPUS = ROOT / "data/processed/reviews.jsonl"


def real_rows():
    return dual.load_real_reviews(CORPUS, 0)


def test_fifty_real_reviews_and_offsets():
    rows = real_rows()
    selected = dual.select_reviews(rows, 50, seed=42)
    again = dual.select_reviews(rows, 50, seed=42)
    assert [(x["place_id"], x["review_index"]) for x in selected] == [
        (x["place_id"], x["review_index"]) for x in again]
    assert len(selected) == 50
    assert len({x["place_id"] for x in selected}) == min(50, len({x["place_id"] for x in rows}))
    original = {(r["place_id"], r["review_index"]): r for r in rows}
    segments = dual.prepare_segments(selected)
    assert len(segments) >= 50
    for s in segments:
        r = original[(s["place_id"], s["review_index"])]
        assert r["text"][s["start"]:s["end"]] == s["text"]
        assert s["source_sha256"] == dual.digest(r["text"])


def test_independent_prompts_and_schemas():
    seg = dual.prepare_segments(real_rows()[:1])[0]
    e = dual.payload_for("evidence", "qwen3:8b", seg)
    t = dual.payload_for("inference", "qwen3:8b", seg)
    assert e["format"] != t["format"]
    assert e["messages"][0]["content"] != t["messages"][0]["content"]
    assert set(json.loads(e["messages"][1]["content"])) == {
        "target_segment", "previous_segment_for_context_only", "next_segment_for_context_only"}
    assert "evidence_label" not in t["messages"][1]["content"]
    assert e["think"] is False
    assert "think" not in dual.payload_for("evidence", "gemma3:4b", seg)


def test_exact_quote_and_task_specific_contracts():
    seg = dual.prepare_segments(real_rows()[:1])[0]
    quote = seg["text"][:min(12, len(seg["text"]))]
    e = {"records": [{"category": "calm", "direction": "supports",
                      "quote": quote, "attribution": "general_report"}]}
    t = {"observations": [{"quote": quote, "kind": "physical", "visible_in_photo": "uncertain",
                            "category": "none", "direction": "none", "reason": ""}]}
    assert dual.validate("evidence", e, seg)[0]["quote_offsets"]
    assert dual.validate("inference", t, seg)[0]["quote_offsets"]
    e["records"][0]["quote"] = "fabricated source quote that is absent"
    with pytest.raises(ValueError, match="exact substring"):
        dual.validate("evidence", e, seg)
    t["observations"][0]["direction"] = "supports"
    with pytest.raises(ValueError, match="none"):
        dual.validate("inference", t, seg)


def test_prepare_only_and_isolated_model_outputs(tmp_path, monkeypatch):
    # Uses real review inputs. Mock model outputs verify transport/output mechanics only.
    out = tmp_path / "pilot"
    argv = [str(SCRIPT), "--output", str(out), "--max-reviews", "2",
            "--seed", "42", "--limit-segments", "2"]
    monkeypatch.setattr(sys, "argv", argv + ["--prepare-only"])
    assert dual.run() == 0
    assert (out / "input/manifest.json").exists()
    assert not (out / "evidence").exists()
    counts = {"evidence": 0, "inference": 0}

    def mock_call(base, payload, timeout):
        task = "evidence" if "records" in payload["format"]["properties"] else "inference"
        counts[task] += 1
        if task == "evidence":
            return json.dumps({"records": []}), {"model": payload["model"]}
        segment = json.loads(payload["messages"][1]["content"])["target_segment"]
        return json.dumps({"observations": [{"quote": segment[:10], "kind": "other",
            "visible_in_photo": "uncertain", "category": "none", "direction": "none", "reason": ""}]}), {"model": payload["model"]}

    monkeypatch.setattr(dual, "check_models", lambda base, models, timeout: {m: m + "_digest" for m in models})
    monkeypatch.setattr(dual, "call", mock_call)
    monkeypatch.setattr(sys, "argv", argv)
    assert dual.run() == 0
    assert counts == {"evidence": 4, "inference": 4}
    for task in dual.TASKS:
        for model in dual.MODELS:
            p = out / task / dual.model_slug(model) / "annotations.jsonl"
            data = dual.read_jsonl(p)
            assert len(data) == 2
            if task == "evidence":
                assert all(row["records"] == [] for row in data)
            else:
                assert all(row["records"] for row in data)
    monkeypatch.setattr(sys, "argv", argv + ["--resume"])
    assert dual.run() == 0
    assert counts == {"evidence": 4, "inference": 4}

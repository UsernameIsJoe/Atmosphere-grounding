"""Offline verification of controlled gate experiment mechanics (no claim of accuracy)."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/stage1a_gate_adj_nli_30.py"
spec = importlib.util.spec_from_file_location("stage1a_gate_adj_nli_30", SCRIPT)
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)
CORPUS = ROOT / "data/processed/reviews.jsonl"


def test_real_30_reviews_broad_place_coverage_and_offsets():
    rows = gate.load_real_reviews(CORPUS, 0)
    chosen = gate.choose_reviews(rows, 30, 42)
    assert len(chosen) == len({r["place_id"] for r in chosen}) == 30
    assert [(r["place_id"], r["review_index"]) for r in chosen] == [
        (r["place_id"], r["review_index"]) for r in gate.choose_reviews(rows, 30, 42)]
    units = gate.make_segments(chosen)
    assert len(units) >= 30
    assert len({gate.key(x) for x in units}) == len(units)
    for s in units:
        assert s["full_review"][s["start"]:s["end"]] == s["segment"]
        assert s["source_sha256"] == gate.sha(s["full_review"])


def test_three_distinct_nli_hypotheses_and_models():
    assert len(gate.HYPOTHESES) == 3
    assert len(set(gate.HYPOTHESES)) == 3
    assert len(gate.NLI_MODELS) == 3
    assert len(set(gate.NLI_MODELS.values())) == 3
    assert all("place" in h or "location" in h for h in gate.HYPOTHESES)


def test_no_gate_leakage_into_llm_prompt_and_identical_model_prompts():
    s = gate.make_segments(gate.choose_reviews(gate.load_real_reviews(CORPUS, 0), 1, 42))[0]
    q = gate.llm_payload("qwen3:8b", s)
    g = gate.llm_payload("gemma3:4b", s)
    assert q["messages"] == g["messages"]
    assert q["format"] == g["format"]
    assert "adjective" not in q["messages"][0]["content"].lower()
    assert "entailment" not in q["messages"][0]["content"].lower()
    assert "evidence channel" not in q["messages"][0]["content"].lower()
    assert "full_original_review_for_context" in q["messages"][1]["content"]
    assert q["think"] is False and "think" not in g


def test_source_quote_and_category_integrity():
    s = gate.make_segments(gate.choose_reviews(gate.load_real_reviews(CORPUS, 0), 1, 42))[0]
    obj = {"ratings": [
        {"category": c, "verdict": "supports" if c == "calm" else "none",
         "quote": s["segment"][:12] if c == "calm" else "",
         "attribution": "place", "reason": "testing"} for c in gate.CATEGORIES
    ]}
    out = gate.validate_llm(obj, s)
    assert len(out) == 3
    assert out[0]["quote_offsets"][0]["start"] == s["start"]
    assert out[0]["quote_status"] == "verified"
    assert out[1]["quote_status"] == "not_required"
    obj["ratings"][0]["quote"] = "invented source quote absent from text"
    unverified = gate.validate_llm(obj, s)
    assert unverified[0]["quote_status"] == "unverified"
    assert unverified[0]["quote_offsets"] == []
    assert unverified[0]["verdict"] == "supports"  # Keep verdict; don't claim source grounding.
    obj["ratings"][0]["quote"] = ""
    missing = gate.validate_llm(obj, s)
    assert missing[0]["quote_status"] == "not_provided"
    obj["ratings"][0]["quote"] = s["segment"][:12]
    obj["ratings"][1]["category"] = "calm"
    with pytest.raises(ValueError, match="Missing/duplicate category"):
        gate.validate_llm(obj, s)


def test_native_nli_binary_not_mislabeled_contradiction():
    model = SimpleNamespace(config=SimpleNamespace(id2label={0: "not_entailment", 1: "entailment"}))
    labels, space = gate.native_labels(model)
    assert space == "binary"
    assert labels[0] == "not_entailment"
    model.config.id2label = {0: "contradiction", 1: "neutral", 2: "entailment"}
    labels, space = gate.native_labels(model)
    assert space == "three_way"
    assert labels[2] == "entailment"


def test_prepare_only_and_frozen_manifest(tmp_path, monkeypatch):
    out = tmp_path / "diagnostic"
    argv = [str(SCRIPT), "--stage", "prepare", "--output", str(out)]
    monkeypatch.setattr(sys, "argv", argv)
    assert gate.main() == 0
    segments = gate.read_jsonl(out / "input/segments.jsonl")
    assert len(segments) >= 30
    assert len({s["review_id"] for s in segments}) == 30
    assert gate.main() == 0  # resume from same source + prompts
    monkeypatch.setattr(sys, "argv", argv + ["--seed", "99"])
    with pytest.raises(ValueError, match="manifest changed"):
        gate.main()


def test_report_keeps_candidate_gates_separate_from_accuracy(tmp_path):
    out = tmp_path / "report"
    units = gate.make_segments(gate.choose_reviews(gate.load_real_reviews(CORPUS, 0), 1, 42))[:2]
    assert len(units) == 2
    for i, s in enumerate(units):
        k = gate.key(s)
        gate.append_jsonl(out / "gates/pos.jsonl", {
            "key": k, "adjective_present": i == 0, "adjectives": []})
        for alias in gate.NLI_MODELS:
            score = .85 if i == 0 else .15
            gate.append_jsonl(out / f"gates/nli_{alias}.jsonl", {
                "key": k, "mean_entailment": score, "entailment_range": 0.0,
                "hypotheses": [{"id": j + 1, "probabilities": {"entailment": score}}
                               for j in range(3)]})
        for model in gate.LLMS:
            verdict = "supports" if i == 0 else "none"
            items = [{"category": c, "verdict": verdict if c == "calm" else "none",
                      "quote": "", "attribution": "place", "reason": "test",
                      "quote_offsets": []} for c in gate.CATEGORIES]
            gate.append_jsonl(out / "llm" / model.replace(":", "_") / "ratings.jsonl",
                              {"key": k, "ratings": items})
    summary = gate.summarize(SimpleNamespace(output=out, seed=42), units)
    assert summary["gate_complete_segments"] == 2
    assert summary["llm_double_rated_segments"] == 2
    assert summary["routing_simulations_NOT_accuracy"]["adjective"]["estimated_two_model_calls"] == 3
    assert summary["routing_simulations_NOT_accuracy"]["nli_median_0.6"]["easy_segments"] == 1
    assert (out / "comparison/human_audit_blind.csv").exists()


def test_progress_bar_reports_percentages_and_resumed_counts(capsys):
    bar = gate.ProgressBar("POS adjectives", 4, completed=2)
    bar.update(3)
    bar.update(4)
    output = capsys.readouterr().out
    assert "[###########-----------] 2/4 (50%)" in output
    assert "4/4 (100%)" in output


def test_progress_bar_reports_failures_without_stopping(capsys):
    bar = gate.ProgressBar("LLM qwen3:8b", 3)
    bar.update(1)
    bar.update(2, failures=1)
    bar.update(3, failures=1)
    output = capsys.readouterr().out
    assert "3/3 (100%) | failed: 1" in output

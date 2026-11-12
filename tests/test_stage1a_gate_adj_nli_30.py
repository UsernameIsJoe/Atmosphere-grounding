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


def test_none_verdict_with_bad_quote_is_not_failed_evidence():
    """The historical bug: even an irrelevant 'none' quote triggered warnings."""
    s = gate.make_segments(gate.choose_reviews(gate.load_real_reviews(CORPUS, 0), 1, 42))[0]
    ratings = [
        {"category": category, "verdict": "none", "quote": "no textual evidence",
         "attribution": "place", "reason": "not present"}
        for category in gate.CATEGORIES
    ]
    output = gate.validate_llm({"ratings": ratings}, s)
    assert all(x["quote_status"] == "not_required" for x in output)
    assert all(x["extraneous_quote_for_none"] for x in output)
    assert all(x["quote_offsets"] == [] for x in output)


def test_unverified_source_still_flagged_for_nonempty_verdict():
    s = gate.make_segments(gate.choose_reviews(gate.load_real_reviews(CORPUS, 0), 1, 42))[0]
    ratings = [
        {"category": category, "verdict": "supports", "quote": "not from this segment",
         "attribution": "place", "reason": "model claimed support"}
        for category in gate.CATEGORIES
    ]
    output = gate.validate_llm({"ratings": ratings}, s)
    assert all(x["quote_status"] == "unverified" for x in output)
    assert not any(x["extraneous_quote_for_none"] for x in output)


def test_diagnose_recomputes_legacy_status_without_editing_saved_rows(tmp_path, capsys):
    s = gate.make_segments(gate.choose_reviews(gate.load_real_reviews(CORPUS, 0), 1, 42))[0]
    rows = [
        {"category": category, "verdict": "none", "quote": "an invented quote",
         "attribution": "place", "reason": "none", "quote_status": "unverified"}
        for category in gate.CATEGORIES
    ]
    path = tmp_path / "qwen3_8b/ratings.jsonl"
    gate.append_jsonl(path, {"key": gate.key(s), "ratings": rows, "model": "qwen3:8b"})
    raw_before = path.read_bytes()
    result = gate.diagnose_saved([s], tmp_path, "qwen3:8b", max_examples=1)
    assert result["saved_segments"] == 1
    assert result["quote_status_recomputed"] == {"not_required": 3}
    assert result["extraneous_quotes_for_none"] == 3
    assert path.read_bytes() == raw_before
    out = capsys.readouterr().out
    assert "UNNECESSARY_NONE_QUOTE" in out


def test_report_recomputes_old_quote_annotations(tmp_path):
    out = tmp_path / "diagnostic"
    u = gate.make_segments(gate.choose_reviews(gate.load_real_reviews(CORPUS, 0), 1, 42))[0]
    k = gate.key(u)
    gate.append_jsonl(out / "gates/pos.jsonl", {
        "key": k, "adjective_present": True, "adjectives": []})
    for alias in gate.NLI_MODELS:
        gate.append_jsonl(out / f"gates/nli_{alias}.jsonl", {
            "key": k, "mean_entailment": .5, "entailment_range": 0,
            "hypotheses": [{"id": j + 1, "probabilities": {"entailment": .5}}
                           for j in range(3)]})
    for model in gate.LLMS:
        ratings = [
            {"category": category, "verdict": "none", "quote": "not in source",
             "attribution": "place", "reason": "none",
             "quote_offsets": [], "quote_status": "unverified"}
            for category in gate.CATEGORIES
        ]
        gate.append_jsonl(out / "llm" / model.replace(":", "_") / "ratings.jsonl",
                          {"key": k, "ratings": ratings})
    summary = gate.summarize(SimpleNamespace(output=out, seed=42), [u])
    assert summary["unverified_quote_counts_by_model"] == {model: 0 for model in gate.LLMS}
    assert summary["extraneous_none_quote_counts_by_model"] == {model: 3 for model in gate.LLMS}



def test_v2_repairs_only_literal_outer_quote_marks():
    source = "This is the place to come for making your day the best one."
    sample = {"segment": source, "full_review": source, "start": 9}
    ratings = [
        {"category": "calm", "verdict": "none", "quote": "",
         "attribution": "place", "reason": "nothing"},
        {"category": "inviting", "verdict": "supports",
         "quote": f'"{source}"', "attribution": "place", "reason": "positive place description"},
        {"category": "safe", "verdict": "none", "quote": "",
         "attribution": "place", "reason": "nothing"},
    ]
    out = gate.validate_llm({"ratings": ratings}, sample, strict_quotes=True)
    inviting = out[1]
    assert inviting["quote"] == source
    assert inviting["quote_raw"] == f'"{source}"'
    assert inviting["quote_normalization"] == "removed_outer_quote_marks"
    assert inviting["quote_offsets"] == [{"start": 9, "end": 9 + len(source)}]
    assert inviting["quote_status"] == "verified"


def test_v2_rejects_emotional_evidence_leaking_from_full_review():
    segment = "My husband and I got eloped here."
    full = segment + " It was so stressful. Everyone was so nice and friendly."
    sample = {"segment": segment, "full_review": full, "start": 0}
    ratings = [
        {"category": "calm", "verdict": "opposes", "quote": "It was so stressful",
         "attribution": "place", "reason": "stressful"},
        {"category": "inviting", "verdict": "none", "quote": "",
         "attribution": "place", "reason": "not stated"},
        {"category": "safe", "verdict": "none", "quote": "",
         "attribution": "place", "reason": "not stated"},
    ]
    with pytest.raises(ValueError, match="context leakage"):
        gate.validate_llm({"ratings": ratings}, sample, strict_quotes=True)


def test_v2_rejects_non_source_paraphrase_and_missing_support_quote():
    segment = "A peaceful place."
    sample = {"segment": segment, "full_review": segment, "start": 0}
    ratings = [
        {"category": "calm", "verdict": "supports", "quote": "It feels very calm.",
         "attribution": "place", "reason": "positive"},
        {"category": "inviting", "verdict": "none", "quote": "",
         "attribution": "place", "reason": "not stated"},
        {"category": "safe", "verdict": "none", "quote": "",
         "attribution": "place", "reason": "not stated"},
    ]
    with pytest.raises(ValueError, match="not source-exact"):
        gate.validate_llm({"ratings": ratings}, sample, strict_quotes=True)
    ratings[0]["quote"] = ""
    with pytest.raises(ValueError, match="source quote absent from target"):
        gate.validate_llm({"ratings": ratings}, sample, strict_quotes=True)


def test_v2_prompt_prevents_context_becoming_target_evidence():
    s = gate.make_segments(gate.choose_reviews(gate.load_real_reviews(CORPUS, 0), 1, 42))[0]
    v1 = gate.llm_payload("qwen3:8b", s, version="v1")
    v2 = gate.llm_payload("qwen3:8b", s, version="v2")
    assert v1["messages"][0]["content"] == gate.LLM_SYSTEM
    assert v2["messages"][0]["content"] == gate.LLM_SYSTEM_V2
    assert v1["messages"][1]["content"] != v2["messages"][1]["content"]
    assert "My husband and I got eloped here." in gate.LLM_SYSTEM_V2
    assert "ONLY the target_segment" in v2["messages"][1]["content"]
    assert v1["format"] == v2["format"]
    assert "adjective" not in v2["messages"][0]["content"].lower()
    assert "entailment" not in v2["messages"][0]["content"].lower()


def test_v2_protocol_never_overwrites_v1_saved_model_outputs(tmp_path, monkeypatch):
    out = tmp_path / "preserved"
    v1 = out / "llm" / "qwen3_8b" / "ratings.jsonl"
    gate.append_jsonl(v1, {"key": "prior-v1", "ratings": []})
    old = v1.read_bytes()
    assert gate.LLM_SYSTEM_V2 != gate.LLM_SYSTEM
    # V2 output directory is necessarily distinct from V1.
    v2 = out / "llm_v2" / "qwen3_8b" / "ratings.jsonl"
    assert v1 != v2
    assert v1.read_bytes() == old



def test_quote_case_only_matches_target_but_not_full_review():
    segment = "Lights in the small box were years away- it was completely dark."
    sample = {"segment": segment, "full_review": segment,
              "start": 12}
    ratings = [
        {"category": "calm", "verdict": "opposes",
         "quote": "It was completely dark.", "attribution": "place", "reason": "darkness"},
        {"category": "inviting", "verdict": "none",
         "quote": "", "attribution": "place", "reason": ""},
        {"category": "safe", "verdict": "none",
         "quote": "", "attribution": "place", "reason": ""},
    ]
    result = gate.validate_llm({"ratings": ratings}, sample, strict_quotes=True)
    assert result[0]["quote_raw"] == "It was completely dark."
    assert result[0]["quote"] == "it was completely dark."
    assert result[0]["quote_normalization"] == "case_only"
    assert result[0]["quote_status"] == "verified"
    assert result[0]["quote_offsets"][0]["start"] == 12 + segment.index("it was completely dark.")


def test_case_only_recovery_never_accepts_context_leakage():
    segment = "Although the flush was operative, the hand washing station was not."
    full = segment + " The bathroom was completely unclean, with tissues all over the place."
    sample = {"segment": segment, "full_review": full, "start": 0}
    ratings = [
        {"category": "calm", "verdict": "opposes",
         "quote": "completely unclean, with tissues all over the place",
         "attribution": "place", "reason": "unclean"},
        {"category": "inviting", "verdict": "none",
         "quote": "", "attribution": "place", "reason": ""},
        {"category": "safe", "verdict": "none",
         "quote": "", "attribution": "place", "reason": ""},
    ]
    with pytest.raises(ValueError, match="context leakage"):
        gate.validate_llm({"ratings": ratings}, sample, strict_quotes=True)

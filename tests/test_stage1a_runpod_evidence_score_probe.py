"""Unit tests for the two-task advanced model capacity probe (real source rows)."""
from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("stage1a_runpod_evidence_score_probe",
    ROOT / "scripts/stage1a_runpod_evidence_score_probe.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def arguments(tmp_path, model=None, task="evidence", mode="segment", limit=2):
    return SimpleNamespace(
        source=mod.SOURCE, output=tmp_path, base="http://127.0.0.1:11434",
        model=model or mod.MODELS[0], task=task, mode=mode,
        timeout=15, limit=limit, retry_errors=False,
    )


def evidence_json(row):
    return {"claims": [
        {"source_quote": row["segment"], "evidence_type": "both",
         "referent": "surroundings", "reason": "complete original claim"}
    ]}


def score_json():
    return {"ratings": [
        {"category": c,
         "direct": {"verdict": "none", "signed_score": 0, "reason": "absent"},
         "inference": {"verdict": "uncertain", "signed_score": 0,
                       "reason": "not enough information"}}
        for c in mod.CATEGORIES
    ]}


def test_real_case_cohort_and_reference_labels_not_visible():
    rows = mod.corpus()
    assert len(rows) == 123
    assert len(mod.selected(rows, "segment")) == 30
    assert len(mod.selected(rows, "context")) == 10
    for row in mod.selected(rows, "segment"):
        for task in mod.TASKS:
            req = mod.request_payload(row, mod.MODELS[0], "segment", task)
            assert json.loads(req["messages"][1]["content"]) == {
                "target_segment": row["segment"]}
            assert "reference_cal" not in json.dumps(req)
            assert "screen_class" not in json.dumps(req)
            assert "qwen_v2" not in json.dumps(req)
            assert "nli" not in json.dumps(req).lower()
            assert req["options"]["temperature"] == 0
            assert req["think"] is False
    for row in mod.selected(rows, "context"):
        req = mod.request_payload(row, mod.MODELS[1], "context", "score")
        assert json.loads(req["messages"][1]["content"]) == {
            "target_segment": row["segment"],
            "full_review_for_reference_only": row["full_review"]}


def test_direct_and_inference_both_preserved_quote_mismatches_flagged():
    example = "The surroundings were very quiet."
    direct = {"source_quote": "very quiet", "evidence_type": "direct",
              "referent": "surroundings", "reason": "asserts quiet"}
    indirect = {"source_quote": example, "evidence_type": "both",
                "referent": "surroundings", "reason": "describes conditions"}
    mismatch = {"source_quote": "Quiet as a whisper", "evidence_type": "inference",
                "referent": "place", "reason": "paraphrase not source"}
    pred = mod.validate_evidence({"claims": [direct, indirect, mismatch]}, example)
    assert [x["source_exact"] for x in pred["claims"]] == [True, True, False]
    assert [x["evidence_type"] for x in pred["claims"]] == ["direct", "both", "inference"]
    assert pred["claims"][2]["source_quote"] == "Quiet as a whisper"
    assert mod.validate_evidence({"claims": []}, example) == {"claims": []}
    with pytest.raises(ValueError, match="empty"):
        mod.validate_evidence({"claims": [{**direct, "source_quote": ""}]}, example)


def test_signed_ordinal_scores_are_consistent_with_verdict_and_channel():
    x = score_json()
    assert mod.validate_score(x)["ratings"][0]["direct"]["signed_score"] == 0
    x["ratings"][1]["direct"] = {
        "verdict": "supports", "signed_score": 2, "reason": "direct claim"}
    x["ratings"][1]["inference"] = {
        "verdict": "opposes", "signed_score": -1, "reason": "inference"}
    assert mod.validate_score(x)["ratings"][1]["direct"]["verdict"] == "supports"
    x["ratings"][1]["direct"]["signed_score"] = -1
    with pytest.raises(ValueError, match="Inconsistent"):
        mod.validate_score(x)
    x["ratings"][1]["direct"]["signed_score"] = 1
    x["ratings"][1]["direct"]["verdict"] = "none"
    with pytest.raises(ValueError, match="Inconsistent"):
        mod.validate_score(x)


def test_separate_tasks_have_separate_logs_and_no_cross_task_leakage(tmp_path, monkeypatch):
    monkeypatch.setattr(mod, "installed_model", lambda *args: "same-fixed-digest")
    models = []
    def stub(base, endpoint, data=None, timeout=400):
        assert endpoint == "/api/chat"
        models.append(data)
        segment = json.loads(data["messages"][1]["content"])["target_segment"]
        which = "evidence" if "TASK A" in data["messages"][0]["content"] else "score"
        raw = evidence_json({"segment": segment}) if which == "evidence" else score_json()
        return {"message": {"content": json.dumps(raw)},
                "done_reason": "stop", "prompt_eval_count": 200,
                "eval_count": 40}
    monkeypatch.setattr(mod, "urlopen_json", stub)
    a = arguments(tmp_path, task="evidence", limit=2)
    mod.run(a)
    assert len(models) == 2
    mod.run(a)
    assert len(models) == 2  # resume
    b = arguments(tmp_path, task="score", limit=2)
    mod.run(b)
    assert len(models) == 4
    assert "TASK B" in models[2]["messages"][0]["content"]
    assert "TASK A" not in models[2]["messages"][0]["content"]
    assert "claims" not in models[2]["messages"][1]["content"]
    x = mod.read_lines(mod.folder_for(tmp_path, mod.MODELS[0], "segment", "evidence")
                       / "results.jsonl")
    y = mod.read_lines(mod.folder_for(tmp_path, mod.MODELS[0], "segment", "score")
                       / "results.jsonl")
    assert len(x) == len(y) == 2
    assert x[0]["prediction"]["claims"][0]["source_exact"]
    assert y[0]["prediction"]["ratings"][0]["direct"]["verdict"] == "none"


def test_blind_and_independent_gold_first_exports(tmp_path):
    result = mod.report(SimpleNamespace(source=mod.SOURCE, output=tmp_path))
    assert result["protocol"] == mod.VERSION
    with (tmp_path / "01_gold_first_BLANK.csv").open(
         encoding="utf-8-sig", newline="") as f:
        gold = list(csv.DictReader(f))
    assert len(gold) == 30
    assert all(not row["human_direct_source_phrases"] for row in gold)
    assert "human_calm_direct_signed_score" in gold[0]
    with (tmp_path / "02_blind_evidence_A_B.csv").open(
         encoding="utf-8-sig", newline="") as f:
        evidence = list(csv.DictReader(f))
    with (tmp_path / "03_blind_scores_A_B.csv").open(
         encoding="utf-8-sig", newline="") as f:
        score = list(csv.DictReader(f))
    assert len(evidence) == len(score) == 40  # 30 primary + 10 context stress
    assert all("qwen3.6" not in line and "gemma4" not in line
               for line in (tmp_path / "02_blind_evidence_A_B.csv").read_text(
                   encoding="utf-8-sig").splitlines())
    private = json.loads((tmp_path / "04_blinding_key_KEEP_PRIVATE.json").read_text())
    assert len(private) == 40
    assert all({x["model_A"], x["model_B"]} == set(mod.MODELS)
               for x in private)
    assert result["results"][f"{mod.MODELS[0]}/segment/evidence"]["valid"] == 0


def test_invalid_output_remains_error_and_does_not_auto_retry(tmp_path, monkeypatch):
    monkeypatch.setattr(mod, "installed_model", lambda *args: "fixed")
    calls = []
    def invalid(*args, **kwargs):
        calls.append(1)
        return {"message": {"content": "{ invalid json"}}
    monkeypatch.setattr(mod, "urlopen_json", invalid)
    args = arguments(tmp_path, limit=1)
    mod.run(args)
    folder = mod.folder_for(tmp_path, args.model, args.mode, args.task)
    assert len(mod.read_lines(folder / "errors.jsonl")) == 1
    assert len(calls) == 1
    mod.run(args)
    assert len(calls) == 1

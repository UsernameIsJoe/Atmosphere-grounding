"""Offline regression tests for the real-data large-LLM Runpod probe."""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "stage1a_runpod_advanced_probe", ROOT / "scripts/stage1a_runpod_advanced_probe.py")
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


def args(out, model=None, mode="segment", limit=0):
    return SimpleNamespace(
        model=model or probe.MODELS[0], mode=mode,
        source=probe.SOURCE, output=out,
        base="http://127.0.0.1:11434", timeout=10,
        limit=limit, retry_errors=False,
    )


def response():
    return {"message": {"content": json.dumps({"ratings": [
        {"category": c, "verdict": "none", "attribution": "place",
         "reason": "not established by target segment"}
        for c in probe.CATEGORIES]})},
        "done_reason": "stop", "eval_count": 15, "prompt_eval_count": 200,
    }


def test_frozen_real_subset_source_composition_and_no_leaked_reference_labels():
    rows = probe.corpus()
    selected = probe.selected(rows, "segment")
    assert len(rows) == 123 and len(selected) == 30
    assert len(probe.selected(rows, "context")) == 10
    assert len({(r["review_id"], r["segment_id"]) for r in selected}) == 30
    for r in selected:
        request = probe.payload(r, probe.MODELS[0], "segment")
        text = request["messages"][1]["content"]
        assert json.loads(text) == {"target_segment": r["segment"]}
        assert "full_review" not in text
        assert "reference_cal" not in json.dumps(request)
        assert "nli" not in json.dumps(request).lower()
        assert "quotes" not in request["format"]["properties"]["ratings"]["items"]["properties"]
        assert request["think"] is False
        assert request["options"]["temperature"] == 0
    for r in probe.selected(rows, "context"):
        user = json.loads(probe.payload(r, probe.MODELS[0], "context")
                          ["messages"][1]["content"])
        assert user == {"target_segment": r["segment"],
                        "full_review_for_reference_only": r["full_review"]}


def test_schema_validator_rejects_missing_categories_and_preserves_uncertain():
    good = json.loads(response()["message"]["content"])
    good["ratings"][0]["verdict"] = "uncertain"
    assert probe.validate(good)[0]["verdict"] == "uncertain"
    good["ratings"][1]["category"] = "calm"
    with pytest.raises(ValueError, match="Missing or duplicate"):
        probe.validate(good)


def test_model_scoped_results_resume_and_separate_context(tmp_path, monkeypatch):
    rows = probe.corpus()
    monkeypatch.setattr(probe, "installed_model", lambda *args: "stable-digest")
    calls = []
    def stub(base, endpoint, data=None, timeout=240):
        assert endpoint == "/api/chat"
        calls.append(data)
        return response()
    monkeypatch.setattr(probe, "urlopen_json", stub)
    a = args(tmp_path, limit=2)
    probe.run(a)
    assert len(calls) == 2
    done = probe.read_lines(probe.model_directory(tmp_path, a.model, a.mode)
                            / "results.jsonl")
    assert [r["index"] for r in done] == list(probe.FROZEN_INDICES[:2])
    probe.run(a)
    assert len(calls) == 2  # resuming never repeats successfully saved cases
    b = args(tmp_path, model=probe.MODELS[1], mode="segment", limit=1)
    probe.run(b)
    assert len(calls) == 3 and calls[-1]["model"] == probe.MODELS[1]
    c = args(tmp_path, model=probe.MODELS[0], mode="context", limit=1)
    probe.run(c)
    assert len(calls) == 4
    assert "full_review_for_reference_only" in calls[-1]["messages"][1]["content"]
    assert len(probe.read_lines(
        probe.model_directory(tmp_path, probe.MODELS[0], "segment") / "results.jsonl")) == 2
    probe.report(SimpleNamespace(source=probe.SOURCE, output=tmp_path))
    with (tmp_path / "blind_human_comparison.csv").open(
            encoding="utf-8-sig", newline="") as f:
        import csv
        out = list(csv.DictReader(f))
    assert len(out) == 40
    assert "model_A_verdicts" in out[0] and "model_B_verdicts" in out[0]
    assert all("qwen3" not in x and "gemma4" not in x
               for x in (tmp_path / "blind_human_comparison.csv").read_text(
                   encoding="utf-8-sig").splitlines())
    private = json.loads((tmp_path / "blinding_key_KEEP_PRIVATE.json").read_text(
        encoding="utf-8"))
    assert len(private) == 40
    assert all(set(x) == {"index", "mode", "model_A", "model_B"} for x in private)
    assert all(set((x["model_A"], x["model_B"])) == set(probe.MODELS)
               for x in private)


def test_response_failure_is_a_logged_missing_result_not_silent_repair(tmp_path, monkeypatch):
    monkeypatch.setattr(probe, "installed_model", lambda *args: "stable-digest")
    calls = []
    def stub(*args):
        calls.append(1)
        return {"message": {"content": "not JSON"}}
    monkeypatch.setattr(probe, "urlopen_json", stub)
    a = args(tmp_path, limit=1)
    probe.run(a)
    assert len(calls) == 1
    folder = probe.model_directory(tmp_path, a.model, a.mode)
    assert len(probe.read_lines(folder / "errors.jsonl")) == 1
    assert not (folder / "results.jsonl").exists()
    probe.run(a)
    assert len(calls) == 1  # no unlimited retrying malformed answers

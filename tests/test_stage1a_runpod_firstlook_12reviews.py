"""Real-source and safety tests for the deliberately simple Runpod first look."""
from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("probe12",ROOT/"scripts/stage1a_runpod_firstlook_12reviews.py")
probe=importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


def args(out, model=None, limit=1):
    return SimpleNamespace(model=model or probe.MODELS[0],
                           output=out, source=probe.CASES,
                           base="http://127.0.0.1:11435",
                           limit=limit, retry_errors=False, timeout=8)


def valid_answer(review):
    return {"evidence": [{
        "quote": review[:min(20, len(review))],
        "kind": "both", "referent": "place",
        "reason": "relevant source fragment"
    }], "emotions": [
        {"category": c, "verdict": "none", "basis": "none",
         "reason": "not inferred from the source"}
        for c in probe.CATEGORIES
    ]}


def test_frozen_complete_reviews_are_real_and_distinct():
    reviews=probe.cases()
    assert len(reviews)==12
    probe.verify_corpus(reviews)
    assert [r["case_id"] for r in reviews]==[
        "K01","K02","K03","K04","K05","K06",
        "U01","U02","U03","U04","U05","U06"]
    assert all("\n" not in r["case_id"] for r in reviews)
    assert all(len(r["text"])>100 for r in reviews)
    assert len({r["place_id"] for r in reviews})==12


def test_model_prompt_uses_full_review_and_no_old_model_answers():
    for r in probe.cases():
        for model in probe.MODELS:
            data=probe.payload(model,r["text"])
            assert data["model"]==model
            assert json.loads(data["messages"][1]["content"])=={"review":r["text"]}
            assert "source_segment" not in data["messages"][1]["content"]
            assert "nli_median" not in json.dumps(data)
            assert "qwen_v2" not in json.dumps(data)
            assert data["options"]["temperature"]==0
            assert data["options"]["num_ctx"]==8192
            assert data["think"] is False


def test_validation_separates_quote_grounding_from_semantic_labels():
    row=probe.cases()[0]
    parsed=probe.validate(valid_answer(row["text"]), row["text"])
    assert parsed["evidence"][0]["source_exact"] is True
    invalid=valid_answer(row["text"])
    invalid["evidence"][0]["quote"]="A made-up quotation"
    parsed=probe.validate(invalid,row["text"])
    assert parsed["evidence"][0]["source_exact"] is False
    assert parsed["evidence"][0]["quote"]=="A made-up quotation"
    invalid=valid_answer(row["text"])
    invalid["emotions"][1]["category"]="calm"
    with pytest.raises(ValueError,match="Duplicate"):
        probe.validate(invalid,row["text"])


def test_gold_first_and_blinding_do_not_overwrite_human_work(tmp_path):
    rows=probe.cases()
    gold=probe.prepare(tmp_path, rows)
    assert gold.exists()
    with gold.open(encoding="utf-8-sig",newline="") as f:
        source=list(csv.DictReader(f))
    assert len(source)==12
    assert source[0]["human_calm_verdict"]==""
    source[0]["human_calm_verdict"]="none"
    with gold.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(source[0]));w.writeheader();w.writerows(source)
    snapshot=gold.read_bytes()
    probe.report(tmp_path, rows)
    assert gold.read_bytes()==snapshot
    blind=tmp_path/"02_blind_models_A_B_C.csv"
    with blind.open(encoding="utf-8-sig",newline="") as f:
        b=list(csv.DictReader(f))
    assert len(b)==12
    assert all(k not in blind.read_text(encoding="utf-8-sig")
               for k in probe.MODELS)
    b[0]["human_analysis_of_errors"]="Manual research notes"
    with blind.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(b[0]));w.writeheader();w.writerows(b)
    original=blind.read_bytes()
    probe.report(tmp_path, rows)
    assert blind.read_bytes()==original
    assert len(json.loads((tmp_path/"03_blinding_key_KEEP_PRIVATE.json").read_text()))==12


def test_real_model_calls_are_resumable_and_use_own_model_output(tmp_path,monkeypatch):
    reviews=probe.cases()
    monkeypatch.setattr(probe,"installed_digest",lambda *a:"dig")
    calls=[]
    def fake_req(base,endpoint,payload=None,timeout=600):
        assert endpoint=="/api/chat"
        calls.append(payload)
        review=json.loads(payload["messages"][1]["content"])["review"]
        return {"message":{"content":json.dumps(valid_answer(review))},
                "prompt_eval_count":150,"eval_count":250}
    monkeypatch.setattr(probe,"request",fake_req)
    a=args(tmp_path)
    probe.run(a,reviews)
    probe.run(a,reviews)
    assert len(calls)==1
    assert len(probe.read_jsonl(probe.folder(tmp_path,a.model)/"predictions.jsonl"))==1
    b=args(tmp_path,model=probe.MODELS[1])
    probe.run(b,reviews)
    assert len(calls)==2 and calls[1]["model"]==probe.MODELS[1]
    probe.report(tmp_path,reviews)
    with (tmp_path/"02_blind_models_A_B_C.csv").open(
         encoding="utf-8-sig",newline="") as f:
        row=list(csv.DictReader(f))[0]
    assert sum(bool(row[f"model_{l}_evidence"]) for l in "ABC")==2


def test_failed_request_logged_and_not_retried_automatically(tmp_path,monkeypatch):
    monkeypatch.setattr(probe,"installed_digest",lambda *a:"dig")
    attempts=[]
    def bad(*a,**k):
        attempts.append(1)
        return {"message":{"content":"BROKEN JSON"}}
    monkeypatch.setattr(probe,"request",bad)
    params=args(tmp_path)
    probe.run(params,probe.cases())
    probe.run(params,probe.cases())
    assert len(attempts)==1
    path=probe.folder(tmp_path,params.model)
    assert len(probe.read_jsonl(path/"errors.jsonl"))==1
    assert not (path/"predictions.jsonl").exists()

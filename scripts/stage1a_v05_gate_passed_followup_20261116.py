#!/usr/bin/env python3
"""Prepared only: v0.5 extraction on the remaining 12 gate-passed reviews.
Default prepare performs no network calls; run requires an absolute deadline.
"""
import argparse
import collections
import csv
import hashlib
import json
import signal
import sys
import time
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import stage1a_codebook_v05_directional_benchmark_20261116 as v05

STUDY = ROOT / "research_audit/stage1a_v05_gate_passed_followup_prepared_2026-11-16"
INPUT = STUDY / "segments.jsonl"
EXPECTED_IDS = ("T02", "T04", "T06", "T10", "T12", "N04", "N06", "N07", "N08", "N09", "N10", "N11")
FROZEN = {
    "codebook_sha256": "eaf8e1f4498087d7847bc321feaa7a224121c51b61b7ff320a0f88d749242e60",
    "prompt_sha256": "92459110bbaf579ee1b6109a671ba260b26eddf870d1678dca0ede939ca83858",
    "schema_sha256": "3d6bd54778868a7a176dc8c7d8af95e98fa76979ee68bf589e39e8906b88f3f7",
    "system_sha256": "b854badb6a8578b8f55d9b490292b6afe08e9afdf2a5857d462cce8df2219288",
}
GATE = ROOT / "research_audit/stage1a_review_gate_v04_regression_qwen8b_2026-11-16/decisions.jsonl"
PREVIOUS = ROOT / "research_audit/stage1a_v05_directional_live_2026-11-16/qwen3.8_27b__repeat1.json"

class DeadlineReached(Exception):
    pass

def alarm_handler(signum, frame):
    raise DeadlineReached("absolute study deadline")

def read_jsonl(path):
    return [json.loads(s) for s in path.read_text(encoding="utf-8").splitlines() if s.strip()]

def digest_file(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def prepare():
    data = read_jsonl(INPUT)
    gate = {r["review_id"]: r for r in read_jsonl(GATE)}
    old_ids = {r["case_id"] for r in json.loads(PREVIOUS.read_text(encoding="utf-8"))["cases"]}
    expected = {k for k, r in gate.items() if r["parsed"]["keep"] and k not in old_ids}
    assert expected == set(EXPECTED_IDS)
    assert len(data) == 71 and {r["case_id"] for r in data} == expected
    assert len({r["segment_id"] for r in data}) == len(data)
    for r in data:
        g = gate[r["case_id"]]
        assert g["parsed"]["keep"] is True
        assert r["full_review_context"] == g["review_text"]
        assert r["review_sha256"] == v05.sha(g["review_text"])
        assert r["review_sha256"] == g["review_sha256"]
        assert (r["place_id"], r["review_index"]) == (g["place_id"], g["review_index"])
        assert r["target_segment"] == g["review_text"][r["start"]:r["end"]]
    # Every non-whitespace source character is covered once; no dropped sentences.
    for cid in EXPECTED_IDS:
        spans = sorted((r["start"], r["end"]) for r in data if r["case_id"] == cid)
        text = gate[cid]["review_text"]
        cursor = 0
        for start, end in spans:
            assert cursor <= start < end <= len(text)
            assert not text[cursor:start].strip()
            cursor = end
        assert not text[cursor:].strip()
    system, schema = v05.system_and_schema()
    actual = {
        "codebook_sha256": v05.sha(v05.CODEBOOK.read_text(encoding="utf-8")),
        "prompt_sha256": v05.sha(v05.PROMPT.read_text(encoding="utf-8")),
        "schema_sha256": v05.sha(schema), "system_sha256": v05.sha(system),
    }
    assert actual == FROZEN, ("Frozen v0.5 drift", actual)
    # Breadth-first sentence order gives every review coverage before later sentences.
    groups = {cid: [r for r in data if r["case_id"] == cid] for cid in EXPECTED_IDS}
    ordered = [groups[cid][i] for i in range(max(map(len, groups.values())))
               for cid in EXPECTED_IDS if i < len(groups[cid])]
    manifest = {
        "protocol": "stage1a_v05_gate_passed_followup", "status": "prepared_not_run",
        "reviews": 12, "segments": 71, "max_inference_calls": 142, "repeats": 1,
        "case_ids": list(EXPECTED_IDS), "models": list(v05.MODELS),
        "expected_model_digests": v05.MODEL_DIGESTS,
        "options": v05.OPTIONS, "think": False, "no_retries": True,
        "input_sha256": digest_file(INPUT), "gate_sha256": digest_file(GATE),
        "previous_run_sha256": digest_file(PREVIOUS), **actual,
        "segmentation": "source-exact sentence boundaries; parenthetical content kept together; no contrast splitting",
        "sampling": "all 12 KEEP reviews outside prior v0.5; all source sentences",
        "target_scope": "one original sentence; complete original review as context",
        "order": "fixed breadth-first sentence order, identical for both models",
        "scope_note": "new to latest extraction pilot; previously used for gate development, not independent holdout",
    }
    return ordered, system, schema, manifest

def request(host, endpoint, payload=None, timeout=90):
    body = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = Request(host.rstrip("/") + endpoint, data=body,
                  headers={"Content-Type": "application/json"})
    with urlopen(req, timeout=timeout) as response:
        return json.load(response)

def append(path, row):
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
        f.flush()

def report(out, data):
    path = out / "predictions.jsonl"
    records = read_jsonl(path) if path.exists() else []
    valid = [r for r in records if r["strict_valid"]]
    by_model = {}
    for model in v05.MODELS:
        rr = [r for r in records if r["model"] == model]
        usable = [r for r in rr if r["strict_valid"]]
        present = {r["segment_id"] for r in rr}
        by_model[model] = {
            "attempted_segments": len(rr), "valid_segments": len(usable),
            "invalid_segments": len(rr) - len(usable),
            "unattempted_segment_ids": [r["segment_id"] for r in data if r["segment_id"] not in present],
            "reviews_touched": len({r["case_id"] for r in rr}),
            "reviews_complete_valid": [
                cid for cid in EXPECTED_IDS
                if {r["segment_id"] for r in data if r["case_id"] == cid}
                <= {r["segment_id"] for r in usable}
            ],
            "valid_claims": sum(len(r["claims"]) for r in usable),
            "valid_empty_segments": sum(not r["claims"] for r in usable),
        }
    common = sorted(set.intersection(*[
        {r["segment_id"] for r in valid if r["model"] == m} for m in v05.MODELS
    ]))
    summary = {"models": by_model, "paired_valid_segments": common,
               "planned_segments_per_model": 71,
               "semantic_accuracy": "not computed; independent source audit required",
               "invalid_policy": "invalid/timeout/missing are not empty or correct"}
    (out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    fields = ["model", "case_id", "segment_id", "emotion", "quote", "direction", "track",
              "referent", "reason", "target_segment", "full_review_context", "case_strict_valid",
              "audit_direction", "audit_track", "audit_referent", "audit_notes"]
    with (out / "claim_audit.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for r in records:
            for c in r["claims"]:
                writer.writerow({**{k: r[k] for k in ("model", "case_id", "segment_id",
                                                      "target_segment", "full_review_context")},
                                 **{k: c[k] for k in ("emotion", "quote", "direction", "track", "referent", "reason")},
                                 "case_strict_valid": r["strict_valid"]})
    with (out / "segment_audit.csv").open("w", newline="", encoding="utf-8") as f:
        fields = ["model", "case_id", "segment_id", "target_segment", "full_review_context",
                  "status", "claims_json", "missed_claims", "audit_notes"]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        lookup = {(r["model"], r["segment_id"]): r for r in records}
        for model in v05.MODELS:
            for d in data:
                r = lookup.get((model, d["segment_id"]))
                writer.writerow({**{k: d[k] for k in ("case_id", "segment_id", "target_segment", "full_review_context")},
                                 "model": model, "status": "missing" if r is None else "valid" if r["strict_valid"] else "invalid",
                                 "claims_json": "" if r is None else json.dumps(r["claims"], ensure_ascii=False)})
    return summary

def run(args):
    data, system, schema, manifest = prepare()
    # Caller supplies start time recorded BEFORE provisioning/downloads.
    # Inference ends at minute 27; final three minutes are reserved for archive/termination.
    if args.started_at is None:
        raise ValueError("--started-at epoch seconds recorded before provisioning is required")
    now = time.time()
    if not 0 <= now - args.started_at < 27 * 60:
        raise ValueError("Invalid/expired study start timestamp")
    deadline = args.started_at + 27 * 60
    signal.signal(signal.SIGALRM, alarm_handler)
    signal.setitimer(signal.ITIMER_REAL, max(0.001, deadline - time.time()))
    args.output.mkdir(parents=True, exist_ok=True)
    if (args.output / "manifest.json").exists():
        raise ValueError("Choose a fresh output directory; no silent resume/retry")
    manifest.update(status="started", study_started_at=args.started_at,
                    inference_deadline_epoch=deadline, cleanup_deadline_epoch=args.started_at + 30 * 60)
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    state = "complete"
    try:
        # Half of remaining inference time per model; same sentence order.
        per_model = max(0, deadline - time.time() - 10) / 2
        for model in v05.MODELS:
            model_deadline = min(deadline - 5, time.time() + per_model)
            tags = request(args.host, "/api/tags", timeout=min(30, max(1, model_deadline - time.time())))
            actual = next((m.get("digest") for m in tags.get("models", [])
                           if m.get("name") == model or m.get("model") == model), None)
            if actual != v05.MODEL_DIGESTS[model]:
                raise RuntimeError("MODEL DIGEST MISMATCH: " + model + " " + str(actual))
            for row in data:
                left = min(deadline, model_deadline) - time.time()
                if left < 5:
                    state = "partial_time_limit"
                    break
                start = time.monotonic()
                raw = ""; parsed = None; claims = []; errors = []; metadata = {}
                # Alarm bounds the entire call including body reads; preserve response failures.
                signal.setitimer(signal.ITIMER_REAL, max(0.001, min(deadline, model_deadline) - time.time()))
                try:
                    reply = request(args.host, "/api/chat", {
                        "model": model, "messages": [
                            {"role": "system", "content": system},
                            {"role": "user", "content": json.dumps({
                                "target_segment": row["target_segment"],
                                "full_review_context": row["full_review_context"]}, ensure_ascii=False)}
                        ], "format": schema, "stream": False, "think": False,
                        "options": v05.OPTIONS, "keep_alive": "20m",
                    }, timeout=min(90, left))
                    raw = reply.get("message", {}).get("content", "")
                    metadata = {k: reply.get(k) for k in ("eval_count", "prompt_eval_count", "total_duration", "done_reason")}
                    parsed = json.loads(raw)
                    errors, claims = v05.examine(parsed, row["target_segment"])
                except Exception as ex:
                    errors.append(type(ex).__name__ + ": " + str(ex))
                finally:
                    signal.setitimer(signal.ITIMER_REAL, max(0.001, deadline - time.time()))
                append(args.output / "predictions.jsonl", {
                    **row, "model": model, "model_digest": actual, "raw": raw,
                    "parsed": parsed, "claims": claims, "validation_errors": errors,
                    "strict_valid": not errors, "metadata": metadata,
                    "seconds": round(time.monotonic() - start, 3),
                })
                print(model, row["segment_id"], "valid" if not errors else "invalid", flush=True)
            # Unload once between models; avoid reloading weights on every sentence.
            if deadline - time.time() > 5:
                request(args.host, "/api/generate", {"model": model, "keep_alive": 0},
                        timeout=min(10, deadline - time.time()))
    except DeadlineReached:
        state = "partial_time_limit"
    except Exception as ex:
        state = "stopped_error"
        append(args.output / "run_errors.jsonl", {"error": type(ex).__name__ + ": " + str(ex)})
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        summary = report(args.output, data)
        complete = all(m["attempted_segments"] == 71 for m in summary["models"].values())
        manifest.update(status="complete" if complete else state if state != "complete" else "partial",
                        inference_finished_at=time.time())
        (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        print(json.dumps(summary, indent=2))
        print("Operator must archive results and terminate compute before cleanup_deadline_epoch.", flush=True)

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--stage", choices=("prepare", "run", "report"), default="prepare")
    p.add_argument("--host", default="http://127.0.0.1:11434")
    p.add_argument("--output", type=Path, default=ROOT / "reports/stage1a_v05_gate_passed_followup_2026-11-16")
    p.add_argument("--started-at", type=float)
    a = p.parse_args()
    if a.stage == "prepare":
        _, _, _, manifest = prepare()
        print(json.dumps(manifest, indent=2))
    elif a.stage == "run":
        run(a)
    else:
        data, _, _, _ = prepare()
        a.output.mkdir(parents=True, exist_ok=True)
        print(json.dumps(report(a.output, data), indent=2))

if __name__ == "__main__":
    main()

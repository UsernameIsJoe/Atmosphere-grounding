#!/usr/bin/env python3
"""Direction-only two-review experiment using PREVIOUSLY extracted exact evidence spans.

No extraction or evidence selection by an LLM. Eight frozen test items from two
real reviews; two model families; 16 short structured calls. No human gold labels.
Every item is verified against the source corpus and original annotation file.
"""
from __future__ import annotations

import argparse
import collections
import json
import urllib.request
from pathlib import Path

from stage1a_panel_pilot import load_real_reviews, prepare, sha256
from stage1a_evidence_first_5 import read_jsonl, append_jsonl

ROOT = Path(__file__).resolve().parents[1]
PROMPT = (
    "Decide the DIRECTION of one PRE-EXTRACTED, SOURCE-GROUNDED evidence span "
    "relative to ONE atmosphere category in a place review. Do not extract "
    "new evidence. Do not equate relevance with positivity. "
    "supports = this evidence specifically favors the category; "
    "opposes = this evidence specifically counts against the category; "
    "neither = insufficient connection to the category; "
    "ambiguous = reasonable interpretations genuinely point different ways. "
    "For CALM, quiet/relaxation supports; chaos/noise opposes. "
    "For INVITING, welcome/comfortable social use supports; unwelcome/repelling "
    "conditions oppose. For SAFE, reduced concrete danger supports; slippery "
    "surfaces or injury hazards oppose. A physical description is not "
    "automatically evidence of felt emotion. "
    "State one short reason based on the provided span, then choose direction. "
    "Return only JSON and do not invent experiences."
)
RUBRIC = {
    "calm": "Atmospheric quietness, tranquility, relaxation vs stress, noise, chaos.",
    "inviting": "Welcome, approachability, comfort to gather vs exclusion or repelling conditions.",
    "safe": "Safety, protection, reduced danger vs injury hazard or reported unsafety.",
}
SCHEMA = {"type": "object", "additionalProperties": False, "properties": {
    "reason": {"type": "string", "maxLength": 180},
    "direction": {"type": "string", "enum": ["supports", "opposes", "neither", "ambiguous"]},
}, "required": ["reason", "direction"]}


def build_items(corpus: Path, prior: Path, casefile: Path) -> list[dict]:
    cfg = json.loads(casefile.read_text(encoding="utf-8"))
    cases = cfg["cases"]
    if len(cases) != 8 or len({x["place_id"] for x in cases}) != 2:
        raise ValueError("Expected exactly 8 cases from exactly 2 review locations")
    originals = {(r["place_id"], r["review_index"]): r
                 for r in load_real_reviews(corpus, 0)}
    prior_rows = read_jsonl(prior)
    indexed = collections.defaultdict(list)
    for r in prior_rows:
        indexed[(r["place_id"], r["review_index"], r["unit_id"],
                 r["emotion"], r["model"])].append(r)
    result = []
    seen = set()
    for n, case in enumerate(cases):
        k = (case["place_id"], case["review_index"], case["unit_id"], case["emotion"])
        if k in seen:
            raise ValueError(f"Duplicate frozen case {k}")
        seen.add(k)
        row = originals.get(k[:2])
        if row is None:
            raise ValueError(f"Missing original review {k[:2]}")
        p = prepare([row])[0]
        unit = next((u for u in p["units"] if u["unit_id"] == case["unit_id"]), None)
        if unit is None:
            raise ValueError(f"Missing original clause {k}")
        matches = indexed.get(k + (case["source_model"],), [])
        if len(matches) != 1:
            raise ValueError(f"Missing or duplicate original extracted result: {k}")
        prev = matches[0]
        span = prev["evidence_span"]
        if (prev["source_sha256"] != p["source_sha256"]
                or prev["clause"] != unit["text"]
                or not span or span not in unit["text"]
                or prev["relevance"] != case["expected_prior_label"]):
            raise ValueError(f"Frozen original evidence does not match: {k}")
        result.append({"case_id": n, **case, "text": p["text"],
                       "clause": unit["text"], "evidence_span": span,
                       "source_sha256": p["source_sha256"],
                       "prior_rationale": prev["rationale"]})
    return result


def request(ollama_url: str, model: str, item: dict, timeout: int) -> dict:
    message = ("CATEGORY: " + item["emotion"] + "\nDEFINITION: " + RUBRIC[item["emotion"]]
               + "\nTARGET CLAUSE:\n" + item["clause"]
               + "\nFIXED EVIDENCE SPAN (DO NOT CHANGE):\n" + item["evidence_span"]
               + "\nJudge only whether this span supports, opposes, neither, or is ambiguous "
                 "relative to the stated category. Do NOT automatically choose supports.")
    payload = {"model": model, "messages": [
        {"role": "system", "content": PROMPT},
        {"role": "user", "content": message}],
        "stream": False, "format": SCHEMA,
        "options": {"temperature": 0, "num_ctx": 4096, "num_predict": 256}}
    if model.lower().startswith("qwen3:"):
        payload["think"] = False
    req = urllib.request.Request(ollama_url.rstrip("/") + "/api/chat",
                                 data=json.dumps(payload).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        body = json.load(response)
    return {"raw_content": body.get("message", {}).get("content", ""),
            "done_reason": body.get("done_reason")}


def validate_result(r: object) -> dict:
    if not isinstance(r, dict) or set(r) != {"reason", "direction"}:
        raise ValueError("Wrong JSON fields")
    if (not isinstance(r["reason"], str) or len(r["reason"]) > 180
            or r["direction"] not in SCHEMA["properties"]["direction"]["enum"]):
        raise ValueError("Invalid reason/direction")
    return r


def run() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "data/processed/reviews.jsonl")
    parser.add_argument("--source-annotations", type=Path,
                        default=ROOT / "reports/stage1a_evidence_first_5/annotations.jsonl")
    parser.add_argument("--cases", type=Path, default=ROOT / "configs/stage1a_direction_2_cases.json")
    parser.add_argument("--output", type=Path, default=ROOT / "reports/stage1a_direction_2")
    parser.add_argument("--models", nargs=2, default=["qwen3:8b", "gemma3:4b"])
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--ollama-url", default="http://localhost:11434")
    parser.add_argument("--timeout", type=int, default=480)
    args = parser.parse_args()
    if len(set(args.models)) != 2:
        parser.error("Choose two different models")
    items = build_items(args.input, args.source_annotations, args.cases)
    manifest = {"version": "stage1a_direction_2_v1",
                "models": args.models, "n_items": len(items),
                "source_hashes": {x["place_id"]: x["source_sha256"] for x in items},
                "cases_hash": sha256(json.dumps(items, sort_keys=True)),
                "prompt_sha256": sha256(PROMPT),
                "schema_sha256": sha256(json.dumps(SCHEMA, sort_keys=True))}
    print(f"VERIFIED 2 original reviews, {len(items)} frozen evidence spans, "
          f"{len(items) * 2} direction calls; no extraction required.", flush=True)
    if args.prepare_only:
        for x in items:
            print(x["case_id"], x["emotion"], x["purpose"],
                  repr(x["evidence_span"]), "prior:", x["expected_prior_label"])
        return
    args.output.mkdir(parents=True, exist_ok=True)
    mf = args.output / "manifest.json"
    if mf.exists():
        if json.loads(mf.read_text(encoding="utf-8")) != manifest:
            raise ValueError("Existing experiment manifest differs")
    else:
        if (args.output / "annotations.jsonl").exists():
            raise ValueError("Existing annotations without manifest")
        mf.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        (args.output / "frozen_items.jsonl").write_text(
            "".join(json.dumps(x, ensure_ascii=False) + "\n" for x in items), encoding="utf-8")
    done_rows = read_jsonl(args.output / "annotations.jsonl")
    expected = {(x["case_id"], m) for x in items for m in args.models}
    done = set()
    for item in done_rows:
        key = (item["case_id"], item["model"])
        if key not in expected or key in done:
            raise ValueError("Duplicate or unexpected saved response")
        original = items[item["case_id"]]
        if (item["source_sha256"] != original["source_sha256"]
                or item["evidence_span"] != original["evidence_span"]):
            raise ValueError("Saved response is not grounded in frozen evidence")
        validate_result({k: item[k] for k in ("reason", "direction")})
        done.add(key)
    for item in items:
        for model in args.models:
            key = (item["case_id"], model)
            if key in done:
                print("SKIP", *key, flush=True)
                continue
            for attempt in (1, 2):
                trace = {"case_id": item["case_id"], "model": model, "attempt": attempt}
                try:
                    body = request(args.ollama_url, model, item, args.timeout)
                    trace.update(body)
                    try:
                        raw = json.loads(body["raw_content"])
                        trace["intended"] = raw
                        label = validate_result(raw)
                        trace["validation"] = "valid"
                        append_jsonl(args.output / "raw_responses.jsonl", trace)
                        append_jsonl(args.output / "annotations.jsonl", {
                            "case_id": item["case_id"], "model": model,
                            "place_id": item["place_id"], "review_index": item["review_index"],
                            "unit_id": item["unit_id"], "emotion": item["emotion"],
                            "source_sha256": item["source_sha256"],
                            "evidence_span": item["evidence_span"],
                            **label})
                        done.add(key)
                        print("OK", item["case_id"], model, label["direction"], flush=True)
                        break
                    except (ValueError, TypeError, KeyError) as exc:
                        trace["validation"] = "invalid"
                        trace["error"] = str(exc)
                        append_jsonl(args.output / "raw_responses.jsonl", trace)
                except (OSError, ValueError) as exc:
                    trace["validation"] = "request_error"
                    trace["error"] = str(exc)
                    append_jsonl(args.output / "raw_responses.jsonl", trace)
            else:
                print("FAILED", *key, flush=True)
    rows = read_jsonl(args.output / "annotations.jsonl")
    by_model = collections.defaultdict(collections.Counter)
    for r in rows:
        by_model[r["model"]][r["direction"]] += 1
    summary = {"expected": len(expected), "completed": len(done),
               "missing": sorted([{"case_id": x, "model": y} for x, y in (expected - done)],
                                 key=lambda r: (r["case_id"], r["model"])),
               "direction_counts": {k: dict(v) for k, v in by_model.items()}}
    (args.output / "diagnostics.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"FINISHED {len(done)}/{len(expected)} decisions. Results are not gold labels.")

if __name__ == "__main__":
    run()

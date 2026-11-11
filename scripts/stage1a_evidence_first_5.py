#!/usr/bin/env python3
"""Five-real-review evidence-first smoke test. Separate, cost-aware experiment.

Uses fixed source hashes from original A/B baseline; no synthetic evaluation reviews.
One emotion per call, simple schema, source-grounded quotations, no label-changing retries.
Run --prepare-only FIRST. Ollama inference happens only when that flag is omitted.
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
import unicodedata
import urllib.error
import urllib.request
from pathlib import Path

from stage1a_panel_pilot import PILOT, prepare, load_real_reviews, sha256

ROOT = Path(__file__).resolve().parents[1]
PROMPT = (
    "You inspect evidence about the atmosphere of a PLACE in a real visitor review. "
    "Work on just ONE emotion and ONE TARGET CLAUSE. The full review is for resolving "
    "references/negation only: the quoted evidence MUST be inside the target clause. "
    "First explain in one SHORT sentence what this clause says that bears on the "
    "emotion, or why it says nothing relevant. Then copy an EXACT contiguous substring "
    "from the TARGET CLAUSE supporting that explanation. Last choose the label. "
    "SUPPORTS means evidence for the emotion; OPPOSES means evidence against it; "
    "MIXED requires both directions within this same clause; NOT_RELEVANT means no "
    "specific link; UNCERTAIN means an actually ambiguous link, not merely absence "
    "of an emotion word. Emotion words are NOT required. Physical features alone "
    "do not prove feelings, but a directly described hazard or a described relevant "
    "experience can be evidence. Do not invent feelings or assume all pleasant "
    "descriptions support all positive emotions. A plain amenity list is not relevant. "
    "Do not write filler or repeat phrases. Return JSON only."
)
RUBRIC = {
    "calm": "Evidence for tranquility, quiet, peace or relaxation; against: noise, chaos or stress. Relaxing activity can be indirect evidence when place-attributed.",
    "inviting": "Evidence for welcome, approachability, comfortable gathering or desire to linger; against: social exclusion, hostility, or experienced lack of welcome. Generic praise alone is not evidence.",
    "safe": "Evidence for feeling protected, secure or free of specific hazards; against: specific injury risks, hazards or feeling unsafe. Do not equate a gate alone with felt safety.",
}
SCHEMA = {"type": "object", "additionalProperties": False, "properties": {
    "rationale": {"type": "string", "maxLength": 220},
    "evidence_span": {"type": "string", "maxLength": 280},
    "relevance": {"type": "string", "enum": ["supports", "opposes", "mixed", "not_relevant", "uncertain"]},
}, "required": ["rationale", "evidence_span", "relevance"]}
MAP = str.maketrans({"’": "'", "‘": "'", "“": '"', "”": '"', "–": "-", "—": "-"})

def normalize_with_offsets(value: str) -> tuple[str, list[int]]:
    out, offsets, whitespace = [], [], False
    for i, ch in enumerate(value):
        for c in unicodedata.normalize("NFKC", ch).translate(MAP).casefold():
            if c.isspace():
                if whitespace:
                    continue
                c, whitespace = " ", True
            else:
                whitespace = False
            out.append(c)
            offsets.append(i)
    return "".join(out), offsets

def ground_span(span: str, clause: str) -> tuple[str | None, str]:
    """Only deterministic normalization; never fuzzy-match, paraphrase, or other clauses."""
    if not isinstance(span, str) or not span:
        return None, "empty"
    if span in clause:
        return span, "exact"
    source, offsets = normalize_with_offsets(clause)
    target, _ = normalize_with_offsets(span)
    target = target.strip()
    if not target:
        return None, "empty"
    hits = []
    start = 0
    while True:
        p = source.find(target, start)
        if p == -1:
            break
        hits.append(p)
        start = p + 1
    if len(hits) != 1:
        return None, "ambiguous" if hits else "not_found"
    p = hits[0]
    return clause[offsets[p]: offsets[p + len(target) - 1] + 1], "normalized"

def validate_answer(answer: dict, clause: str) -> dict:
    if not isinstance(answer, dict) or set(answer) != set(SCHEMA["properties"]):
        raise ValueError("schema keys")
    if not isinstance(answer["rationale"], str) or not isinstance(answer["evidence_span"], str):
        raise ValueError("types")
    if len(answer["rationale"]) > 220 or len(answer["evidence_span"]) > 280:
        raise ValueError("overlong")
    label = answer["relevance"]
    if label not in SCHEMA["properties"]["relevance"]["enum"]:
        raise ValueError("unknown label")
    span = answer["evidence_span"]
    if label in ("supports", "opposes", "mixed"):
        grounded, method = ground_span(span, clause)
        if grounded is None:
            raise ValueError("ungrounded evidence")
    elif span:
        grounded, method = ground_span(span, clause)
        if grounded is None:
            raise ValueError("ungrounded optional evidence")
    else:
        grounded, method = "", "none"
    return {**answer, "evidence_span": grounded, "model_evidence_span": span,
            "grounding": method}

def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

def append_jsonl(path: Path, value: dict) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(value, ensure_ascii=False) + "\n")
        f.flush()

def frozen_reviews(corpus: Path, config: Path) -> tuple[list[dict], dict]:
    spec = json.loads(config.read_text(encoding="utf-8"))
    selected = spec["reviews"]
    corpus_rows = load_real_reviews(corpus, 0)
    indexed = {(r["place_id"], r["review_index"]): r for r in corpus_rows}
    if len(selected) != 5 or len({r["place_id"] for r in selected}) != 5:
        raise ValueError("Five distinct places required")
    chosen = []
    for item in selected:
        key = (item["place_id"], item["review_index"])
        row = indexed.get(key)
        if row is None or sha256(row["text"]) != item["source_sha256"]:
            raise ValueError(f"Corpus identity/hash mismatch for {key}")
        prepared = prepare([row])[0]
        if len(prepared["units"]) != item["n_clauses"]:
            raise ValueError(f"Clause count changed for {key}")
        chosen.append(prepared)
    return chosen, spec

def request(base: str, model: str, emotion: str, review: dict, unit: dict, timeout: int) -> dict:
    user = ("EMOTION: " + emotion + "\nDEFINITION: " + RUBRIC[emotion]
            + "\nFULL REVIEW (CONTEXT ONLY):\n" + review["text"]
            + "\nTARGET CLAUSE (QUOTE ONLY THIS):\n" + unit["text"]
            + "\nReturn rationale, then evidence_span, then relevance. "
              "If no relevant evidence, evidence_span must be empty.")
    payload = {"model": model, "messages": [
        {"role": "system", "content": PROMPT}, {"role": "user", "content": user}],
        "stream": False, "format": SCHEMA,
        "options": {"temperature": 0, "num_ctx": 8192, "num_predict": 512}}
    if model.lower().startswith("qwen3:"):
        payload["think"] = False
    req = urllib.request.Request(base.rstrip("/") + "/api/chat",
                                 data=json.dumps(payload).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        data = json.load(response)
    return {"content": data.get("message", {}).get("content", ""),
            "done_reason": data.get("done_reason"), "model": model,
            "prompt_sha256": sha256(PROMPT)}

def run() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "data/processed/reviews.jsonl")
    parser.add_argument("--config", type=Path, default=ROOT / "configs/stage1a_evidence_first_5.json")
    parser.add_argument("--output", type=Path, default=ROOT / "reports/stage1a_evidence_first_5")
    parser.add_argument("--models", nargs="+", default=["qwen3:8b", "gemma3:4b"])
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--ollama-url", default="http://localhost:11434")
    parser.add_argument("--timeout", type=int, default=480)
    args = parser.parse_args()
    if len(args.models) != len(set(args.models)):
        parser.error("Duplicate model names")
    reviews, spec = frozen_reviews(args.input, args.config)
    manifest = {"version": "evidence_first_5_v1", "models": args.models,
                "review_ids": [(r["place_id"], r["review_index"], r["source_sha256"]) for r in reviews],
                "n_reviews": len(reviews), "n_clauses": sum(len(r["units"]) for r in reviews),
                "prompt_sha256": sha256(PROMPT), "rubric_sha256": sha256(json.dumps(RUBRIC, sort_keys=True)),
                "schema_sha256": sha256(json.dumps(SCHEMA, sort_keys=True))}
    print("VERIFIED", manifest["n_reviews"], "real reviews,", manifest["n_clauses"],
          "clauses,", len(PILOT), "emotions,", len(args.models), "models;",
          manifest["n_clauses"] * len(PILOT) * len(args.models), "single-emotion calls", flush=True)
    if args.prepare_only:
        for review in reviews:
            print(review["place_id"], review["review_index"],
                  len(review["units"]), review["source_sha256"])
        return
    args.output.mkdir(parents=True, exist_ok=True)
    manifest_file = args.output / "manifest.json"
    if manifest_file.exists():
        if json.loads(manifest_file.read_text(encoding="utf-8")) != manifest:
            raise ValueError("Existing output manifest does not match this experiment")
    else:
        if (args.output / "annotations.jsonl").exists():
            raise ValueError("Annotations exist without a manifest; use a new output folder")
        manifest_file.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        (args.output / "clauses.jsonl").write_text(
            "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in reviews), encoding="utf-8")
    annotations = read_jsonl(args.output / "annotations.jsonl")
    keys = set()
    for a in annotations:
        key = (a["place_id"], a["review_index"], a["unit_id"], a["emotion"], a["model"])
        if key in keys or a["source_sha256"] != next(
            r["source_sha256"] for r in reviews if r["place_id"] == a["place_id"]):
            raise ValueError("Duplicate or untrusted saved result")
        keys.add(key)
    attempted = 0
    errors = []
    for review in reviews:
        for unit in review["units"]:
            for emotion in PILOT:
                for model in args.models:
                    key = (review["place_id"], review["review_index"], unit["unit_id"], emotion, model)
                    if key in keys:
                        continue
                    for attempt in (1, 2):
                        attempted += 1
                        try:
                            response = request(args.ollama_url, model, emotion, review, unit, args.timeout)
                            trace = {"place_id": review["place_id"], "review_index": review["review_index"],
                                     "unit_id": unit["unit_id"], "emotion": emotion, "model": model,
                                     "attempt": attempt, **response}
                            try:
                                intended = json.loads(response["content"])
                                trace["intended"] = intended
                                valid = validate_answer(intended, unit["text"])
                                trace["validation"] = "valid"
                                append_jsonl(args.output / "raw_responses.jsonl", trace)
                                record = {**valid, "place_id": review["place_id"],
                                          "review_index": review["review_index"],
                                          "unit_id": unit["unit_id"], "emotion": emotion, "model": model,
                                          "source_sha256": review["source_sha256"],
                                          "clause": unit["text"]}
                                append_jsonl(args.output / "annotations.jsonl", record)
                                keys.add(key)
                                print(model, review["place_id"], unit["unit_id"], emotion,
                                      valid["relevance"], flush=True)
                                break
                            except (ValueError, TypeError, KeyError) as e:
                                trace["validation"] = "invalid"
                                trace["validation_error"] = str(e)
                                append_jsonl(args.output / "raw_responses.jsonl", trace)
                        except (OSError, ValueError) as e:
                            append_jsonl(args.output / "raw_responses.jsonl",
                                         {"place_id": review["place_id"], "review_index": review["review_index"],
                                          "unit_id": unit["unit_id"], "emotion": emotion, "model": model,
                                          "attempt": attempt, "validation": "request_error", "error": str(e)})
                    else:
                        errors.append({"place_id": review["place_id"], "unit_id": unit["unit_id"],
                                       "emotion": emotion, "model": model})
    expected = manifest["n_clauses"] * len(PILOT) * len(args.models)
    count = len(keys)
    summary = {"expected_judgments": expected, "completed_judgments": count,
               "missing_judgments": errors, "label_counts": dict(collections.Counter(
                   a["relevance"] for a in read_jsonl(args.output / "annotations.jsonl"))),
               "models": args.models, "n_requests_this_execution": attempted}
    (args.output / "diagnostics.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"FINISHED {count}/{expected} judgments. Incomplete cases preserved for targeted rerun.")

if __name__ == "__main__":
    run()

#!/usr/bin/env python3
"""First Runpod capability look: 12 REAL complete reviews, 3 LLMs, same prompt.

No segmentation, no NLI, no inference pipeline, no cross-model judging, no
claim of accuracy without researcher adjudication. Python standard library.

    python3 scripts/stage1a_runpod_firstlook_12reviews.py --stage prepare
    python3 scripts/stage1a_runpod_firstlook_12reviews.py --stage check --base http://127.0.0.1:11435
    python3 scripts/stage1a_runpod_firstlook_12reviews.py --stage run --base http://127.0.0.1:11435 --model qwen3:8b --limit 2
    python3 scripts/stage1a_runpod_firstlook_12reviews.py --stage report
"""
from __future__ import annotations

import argparse
import csv
from hashlib import sha256
import json
from pathlib import Path
import random
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "research_audit/stage1a_runpod_12review_firstlook_2026-11-13/cases.jsonl"
OUT = ROOT / "reports/stage1a_runpod_firstlook_12reviews_2026-11-13"
MODELS = ("qwen3:8b", "qwen3.6:27b-bf16", "gemma4:31b-it-bf16")
CATEGORIES = ("calm", "inviting", "safe")
VERDICTS = ("supports", "opposes", "mixed", "none", "uncertain")
BASIS = ("direct", "inference", "both", "none", "uncertain")
CHANNELS = ("direct", "inference", "both")
REFERENTS = ("place", "surroundings", "people", "animals", "other", "ambiguous")
VERSION = "runpod_12_full_reviews_firstlook_v1"
SYSTEM = """Read one authentic review of a place. Your task is to demonstrate
how well you interpret the source, not to maximize the number of labels.

First, identify all meaningful statements relevant to a visitor's experienced
atmosphere, whether DIRECT (the author actually characterizes experience,
environment, or relevant safety/comfort/peacefulness), INFERENCE (a reported
physical/spatial/sensory/social/access condition from which atmosphere might
be hypothesized), or BOTH. A claim can be both. Copy a precise short source
phrase, preserve negation, and name its referent. The scope may be nearby
surroundings, a person, an animal, etc., not always the whole place.

Second, judge whether the entire review provides evidence supporting or
opposing EACH of calm, inviting, safe. For each emotion, distinguish
directly claimed vs inferred basis, and say none when no defensible evidence
exists. Mixed and uncertain remain distinct. Give a short explanation.

Calm: peaceful, relaxing, quiet vs disruptive, stressful, noisy.
Inviting: welcoming, approachable, comfortable vs excluding, unwelcoming.
Safe: secure, protected vs dangerous, threatened.

Do not infer a specific atmosphere automatically from mere beauty, general
praise, darkness, dirt, graffiti, greenery, cost, maintenance, or activity.
The appearance of those conditions does NOT automatically imply all three
atmospheric categories. Do not turn politeness of one person into claims
about the whole location, and do not turn 'meditative walk' into a direct
assertion that a place is calm. Preserve ambiguity and scope. No invented
facts, no source text outside this one review.

Return only JSON matching the supplied schema. Source quotes are mechanically
checked for traceability, but this is NOT a benchmark of quote-copying skill."""
SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "evidence": {
            "type": "array", "items": {
                "type": "object", "additionalProperties": False,
                "properties": {
                    "quote": {"type": "string"},
                    "kind": {"type": "string", "enum": list(CHANNELS)},
                    "referent": {"type": "string", "enum": list(REFERENTS)},
                    "reason": {"type": "string"},
                }, "required": ["quote", "kind", "referent", "reason"],
            },
        },
        "emotions": {
            "type": "array", "minItems": 3, "maxItems": 3,
            "items": {
                "type": "object", "additionalProperties": False,
                "properties": {
                    "category": {"type": "string", "enum": list(CATEGORIES)},
                    "verdict": {"type": "string", "enum": list(VERDICTS)},
                    "basis": {"type": "string", "enum": list(BASIS)},
                    "reason": {"type": "string"},
                }, "required": ["category", "verdict", "basis", "reason"],
            },
        },
    }, "required": ["evidence", "emotions"],
}


def sha(value: object) -> str:
    return sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                             separators=(",", ":")).encode("utf-8")).hexdigest()


def cases(path: Path = CASES) -> list[dict]:
    data = [json.loads(row) for row in path.read_text(encoding="utf-8").splitlines()
            if row.strip()]
    if len(data) != 12 or len({r["case_id"] for r in data}) != 12:
        raise ValueError("The frozen 12-case pilot has been changed")
    if len({r["place_id"] for r in data}) != 12:
        raise ValueError("Pilot reviews are not from distinct places")
    if sum(r["group"] == "known_failure_review" for r in data) != 6 or (
        sum(r["group"] == "unseen_place_review" for r in data) != 6
    ):
        raise ValueError("The six-plus-six sample composition changed")
    if not all(isinstance(r["text"], str) and r["text"].strip() for r in data):
        raise ValueError("Missing original review text")
    return data


def verify_corpus(sample: list[dict]) -> None:
    original = ROOT / "data/processed/reviews.jsonl"
    catalog = {
        (r["place_id"], r["review_index"]): r["text"]
        for r in (json.loads(line) for line in original.read_text(
            encoding="utf-8").splitlines() if line.strip())
    }
    for r in sample:
        if catalog.get((r["place_id"], r["review_index"])) != r["text"]:
            raise ValueError("Source review differs from collected corpus: " + r["case_id"])


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(
        encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(value, ensure_ascii=False) + "\n")


def write_csv(path: Path, rows: list[dict], *, protect_existing: bool = True) -> None:
    if not rows:
        raise ValueError("No CSV rows")
    if path.exists() and protect_existing:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def request(base: str, endpoint: str, payload: dict | None = None, timeout=600) -> dict:
    body = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        base.rstrip("/") + endpoint, data=body,
        headers={"Content-Type": "application/json"} if body else {},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def installed_digest(base: str, model: str) -> str:
    tags = request(base, "/api/tags", timeout=15).get("models", [])
    for item in tags:
        if item.get("name") == model:
            return item.get("digest", "")
    raise RuntimeError(f"{model} not installed on remote Pod; installed: {[x.get('name') for x in tags]}")


def payload(model: str, review: str) -> dict:
    return {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": json.dumps({"review": review}, ensure_ascii=False)},
        ],
        "format": SCHEMA,
        "stream": False, "think": False,
        "options": {"temperature": 0, "seed": 42, "num_ctx": 8192,
                    "num_predict": 2048},
        "keep_alive": "1m",
    }


def validate(raw: object, source: str) -> dict:
    if not isinstance(raw, dict) or set(raw) != {"evidence", "emotions"}:
        raise ValueError("Response requires evidence and emotions")
    ev, em = raw["evidence"], raw["emotions"]
    if not isinstance(ev, list) or not isinstance(em, list) or len(em) != 3:
        raise ValueError("Missing evidence array or three emotion categories")
    grounded = []
    for row in ev:
        if not isinstance(row, dict) or set(row) != {"quote", "kind", "referent", "reason"}:
            raise ValueError("Malformed evidence fields")
        if not all(isinstance(v, str) for v in row.values()):
            raise ValueError("Non-string evidence value")
        if row["kind"] not in CHANNELS or row["referent"] not in REFERENTS:
            raise ValueError("Invalid evidence channel or referent")
        # Don't silently fix inaccurate quotations or discard bad model claims.
        grounded.append({**row, "source_exact": bool(row["quote"]) and row["quote"] in source})
    categories = []
    for row in em:
        if not isinstance(row, dict) or set(row) != {"category", "verdict", "basis", "reason"}:
            raise ValueError("Malformed emotion fields")
        if row["category"] not in CATEGORIES or row["verdict"] not in VERDICTS:
            raise ValueError("Unknown emotion category or direction")
        if row["basis"] not in BASIS or not isinstance(row["reason"], str):
            raise ValueError("Invalid evidence basis or reason")
        categories.append(row["category"])
    if set(categories) != set(CATEGORIES) or len(set(categories)) != 3:
        raise ValueError("Duplicate or missing categories")
    return {"evidence": grounded,
            "emotions": sorted(em, key=lambda r: CATEGORIES.index(r["category"]))}


def prepare(root: Path, sample: list[dict]) -> Path:
    dest = root / "01_human_reference_FILL_BEFORE_READING_MODEL_OUTPUTS.csv"
    rows = []
    for r in sample:
        row = {"case_id": r["case_id"], "original_review": r["text"],
               "human_direct_claims_with_quotes": "",
               "human_inferred_conditions_with_quotes": "",
               "human_overlap_or_referent_notes": ""}
        for cat in CATEGORIES:
            row[f"human_{cat}_verdict"] = ""
            row[f"human_{cat}_basis"] = ""
            row[f"human_{cat}_notes"] = ""
        row["ambiguities_to_adjudicate"] = ""
        rows.append(row)
    if dest.exists():
        with dest.open(encoding="utf-8-sig", newline="") as f:
            existing = list(csv.DictReader(f))
        if [r["case_id"] for r in existing] != [r["case_id"] for r in rows] or any(
            a["original_review"] != b["original_review"]
            for a, b in zip(existing, rows)
        ):
            raise ValueError("Existing human reference is for different source text")
        return dest
    write_csv(dest, rows)
    return dest


def folder(root: Path, model: str) -> Path:
    return root / model.replace(":", "_").replace("/", "_")


def run(args, sample: list[dict]) -> None:
    digest = installed_digest(args.base, args.model)
    root = folder(args.output, args.model)
    manifest = {
        "version": VERSION,
        "model": args.model,
        "ollama_digest": digest,
        "cases_sha256": sha(sample),
        "prompt_sha256": sha(SYSTEM),
        "schema_sha256": sha(SCHEMA),
        "generation": {"temperature": 0, "seed": 42, "num_ctx": 8192,
                       "num_predict": 2048, "think": False},
    }
    file = root / "manifest.json"
    if file.exists():
        if json.loads(file.read_text(encoding="utf-8")) != manifest:
            raise ValueError("Model/version/source changed. Use a NEW output folder.")
    else:
        if root.exists() and any(root.iterdir()):
            raise ValueError("Results exist without a frozen manifest")
        root.mkdir(parents=True, exist_ok=True)
        file.write_text(json.dumps(manifest, indent=2, ensure_ascii=False),
                        encoding="utf-8")
    passed = {r["case_id"] for r in read_jsonl(root / "predictions.jsonl")}
    failed = {r["case_id"] for r in read_jsonl(root / "errors.jsonl")}
    pool = sample[:args.limit] if args.limit else sample
    pending = [r for r in pool if r["case_id"] not in passed and
               (args.retry_errors or r["case_id"] not in failed)]
    print(f"{args.model}: {len(passed)} validated; {len(pending)} pending",
          flush=True)
    for i, review in enumerate(pending, 1):
        start = time.perf_counter()
        raw, err, timing = "", "", {}
        try:
            reply = request(args.base, "/api/chat",
                            payload(args.model, review["text"]), args.timeout)
            raw = reply.get("message", {}).get("content", "")
            timing = {k: reply.get(k) for k in (
                "total_duration", "load_duration", "prompt_eval_count",
                "prompt_eval_duration", "eval_count", "eval_duration",
                "done_reason")}
            pred = validate(json.loads(raw), review["text"])
        except (OSError, TimeoutError, TypeError, ValueError, KeyError) as e:
            err = f"{type(e).__name__}: {e}"
        elapsed = round(time.perf_counter() - start, 3)
        meta = {"case_id": review["case_id"], "model": args.model,
                "elapsed_seconds": elapsed, "inference": timing}
        write_jsonl(root / "raw_responses.jsonl", {**meta, "raw": raw,
                                                  "error": err or None})
        if err:
            write_jsonl(root / "errors.jsonl", {**meta, "error": err})
        else:
            write_jsonl(root / "predictions.jsonl", {**meta, "result": pred})
        print(f"{i}/{len(pending)} {review['case_id']}: "
              f"{'ERROR '+err[:120] if err else 'OK'} ({elapsed}s)",
              flush=True)


def report(root: Path, sample: list[dict]) -> None:
    prepare(root, sample)
    by_model = {
        model: {r["case_id"]: r for r in read_jsonl(
            folder(root, model) / "predictions.jsonl")}
        for model in MODELS
    }
    blinds, keys = [], []
    for case in sample:
        order = list(MODELS)
        random.Random(20261113 + sum(map(ord, case["case_id"]))).shuffle(order)
        keys.append({"case_id": case["case_id"],
                     "A": order[0], "B": order[1], "C": order[2]})
        row = {"case_id": case["case_id"], "original_review": case["text"]}
        for letter, model in zip(("A", "B", "C"), order):
            obj = by_model[model].get(case["case_id"], {}).get("result")
            row[f"model_{letter}_evidence"] = (
                json.dumps(obj["evidence"], ensure_ascii=False)
                if obj else "")
            row[f"model_{letter}_emotions"] = (
                json.dumps(obj["emotions"], ensure_ascii=False)
                if obj else "")
        row["human_preference_A_B_C_or_tie"] = ""
        row["human_analysis_of_errors"] = ""
        blinds.append(row)
    path = root / "02_blind_models_A_B_C.csv"
    if path.exists():
        with path.open(encoding="utf-8-sig", newline="") as f:
            old = list(csv.DictReader(f))
        if len(old) != len(blinds) or any(
            a["case_id"] != b["case_id"] or a["original_review"] != b["original_review"]
            for a, b in zip(old, blinds)
        ):
            raise ValueError("Cannot overwrite blind assessment with different cases")
        if any(a["human_preference_A_B_C_or_tie"] or a["human_analysis_of_errors"]
               for a in old):
            print(f"Preserving completed human assessment: {path}")
        else:
            write_csv(path, blinds, protect_existing=False)
    else:
        write_csv(path, blinds)
    key = root / "03_blinding_key_KEEP_PRIVATE.json"
    if key.exists():
        if json.loads(key.read_text(encoding="utf-8")) != keys:
            raise ValueError("Blinding key changed")
    else:
        key.write_text(json.dumps(keys, indent=2), encoding="utf-8")
    status = {m: {"valid": len(by_model[m]), "missing": len(sample)-len(by_model[m]),
                  "failed": len(read_jsonl(folder(root, m) / "errors.jsonl"))}
              for m in MODELS}
    (root / "coverage.json").write_text(json.dumps(status, indent=2), encoding="utf-8")
    print(json.dumps(status, indent=2))
    print("Human reference:", root / "01_human_reference_FILL_BEFORE_READING_MODEL_OUTPUTS.csv")
    print("Blind comparison:", path)
    print("No accuracy is reported until independent human adjudication.")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--stage", choices=("prepare", "check", "run", "report"),
                   required=True)
    p.add_argument("--model", choices=MODELS, default=MODELS[0])
    p.add_argument("--base", default="http://127.0.0.1:11434")
    p.add_argument("--output", type=Path, default=OUT)
    p.add_argument("--source", type=Path, default=CASES)
    p.add_argument("--timeout", type=int, default=600)
    p.add_argument("--limit", type=int, default=0)
    p.add_argument("--retry-errors", action="store_true")
    args = p.parse_args()
    if args.timeout <= 0 or args.limit < 0:
        p.error("Invalid timeout or limit")
    sample = cases(args.source)
    verify_corpus(sample)
    if args.stage == "prepare":
        print("Frozen cases:", len(sample), "from", len({x["place_id"] for x in sample}), "places")
        print("Fill before looking at models:", prepare(args.output, sample))
    elif args.stage == "check":
        tags = request(args.base, "/api/tags", timeout=20).get("models", [])
        print("Remote installed Ollama models:",
              [(r.get("name"), r.get("digest")) for r in tags])
    elif args.stage == "run":
        prepare(args.output, sample)
        run(args, sample)
    else:
        report(args.output, sample)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Local two-model, 50-real-review E/T pilot. No semantic truth/accuracy claims.

E = explicit reported atmosphere; T = independent descriptive/indirect inference.
Both read identical source segments, never each other's labels. No Stage 1B images.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import random
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from stage1a_panel_pilot import load_real_reviews, segment_review

VERSION = "stage1a_e_t_independent_50_v1"
CATEGORIES = ("calm", "inviting", "safe")
MODELS = ("qwen3:8b", "gemma3:4b")
TASKS = ("evidence", "inference")
RUBRIC = """CALM: Tranquility, peacefulness, low stimulation and relaxation, versus experienced agitation or disturbance.
INVITING: Welcome, approachability, social comfort or belonging, versus exclusion or hostility.
SAFE: Perceived protection or security, versus danger, vulnerability or threat.
Both tasks use these CATEGORY MEANINGS, but their evidence standards differ. A physical feature does not prove a feeling."""

SYSTEM = {
    "evidence": """You are the EXPLICIT EVIDENCE annotator, NOT an inference model.
Read ONLY the TARGET SEGMENT for evidence; neighbor segments are for reference resolution and negation context only.
Return source-grounded, place-attributed atmosphere statements for calm, inviting, safe.
An explicit report may be first-person (I felt safe) or a direct description of the place's atmosphere (a peaceful park).
If an emotion is only suggested by vegetation, design, amenities, crowds or activities, DO NOT label it.
Keep supports/opposes separate; preserve negation, the target of the description and attribution.
Copy the shortest sufficient EXACT substring of the TARGET SEGMENT into quote; never invent, rewrite or normalize it.
One record per genuinely distinct explicit report and category. Return records: [] when there are none.
Do not attempt to predict how this place might feel. Respond as schema JSON only.""",
    "inference": """You are the DESCRIPTIVE / INDIRECT INFERENCE annotator, NOT an explicit-emotion evidence judge.
Independently read only the TARGET SEGMENT; neighbor segments are only for resolving references and negation.
Extract place-attributed physical, spatial, behavioral, activity, social and sensory descriptions, keeping the original exact quote.
Do NOT use explicit emotion/atmosphere words or subjective feeling reports as the BASIS for observations.
A description may have a cautiously inferred relation to calm, inviting or safe, but inference is HYPOTHESIS, not experienced emotion.
Record category='none', direction='none' when a described fact has no specific defensible atmosphere hypothesis.
Do not infer that trees automatically mean calm, a gate means safe, or positive review sentiment means inviting.
Classify whether the described quality is plausibly visible in a still photo. Noise, smell and transient behavior often are not.
Copy exact substrings of the TARGET SEGMENT, without rewriting; return observations: [] if no non-emotional place description exists.
No access to evidence labels or other model output. Respond as schema JSON only.""",
}

E_FIELDS = {
    "category": {"type": "string", "enum": list(CATEGORIES)},
    "direction": {"type": "string", "enum": ["supports", "opposes"]},
    "quote": {"type": "string"},
    "attribution": {"type": "string", "enum": ["first_person", "general_report", "secondhand", "uncertain"]},
}
T_FIELDS = {
    "quote": {"type": "string"},
    "kind": {"type": "string", "enum": ["physical", "spatial", "activity", "social", "sensory", "access", "other"]},
    "visible_in_photo": {"type": "string", "enum": ["yes", "no", "uncertain"]},
    "category": {"type": "string", "enum": list(CATEGORIES) + ["none"]},
    "direction": {"type": "string", "enum": ["supports", "opposes", "none"]},
    "reason": {"type": "string"},
}


def schema(fields: dict, key: str) -> dict:
    item = {"type": "object", "additionalProperties": False,
            "properties": fields, "required": list(fields)}
    return {"type": "object", "additionalProperties": False,
            "properties": {key: {"type": "array", "items": item}}, "required": [key]}


SCHEMAS = {"evidence": schema(E_FIELDS, "records"),
           "inference": schema(T_FIELDS, "observations")}


def digest(value: object) -> str:
    if isinstance(value, bytes):
        data = value
    elif isinstance(value, str):
        data = value.encode("utf-8")
    else:
        data = json.dumps(value, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def select_reviews(rows: list[dict], n: int, seed: int) -> list[dict]:
    """Unbiased-within-place sampling: one/place first, then seeded remaining reviews."""
    if len(rows) < n:
        raise ValueError(f"Only {len(rows)} real reviews available; requested {n}")
    by_place = collections.defaultdict(list)
    for r in rows:
        by_place[r["place_id"]].append(r)
    rng = random.Random(seed)
    places = sorted(by_place)
    rng.shuffle(places)
    first = [rng.choice(sorted(by_place[p], key=lambda r: r["review_index"])) for p in places]
    selected = first[:n]
    chosen = {(r["place_id"], r["review_index"]) for r in selected}
    remaining = [r for r in rows if (r["place_id"], r["review_index"]) not in chosen]
    rng.shuffle(remaining)
    selected.extend(remaining[:n - len(selected)])
    if len(selected) != n or len({(r["place_id"], r["review_index"]) for r in selected}) != n:
        raise ValueError("Sampling failed to select unique review IDs")
    return selected


def prepare_segments(rows: list[dict]) -> list[dict]:
    result = []
    for review in rows:
        text = review["text"]
        units = segment_review(text)
        for j, u in enumerate(units):
            result.append({
                "review_id": digest([review["place_id"], review["review_index"], text])[:20],
                "place_id": review["place_id"], "review_index": review["review_index"],
                "publish_time": review["publish_time"], "source_sha256": digest(text),
                "segment_id": u["unit_id"], "start": u["start"], "end": u["end"],
                "text": u["text"],
                "previous_segment": units[j - 1]["text"] if j else "",
                "next_segment": units[j + 1]["text"] if j + 1 < len(units) else "",
            })
        if not units:
            raise ValueError("Empty review after segmentation")
    return result


def payload_for(task: str, model: str, segment: dict) -> dict:
    user = {
        "target_segment": segment["text"],
        "previous_segment_for_context_only": segment["previous_segment"],
        "next_segment_for_context_only": segment["next_segment"],
    }
    system = SYSTEM[task] + "\n\nCATEGORY RUBRIC (for consistent interpretation):\n" + RUBRIC
    return {
        "model": model,
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": json.dumps(user, ensure_ascii=False)}],
        "format": SCHEMAS[task], "stream": False,
        "options": {"temperature": 0, "num_ctx": 8192, "num_predict": 1300},
        **({"think": False} if model.lower().startswith("qwen3:") else {}),
    }


def occurrences(text: str, quote: str, start: int) -> list[dict]:
    result, at = [], 0
    while True:
        pos = text.find(quote, at)
        if pos == -1:
            break
        result.append({"start": start + pos, "end": start + pos + len(quote)})
        at = pos + 1
    return result


def validate(task: str, obj: dict, seg: dict) -> list[dict]:
    key, fields = ("records", E_FIELDS) if task == "evidence" else ("observations", T_FIELDS)
    if not isinstance(obj, dict) or set(obj) != {key} or not isinstance(obj[key], list):
        raise ValueError("Invalid task envelope")
    if len(obj[key]) > 20:
        raise ValueError("Too many records for one segment")
    result = []
    for item in obj[key]:
        if not isinstance(item, dict) or set(item) != set(fields):
            raise ValueError("Missing/extra record fields")
        for field, spec in fields.items():
            if not isinstance(item[field], str):
                raise ValueError(f"Non-string field: {field}")
            if "enum" in spec and item[field] not in spec["enum"]:
                raise ValueError(f"Bad {field}: {item[field]}")
        quote = item["quote"]
        if not quote or not quote.strip():
            raise ValueError("Blank quotation")
        spans = occurrences(seg["text"], quote, seg["start"])
        if not spans:
            raise ValueError("Quote is not exact substring of target segment")
        if task == "inference" and ((item["category"] == "none") != (item["direction"] == "none")):
            raise ValueError("Inconsistent none category/direction")
        if task == "inference" and item["category"] != "none" and not item["reason"].strip():
            raise ValueError("Inferred category missing reason")
        result.append({**item, "quote_offsets": spans,
                       "quote_ambiguous": len(spans) > 1})
    return result


def get_json(url: str, timeout: int) -> dict:
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return json.load(resp)


def check_models(base: str, models: tuple[str, ...], timeout: int) -> dict:
    installed = {m.get("name"): m.get("digest") for m in get_json(base.rstrip("/") + "/api/tags", timeout)["models"]}
    missing = [name for name in models if name not in installed]
    if missing:
        raise RuntimeError("Ollama missing models " + ", ".join(missing) + "; run ollama pull <model>")
    return {name: installed[name] for name in models}


def call(base: str, payload: dict, timeout: int) -> tuple[str, dict]:
    request = urllib.request.Request(base.rstrip("/") + "/api/chat",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        outer = json.load(response)
    return outer.get("message", {}).get("content", ""), {
        "done_reason": outer.get("done_reason"), "model": outer.get("model"),
        "prompt_eval_count": outer.get("prompt_eval_count"), "eval_count": outer.get("eval_count"),
    }


def model_slug(model: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]+", "_", model)


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def append_jsonl(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(value, ensure_ascii=False) + "\n")
        f.flush()


def run() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", type=Path, default=ROOT / "data/processed/reviews.jsonl")
    p.add_argument("--output", type=Path, default=ROOT / "reports/stage1a_e_t_50_2026-11-11")
    p.add_argument("--base", default="http://127.0.0.1:11434")
    p.add_argument("--models", nargs=2, default=list(MODELS))
    p.add_argument("--task", choices=["both", *TASKS], default="both")
    p.add_argument("--max-reviews", type=int, default=50)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--timeout", type=int, default=480)
    p.add_argument("--prepare-only", action="store_true")
    p.add_argument("--resume", action="store_true")
    p.add_argument("--limit-segments", type=int, default=0,
                   help="Smoke test only; resume without this flag for full run")
    p.add_argument("--max-errors", type=int, default=12)
    args = p.parse_args()
    if args.max_reviews < 1 or args.max_errors < 1 or args.limit_segments < 0:
        p.error("Invalid count")
    if "fixtures" in args.input.parts or args.input.name != "reviews.jsonl":
        p.error("Use original processed reviews.jsonl, not synthetic fixtures or model labels")
    corpus_sha = digest(args.input.read_bytes())
    reviews = select_reviews(load_real_reviews(args.input, 0), args.max_reviews, args.seed)
    segments = prepare_segments(reviews)
    if len(set([s["review_id"] for s in segments])) != args.max_reviews:
        raise ValueError("Invalid review sample")
    manifest = {"version": VERSION, "input_source_sha256": corpus_sha,
        "sample_seed": args.seed, "n_reviews": len(reviews),
        "n_places": len(set(r["place_id"] for r in reviews)), "n_segments": len(segments),
        "review_keys": [[r["place_id"], r["review_index"], digest(r["text"])] for r in reviews],
        "segment_rows_sha256": digest(segments), "categories": list(CATEGORIES),
        "models": list(args.models), "rubric_sha256": digest(RUBRIC),
        "tasks": {task: {"prompt_sha256": digest(SYSTEM[task]),
                         "schema_sha256": digest(SCHEMAS[task])} for task in TASKS},
        "status": "experiment setup, not validated emotional accuracy"}
    manifest_path = args.output / "input/manifest.json"
    if manifest_path.exists():
        old = json.loads(manifest_path.read_text(encoding="utf-8"))
        if old != manifest:
            raise ValueError("Input/prompt/model manifest changed; use a NEW output directory")
    else:
        if args.resume:
            raise ValueError("Cannot resume without existing manifest")
        write_json(manifest_path, manifest)
    segment_path = args.output / "input/segments.jsonl"
    if segment_path.exists():
        if digest(read_jsonl(segment_path)) != digest(segments):
            raise ValueError("Prepared segments changed; use NEW output directory")
    else:
        with segment_path.open("w", encoding="utf-8") as f:
            for s in segments:
                f.write(json.dumps(s, ensure_ascii=False) + "\n")
    print(f"PREPARED {len(reviews)} real reviews; {manifest['n_places']} places; {len(segments)} segments", flush=True)
    if args.prepare_only:
        print("Prepared source segments only; no LLM predictions made", flush=True)
        return 0
    digests = check_models(args.base, tuple(args.models), min(args.timeout, 30))
    model_path = args.output / "input/model_digests.json"
    if model_path.exists():
        if json.loads(model_path.read_text(encoding="utf-8")) != digests:
            raise ValueError("Ollama model digest changed; use a NEW output directory")
    else:
        write_json(model_path, digests)
    failures = 0
    selected_tasks = TASKS if args.task == "both" else (args.task,)
    for task in selected_tasks:
        for model in args.models:
            out = args.output / task / model_slug(model)
            annotations = out / "annotations.jsonl"
            raw_path = out / "raw_responses.jsonl"
            errors = out / "errors.jsonl"
            if any(p.exists() for p in (annotations, raw_path, errors)) and not args.resume:
                raise ValueError(f"Prior {task}/{model} outputs exist; use --resume or new --output")
            saved = read_jsonl(annotations)
            segment_by_id = {(s["review_id"], s["segment_id"]): s for s in segments}
            done = set()
            for item in saved:
                key = (item["review_id"], item["segment_id"])
                if key in done or key not in segment_by_id or item["source_sha256"] != segment_by_id[key]["source_sha256"]:
                    raise ValueError("Saved completion invalid; do not resume")
                original = segment_by_id[key]
                plain = [{k: value for k, value in entry.items() if k not in ("quote_offsets", "quote_ambiguous")}
                         for entry in item["records"]]
                if validate(task, {"records" if task == "evidence" else "observations": plain}, original) != item["records"]:
                    raise ValueError("Saved annotation source offsets tampered")
                done.add(key)
            pool = segments[:args.limit_segments] if args.limit_segments else segments
            for index, seg in enumerate(pool, 1):
                key = (seg["review_id"], seg["segment_id"])
                if key in done:
                    continue
                request = payload_for(task, model, seg)
                good = False
                for attempt in (1, 2):
                    raw, meta, issue = "", {}, None
                    try:
                        raw, meta = call(args.base, request, args.timeout)
                        parsed = json.loads(raw)
                        records = validate(task, parsed, seg)
                        good = True
                    except (ValueError, TypeError, KeyError, json.JSONDecodeError,
                            urllib.error.URLError, TimeoutError) as error:
                        issue = f"{type(error).__name__}: {error}"
                    append_jsonl(raw_path, {"review_id": seg["review_id"], "segment_id": seg["segment_id"],
                        "attempt": attempt, "raw_content": raw, "metadata": meta, "error": issue,
                        "source_sha256": seg["source_sha256"]})
                    if good:
                        append_jsonl(annotations, {"review_id": seg["review_id"], "segment_id": seg["segment_id"],
                            "place_id": seg["place_id"], "review_index": seg["review_index"],
                            "source_sha256": seg["source_sha256"], "start": seg["start"],
                            "end": seg["end"], "segment_text": seg["text"], "records": records})
                        done.add(key)
                        break
                if not good:
                    failures += 1
                    append_jsonl(errors, {"review_id": seg["review_id"], "segment_id": seg["segment_id"],
                                          "source_sha256": seg["source_sha256"], "error": issue})
                print(f"{task} {model} {index}/{len(pool)} {'OK' if good else 'ERROR'}", flush=True)
                if failures >= args.max_errors:
                    print("ERROR LIMIT reached; inspect raw_responses.jsonl and resume later", file=sys.stderr)
                    return 2
            n_done = sum((s["review_id"], s["segment_id"]) in done for s in segments)
            counts = collections.Counter(rec["category"] for row in read_jsonl(annotations) for rec in row["records"])
            write_json(out / "summary.json", {"task": task, "model": model, "model_digest": digests[model],
                "n_review_input": len(reviews), "n_segments_total": len(segments),
                "n_segments_completed": n_done, "n_segments_remaining": len(segments) - n_done,
                "n_records_by_category": dict(counts),
                "warning": "Model output, NOT independent accuracy or independent E/T corroboration"})
            print(f"SAVED {task}/{model}: {n_done}/{len(segments)} segments", flush=True)
    return 2 if failures else 0


if __name__ == "__main__":
    raise SystemExit(run())

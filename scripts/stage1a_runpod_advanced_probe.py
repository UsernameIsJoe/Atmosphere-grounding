#!/usr/bin/env python3
"""First-pass larger-LLM capacity test on 30 frozen REAL text review segments.

No synthetic evaluation cases, downloads, labels from another model, NLI gate,
or handwavy LLM-as-judge. Uses standard-library Python and Ollama over a
private SSH-tunneled localhost endpoint. Original audit reference judgments
are provisional, never leaked to a model prompt.

Primary: 30 real segments * 2 large BF16 models, identical segment-only task.
Context stress: 10 selected real segments * 2 models, same task + full review.
Each prediction and failure is saved separately, with model digest, prompt
fingerprint, runtime/token metadata, and actual input. A blinded CSV can be
reviewed by a human before seeing model identities.
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
SOURCE = ROOT / "research_audit/stage1a_gate_adj_nli_30_2026-11-12/audit_123_segments.csv"
DEFAULT_OUT = ROOT / "reports/stage1a_runpod_advanced_probe_2026-11-13"
MODELS = ("qwen3.6:27b-bf16", "gemma4:31b-it-bf16")
# Purposive stress test, NOT randomly representative: 10 direct experiential
# statements, 10 indirect environmental descriptions, 5 generic evaluative
# statements and 5 unrelated target fragments. All indices from frozen archive.
FROZEN_INDICES = (0, 2, 3, 9, 10, 12, 14, 18, 21, 24, 25, 26, 27,
                  32, 42, 45, 48, 53, 57, 59, 70, 74, 75, 81, 87,
                  95, 97, 105, 107, 122)
# Review-context stress arm deliberately enriched in earlier leakage and
# context/scope ambiguities. No label score from this arm is a fair comparison
# to a local model unless the prompt and context are matched.
CONTEXT_INDICES = (9, 10, 24, 26, 27, 32, 53, 59, 74, 87)
CATEGORIES = ("calm", "inviting", "safe")
VERDICTS = ("supports", "opposes", "mixed", "none", "uncertain")
ATTRIBUTIONS = ("place", "person", "other", "ambiguous")
PROTOCOL = "advanced_capacity_probe_v1_no_quote"
SYSTEM = """You are annotating what a real visitor says about the experienced
atmosphere of a PLACE. Classify only the TARGET SEGMENT, not the whole review.
For each category (calm, inviting, safe), decide supports/opposes/mixed/none/
uncertain. Each judgment must be justified by the TARGET SEGMENT itself.

Calm is about peacefulness, relaxation, quiet or their opposites.
Inviting is about feeling welcome, approachable or comfortable or their
opposites. Safe is about perceived security and danger or their opposites.

Don't automatically equate a place being beautiful, well-maintained, dirty,
dark, crowded, green or expensive with any specific atmospheric category.
Avoid giving the same verdict to all categories just because a description
is good or bad. Preserve negation. Distinguish the conditions of a place
from a person's behavior, a travel anecdote and a generic recommendation.
Use 'none' when a category is not conveyed by the target. Use 'uncertain'
if the evidence permits plausible opposing readings. Do not invent facts.
Full review (if supplied) resolves references ONLY and cannot contribute
independent evidence to the TARGET SEGMENT. Never use another sentence in
the full review to decide the target's category. Do not provide quotations;
the input text and its source offsets are stored by the program.

Return exactly three JSON ratings, one for each named category, with one
verdict, attribution and concise source-based reason. No other content."""
RATING = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "category": {"type": "string", "enum": list(CATEGORIES)},
        "verdict": {"type": "string", "enum": list(VERDICTS)},
        "attribution": {"type": "string", "enum": list(ATTRIBUTIONS)},
        "reason": {"type": "string"},
    }, "required": ["category", "verdict", "attribution", "reason"],
}
SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {"ratings": {"type": "array", "minItems": 3, "maxItems": 3,
                              "items": RATING}},
    "required": ["ratings"],
}


def digest(value: object) -> str:
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                             separators=(",", ":")).encode("utf-8")).hexdigest()


def corpus(path: Path = SOURCE) -> dict[int, dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        raw = list(csv.DictReader(f))
    if len(raw) != 123:
        raise ValueError("Must use archived 123-segment review sample")
    return {int(row["index"]): row for row in raw}


def selected(rows: dict[int, dict], mode: str) -> list[dict]:
    indices = FROZEN_INDICES if mode == "segment" else CONTEXT_INDICES
    subset = [rows[i] for i in indices]
    if mode == "segment":
        composition = {k: sum(r["screen_class"] == k for r in subset)
                       for k in ("D", "I", "G", "X")}
        if composition != {"D": 10, "I": 10, "G": 5, "X": 5}:
            raise ValueError("Archived source-screening composition changed")
    return subset


def urlopen_json(base: str, endpoint: str, data=None, timeout=240):
    if data is None:
        req = urllib.request.Request(base.rstrip("/") + endpoint)
    else:
        req = urllib.request.Request(base.rstrip("/") + endpoint,
                                     json.dumps(data, ensure_ascii=False).encode("utf-8"),
                                     headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.load(response)


def installed_model(base: str, model: str) -> str:
    tags = urlopen_json(base, "/api/tags", timeout=20)
    match = [m for m in tags.get("models", [])
             if m.get("name") == model or m.get("model") == model]
    if not match:
        found = [m.get("name") for m in tags.get("models", [])]
        raise RuntimeError(f"{model} is not installed on the remote Pod. Installed: {found}")
    return match[0].get("digest", "")


def payload(row: dict, model: str, mode: str) -> dict:
    user = {"target_segment": row["segment"]}
    if mode == "context":
        user["full_review_for_reference_only"] = row["full_review"]
    return {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
        ],
        "format": SCHEMA, "stream": False, "think": False,
        "options": {"temperature": 0, "seed": 42,
                    "num_ctx": 4096, "num_predict": 500},
        "keep_alive": "5m",
    }


def validate(raw: object) -> list[dict]:
    if not isinstance(raw, dict) or set(raw) != {"ratings"}:
        raise ValueError("Wrong JSON object structure")
    ratings = raw["ratings"]
    if not isinstance(ratings, list) or len(ratings) != 3:
        raise ValueError("Exactly three ratings required")
    names = []
    for r in ratings:
        if not isinstance(r, dict) or set(r) != {"category", "verdict", "attribution", "reason"}:
            raise ValueError("Wrong rating fields")
        if r["category"] not in CATEGORIES or r["verdict"] not in VERDICTS:
            raise ValueError("Invalid category or verdict")
        if r["attribution"] not in ATTRIBUTIONS or not isinstance(r["reason"], str):
            raise ValueError("Invalid attribution or reason")
        names.append(r["category"])
    if set(names) != set(CATEGORIES) or len(set(names)) != 3:
        raise ValueError("Missing or duplicate category")
    return sorted(ratings, key=lambda r: CATEGORIES.index(r["category"]))


def read_lines(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()]


def append(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(value, ensure_ascii=False) + "\n")


def model_directory(root: Path, model: str, mode: str) -> Path:
    return root / (model.replace(":", "_").replace("/", "_")) / mode


def run(args) -> None:
    rows = corpus(args.source)
    cases = selected(rows, args.mode)
    expected = {
        "version": PROTOCOL, "sample_sha256": digest([
            (row["review_id"], row["segment_id"], row["segment"], row["full_review"])
            for row in cases]),
        "system_sha256": digest(SYSTEM), "schema_sha256": digest(SCHEMA),
        "model": args.model, "model_digest": installed_model(args.base, args.model),
        "mode": args.mode, "thinking": False, "sampling": {"temperature": 0, "seed": 42},
        "schema_validation": "structure_only_no_literal_quote_gate",
    }
    folder = model_directory(args.output, args.model, args.mode)
    manifest = folder / "manifest.json"
    if manifest.exists():
        if json.loads(manifest.read_text(encoding="utf-8")) != expected:
            raise ValueError("This output belongs to a different model/prompt/corpus digest")
    else:
        if folder.exists() and any(folder.iterdir()):
            raise ValueError("Nonempty result folder is missing immutable manifest")
        folder.mkdir(parents=True, exist_ok=True)
        manifest.write_text(json.dumps(expected, indent=2, ensure_ascii=False),
                            encoding="utf-8")
    completed = {x["index"] for x in read_lines(folder / "results.jsonl")}
    failed = {x["index"] for x in read_lines(folder / "errors.jsonl")}
    attempted = cases[:args.limit] if args.limit else cases
    pending = [r for r in attempted if int(r["index"]) not in completed and
               (args.retry_errors or int(r["index"]) not in failed)]
    print(f"{args.model} / {args.mode}: selected {len(attempted)}, "
          f"already valid {len(completed)}, to call {len(pending)}", flush=True)
    for i, row in enumerate(pending, 1):
        idx = int(row["index"])
        request = payload(row, args.model, args.mode)
        raw, metadata, error = "", {}, ""
        started = time.perf_counter()
        try:
            reply = urlopen_json(args.base, "/api/chat", request, args.timeout)
            raw = reply.get("message", {}).get("content", "")
            metadata = {k: reply.get(k) for k in
                        ("done_reason", "total_duration", "load_duration",
                         "prompt_eval_count", "prompt_eval_duration",
                         "eval_count", "eval_duration")}
            prediction = validate(json.loads(raw))
        except (ValueError, TypeError, KeyError, TimeoutError, OSError) as exc:
            error = f"{type(exc).__name__}: {exc}"
        elapsed = round(time.perf_counter() - started, 3)
        record = {"index": idx, "key": f'{row["review_id"]}:{row["segment_id"]}',
                  "model": args.model, "mode": args.mode, "raw": raw,
                  "duration_seconds": elapsed, "server_metadata": metadata,
                  "error": error or None}
        append(folder / "raw_responses.jsonl", record)
        if error:
            append(folder / "errors.jsonl", {"index": idx, "error": error})
        else:
            append(folder / "results.jsonl",
                   {"index": idx, "key": record["key"],
                    "ratings": prediction, "model": args.model, "mode": args.mode,
                    "duration_seconds": elapsed, "server_metadata": metadata,
                    "source_segment": row["segment"]})
        print(f"{i}/{len(pending)} case {idx}: "
              f"{'ERROR '+error[:110] if error else 'OK'} ({elapsed}s)", flush=True)


def report(args) -> None:
    rows = corpus(args.source)
    out = args.output
    results = {}
    for model in MODELS:
        for mode in ("segment", "context"):
            folder = model_directory(out, model, mode)
            items = read_lines(folder / "results.jsonl")
            results[(model, mode)] = {row["index"]: row for row in items}
    total = []
    for mode in ("segment", "context"):
        for row in selected(rows, mode):
            idx = int(row["index"])
            models = list(MODELS)
            # Per-case label shuffle to prevent a persistent model-A bias.
            random.Random(20261113 + idx + (1000 if mode == "context" else 0)).shuffle(models)
            a, b = (results[(m, mode)].get(idx) for m in models)
            total.append({
                "index": idx, "mode": mode, "target_segment": row["segment"],
                "full_review_for_human_reference": row["full_review"],
                "model_A_verdicts": " | ".join(
                    f"{r['category']}:{r['verdict']} ({r['reason']})"
                    for r in a["ratings"]) if a else "",
                "model_B_verdicts": " | ".join(
                    f"{r['category']}:{r['verdict']} ({r['reason']})"
                    for r in b["ratings"]) if b else "",
                "human_preference_A_B_tie": "",
                "human_notes": "",
            })
    out.mkdir(parents=True, exist_ok=True)
    file = out / "blind_human_comparison.csv"
    with file.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(total[0]))
        writer.writeheader()
        writer.writerows(total)
    summary = {}
    for (model, mode), saved in results.items():
        times = [r["duration_seconds"] for r in saved.values()]
        summary[f"{model}/{mode}"] = {
            "valid": len(saved),
            "planned": len(selected(rows, mode)),
            "mean_seconds_per_valid": round(sum(times)/len(times), 2) if times else None,
        }
    print(json.dumps(summary, indent=2))
    print(f"Human review packet: {file}")
    print("NOTE: Blinded labels are deliberately excluded from this report. "
          "Do not score ambiguous archived labels as ground truth.")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--stage", choices=["check", "run", "report"], default="check")
    p.add_argument("--model", choices=MODELS, default=MODELS[0])
    p.add_argument("--mode", choices=["segment", "context"], default="segment")
    p.add_argument("--base", default="http://127.0.0.1:11434")
    p.add_argument("--source", type=Path, default=SOURCE)
    p.add_argument("--output", type=Path, default=DEFAULT_OUT)
    p.add_argument("--timeout", type=int, default=300)
    p.add_argument("--limit", type=int, default=0, help="Small initial smoke test")
    p.add_argument("--retry-errors", action="store_true")
    args = p.parse_args()
    if args.limit < 0 or args.timeout < 1:
        p.error("Invalid arguments")
    if args.stage == "check":
        print("Source segments:", len(corpus(args.source)))
        print("Pilot composition:", {k: sum(r["screen_class"] == k
              for r in selected(corpus(args.source), "segment"))
              for k in ("D", "I", "G", "X")})
        print("Installed Ollama models:", [m["name"] for m in
              urlopen_json(args.base, "/api/tags", timeout=20)["models"]])
    elif args.stage == "run":
        run(args)
    else:
        report(args)


if __name__ == "__main__":
    main()

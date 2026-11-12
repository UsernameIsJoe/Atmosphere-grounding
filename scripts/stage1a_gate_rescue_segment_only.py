#!/usr/bin/env python3
"""Targeted Gemma recovery: classify only V2-missing segments, WITHOUT full-review context.

A diagnostic complement to the 30-review gate experiment, not a replacement
for the original (same-prompt) Qwen/Gemma comparison. Preserve original
V2 model files; write new, clearly identified segment-only outputs.

No model-produced quotation is requested. Source grounding is the original,
literal target segment (and its original character offsets), not a generated
quote. This eliminates quote-copy and cross-segment context-leakage errors
without asserting that category judgments are accurate.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from stage1a_gate_adj_nli_30 import (
    CATEGORIES, ProgressBar, append_jsonl, key, ollama_call,
    read_jsonl, sha, write_json,
)

MODEL = "gemma3:4b"
VERSION = "gemma_segment_only_rescue_v1"
SYSTEM = """Read only the TARGET_SEGMENT from an authentic visitor review.
Evaluate what THIS SEGMENT conveys about how the place feels to visitors.
There is NO full review supplied; do not invent surrounding context.

For EACH of the three categories, return one verdict:
calm: peaceful/quiet/relaxing versus disruptive/stressful/noisy;
inviting: welcoming/approachable/comfortable versus excluding/unwelcoming;
safe: secure/protected vs hazardous/unsafe/threatening.
Verdicts are supports, opposes, mixed, none, or uncertain.

Judge only the meaning of the target text. Do not automatically convert
generic praise, greenery, activities, maintenance, darkness or cleanliness
into particular feelings. Be careful about whether descriptions concern
the place or a person. If a category is not described or defensibly
implicated, return none. If ambiguity prevents a confident judgment,
return uncertain. Preserve negation and do not infer missing information.

Do NOT create, copy, or paraphrase any source quotation. The exact
target segment is already stored as the evidence unit by the software;
your task is classification only. Supply a short rationale for each row.
Return only the required JSON object with exactly three rows."""

FIELDS = {
    "category": {"type": "string", "enum": list(CATEGORIES)},
    "verdict": {"type": "string",
                "enum": ["supports", "opposes", "mixed", "none", "uncertain"]},
    "attribution": {"type": "string", "enum": ["place", "person", "other", "ambiguous"]},
    "reason": {"type": "string"},
}
SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {"ratings": {"type": "array", "minItems": 3, "maxItems": 3,
                              "items": {"type": "object", "additionalProperties": False,
                                        "properties": FIELDS, "required": list(FIELDS)}}},
    "required": ["ratings"],
}


def keyed(rows: list[dict], allowed: set[str]) -> dict[str, dict]:
    out = {}
    for row in rows:
        k = row["key"]
        if k not in allowed:
            raise ValueError("Saved output contains an unknown source segment: " + k)
        if k in out:
            raise ValueError("Duplicate successful rating for segment: " + k)
        out[k] = row
    return out


def check_gemma(base: str, timeout: int) -> str:
    with urllib.request.urlopen(base.rstrip("/") + "/api/tags", timeout=min(20, timeout)) as f:
        installed = json.load(f).get("models", [])
    match = [m for m in installed if m.get("name") == MODEL]
    if not match:
        raise RuntimeError(f"Model {MODEL} is not installed in Ollama.")
    return str(match[0].get("digest") or "unknown")


def payload(segment: dict, feedback: str = "") -> dict:
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": json.dumps({"target_segment": segment["segment"]},
                                                ensure_ascii=False)},
    ]
    if feedback:
        messages.append({"role": "user", "content": feedback})
    return {"model": MODEL, "messages": messages, "format": SCHEMA, "stream": False,
            "options": {"temperature": 0, "num_ctx": 4096, "num_predict": 900}}


def validate(body: object) -> list[dict]:
    if not isinstance(body, dict) or set(body) != {"ratings"}:
        raise ValueError("Output must contain only ratings")
    ratings = body["ratings"]
    if not isinstance(ratings, list) or len(ratings) != len(CATEGORIES):
        raise ValueError("Expected exactly three category ratings")
    seen = set()
    for r in ratings:
        if not isinstance(r, dict) or set(r) != set(FIELDS):
            raise ValueError("Missing/extra rating fields")
        for field, spec in FIELDS.items():
            if not isinstance(r[field], str):
                raise ValueError("Non-string field: " + field)
            if "enum" in spec and r[field] not in spec["enum"]:
                raise ValueError(f"Invalid {field}: {r[field]}")
        seen.add(r["category"])
    if seen != set(CATEGORIES):
        raise ValueError("Missing/duplicate category")
    return sorted(ratings, key=lambda r: CATEGORIES.index(r["category"]))


def read_state(root: Path) -> tuple[list[dict], dict[str, dict], dict[str, dict], dict[str, dict]]:
    segment_path = root / "input/segments.jsonl"
    if not segment_path.exists():
        raise RuntimeError("Original 30-review input not found. Run the original preparation first.")
    units = read_jsonl(segment_path)
    if not units:
        raise RuntimeError("Original segment sample is empty.")
    allowed = {key(u) for u in units}
    if len(allowed) != len(units):
        raise ValueError("Duplicate original source segments")
    for u in units:
        if u["full_review"][u["start"]:u["end"]] != u["segment"]:
            raise ValueError("Source offset mismatch: " + key(u))
    qwen = keyed(read_jsonl(root / "llm_v2/qwen3_8b/ratings.jsonl"), allowed)
    gemma = keyed(read_jsonl(root / "llm_v2/gemma3_4b/ratings.jsonl"), allowed)
    return units, qwen, gemma, {key(u): u for u in units}


def create_manifest(out: Path, units: list[dict], digest: str) -> None:
    expected = {"version": VERSION, "model": MODEL, "model_digest": digest,
                "source_segments_sha256": sha(units), "system_sha256": sha(SYSTEM),
                "schema_sha256": sha(SCHEMA),
                "policy": "only V2 missing segments; segment-only input; no model quote; 2 attempts"}
    path = out / "manifest.json"
    if path.exists():
        if json.loads(path.read_text(encoding="utf-8")) != expected:
            raise ValueError("Recovery protocol changed; use a separate output directory.")
    elif out.exists() and any(out.iterdir()):
        raise ValueError("Recovery output exists without manifest. Use a fresh directory.")
    else:
        write_json(path, expected)


def output_status(root: Path, out: Path) -> dict:
    units, qwen, gemma, lookup = read_state(root)
    allowed = set(lookup)
    rescue = keyed(read_jsonl(out / "ratings.jsonl"), allowed)
    # Gemma V2 remains preferred: rescue is used only for V2-missing cases.
    candidates = {k: v for k, v in rescue.items() if k not in gemma}
    gate_adj = keyed(read_jsonl(root / "gates/pos.jsonl"), allowed)
    gates_nli = {model: keyed(read_jsonl(root / f"gates/nli_{model}.jsonl"), allowed)
                 for model in ("bart", "deberta", "modernbert")}
    output_rows = []
    for u in units:
        k = key(u)
        gemma_v2 = gemma.get(k)
        gemma_recovered = candidates.get(k)
        chosen = gemma_v2 or gemma_recovered
        route = ("v2_full_review" if gemma_v2 else
                 "segment_only_rescue" if gemma_recovered else "unresolved")
        output_rows.append({
            "key": k, "place_id": u["place_id"], "review_index": u["review_index"],
            "target_segment": u["segment"],
            "adjective": gate_adj.get(k, {}).get("adjective_present", ""),
            "nli_bart": gates_nli["bart"].get(k, {}).get("mean_entailment", ""),
            "nli_deberta": gates_nli["deberta"].get(k, {}).get("mean_entailment", ""),
            "nli_modernbert": gates_nli["modernbert"].get(k, {}).get("mean_entailment", ""),
            "qwen_v2_available": k in qwen, "gemma_protocol": route,
            "gemma_available": chosen is not None,
            "gemma_verdicts": (" | ".join(
                f"{r['category']}:{r['verdict']}" for r in chosen["ratings"]) if chosen else ""),
            "qwen_v2_verdicts": (" | ".join(
                f"{r['category']}:{r['verdict']}" for r in qwen[k]["ratings"]) if k in qwen else ""),
            "same_protocol_comparison": (k in qwen and k in gemma),
        })
    out.mkdir(parents=True, exist_ok=True)
    with (out / "comparison_with_recovery.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(output_rows[0]))
        writer.writeheader()
        writer.writerows(output_rows)
    status = {
        "sampled_segments": len(units),
        "qwen_v2_valid": len(qwen),
        "gemma_v2_valid": len(gemma),
        "gemma_segment_only_recovered": len(candidates),
        "gemma_total_available_mixed_protocol": len(gemma) + len(candidates),
        "gemma_still_unresolved": len(units) - len(gemma) - len(candidates),
        "same_protocol_Qwen_Gemma_comparisons": sum(
            k in gemma and k in qwen for k in lookup),
        "methodology": ("Segment-only recovery is a DIFFERENT protocol. "
                        "Do not treat fallback rows as the same prompt/context "
                        "as full-review V2 rows. No model-generated quotes; "
                        "the exact target segment is the source evidence unit."),
    }
    write_json(out / "summary.json", status)
    print("COVERAGE " + json.dumps(status, ensure_ascii=False), flush=True)
    return status


def run(args) -> dict:
    root = args.root
    units, qwen, gemma, lookup = read_state(root)
    out = args.output or root / "llm_segment_only_rescue_gemma_v1"
    digest = check_gemma(args.base, args.timeout)
    create_manifest(out, units, digest)
    allowed = set(lookup)
    recovered = keyed(read_jsonl(out / "ratings.jsonl"), allowed)
    errors = read_jsonl(out / "errors.jsonl")
    failed_before = {x["key"] for x in errors}
    # A prior failure is not automatically retried each time. Opt in explicitly.
    pending = [u for u in units if key(u) not in gemma]
    if args.limit > 0:
        pending = pending[:args.limit]
    n_done = sum(key(u) in recovered or
                 (not args.retry_errors and key(u) in failed_before) for u in pending)
    progress = ProgressBar("Gemma segment-only", len(pending), n_done)
    failures = 0
    for unit in pending:
        k = key(unit)
        if k in recovered or (k in failed_before and not args.retry_errors):
            continue
        succeeded, error = False, ""
        for attempt in (1, 2):
            started = time.perf_counter()
            raw, metadata = "", {}
            try:
                raw, metadata = ollama_call(args.base, payload(unit, error if attempt == 2 else ""),
                                           args.timeout)
                ratings = validate(json.loads(raw))
                succeeded = True
                error = ""
            except (ValueError, KeyError, TypeError, TimeoutError, OSError) as exc:
                error = f"{type(exc).__name__}: {exc}"
            append_jsonl(out / "raw_responses.jsonl", {
                "key": k, "attempt": attempt, "raw": raw, "metadata": metadata,
                "error": error or None, "duration_s": round(time.perf_counter() - started, 4)})
            if succeeded:
                append_jsonl(out / "ratings.jsonl", {
                    "key": k, "model": MODEL, "protocol": VERSION,
                    "ratings": ratings, "source_segment": unit["segment"],
                    "source_offsets": {"start": unit["start"], "end": unit["end"]},
                    "source_sha256": sha(unit["segment"]),
                    "evidence_scope": "whole_original_target_segment",
                    "extracted_phrases": "not_requested",
                })
                recovered[k] = True
                break
        if not succeeded:
            append_jsonl(out / "errors.jsonl", {"key": k, "error": error})
            failures += 1
            print(f"\nGemma rescue unresolved {k}: {error[:200]}", flush=True)
        n_done += 1
        progress.update(n_done, failures)
    return output_status(root, out)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path,
                   default=ROOT / "reports/stage1a_gate_adj_nli_30_2026-11-12")
    p.add_argument("--output", type=Path, default=None)
    p.add_argument("--base", default="http://127.0.0.1:11434")
    p.add_argument("--timeout", type=int, default=480)
    p.add_argument("--limit", type=int, default=0, help="Smoke test first N missing segments; 0=all")
    p.add_argument("--retry-errors", action="store_true",
                   help="Explicitly retry previously logged rescue failures")
    p.add_argument("--report-only", action="store_true",
                   help="Regenerate comparison and coverage without any model call")
    args = p.parse_args()
    if args.timeout < 1 or args.limit < 0:
        p.error("Invalid timeout/limit")
    if args.report_only:
        output_status(args.root, args.output or args.root / "llm_segment_only_rescue_gemma_v1")
    else:
        run(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

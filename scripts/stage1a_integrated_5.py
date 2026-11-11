#!/usr/bin/env python3
"""Stage 1A: five real reviews, extraction -> independent direction verification.

Cost-aware integration trial: reuse the 120 saved evidence-first outputs as the
extraction stage. The previous relevance labels are never shown to the
direction classifier. No new extraction inference is performed in this trial.
This is a REPLAY of Stage 1, not proof that extraction is direction-neutral.
"""
from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path

from stage1a_panel_pilot import sha256
from stage1a_evidence_first_5 import (
    PILOT, frozen_reviews, read_jsonl, append_jsonl, validate_answer,
)
from stage1a_direction_2 import request as classify_direction, validate_result, PROMPT as DIRECTION_PROMPT

ROOT = Path(__file__).resolve().parents[1]
EMOTIONS = tuple(PILOT)
DIRECTIONS = ("supports", "opposes", "neither", "ambiguous")


def load_extractions(source: Path, reviews: list[dict],
                     models: list[str]) -> list[dict]:
    """Verify exactly one saved Stage 1 result for every model/clauses/emotion.

    This does NOT use or trust the original relevance as the Stage 2 decision.
    It preserves original labels for analysis of direction errors.
    """
    raw = read_jsonl(source)
    expected = {(r["place_id"], r["review_index"], u["unit_id"], e, m)
                for r in reviews for u in r["units"] for e in EMOTIONS for m in models}
    known = {(r["place_id"], r["review_index"]): r for r in reviews}
    found = {}
    for r in raw:
        key = (r["place_id"], r["review_index"], r["unit_id"], r["emotion"], r["model"])
        if key not in expected or key in found:
            raise ValueError(f"Unexpected or duplicate Stage 1 extraction: {key}")
        original = known[(key[0], key[1])]
        unit = next((u for u in original["units"] if u["unit_id"] == key[2]), None)
        if unit is None or r["source_sha256"] != original["source_sha256"] or r["clause"] != unit["text"]:
            raise ValueError(f"Stage 1 source provenance mismatch: {key}")
        validated = validate_answer({k: r[k] for k in ("rationale", "evidence_span", "relevance")},
                                    unit["text"])
        if validated["evidence_span"] != r["evidence_span"]:
            raise ValueError(f"Stage 1 original quote mismatch: {key}")
        if r["evidence_span"] and r["evidence_span"] not in unit["text"]:
            raise ValueError(f"Evidence span is not in original clause: {key}")
        found[key] = dict(r)
    if set(found) != expected:
        raise ValueError(f"Stage 1 extraction incomplete: {len(expected - set(found))} missing")
    return [found[k] for k in sorted(expected)]


def direction_job(item: dict) -> bool:
    """Even a neutral/uncertain Stage 1 label may contain quoted evidence."""
    return bool(item["evidence_span"])


def reconstruct(item: dict, direction: str | None) -> dict:
    if not direction_job(item):
        label = "uncertain" if item["relevance"] == "uncertain" else "not_relevant"
    else:
        if direction is None:
            raise ValueError("Missing direction for a quoted evidence candidate")
        if direction not in DIRECTIONS:
            raise ValueError("Invalid direction")
        label = {"neither": "not_relevant", "ambiguous": "uncertain"}.get(direction, direction)
    return {k: item[k] for k in ("place_id", "review_index", "unit_id", "emotion",
                                "model", "source_sha256", "clause", "evidence_span")} | {
        "stage1_relevance": item["relevance"], "stage1_rationale": item["rationale"],
        "direction": direction, "final_relevance": label,
    }


def run() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "data/processed/reviews.jsonl")
    parser.add_argument("--config", type=Path, default=ROOT / "configs/stage1a_evidence_first_5.json")
    parser.add_argument("--source-annotations", type=Path,
                        default=ROOT / "reports/stage1a_evidence_first_5/annotations.jsonl")
    parser.add_argument("--output", type=Path, default=ROOT / "reports/stage1a_integrated_5")
    parser.add_argument("--models", nargs=2, default=["qwen3:8b", "gemma3:4b"])
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--timeout", type=int, default=480)
    parser.add_argument("--ollama-url", default="http://localhost:11434")
    args = parser.parse_args()
    if len(set(args.models)) != 2:
        parser.error("Two distinct models required")
    reviews, _ = frozen_reviews(args.input, args.config)
    items = load_extractions(args.source_annotations, reviews, args.models)
    jobs = [r for r in items if direction_job(r)]
    print(f"VERIFIED {len(reviews)} real reviews, {sum(len(x['units']) for x in reviews)} clauses, "
          f"{len(items)} existing Stage 1 annotations, {len(jobs)} direction calls; "
          "zero new extraction calls.", flush=True)
    if args.prepare_only:
        by_model = collections.Counter(r["model"] for r in jobs)
        print("Direction jobs by model:", dict(sorted(by_model.items())))
        for r in items:
            if not direction_job(r):
                print("NO SPAN", r["place_id"], r["unit_id"], r["emotion"],
                      r["model"], r["relevance"])
        return

    args.output.mkdir(parents=True, exist_ok=True)
    manifest = {
        "version": "stage1a_integrated_5_replay_v1",
        "models": args.models,
        "source_hashes": {r["place_id"]: r["source_sha256"] for r in reviews},
        "n_stage1": len(items), "n_direction_jobs": len(jobs),
        "stage1_source_sha256": sha256(args.source_annotations.read_text(encoding="utf-8")),
        "direction_prompt_sha256": sha256(DIRECTION_PROMPT),
        "items_sha256": sha256(json.dumps(items, sort_keys=True, ensure_ascii=False)),
        "mode": "replayed_existing_extraction",
    }
    manifest_path = args.output / "manifest.json"
    if manifest_path.exists():
        if json.loads(manifest_path.read_text(encoding="utf-8")) != manifest:
            raise ValueError("Cannot resume: manifest/input differs")
    else:
        if (args.output / "direction_annotations.jsonl").exists():
            raise ValueError("Found saved annotations without a verified manifest")
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    lookup = {(r["place_id"], r["review_index"], r["unit_id"], r["emotion"], r["model"]): r
              for r in items}
    previous = read_jsonl(args.output / "direction_annotations.jsonl")
    complete = {}
    for saved in previous:
        key = (saved["place_id"], saved["review_index"], saved["unit_id"],
               saved["emotion"], saved["model"])
        if key not in lookup or key in complete or not direction_job(lookup[key]):
            raise ValueError("Unexpected or duplicate Stage 2 saved item")
        item = lookup[key]
        if (saved["source_sha256"] != item["source_sha256"]
                or saved["evidence_span"] != item["evidence_span"]):
            raise ValueError("Stage 2 saved result/source mismatch")
        validate_result({k: saved[k] for k in ("reason", "direction")})
        complete[key] = saved

    for item in jobs:
        key = (item["place_id"], item["review_index"], item["unit_id"],
               item["emotion"], item["model"])
        if key in complete:
            continue
        # Stage 2 never receives the prior classification or rationale.
        direction_input = {"emotion": item["emotion"], "clause": item["clause"],
                           "evidence_span": item["evidence_span"]}
        for attempt in (1, 2):
            trace = {"key": key, "attempt": attempt}
            try:
                raw = classify_direction(args.ollama_url, item["model"], direction_input, args.timeout)
                trace.update(raw)
                try:
                    parsed = json.loads(raw["raw_content"])
                    trace["intended"] = parsed
                    verdict = validate_result(parsed)
                    trace["validation"] = "valid"
                    append_jsonl(args.output / "raw_responses.jsonl", trace)
                    saved = {k: item[k] for k in ("place_id", "review_index", "unit_id",
                            "emotion", "model", "source_sha256", "evidence_span")} | verdict
                    append_jsonl(args.output / "direction_annotations.jsonl", saved)
                    complete[key] = saved
                    print("OK", item["model"], item["unit_id"], item["emotion"],
                          verdict["direction"], flush=True)
                    break
                except (ValueError, KeyError, TypeError) as exc:
                    trace["validation"] = "invalid"
                    trace["error"] = str(exc)
                    append_jsonl(args.output / "raw_responses.jsonl", trace)
            except (OSError, ValueError) as exc:
                trace["validation"] = "request_error"
                trace["error"] = str(exc)
                append_jsonl(args.output / "raw_responses.jsonl", trace)
        else:
            print("FAILED", item["model"], item["unit_id"], item["emotion"], flush=True)

    final = []
    for item in items:
        key = (item["place_id"], item["review_index"], item["unit_id"],
               item["emotion"], item["model"])
        if direction_job(item) and key not in complete:
            continue
        dir_label = complete[key]["direction"] if key in complete else None
        rec = reconstruct(item, dir_label)
        if key in complete:
            rec["direction_reason"] = complete[key]["reason"]
        final.append(rec)
    final_path = args.output / "integrated_annotations.jsonl"
    final_path.write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in final), encoding="utf-8")
    agreement = collections.Counter()
    group = collections.defaultdict(dict)
    for r in final:
        group[(r["place_id"], r["review_index"], r["unit_id"], r["emotion"])][r["model"]] = r["final_relevance"]
    for votes in group.values():
        if len(votes) == 2:
            agreement["both_present"] += 1
            if len(set(votes.values())) == 1:
                agreement["same_label"] += 1
    diagnostics = {
        "expected": len(items), "completed": len(final), "direction_calls_expected": len(jobs),
        "direction_calls_completed": len(complete), "missing_direction_calls": len(jobs) - len(complete),
        "stage1_labels": {m: dict(collections.Counter(r["relevance"] for r in items if r["model"] == m))
                          for m in args.models},
        "final_labels": {m: dict(collections.Counter(r["final_relevance"] for r in final if r["model"] == m))
                         for m in args.models},
        "inter_model_agreement": dict(agreement),
        "note": "Replays existing stage1 span proposals; agreement is not accuracy. Stage1 can be overinclusive.",
    }
    (args.output / "diagnostics.json").write_text(json.dumps(diagnostics, indent=2) + "\n", encoding="utf-8")
    print(f"FINISHED {len(final)}/{len(items)} integrated judgments; "
          f"{len(complete)}/{len(jobs)} direction calls.", flush=True)


if __name__ == "__main__":
    run()

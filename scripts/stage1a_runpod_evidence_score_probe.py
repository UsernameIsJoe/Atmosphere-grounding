#!/usr/bin/env python3
"""Runpod advanced-LLM probe V2: independent evidence detection and emotion scoring.

Data: 30 frozen authentic review segments from the archived 123-row source audit
(+ a separate 10-segment context stress arm). No generated evaluation text.

Each large model is evaluated INDEPENDENTLY on TWO tasks:
  evidence: extract literal textual claims and tag direct, inference, or both.
  scoring: independently score calm/inviting/safe for DIRECT vs INFERRED
           evidence, without being shown task-A model outputs.

Human gold packet can be filled before looking at model outputs; blind model
packets and reversible private key allow fair post-run adjudication.

Use through SSH tunnel to private Runpod Ollama. No local ML dependencies.
No semantic post-processing of predictions; false unsupported quotes are logged
as their own provenance error, not silently turned into valid claims.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import random
import sys
import time
from collections import Counter

sys.path.insert(0, str(Path(__file__).resolve().parent))
from stage1a_runpod_advanced_probe import (
    MODELS, SOURCE, corpus, selected, digest, urlopen_json, installed_model,
    read_lines, append,
)

TASKS = ("evidence", "score")
BASELINE_MODELS = ("qwen3:8b",)
AVAILABLE_MODELS = MODELS + BASELINE_MODELS
CHANNELS = ("direct", "inference", "both")
REFERENTS = ("place", "surroundings", "person", "other", "ambiguous")
CATEGORIES = ("calm", "inviting", "safe")
VERDICTS = ("supports", "opposes", "mixed", "none", "uncertain")
DEFAULT_OUT = Path(__file__).resolve().parents[1] / "reports/stage1a_runpod_evidence_score_v2_2026-11-13"
VERSION = "advanced_evidence_score_v2_2026_11_13"

CORE_RULES = """Analyze the precise TARGET_SEGMENT of an authentic place review.
Only the TARGET_SEGMENT may supply evidence. If a full review is provided, it
may clarify pronouns or context but its other sentences cannot contribute
claims, source quotes, or emotion scores.

An explicit/direct atmosphere claim is the author's ACTUAL assertion about a
felt or described experiential quality: e.g. directly calling a place peaceful,
welcoming, dangerous; reporting feeling relaxed; or explicitly asserting a
relevant condition (e.g. surroundings were quiet, an animal is harmless).
Direct need not be first person. Record the precise referent: nearby
neighborhood, person, chickens, etc. are NOT automatically the entire place.

An inferred/indirect condition is a stated factual or observational
description of physical, sensory, activity, social or access circumstances from
which a reader might HYPOTHESIZE an atmosphere, without the author actually
claiming that emotion. A statement may contain BOTH direct quality and
descriptive condition, so do not force a binary E-versus-T choice.

NEVER automatically convert generic praise, beauty, price, cleanliness,
amenities, greenery, graffito, darkness, or popularity into calm, inviting or
safe. Preserve grammatical negation and scope. Respect that a preference for
a meditative walk does not directly assert that the park is calm.

Avoid inventing missing information, overreading a short fragment, turning
a person's character into a property of the place, or copying sentiment
from a different sentence in the full review. Report uncertainty where needed."""

EVIDENCE_SYSTEM = CORE_RULES + """

TASK A: Locate source-supported claims, WITHOUT EMOTION SCORING.
Return a list of all relevant source-claim records in TARGET_SEGMENT.
For each record, give a verbatim contiguous substring from TARGET_SEGMENT
as source_quote (keep relevant negation and qualifiers); evidence_type is
direct, inference or both. Record referent and why it belongs in that class.
Do not emit records for unrelated logistics or generic compliments that have
no defensible experiential/scene information. Empty list is correct.
Do not assign calm/inviting/safe or their polarities. You may include more
than one record for a sentence, but avoid redundant duplicate claims.
The model's copied quotation will be checked mechanically and independently:
a mismatch must not be disguised as a correct quotation."""

SCORE_SYSTEM = CORE_RULES + """

TASK B: Independently judge the three named atmospheric emotions.
Do NOT read evidence-extraction output, NLI results or another model's labels.
For each emotion, return TWO INDEPENDENT potential assessments:
DIRECT: what the reviewer explicitly reports as an atmosphere/experience.
INFERENCE: what is defensibly HYPOTHESIZED from described conditions alone.
The same emotion can have both direct and inference support, or neither.
Do not turn every observed physical object into a subjective mood.

Each assessment MUST include:
- verdict: supports / opposes / mixed / none / uncertain
- signed_score: integer -2,-1,0,1,2
  +2 strong textual evidence for category, +1 moderate support;
  -1 moderate opposition, -2 strong opposition;
  0 for mixed/none/uncertain (these are DISTINGUISHED by verdict).
  This is an ORDINAL textual support scale, NOT a probability of how
  actual visitors feel or a place-level aggregation score.
- concise reason grounded in TARGET_SEGMENT alone.
For supports/ opposes, signed_score sign must match verdict.
For mixed/none/uncertain, signed_score must be 0.
When evidence is absent, verdict=none and signed_score=0.
Be especially cautious on safe vs inviting vs calm: one negative word does
not imply all three. The channel refers to justification type, NOT whether
the original text is generally positive or negative.
Do not provide model-generated source quotations."""

EVIDENCE_ITEM = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "source_quote": {"type": "string"},
        "evidence_type": {"type": "string", "enum": list(CHANNELS)},
        "referent": {"type": "string", "enum": list(REFERENTS)},
        "reason": {"type": "string"},
    }, "required": ["source_quote", "evidence_type", "referent", "reason"],
}
EVIDENCE_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {"claims": {"type": "array", "items": EVIDENCE_ITEM}},
    "required": ["claims"],
}
SCORE_ITEM = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "verdict": {"type": "string", "enum": list(VERDICTS)},
        "signed_score": {"type": "integer", "minimum": -2, "maximum": 2},
        "reason": {"type": "string"},
    }, "required": ["verdict", "signed_score", "reason"],
}
SCORE_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {"ratings": {
        "type": "array", "minItems": 3, "maxItems": 3,
        "items": {
            "type": "object", "additionalProperties": False,
            "properties": {
                "category": {"type": "string", "enum": list(CATEGORIES)},
                "direct": SCORE_ITEM, "inference": SCORE_ITEM,
            },
            "required": ["category", "direct", "inference"],
        },
    }},
    "required": ["ratings"],
}
SCHEMAS = {"evidence": EVIDENCE_SCHEMA, "score": SCORE_SCHEMA}
SYSTEMS = {"evidence": EVIDENCE_SYSTEM, "score": SCORE_SYSTEM}


def request_payload(row: dict, model: str, mode: str, task: str) -> dict:
    data = {"target_segment": row["segment"]}
    if mode == "context":
        data["full_review_for_reference_only"] = row["full_review"]
    return {
        "model": model, "messages": [
            {"role": "system", "content": SYSTEMS[task]},
            {"role": "user", "content": json.dumps(data, ensure_ascii=False)},
        ],
        "format": SCHEMAS[task], "stream": False, "think": False,
        "options": {"temperature": 0, "seed": 42,
                    "num_ctx": 4096, "num_predict": 1050},
        "keep_alive": "5m",
    }


def validate_evidence(payload: object, segment: str) -> dict:
    if not isinstance(payload, dict) or set(payload) != {"claims"} or not isinstance(payload["claims"], list):
        raise ValueError("Expected only list-valued 'claims'")
    output = []
    for item in payload["claims"]:
        if not isinstance(item, dict) or set(item) != set(EVIDENCE_ITEM["properties"]):
            raise ValueError("Malformed evidence claim fields")
        if not all(isinstance(x, str) for x in item.values()):
            raise ValueError("Claim fields must be strings")
        if item["evidence_type"] not in CHANNELS or item["referent"] not in REFERENTS:
            raise ValueError("Unknown evidence type or referent")
        quote = item["source_quote"]
        if not quote:
            raise ValueError("Evidence record has empty quote")
        # Do NOT fix, delete or repair model mistakes. Keep raw quote and
        # explicit grounding diagnostic for transparent human review.
        output.append({**item, "source_exact": quote in segment,
                       "source_occurrences": segment.count(quote)})
    return {"claims": output}


def validate_score(payload: object) -> dict:
    if not isinstance(payload, dict) or set(payload) != {"ratings"} or not isinstance(payload["ratings"], list):
        raise ValueError("Expected only list-valued 'ratings'")
    if len(payload["ratings"]) != 3:
        raise ValueError("Three emotion category rows required")
    got = set()
    output = []
    for entry in payload["ratings"]:
        if not isinstance(entry, dict) or set(entry) != {"category", "direct", "inference"}:
            raise ValueError("Malformed category row")
        c = entry["category"]
        if c not in CATEGORIES or c in got:
            raise ValueError("Invalid or duplicated emotion category")
        got.add(c)
        for channel in ("direct", "inference"):
            item = entry[channel]
            if not isinstance(item, dict) or set(item) != set(SCORE_ITEM["properties"]):
                raise ValueError(f"Malformed {channel} assessment")
            v, n = item["verdict"], item["signed_score"]
            if v not in VERDICTS or type(n) is not int or not -2 <= n <= 2:
                raise ValueError("Invalid score type, verdict or score bounds")
            if not isinstance(item["reason"], str):
                raise ValueError("Score rationale must be a string")
            if ((v == "supports" and n <= 0) or
                (v == "opposes" and n >= 0) or
                (v in ("mixed", "none", "uncertain") and n != 0)):
                raise ValueError(f"Inconsistent {channel} verdict and signed_score")
        output.append(entry)
    if got != set(CATEGORIES):
        raise ValueError("Missing emotion category")
    return {"ratings": sorted(output, key=lambda v: CATEGORIES.index(v["category"]))}


def folder_for(output: Path, model: str, mode: str, task: str) -> Path:
    return output / model.replace(":", "_").replace("/", "_") / mode / task


def run(args) -> None:
    all_rows = corpus(args.source)
    cases = selected(all_rows, args.mode)
    expected = {
        "protocol": VERSION, "task": args.task, "model": args.model,
        "model_digest": installed_model(args.base, args.model),
        "mode": args.mode, "source_digest": digest([
            (r["review_id"], r["segment_id"], r["segment"], r["full_review"])
            for r in cases]),
        "system_sha256": digest(SYSTEMS[args.task]),
        "schema_sha256": digest(SCHEMAS[args.task]),
        "options": {"temperature": 0, "seed": 42, "num_ctx": 4096,
                    "num_predict": 1050, "think": False},
    }
    folder = folder_for(args.output, args.model, args.mode, args.task)
    manifest = folder / "manifest.json"
    if manifest.exists():
        if json.loads(manifest.read_text(encoding="utf-8")) != expected:
            raise ValueError("Source/model/prompt changed; use a fresh output directory")
    else:
        if folder.exists() and any(folder.iterdir()):
            raise ValueError("Preexisting output lacks protocol manifest")
        folder.mkdir(parents=True, exist_ok=True)
        manifest.write_text(json.dumps(expected, indent=2, ensure_ascii=False),
                            encoding="utf-8")
    valid = {r["index"] for r in read_lines(folder / "results.jsonl")}
    failed = {r["index"] for r in read_lines(folder / "errors.jsonl")}
    work = cases[:args.limit] if args.limit else cases
    pending = [r for r in work if int(r["index"]) not in valid
               and (args.retry_errors or int(r["index"]) not in failed)]
    print(f"{args.model} task={args.task} mode={args.mode}: "
          f"valid {len(valid)}, remaining {len(pending)} / {len(work)}", flush=True)
    for count, row in enumerate(pending, 1):
        index = int(row["index"])
        t0 = time.perf_counter()
        raw, error, meta = "", "", {}
        try:
            result = urlopen_json(args.base, "/api/chat",
                                  request_payload(row, args.model, args.mode, args.task),
                                  args.timeout)
            raw = result.get("message", {}).get("content", "")
            meta = {k: result.get(k) for k in
                    ("done_reason", "load_duration", "total_duration", "eval_count",
                     "eval_duration", "prompt_eval_count", "prompt_eval_duration")}
            result_json = json.loads(raw)
            parsed = (validate_evidence(result_json, row["segment"])
                      if args.task == "evidence" else validate_score(result_json))
        except (ValueError, TypeError, KeyError, TimeoutError, OSError) as exc:
            error = type(exc).__name__ + ": " + str(exc)
        elapsed = round(time.perf_counter() - t0, 3)
        common = {"index": index, "key": row["review_id"] + ":" + row["segment_id"],
                  "model": args.model, "mode": args.mode, "task": args.task,
                  "duration_seconds": elapsed, "server_metadata": meta}
        append(folder / "raw_responses.jsonl", {**common, "raw": raw, "error": error or None})
        if error:
            append(folder / "errors.jsonl", {**common, "error": error})
        else:
            append(folder / "results.jsonl", {**common, "prediction": parsed,
                                             "target_segment": row["segment"]})
        print(f"[{count}/{len(pending)}] row {index}: "
              f"{'ERROR ' + error[:120] if error else 'OK'} "
              f"({elapsed}s)", flush=True)


def write_rows(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError("No rows to write")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def claim_text(record: dict | None) -> str:
    if record is None:
        return ""
    return json.dumps(record["prediction"]["claims"], ensure_ascii=False)


def score_text(record: dict | None, category: str, channel: str) -> str:
    if record is None:
        return ""
    obj = next(r[channel] for r in record["prediction"]["ratings"]
               if r["category"] == category)
    return f'{obj["verdict"]} / {obj["signed_score"]}: {obj["reason"]}'


def report(args) -> dict:
    rows = corpus(args.source)
    outputs = {}
    for model in MODELS:
        for mode in ("segment", "context"):
            for task in TASKS:
                folder = folder_for(args.output, model, mode, task)
                results = read_lines(folder / "results.jsonl")
                outputs[(model, mode, task)] = {r["index"]: r for r in results}
    gold, evidence_compare, score_compare, blinding = [], [], [], []
    for mode in ("segment", "context"):
        for row in selected(rows, mode):
            idx = int(row["index"])
            base = {"index": idx, "mode": mode, "target_segment": row["segment"],
                    "full_review_for_reference_only": row["full_review"]}
            if mode == "segment":
                template = dict(base)
                template.update({
                    "human_direct_source_phrases": "",
                    "human_inference_source_phrases": "",
                    "human_is_both_possible": "",
                    "human_source_scope_notes": "",
                    "human_ambiguity_notes": "",
                })
                for c in CATEGORIES:
                    for channel in ("direct", "inference"):
                        template[f"human_{c}_{channel}_verdict"] = ""
                        template[f"human_{c}_{channel}_signed_score"] = ""
                gold.append(template)
            order = list(MODELS)
            random.Random(20261113 + idx + (10000 if mode == "context" else 0)).shuffle(order)
            blinding.append({"index": idx, "mode": mode,
                             "model_A": order[0], "model_B": order[1]})
            ev = dict(base)
            ev["model_A_claims"] = claim_text(outputs[(order[0], mode, "evidence")].get(idx))
            ev["model_B_claims"] = claim_text(outputs[(order[1], mode, "evidence")].get(idx))
            ev["human_preference_A_B_tie"] = ""
            ev["human_notes"] = ""
            evidence_compare.append(ev)
            sc = dict(base)
            for c in CATEGORIES:
                for channel in ("direct", "inference"):
                    for letter, model in (("A", order[0]), ("B", order[1])):
                        sc[f"model_{letter}_{c}_{channel}"] = score_text(
                            outputs[(model, mode, "score")].get(idx), c, channel)
            sc["human_preference_A_B_tie"] = ""
            sc["human_notes"] = ""
            score_compare.append(sc)
    write_rows(args.output / "01_gold_first_BLANK.csv", gold)
    write_rows(args.output / "02_blind_evidence_A_B.csv", evidence_compare)
    write_rows(args.output / "03_blind_scores_A_B.csv", score_compare)
    (args.output / "04_blinding_key_KEEP_PRIVATE.json").write_text(
        json.dumps(blinding, ensure_ascii=False, indent=2), encoding="utf-8")
    # The same-prompt 8B baseline is optional: do not use it as an A/B
    # competitor in the primary, two-advanced-model blind review packet.
    baseline_coverage = {}
    for mode in ("segment", "context"):
        for task in TASKS:
            baseline_path = folder_for(args.output, BASELINE_MODELS[0], mode, task)
            saved = read_lines(baseline_path / "results.jsonl")
            baseline_coverage[f"{BASELINE_MODELS[0]}/{mode}/{task}"] = {
                "valid": len(saved), "planned": len(selected(rows, mode))
            }
    summary = {
        "optional_same_prompt_8b_baseline": baseline_coverage,
        "protocol": VERSION,
        "gold_first": "01_gold_first_BLANK.csv",
        "blind_evidence": "02_blind_evidence_A_B.csv",
        "blind_emotion": "03_blind_scores_A_B.csv",
        "blinding_private": "04_blinding_key_KEEP_PRIVATE.json",
        "results": {},
        "caution": (
            "No model accuracy is computed because researcher gold is not complete. "
            "Both E and T can occur in one segment. Category scores are ordinal, "
            "not probabilities. Context-arm output is distinct from segment-only."
        ),
    }
    for (model, mode, task), values in outputs.items():
        seconds = [v["duration_seconds"] for v in values.values()]
        item = {"valid": len(values), "planned": len(selected(rows, mode)),
                "mean_seconds": round(sum(seconds) / len(seconds), 2) if seconds else None}
        if task == "evidence":
            counts = Counter(
                "source_exact" if claim["source_exact"] else "unverified_quote"
                for row in values.values() for claim in row["prediction"]["claims"]
            )
            item["source_quote_counts"] = dict(counts)
        summary["results"][f"{model}/{mode}/{task}"] = item
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False),
                                               encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return summary


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--stage", choices=("check", "run", "report"), default="check")
    p.add_argument("--task", choices=TASKS, default=TASKS[0])
    p.add_argument("--model", choices=AVAILABLE_MODELS, default=MODELS[0])
    p.add_argument("--mode", choices=("segment", "context"), default="segment")
    p.add_argument("--source", type=Path, default=SOURCE)
    p.add_argument("--output", type=Path, default=DEFAULT_OUT)
    p.add_argument("--base", default="http://127.0.0.1:11434")
    p.add_argument("--timeout", type=int, default=400)
    p.add_argument("--limit", type=int, default=0)
    p.add_argument("--retry-errors", action="store_true")
    args = p.parse_args()
    if args.limit < 0 or args.timeout < 1:
        p.error("Invalid timeout/limit")
    if args.stage == "check":
        rows = corpus(args.source)
        print("Source rows:", len(rows), "challenge cohort:", len(selected(rows, "segment")))
        print("Installed Pod models:", [
            m["name"] for m in urlopen_json(args.base, "/api/tags", timeout=20)["models"]
        ])
    elif args.stage == "run":
        run(args)
    else:
        report(args)


if __name__ == "__main__":
    main()

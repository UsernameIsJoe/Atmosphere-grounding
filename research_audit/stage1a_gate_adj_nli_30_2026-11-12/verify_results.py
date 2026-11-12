#!/usr/bin/env python3
"""Recompute the archived gate study's descriptive metrics from its ORIGINAL ZIP.

Usage:
    python research_audit/stage1a_gate_adj_nli_30_2026-11-12/verify_results.py \
        --zip stage1a_gate_results.zip

No ML dependencies, no model calls, no new labels or score optimization.
Human screening labels are read as PROVISIONAL and non-blind.
Run-result ZIP is a source artifact; do not substitute invented examples.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
import json
import math
from pathlib import Path
from statistics import mean, median
import zipfile

ROOT = Path(__file__).resolve().parents[2]
AUDIT_CSV = Path(__file__).with_name("audit_123_segments.csv")
CATEGORIES = ("calm", "inviting", "safe")
MODELS = ("bart", "deberta", "modernbert")


def open_archive(path: Path) -> dict:
    with zipfile.ZipFile(path) as archive:
        members = {name.replace("\\", "/"): name for name in archive.namelist()}

        def read(relpath: str) -> str:
            matches = [path for path in members if path.endswith("/" + relpath)]
            if len(matches) != 1:
                raise ValueError(f"Expected exactly one archive member: {relpath}, found {matches}")
            return archive.read(members[matches[0]]).decode("utf-8-sig")

        def jsonl(relpath: str) -> list[dict]:
            return [json.loads(line) for line in read(relpath).splitlines() if line.strip()]

        return {
            "manifest": json.loads(read("input/manifest.json")),
            "segments": jsonl("input/segments.jsonl"),
            "pos": jsonl("gates/pos.jsonl"),
            "nli": {m: jsonl(f"gates/nli_{m}.jsonl") for m in MODELS},
            "qwen": jsonl("llm_v2/qwen3_8b/ratings.jsonl"),
            "gemma": jsonl("llm_v2/gemma3_4b/ratings.jsonl"),
            "gemma_rescue": jsonl("llm_segment_only_rescue_gemma_v1/ratings.jsonl"),
        }


def bykey(rows: list[dict]) -> dict[str, dict]:
    out = {}
    for row in rows:
        k = row["key"]
        if k in out:
            raise ValueError(f"Duplicate result key: {k}")
        out[k] = row
    return out


def key(segment: dict) -> str:
    return f'{segment["review_id"]}:{segment["segment_id"]}'


def as_verdicts(row: dict) -> list[str]:
    ordered = {r["category"]: r["verdict"] for r in row["ratings"]}
    if set(ordered) != set(CATEGORIES) or len(row["ratings"]) != 3:
        raise ValueError("Missing or duplicated emotion categories")
    return [ordered[c] for c in CATEGORIES]


def verify(data: dict, audit_csv: Path) -> dict:
    manifest, source = data["manifest"], data["segments"]
    keys = [key(s) for s in source]
    if len(set(keys)) != len(keys):
        raise ValueError("Duplicate segments in source")
    for seg in source:
        if seg["full_review"][seg["start"]:seg["end"]] != seg["segment"]:
            raise ValueError(f"Original source substring mismatch: {key(seg)}")
    source_set = set(keys)
    pos = bykey(data["pos"])
    nli = {m: bykey(data["nli"][m]) for m in MODELS}
    qwen, gemma, rescue = (bykey(data[k]) for k in ("qwen", "gemma", "gemma_rescue"))
    for label, values in [("pos", pos), *nli.items(), ("qwen", qwen),
                          ("gemma", gemma), ("gemma_rescue", rescue)]:
        if not set(values) <= source_set:
            raise ValueError(f"Unknown source key in {label}")
    if set(pos) != source_set or any(set(rows) != source_set for rows in nli.values()):
        raise ValueError("Incomplete adjective or NLI results")
    if set(gemma) & set(rescue):
        raise ValueError("Recovery incorrectly overlaps original Gemma results")
    if set(gemma) | set(rescue) != source_set:
        raise ValueError("Missing original Gemma or rescue output")
    if len(source) != manifest["n_segments"] or len({s["review_id"] for s in source}) != manifest["reviews"]:
        raise ValueError("Original sample manifest count mismatch")

    with audit_csv.open(encoding="utf-8-sig", newline="") as f:
        audit = list(csv.DictReader(f))
    if len(audit) != len(source):
        raise ValueError("Audit file no longer matches original segment count")
    screen = Counter()
    unresolved = 0
    for i, (seg, row) in enumerate(zip(source, audit)):
        if row["index"] != str(i) or row["review_id"] != seg["review_id"] or int(row["segment_id"]) != seg["segment_id"]:
            raise ValueError(f"Audit source ID/order mismatch at row {i}")
        if row["segment"] != seg["segment"] or row["full_review"] != seg["full_review"]:
            raise ValueError(f"Audit source text differs at row {i}")
        k = key(seg)
        if (row["adjective"].lower() == "true") != pos[k]["adjective_present"]:
            raise ValueError(f"Audit adjective gate mismatch at {k}")
        for name in MODELS:
            value = float(row[f"nli_{name}_mean"])
            if abs(value - nli[name][k]["mean_entailment"]) > 0.00006:
                raise ValueError(f"Audit NLI score mismatch ({name}): {k}")
        screen[row["screen_class"]] += 1
        unresolved += sum(row[f"reference_{c}"] == "U" for c in ("cal", "inv", "safe"))
        for model_name, saved, column in [
            ("qwen", qwen, "qwen_v2"),
            ("gemma", gemma, "gemma_v2"),
            ("gemma_rescue", rescue, "gemma_rescue"),
        ]:
            values = ",".join(as_verdicts(saved[k])) if k in saved else ""
            if row[column] != values:
                raise ValueError(f"Audit saved {model_name} verdict mismatch at {k}")

    overlap = set(qwen) & set(gemma)
    compare = lambda k: as_verdicts(qwen[k]) != as_verdicts(gemma[k])
    nli_median = {k: median(nli[m][k]["mean_entailment"] for m in MODELS) for k in keys}
    candidates = {
        "adjective": lambda k: pos[k]["adjective_present"],
        "nli_median_ge_0.4": lambda k: nli_median[k] >= 0.4,
        "nli_median_ge_0.6": lambda k: nli_median[k] >= 0.6,
        "nli_median_ge_0.8": lambda k: nli_median[k] >= 0.8,
        "adjective_OR_nli_ge_0.6": lambda k: pos[k]["adjective_present"] or nli_median[k] >= .6,
        "adjective_AND_nli_ge_0.6": lambda k: pos[k]["adjective_present"] and nli_median[k] >= .6,
    }
    routing = {}
    for name, qualifies in candidates.items():
        selected = [k for k in keys if qualifies(k)]
        comparable = [k for k in overlap if qualifies(k)]
        disagreements = sum(compare(k) for k in comparable)
        routing[name] = {
            "one_model_candidates": len(selected),
            "hypothetical_calls_saved": len(selected),
            "saved_fraction_of_two_model_baseline": round(len(selected)/(2*len(keys)),4),
            "same_protocol_comparable": len(comparable),
            "same_protocol_disagreements": disagreements,
            "same_protocol_disagreement_rate": round(disagreements/len(comparable),4)
                if comparable else None,
        }

    nli_diagnostics = {}
    for name in MODELS:
        rows = data["nli"][name]
        means = [mean(r["hypotheses"][j]["probabilities"]["entailment"] for r in rows)
                 for j in range(3)]
        ranges = [
            max(h["probabilities"]["entailment"] for h in r["hypotheses"]) -
            min(h["probabilities"]["entailment"] for h in r["hypotheses"])
            for r in rows
        ]
        nli_diagnostics[name] = {
            "checkpoint": manifest["nli_models"][name],
            "native_label_space": sorted({r["label_space"] for r in rows}),
            "mean_entailment_by_hypothesis": [round(v,4) for v in means],
            "count_hypothesis_range_gt_0.5": sum(v > .5 for v in ranges),
            "forward_seconds_excluding_load": round(sum(r["duration_s"] for r in rows),2),
        }

    return {
        "sample": {"reviews": manifest["reviews"], "places": manifest["places"],
                   "segments": len(source), "seed": manifest["seed"],
                   "source_file_sha256": manifest["source_file_sha256"],
                   "segments_sha256": manifest["segments_sha256"]},
        "coverage": {
            "adjective_and_each_nli": len(source), "qwen_v2_valid": len(qwen),
            "gemma_v2_valid": len(gemma), "gemma_segment_only_rescue": len(rescue),
            "gemma_combined_mixed_protocol": len(set(gemma)|set(rescue)),
            "same_protocol_overlap": len(overlap),
            "same_protocol_any_disagreement": sum(compare(k) for k in overlap),
        },
        "adjective_present": sum(pos[k]["adjective_present"] for k in keys),
        "routing_simulations_not_measured_accuracy": routing,
        "nli": nli_diagnostics,
        "source_audit_provisional_not_ground_truth": {
            "screen_class_counts": dict(screen),
            "uncertain_category_cells": unresolved,
            "category_cells_total": len(source)*3,
        },
        "limitations": [
            "All saved LLM ratings are uncalibrated; agreements are not proof of correctness",
            "123-row human audit is provisional, single-reviewer and non-blind",
            "Missing V2 outputs may be non-random; 43 rescue rows use a different context/prompt",
            "NLI three-way vs two-way probabilities are not calibrated across checkpoints",
            "Saved-call estimates exclude NLI load time, retries and third-model adjudication",
        ],
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--zip", type=Path, required=True, help="Unmodified experiment result ZIP")
    ap.add_argument("--audit-csv", type=Path, default=AUDIT_CSV)
    args = ap.parse_args()
    print(json.dumps(verify(open_archive(args.zip), args.audit_csv),
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Independent local-LLM silver annotation for Stage 1A v2."""
from __future__ import annotations
import argparse
import collections
import json
import re
import subprocess

from stage1a_component1_ollama import call_ollama
from stage1a_v2 import (EMOTIONS, OUT, RELEVANCE, STEP_A_SCHEMA,
                         annotation_map, load_items, read_jsonl)

JUDGE_SYSTEM = """Act as an independent annotation judge for place-atmosphere evidence in a REAL Google review.
You must label calm, inviting, and safe separately from the original sentence and its full review context.
For relevance choose supports when the sentence gives evidence for the emotion, opposes when it gives evidence against it,
mixed when both directions are present, not_relevant when there is no emotion-specific link, and uncertain only for genuinely
ambiguous wording or reference. A missing link is not uncertainty.
Generic praise such as great, nice, or cute is not_relevant unless it has emotion-specific meaning. Bare location facts and
complaints about food, service, or prices are also not_relevant for these emotions.
For relevant labels, type is explicit when the sentence itself names the emotion or a clear synonym about the place;
direct_indicator when a concrete place condition specifically bears on the emotion without reporting a felt emotion
(for example, a source-grounded police patrol is direct safety evidence); indirect when the connection requires a looser inference,
such as off the beaten path being used as evidence about calm.
Attribution is first_person, secondhand, hedged, or general. Mark reports learned from other people's narratives as secondhand.
Copy a minimal exact contiguous evidence_span from ORIGINAL SENTENCE for relevant labels. For not_relevant or uncertain,
use an empty evidence_span and null type. Do not inspect or infer any other model's answer. Return JSON only."""


def family(tag: str):
    base = tag.split(":", 1)[0].lower()
    base = re.sub(r"\d+(?:\.\d+)*$", "", base)
    return base.rstrip("-_.")


def size_hint(tag: str):
    m = re.findall(r"(\d+(?:\.\d+)?)b\b", tag.lower())
    return float(m[-1]) if m else 0.0


def ollama_models():
    proc = subprocess.run(["ollama", "list"], text=True, capture_output=True, check=True)
    rows = []
    for line in proc.stdout.splitlines()[1:]:
        parts = line.split()
        if parts:
            rows.append(parts[0])
    return rows


def choose_models(spec: str | None):
    installed = ollama_models()
    if spec:
        chosen = [x.strip() for x in spec.split(",") if x.strip()]
        missing = [x for x in chosen if x not in installed]
        if missing:
            raise ValueError("requested judge models are not installed: " + ", ".join(missing))
    else:
        candidates = [x for x in installed if "qwen" not in x.lower()]
        candidates.sort(key=lambda x: (-size_hint(x), x))
        chosen = []
        used_families = set()
        for tag in candidates:
            f = family(tag)
            if f in used_families:
                continue
            chosen.append(tag); used_families.add(f)
            if len(chosen) == 2:
                break
    if len(chosen) != 2:
        raise ValueError("need exactly two installed non-Qwen judge models from different families; check ollama list")
    if any("qwen" in x.lower() for x in chosen) or family(chosen[0]) == family(chosen[1]):
        raise ValueError("judge models must be non-Qwen and from different families")
    return chosen


def kappa(pairs):
    if not pairs:
        return None
    labels = list(RELEVANCE)
    n = len(pairs)
    observed = sum(a == b for a, b in pairs) / n
    ca, cb = collections.Counter(a for a, _ in pairs), collections.Counter(b for _, b in pairs)
    expected = sum((ca[x] / n) * (cb[x] / n) for x in labels)
    if expected >= 1.0:
        return 1.0 if observed == 1.0 else None
    return (observed - expected) / (1.0 - expected)


def spans_overlap(a: str, b: str, sentence: str):
    if not a or not b:
        return False
    aa, bb = sentence.find(a), sentence.find(b)
    if aa < 0 or bb < 0:
        return False
    return max(aa, bb) < min(aa + len(a), bb + len(b))


def run(args, items, models, outdir):
    path = outdir / "judges.jsonl"
    done = {}
    if path.exists() and args.resume:
        for r in read_jsonl(path):
            key = (r["source"]["row"], r["source"]["start"], r["source"]["end"])
            done[key] = r
    elif path.exists():
        raise ValueError(f"{path} exists; use --resume or remove it")
    with path.open("a" if args.resume else "w", encoding="utf8") as fh:
        for source in items:
            key = (source["row"], source["start"], source["end"])
            if key in done:
                continue
            judgments = {}
            for model in models:
                payload, meta = call_ollama(
                    args.url, model, JUDGE_SYSTEM,
                    "FULL REVIEW CONTEXT:\n" + source["review_text"] +
                    "\n\nORIGINAL SENTENCE:\n" + source["sentence"],
                    STEP_A_SCHEMA, args.timeout, args.num_ctx, think=False, num_predict=1400,
                )
                judgments[model] = {"emotions": annotation_map(payload, source["sentence"]), "model_meta": meta}
            r = {"source": source, "judge_models": models, "judgments": judgments}
            fh.write(json.dumps(r, ensure_ascii=False) + "\n"); fh.flush()
            done[key] = r
            print(f"JUDGES {len(done)}/{len(items)} row={source['row']}", flush=True)
    return [done[(x["row"], x["start"], x["end"])] for x in items]


def make_silver(rows, models, outdir):
    silver_path = outdir / "silver.jsonl"
    silver_rows = []
    pairs = {e: [] for e in EMOTIONS}
    disagreements = []
    with silver_path.open("w", encoding="utf8") as fh:
        for r in rows:
            source = r["source"]
            j1 = r["judgments"][models[0]]["emotions"]
            j2 = r["judgments"][models[1]]["emotions"]
            emotions = {}
            for e in EMOTIONS:
                a, b = j1[e], j2[e]
                valid = a["valid_for_downstream"] and b["valid_for_downstream"]
                if valid:
                    pairs[e].append((a["relevance"], b["relevance"]))
                agreement = valid and a["relevance"] == b["relevance"]
                relevant = agreement and a["relevance"] in ("supports", "opposes", "mixed")
                typ = a["type"] if relevant and a["type"] == b["type"] else None
                overlap = relevant and spans_overlap(a["evidence_span"], b["evidence_span"], source["sentence"])
                emotions[e] = {
                    "silver_relevance": a["relevance"] if agreement else None,
                    "silver_type": typ,
                    "judge_spans": [a["evidence_span"], b["evidence_span"]] if overlap else [],
                    "span_overlap": bool(overlap),
                    "contested": not agreement,
                    "judge_1": {"model": models[0], "label": a},
                    "judge_2": {"model": models[1], "label": b},
                }
                if not agreement:
                    disagreements.append({"emotion": e, "sentence": source["sentence"],
                                          "judge_1": a["relevance"] if valid else "invalid",
                                          "judge_2": b["relevance"] if valid else "invalid"})
            out = {"source": source, "emotions": emotions}
            silver_rows.append(out)
            fh.write(json.dumps(out, ensure_ascii=False) + "\n")
    kappas = {e: kappa(pairs[e]) for e in EMOTIONS}
    pattern_counts = collections.Counter((x["emotion"], x["judge_1"], x["judge_2"]) for x in disagreements)
    top = sorted(disagreements, key=lambda x: (-pattern_counts[(x["emotion"], x["judge_1"], x["judge_2"])], x["emotion"], x["sentence"]))[:10]
    for x in top:
        x["pattern_count"] = pattern_counts[(x["emotion"], x["judge_1"], x["judge_2"])]
    summary = {
        "judge_models": models,
        "cohen_kappa_relevance": kappas,
        "definition_unstable": [e for e, v in kappas.items() if v is None or v < 0.4],
        "contested_count": sum(x["emotions"][e]["contested"] for x in silver_rows for e in EMOTIONS),
        "top_10_disagreements": top,
    }
    (outdir / "judge_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--split", choices=("dev", "holdout"), default="dev")
    p.add_argument("--models", help="exact two installed Ollama tags, comma-separated")
    p.add_argument("--url", default="http://127.0.0.1:11434")
    p.add_argument("--timeout", type=int, default=300)
    p.add_argument("--num-ctx", type=int, default=8192)
    p.add_argument("--resume", action="store_true")
    p.add_argument("--allow-holdout", action="store_true")
    args = p.parse_args()
    if args.split == "holdout" and not args.allow_holdout:
        p.error("holdout is locked; use --allow-holdout only after gate confirmation")
    models = choose_models(args.models)
    items, _ = load_items(args.split)
    outdir = OUT / args.split
    outdir.mkdir(parents=True, exist_ok=True)
    rows = run(args, items, models, outdir)
    make_silver(rows, models, outdir)


if __name__ == "__main__":
    main()

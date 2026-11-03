#!/usr/bin/env python3
"""Label-free Stage 1A expanded vocabulary test: 214 reviews x 60 candidate hypotheses.

Runs pretrained BART-MNLI, saves exact per-review distributions, reports
within-family variation and alternative core-paraphrase ensembles.
Does not claim human-rated accuracy, calibration, or validated emotion intensity.
"""
import argparse
import collections
import hashlib
import json
import math
import pathlib
import statistics
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from stage1a_text_pilot import read_jsonl
from stage1a_hypothesis_robustness import batch_nli, decide, entropy

MODEL = "facebook/bart-large-mnli"
LABELS = ("S", "C", "U")


def load_registry(path):
    obj = json.loads(path.read_text(encoding="utf-8"))
    candidates = obj["candidates"]
    ids = [x["id"] for x in candidates]
    if not candidates or len(ids) != len(set(ids)):
        raise ValueError("Registry empty or duplicate candidate ID")
    for x in candidates:
        if not all(x.get(key) for key in ("id", "emotion", "role", "family", "text", "source")):
            raise ValueError(f"Candidate missing required field: {x}")
        if x["role"] not in ("core", "facet", "opposition"):
            raise ValueError(f"Unexpected role {x['role']}")
    for emotion in {x["emotion"] for x in candidates}:
        if sum(x["emotion"] == emotion and x["role"] == "core" for x in candidates) < 3:
            raise ValueError(f"Not enough core hypotheses for {emotion}")
    return obj


def mean_distribution(probs):
    return {k: sum(p[k] for p in probs) / len(probs) for k in LABELS}


def median_distribution(probs):
    raw = {k: statistics.median([p[k] for p in probs]) for k in LABELS}
    total = sum(raw.values())
    return {k: v / total for k, v in raw.items()}


def trimmed_distribution(probs):
    # On >= 5 expressions, remove 1 highest and 1 lowest value per class.
    # Normalize, since per-class trimming does not preserve sum=1.
    raw = {}
    for k in LABELS:
        vals = sorted(p[k] for p in probs)
        core = vals[1:-1] if len(vals) >= 5 else vals
        raw[k] = sum(core) / len(core)
    total = sum(raw.values())
    return {k: v / total for k, v in raw.items()}


def majority_label(labels):
    tally = collections.Counter(labels)
    if not tally:
        return None
    best = max(tally.values())
    winners = [k for k in LABELS if tally[k] == best]
    return winners[0] if len(winners) == 1 else "ABSTAIN"


def ensemble(core):
    probs = [x["probs"] for x in core]
    strategies = {
        "mean": mean_distribution(probs),
        "median": median_distribution(probs),
        "trimmed": trimmed_distribution(probs),
    }
    labels = [x["label"] for x in core]
    output = {k: {"probs": v, "label": decide(v)} for k, v in strategies.items()}
    output["majority"] = {"label": majority_label(labels), "counts": dict(collections.Counter(labels))}
    output["unanimous"] = len(set(labels)) == 1
    output["support_range"] = max(p["S"] for p in probs) - min(p["S"] for p in probs)
    output["mean_entropy"] = sum(entropy(p) for p in probs) / len(probs)
    output["leave_one_out_mean_labels"] = [
        decide(mean_distribution(probs[:i] + probs[i+1:])) for i in range(len(probs))
    ]
    output["leave_one_out_stable"] = all(x == output["mean"]["label"] for x in output["leave_one_out_mean_labels"])
    output["strategies_agree"] = len({output[k]["label"] for k in ("mean", "median", "trimmed", "majority")}) == 1
    return output


def summarize(rows, registry):
    by_emotion = {}
    for emotion in sorted({c["emotion"] for c in registry}):
        candidates = [c for c in registry if c["emotion"] == emotion]
        core_ids = [c["id"] for c in candidates if c["role"] == "core"]
        cases = [r["emotions"][emotion] for r in rows]
        ensemble_rows = [x["core_ensemble"] for x in cases]
        by_family = {}
        for family in sorted({c["family"] for c in candidates if c["role"] == "facet"}):
            group = [c["id"] for c in candidates if c["family"] == family and c["role"] == "facet"]
            labels = [x["predictions"][cid]["label"] for x in cases for cid in group]
            by_family[family] = {"candidate_ids": group, "label_counts": dict(collections.Counter(labels))}
        per_candidate = {}
        for c in candidates:
            predictions = [x["predictions"][c["id"]] for x in cases]
            per_candidate[c["id"]] = {
                "role": c["role"], "family": c["family"],
                "label_counts": dict(collections.Counter(p["label"] for p in predictions)),
                "mean_support_probability": round(statistics.mean(p["probs"]["S"] for p in predictions), 5),
                "mean_entropy": round(statistics.mean(p["entropy"] for p in predictions), 5),
            }
        core_pairs = {}
        for i, a in enumerate(core_ids):
            for b in core_ids[i+1:]:
                diffs = [abs(x["predictions"][a]["probs"]["S"] - x["predictions"][b]["probs"]["S"]) for x in cases]
                agree = [x["predictions"][a]["label"] == x["predictions"][b]["label"] for x in cases]
                core_pairs[a + "|" + b] = {
                    "label_agreement": round(sum(agree)/len(agree), 4),
                    "mean_absolute_support_difference": round(statistics.mean(diffs), 4),
                }
        disagreement = sorted(
            [{"row": r["row"], "place_id": r["place_id"],
              "support_range": r["emotions"][emotion]["core_ensemble"]["support_range"],
              "core_labels": [r["emotions"][emotion]["predictions"][cid]["label"] for cid in core_ids]}
             for r in rows], key=lambda x: x["support_range"], reverse=True
        )
        by_emotion[emotion] = {
            "reviews": len(cases), "core_ids": core_ids,
            "core_unanimity_rate": round(sum(x["unanimous"] for x in ensemble_rows)/len(cases), 4),
            "mean_core_support_probability_range": round(statistics.mean(x["support_range"] for x in ensemble_rows), 4),
            "mean_core_entropy": round(statistics.mean(x["mean_entropy"] for x in ensemble_rows), 4),
            "leave_one_out_mean_stability": round(sum(x["leave_one_out_stable"] for x in ensemble_rows)/len(cases), 4),
            "ensemble_strategy_agreement": round(sum(x["strategies_agree"] for x in ensemble_rows)/len(cases), 4),
            "ensemble_label_counts": {method: dict(collections.Counter(x[method]["label"] for x in ensemble_rows))
                                      for method in ("mean","median","trimmed","majority")},
            "core_pairwise": core_pairs,
            "facets_by_family": by_family,
            "per_candidate": per_candidate,
            "top_10_core_disagreements": disagreement[:10],
        }
    return by_emotion


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="reports/stage1a_vocabulary")
    parser.add_argument("--registry", default="configs/stage1a_hypothesis_vocabulary_draft.json")
    parser.add_argument("--limit", type=int, default=0, help="0 = all reviews; N = first N")
    parser.add_argument("--batch-size", type=int, default=8)
    args = parser.parse_args()
    if args.limit < 0 or args.batch_size < 1:
        raise ValueError("Invalid limit or batch size")
    registry_path = ROOT / args.registry
    registry = load_registry(registry_path)
    candidates = registry["candidates"]
    reviews = read_jsonl(ROOT / "data/processed/reviews.jsonl")
    selected = reviews[:args.limit or None]
    if not selected:
        raise RuntimeError("No reviews found")

    import torch
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    torch.set_num_threads(min(4, torch.get_num_threads()))
    tok = AutoTokenizer.from_pretrained(MODEL)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL).eval()

    groups = {}
    for emotion in sorted({c["emotion"] for c in candidates}):
        groups[emotion] = [c for c in candidates if c["emotion"] == emotion]

    dest = ROOT / args.output
    dest.mkdir(parents=True, exist_ok=True)
    rows = []
    with (dest / "review_cases.jsonl").open("w", encoding="utf-8") as handle:
        for idx, review in enumerate(selected):
            row = {"row": idx, "place_id": review["place_id"],
                   "review_index": review["review_index"], "review": review["text"], "emotions": {}}
            for emotion, subset in groups.items():
                probs = batch_nli(tok, model, review["text"], [c["text"] for c in subset], torch, args.batch_size)
                pred = {c["id"]: {"label": decide(p), "probs": p, "entropy": entropy(p)}
                        for c, p in zip(subset, probs)}
                core = [pred[c["id"]] for c in subset if c["role"] == "core"]
                row["emotions"][emotion] = {"predictions": pred, "core_ensemble": ensemble(core)}
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
            rows.append(row)
            if (idx + 1) % 10 == 0 or idx + 1 == len(selected):
                print(f"Completed {idx+1}/{len(selected)} reviews", flush=True)
    summary = {
        "model": MODEL, "registry_path": args.registry,
        "registry_sha256": hashlib.sha256(registry_path.read_bytes()).hexdigest(),
        "corpus_size": len(reviews), "evaluated_reviews": len(rows),
        "locations": len({x["place_id"] for x in rows}),
        "candidate_count": len(candidates),
        "total_pairs": len(rows) * len(candidates),
        "metrics": summarize(rows, candidates),
        "caveats": [
            "No independent human review–emotion ground truth; results show stability, not accuracy.",
            "Core statements are only proposed semantic paraphrases; similarity is not independently validated.",
            "Facet hypotheses are different constructs and are NOT aggregated into core ensembles.",
            "High ensemble agreement can arise from all-neutral predictions and shared checkpoint biases.",
            "No calibration, validated emotion intensity, causal or image-based inference.",
            "Location-clustered reviews are not independent observations.",
            "Potential 512-token truncation of long review–hypothesis pairs.",
        ],
    }
    (dest / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (dest / "registry_snapshot.json").write_text(json.dumps(registry, indent=2), encoding="utf-8")
    print(json.dumps({k: {
        "core_unanimity_rate": v["core_unanimity_rate"],
        "leave_one_out_mean_stability": v["leave_one_out_mean_stability"],
        "ensemble_strategy_agreement": v["ensemble_strategy_agreement"],
        "mean_core_support_probability_range": v["mean_core_support_probability_range"]
    } for k, v in summary["metrics"].items()}, indent=2), flush=True)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Stage 1A Step 1: hypothesis sensitivity without human ground truth.

Compare broad paraphrases, atomic supporting attributes, and negated/opposing
hypotheses on the same real reviews using the same pretrained NLI checkpoint.

Outputs descriptive consistency/uncertainty diagnostics, NOT accuracy or
validated emotional intensity. Pilot labels from earlier tests are NOT used.
"""
import argparse
import collections
import json
import math
from pathlib import Path

from stage1a_text_pilot import CATS, GOLD, read_jsonl
from stage1a_compare_abc import pair_nli, decide

ROOT = Path(__file__).resolve().parents[1]
MODEL = "facebook/bart-large-mnli"

# All descriptions are explicitly exploratory, not finalized theory.
# Only a set of semantic paraphrases can reasonably be assessed for agreement.
# Facets measure distinct ideas: disagreement there is not necessarily error.
HYPOTHESES = {
    "calm": {
        "paraphrases": [
            "This location has a peaceful and relaxing atmosphere.",
            "People experience this place as calm and tranquil.",
            "The atmosphere of this place is serene and restful.",
        ],
        "facets": [
            "This location is generally quiet, without disruptive noise.",
            "This location offers a peaceful atmosphere.",
            "Visitors can relax comfortably at this location.",
        ],
        "opposing": [
            "This location has a stressful and agitating atmosphere.",
        ],
    },
    "inviting": {
        "paraphrases": [
            "This location has a welcoming and inviting atmosphere.",
            "People experience this place as welcoming.",
            "The atmosphere encourages visitors to enter and spend time here.",
        ],
        "facets": [
            "The location is easy and welcoming to enter.",
            "There are comfortable places for visitors to spend time at this location.",
            "This location encourages people to stay and enjoy themselves.",
        ],
        "opposing": [
            "This location is hostile and unwelcoming to visitors.",
        ],
    },
    "safe": {
        "paraphrases": [
            "This location feels physically safe for visitors.",
            "Visitors can use this location without feeling physically endangered.",
            "The location provides an environment free from serious physical hazards.",
        ],
        "facets": [
            "Visitors are protected from traffic hazards at this location.",
            "The location does not present dangerous physical conditions.",
            "This location feels secure for visitors.",
        ],
        "opposing": [
            "This location poses serious physical safety risks for visitors.",
        ],
    },
}

def spread(vals):
    """Range of support probabilities, not a calibrated uncertainty interval."""
    return max(vals) - min(vals)

def entropy(probs):
    """Normalized 3-class predictive entropy (0 low, 1 high)."""
    return -sum(p * math.log(max(p, 1e-12)) for p in probs.values()) / math.log(3)

def summarize(items):
    output = {}
    for emotion in CATS:
        cases = [item["emotions"][emotion] for item in items]
        labels = [x["paraphrases"]["labels"] for x in cases]
        unanimous = sum(len(set(l)) == 1 for l in labels)
        support_ranges = [x["paraphrases"]["support_range"] for x in cases]
        max_entropies = [x["paraphrases"]["mean_entropy"] for x in cases]
        # Red flag only, never a proof of logical inconsistency:
        # opposite emotional statements are not always strict logical negations.
        conflict = sum(x["opposition"]["both_support"] for x in cases)
        output[emotion] = {
            "n_reviews": len(cases),
            "paraphrase_unanimous_rate": round(unanimous / len(cases), 3),
            "mean_paraphrase_entailment_range": round(sum(support_ranges) / len(cases), 3),
            "mean_paraphrase_entropy": round(sum(max_entropies) / len(cases), 3),
            "both_positive_and_opposing_entailment_count": conflict,
            "facet_label_counts": dict(collections.Counter(
                label for x in cases for label in x["facets"]["labels"]
            )),
            "paraphrase_label_counts": dict(collections.Counter(
                label for l in labels for label in l
            )),
        }
    return output

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", default="reports/stage1a_hypotheses")
    ap.add_argument("--limit", type=int, default=30)
    args = ap.parse_args()
    if not 1 <= args.limit <= len(GOLD):
        raise ValueError("limit must be 1..30")

    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    import torch

    tokenizer = AutoTokenizer.from_pretrained(MODEL)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL).eval()
    reviews = read_jsonl(ROOT / "data/processed/reviews.jsonl")
    selected = list(GOLD)[:args.limit]
    results = []
    for i, row in enumerate(selected):
        review = reviews[row]
        record = {
            "row": row,
            "place_id": review["place_id"],
            "review_index": review["review_index"],
            "review": review["text"],
            "emotions": {},
        }
        for emotion in CATS:
            config = HYPOTHESES[emotion]
            groups = {}
            for kind in ("paraphrases", "facets", "opposing"):
                pairs = []
                for hypothesis in config[kind]:
                    probs = pair_nli(tokenizer, model, review["text"], hypothesis, torch)
                    pairs.append({"hypothesis": hypothesis, "label": decide(probs),
                                  "probs": probs, "predictive_entropy": entropy(probs)})
                groups[kind] = {"cases": pairs, "labels": [x["label"] for x in pairs]}
            paraphrases = groups["paraphrases"]["cases"]
            groups["paraphrases"]["support_range"] = round(spread([x["probs"]["S"] for x in paraphrases]), 5)
            groups["paraphrases"]["mean_entropy"] = round(sum(x["predictive_entropy"] for x in paraphrases) / len(paraphrases), 5)
            groups["opposition"] = {
                "both_support": any(x["label"] == "S" for x in paraphrases)
                and any(x["label"] == "S" for x in groups["opposing"]["cases"])
            }
            record["emotions"][emotion] = groups
        results.append(record)
        print(f"Finished {i + 1}/{len(selected)} row {row}", flush=True)

    dest = ROOT / args.output
    dest.mkdir(parents=True, exist_ok=True)
    with (dest / "review_cases.jsonl").open("w", encoding="utf-8") as f:
        for record in results:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    summary = {
        "run_type": "unsupervised hypothesis robustness diagnostic",
        "model": MODEL,
        "sample": {"reviews": len(results),
                   "locations": len({r["place_id"] for r in results}),
                   "selection": "same 30 previously sampled diagnostic reviews"},
        "hypotheses": HYPOTHESES,
        "by_emotion": summarize(results),
        "limitations": [
            "No human-rated ground truth; no accuracy/precision/F1 measured.",
            "Paraphrases are not guaranteed perfectly equivalent.",
            "Facets are distinct supporting qualities; their disagreement is descriptive.",
            "Opposite atmosphere claims are not strict logical complements.",
            "NLI softmax probabilities are not calibrated confidence or emotional strength.",
            "Reviews grouped within seven locations are not independent samples.",
        ],
    }
    (dest / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary["by_emotion"], indent=2), flush=True)

if __name__ == "__main__":
    main()

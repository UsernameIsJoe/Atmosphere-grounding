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
from stage1a_compare_abc import decide

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

def batch_nli(tokenizer, model, premise, hypotheses, torch, batch_size=8):
    """Batch same-review hypothesis pairs, returning complete NLI probabilities."""
    found = []
    for offset in range(0, len(hypotheses), batch_size):
        group = hypotheses[offset:offset + batch_size]
        encoded = tokenizer(
            [premise] * len(group), group,
            padding=True, truncation=True, max_length=512, return_tensors="pt"
        )
        with torch.inference_mode():
            logits = model(**encoded).logits
        for scores in torch.softmax(logits, dim=-1).tolist():
            probs = {
                model.config.id2label[i].upper(): float(score)
                for i, score in enumerate(scores)
            }
            mapped = {
                {"ENTAILMENT": "S", "CONTRADICTION": "C", "NEUTRAL": "U"}.get(k, k): v
                for k, v in probs.items()
            }
            if set(mapped) != {"S", "C", "U"}:
                raise ValueError(f"Unexpected NLI labels: {mapped}")
            found.append(mapped)
    return found

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", default="reports/stage1a_hypotheses")
    ap.add_argument("--limit", type=int, default=0, help="0 means all available reviews; positive N means first N rows")
    args = ap.parse_args()
    if args.limit < 0:
        raise ValueError("limit must be zero or positive")

    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    import torch

    tokenizer = AutoTokenizer.from_pretrained(MODEL)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL).eval()
    reviews = read_jsonl(ROOT / "data/processed/reviews.jsonl")
    selected = list(range(len(reviews)))[:args.limit or None]
    if not selected:
        raise RuntimeError("No review records found")
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
            kinds = ("paraphrases", "facets", "opposing")
            all_hypotheses = [h for kind in kinds for h in config[kind]]
            predictions = iter(batch_nli(tokenizer, model, review["text"], all_hypotheses, torch))
            for kind in kinds:
                pairs = []
                for hypothesis in config[kind]:
                    probs = next(predictions)
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
                   "selection": "all available repo reviews (or first N if --limit set)",
                   "historical_30_review_rows": len(set(selected) & set(GOLD))},
        "historical_30_review_subset": summarize([r for r in results if r["row"] in GOLD]) if set(selected) >= set(GOLD) else None,
        "review_length_words": {"min": min(len(r["review"].split()) for r in results),
                                "max": max(len(r["review"].split()) for r in results),
                                "mean": round(sum(len(r["review"].split()) for r in results)/len(results), 1)},
        "hypotheses": HYPOTHESES,
        "by_emotion": summarize(results),
        "limitations": [
            "No human-rated ground truth; no accuracy/precision/F1 measured.",
            "Paraphrases are not guaranteed perfectly equivalent.",
            "Facets are distinct supporting qualities; their disagreement is descriptive.",
            "Opposite atmosphere claims are not strict logical complements.",
            "NLI softmax probabilities are not calibrated confidence or emotional strength.",
            "Reviews grouped by locations are not independent samples; counts refer to observed corpus only.",
            "Review truncation is limited to the model token window (512); longer reviews could lose content.",
        ],
    }
    (dest / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary["by_emotion"], indent=2), flush=True)

if __name__ == "__main__":
    main()

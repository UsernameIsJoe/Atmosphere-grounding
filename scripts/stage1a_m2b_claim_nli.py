#!/usr/bin/env python3
"""M2b: controlled claim-level vs whole-review NLI with relation ablations.
Synthetic authored cases test logical behavior, NOT real-review accuracy or
the quality of any ABSA model. No extractor is run in this experiment.
"""
import argparse
import json
import statistics
import time
from pathlib import Path

MODEL = "facebook/bart-large-mnli"
HYPOTHESES = {
    "calm": "The atmosphere of this location is calm.",
    "inviting": "This location has an inviting atmosphere.",
    "safe": "This location feels physically safe for visitors.",
}
CASES = [
    ("quiet_yes", [("The park is quiet.", "park", "quiet")]),
    ("quiet_no", [("The park is not quiet.", "park", "not quiet")]),
    ("noise_yes", [("The traffic is deafening.", "traffic", "deafening")]),
    ("noise_no", [("The traffic is not deafening.", "traffic", "not deafening")]),
    ("safe_yes", [("The path feels safe.", "path", "safe")]),
    ("safe_no", [("The path does not feel safe.", "path", "does not feel safe")]),
    ("welcome_yes", [("The entrance is welcoming.", "entrance", "welcoming")]),
    ("welcome_no", [("The entrance is not welcoming.", "entrance", "not welcoming")]),
    ("parking_zero", [("There is zero adequate bike parking.", "bike parking", "zero adequate")]),
    ("parking_adequate", [("There is adequate bike parking.", "bike parking", "adequate")]),
    ("garden_traffic", [("The gardens are beautiful.", "gardens", "beautiful"),
                        ("The traffic is deafening.", "traffic", "deafening")]),
    ("garden_traffic_quiet", [("The gardens are beautiful.", "gardens", "beautiful"),
                              ("The traffic is quiet.", "traffic", "quiet")]),
    ("benches_lighting", [("The benches are comfortable.", "benches", "comfortable"),
                          ("The lighting is harsh.", "lighting", "harsh")]),
    ("mixed_welcome", [("The entrance is welcoming.", "entrance", "welcoming"),
                       ("The path feels unsafe.", "path", "unsafe")]),
    ("mixed_safe", [("The path feels safe.", "path", "safe"),
                    ("The stairs are dangerous.", "stairs", "dangerous")]),
    ("reviewer_only", [("I was happy because I found my phone.", "phone", "found")]),
    ("negative_review_with_park", [("The park is beautiful.", "park", "beautiful"),
                                   ("Sirens are loud.", "Sirens", "loud")]),
    ("two_positive", [("The garden is peaceful.", "garden", "peaceful"),
                      ("The walkway is quiet.", "walkway", "quiet")]),
]

def offsets(text, phrase):
    i = text.find(phrase)
    if i < 0 or text.find(phrase, i + 1) >= 0:
        raise ValueError("Phrase missing or ambiguous: " + repr((text, phrase)))
    return {"text": phrase, "start": i, "end": i + len(phrase)}

def dataset():
    output = []
    for case_id, triples in CASES:
        claims = [
            {"text": text, "aspect": offsets(text, aspect), "opinion": offsets(text, opinion)}
            for text, aspect, opinion in triples
        ]
        output.append({"id": case_id, "review": " ".join(c["text"] for c in claims), "claims": claims})
    return output

def structured(claims, swap=False):
    opinions = [x["opinion"]["text"] for x in claims]
    if swap and len(opinions) > 1:
        opinions = opinions[1:] + opinions[:1]
    return " ".join(
        "At this location, " + c["aspect"]["text"] + " is described as " + opinion + "."
        for c, opinion in zip(claims, opinions)
    )

def evidence_set(predictions):
    labels = [x["label"] for x in predictions]
    return {
        "any_support": "entailment" in labels,
        "any_contradiction": "contradiction" in labels,
        "mixed_evidence": "entailment" in labels and "contradiction" in labels,
        "all_neutral": all(x == "neutral" for x in labels),
        "claim_labels": labels,
    }

def mean_probs(outputs):
    return {k: statistics.mean(o["probs"][k] for o in outputs)
            for k in ("entailment", "neutral", "contradiction")}

def classifier():
    import torch
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    torch.set_num_threads(min(4, torch.get_num_threads()))
    tokenizer = AutoTokenizer.from_pretrained(MODEL)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL).eval()
    mapping = {str(v).lower(): int(k) for k, v in model.config.id2label.items()}
    if set(mapping) != {"entailment", "neutral", "contradiction"}:
        raise ValueError("Unexpected BART label space: " + repr(mapping))
    def classify(premise, hypothesis):
        tokens = tokenizer(premise, hypothesis, return_tensors="pt",
                           truncation=True, max_length=512)
        with torch.inference_mode():
            scores = torch.softmax(model(**tokens).logits[0], dim=-1).tolist()
        probs = {label: scores[index] for label, index in mapping.items()}
        return {"label": max(probs, key=probs.get), "probs": probs}
    return classify

def summarize(rows):
    by_emotion = {}
    for emotion in HYPOTHESES:
        group = [x for x in rows if x["emotion"] == emotion]
        eligible = [x for x in group if x["swap_eligible"]]
        by_emotion[emotion] = {
            "cases": len(group),
            "swappable_cases": len(eligible),
            "duplicate_vs_full_changes": sum(x["duplicate"]["label"] != x["full"]["label"] for x in group),
            "structured_vs_full_changes": sum(x["structured"]["label"] != x["full"]["label"] for x in group),
            "claim_mean_vs_full_changes": sum(x["mean_claim_label"] != x["full"]["label"] for x in group),
            "swapped_vs_structured_changes_on_eligible": sum(
                x["swapped"]["label"] != x["structured"]["label"] for x in eligible),
            "reordered_vs_full_changes_on_eligible": sum(
                x["reordered"]["label"] != x["full"]["label"] for x in eligible),
            "mixed_evidence_flags": sum(x["evidence_set"]["mixed_evidence"] for x in group),
        }
    contrasts = [
        ("quiet_yes", "quiet_no", "calm"),
        ("noise_yes", "noise_no", "calm"),
        ("safe_yes", "safe_no", "safe"),
        ("welcome_yes", "welcome_no", "inviting"),
        ("parking_zero", "parking_adequate", "inviting"),
        ("garden_traffic", "garden_traffic_quiet", "calm"),
    ]
    lookup = {(x["case_id"], x["emotion"]): x for x in rows}
    pairs = []
    for a, b, emotion in contrasts:
        left, right = lookup[(a, emotion)], lookup[(b, emotion)]
        pairs.append({
            "case_ids": [a, b], "emotion": emotion,
            "full_labels": [left["full"]["label"], right["full"]["label"]],
            "structured_labels": [left["structured"]["label"], right["structured"]["label"]],
            "claim_mean_labels": [left["mean_claim_label"], right["mean_claim_label"]],
            "full_support_probability_difference":
                right["full"]["probs"]["entailment"] - left["full"]["probs"]["entailment"],
        })
    return {"by_emotion": by_emotion, "contrastive_pairs": pairs}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", default="reports/stage1a_m2b_claim_nli")
    args = ap.parse_args()
    dest = Path(args.output)
    dest.mkdir(parents=True, exist_ok=True)
    cases = dataset()
    (dest / "controlled_cases.json").write_text(json.dumps(cases, indent=2), encoding="utf-8")
    classify = classifier()
    start = time.perf_counter()
    results = []
    with (dest / "cases.jsonl").open("w", encoding="utf-8") as handle:
        for case in cases:
            claims, review = case["claims"], case["review"]
            premises = {
                "full": review,
                "duplicate": review + " " + review,
                "structured": structured(claims),
                "swapped": structured(claims, swap=True),
                "reordered": " ".join(c["text"] for c in reversed(claims)),
            }
            for emotion, hypothesis in HYPOTHESES.items():
                preds = {k: classify(text, hypothesis) for k, text in premises.items()}
                each = [classify(c["text"], hypothesis) for c in claims]
                mean = mean_probs(each)
                record = {
                    "case_id": case["id"], "emotion": emotion, "hypothesis": hypothesis,
                    "review": review, "claims": claims, "premises": premises,
                    "swap_eligible": len(claims) > 1,
                    **preds,
                    "claim_outputs": each, "claim_mean_probs": mean,
                    "mean_claim_label": max(mean, key=mean.get),
                    "evidence_set": evidence_set(each),
                }
                results.append(record)
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
                handle.flush()
            print("Completed", case["id"], flush=True)
    summary = {
        "checkpoint": MODEL, "cases": len(cases),
        "review_emotion_cases": len(results),
        "inferences": sum(5 + len(x["claims"]) for x in results),
        "elapsed_seconds": round(time.perf_counter() - start, 2),
        "analysis": summarize(results),
        "limitations": [
            "All cases are authored logic probes, not natural-review accuracy.",
            "Aspect/opinion annotations are authored and verified, not actual ABSA model outputs.",
            "Swapped relations are deliberately false; model sensitivity is not correctness.",
            "Structured rewording can change meaning and duplicate/reorder are not length-matched.",
            "Evidence flags derive from NLI argmax; they are not human-validated facts.",
            "Mean across claims can hide support and contradiction; evidence_set preserves both.",
            "No final NLI model, vocabulary, ABSA extractor, or atmosphere score is selected.",
        ],
    }
    (dest / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({"cases": summary["cases"], "inferences": summary["inferences"]}, indent=2))

if __name__ == "__main__":
    main()

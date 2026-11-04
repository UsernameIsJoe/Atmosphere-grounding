#!/usr/bin/env python3
"""Stage 1A M2c: bounded relevance direction check, not a new pipeline.

Tests whether BART's zero-shot metalinguistic relevance judgment separates
obviously pertinent from irrelevant claims before spending effort on gating.
Uses authored diagnostic labels only; no measured real-world accuracy.
"""
import argparse
import json
import statistics
from pathlib import Path

MODEL = "facebook/bart-large-mnli"
EMOTIONS = {
    "calm": ("calm", "The atmosphere of this location is calm."),
    "inviting": ("inviting", "The atmosphere of this location is inviting."),
    "safe": ("physically safe", "This location feels physically safe to visitors."),
}
# Relevance labels are authored experimental EXPECTATIONS, not annotator ground truth.
# D = direct emotional statement, R = related physical/social observation,
# N = deliberately irrelevant or insufficient information.
CASES = [
    ("quiet", "The park is quiet.", "RNN"),
    ("not_quiet", "The park is not quiet.", "RNN"),
    ("traffic_loud", "The traffic is deafening.", "RNN"),
    ("garden_peaceful", "The garden feels peaceful.", "DRN"),
    ("calm_by_lake", "I felt calm while sitting beside the lake.", "DNN"),
    ("calm_after_exam", "I felt calm because my exam was finally over.", "NNN"),
    ("welcoming_entry", "The entrance is welcoming.", "NDN"),
    ("not_welcoming_entry", "The entrance is not welcoming.", "NDN"),
    ("staff_friendly", "The staff greeted visitors warmly.", "NRN"),
    ("comfortable_benches", "The benches are comfortable.", "NRN"),
    ("safe_path", "The path feels safe.", "NND"),
    ("unsafe_path", "The path does not feel safe.", "NND"),
    ("dangerous_stairs", "The stairs are dangerous.", "NNR"),
    ("broken_glass", "Broken glass covers the sidewalk.", "NNR"),
    ("harsh_lighting", "The lighting is harsh.", "NRN"),
    ("adequate_bikes", "There is adequate bike parking.", "NNN"),
    ("zero_bikes", "There is zero adequate bike parking.", "NNN"),
    ("lost_phone", "I was happy because I found my lost phone.", "NNN"),
    ("coffee_quality", "The coffee tasted excellent.", "NNN"),
    ("beautiful_trees", "The trees are beautiful.", "NRN"),
]
ORDER = tuple(EMOTIONS)

def authored_cases():
    items = []
    for case_id, sentence, codes in CASES:
        assert len(codes) == len(ORDER) and set(codes) <= {"D", "R", "N"}
        items.append({"id": case_id, "text": sentence,
                      "expected": dict(zip(ORDER, codes))})
    return items

def relevance_hypothesis(adjective):
    return ("This statement describes something about the location "
            "that is relevant to whether it feels " + adjective + ".")

def nli_classifier():
    import torch
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    torch.set_num_threads(min(4, torch.get_num_threads()))
    tok = AutoTokenizer.from_pretrained(MODEL)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL).eval()
    index = {str(name).lower(): int(i) for i, name in model.config.id2label.items()}
    assert set(index) == {"contradiction", "neutral", "entailment"}
    def score(premise, hypothesis):
        tokens = tok(premise, hypothesis, truncation=True, max_length=512, return_tensors="pt")
        with torch.inference_mode():
            values = torch.softmax(model(**tokens).logits[0], dim=-1).tolist()
        probs = {k: values[i] for k, i in index.items()}
        return {"label": max(probs, key=probs.get), "probs": probs}
    return score

def summarize(records):
    # A fixed directional threshold, not optimized on the authored cases.
    threshold = 0.5
    totals = {}
    for emotion in ORDER:
        rows = [r for r in records if r["emotion"] == emotion]
        yes = [r for r in rows if r["expected"] != "N"]
        no = [r for r in rows if r["expected"] == "N"]
        gate = lambda r: r["relevance"]["probs"]["entailment"] >= threshold
        direct = lambda r: r["direct"]["probs"]["entailment"] >= threshold
        totals[emotion] = {
            "expected_relevant": len(yes), "expected_irrelevant": len(no),
            "gate_recall_relevant": sum(gate(r) for r in yes),
            "gate_false_positives_irrelevant": sum(gate(r) for r in no),
            "direct_support_on_irrelevant": sum(direct(r) for r in no),
            "gate_mean_relevance_prob_expected_relevant":
                round(statistics.mean(r["relevance"]["probs"]["entailment"] for r in yes), 4),
            "gate_mean_relevance_prob_expected_irrelevant":
                round(statistics.mean(r["relevance"]["probs"]["entailment"] for r in no), 4),
            "gate_vs_direct_disagreements": sum(gate(r) != direct(r) for r in rows),
        }
    relevant = [r for r in records if r["expected"] != "N"]
    irrelevant = [r for r in records if r["expected"] == "N"]
    gate = lambda r: r["relevance"]["probs"]["entailment"] >= threshold
    tp = sum(gate(r) for r in relevant)
    fp = sum(gate(r) for r in irrelevant)
    return {
        "threshold": threshold, "by_emotion": totals,
        "overall": {"relevant_expected": len(relevant), "irrelevant_expected": len(irrelevant),
                    "relevant_retained": tp, "irrelevant_retained": fp,
                    "relevant_retention_fraction": round(tp / len(relevant), 4),
                    "irrelevant_retention_fraction": round(fp / len(irrelevant), 4)},
    }

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", default="reports/stage1a_m2c_relevance")
    args = p.parse_args()
    target = Path(args.output)
    target.mkdir(parents=True, exist_ok=True)
    cases = authored_cases()
    (target / "cases.json").write_text(json.dumps(cases, indent=2), encoding="utf-8")
    score = nli_classifier()
    rows = []
    with (target / "results.jsonl").open("w", encoding="utf-8") as handle:
        for case in cases:
            for emotion, (adjective, direct_hypothesis) in EMOTIONS.items():
                row = {
                    "id": case["id"], "text": case["text"],
                    "emotion": emotion, "expected": case["expected"][emotion],
                    "relevance_hypothesis": relevance_hypothesis(adjective),
                    "direct_hypothesis": direct_hypothesis,
                    "direct": score(case["text"], direct_hypothesis),
                    "relevance": score(case["text"], relevance_hypothesis(adjective)),
                }
                rows.append(row)
                handle.write(json.dumps(row) + "\n")
                handle.flush()
            print("Evaluated", case["id"], flush=True)
    report = {
        "checkpoint": MODEL, "n_cases": len(cases), "n_emotion_pairs": len(rows),
        "n_nli_inferences": 2 * len(rows),
        "analysis": summarize(rows),
        "limits": [
            "Hand-authored relevance expectations are NOT independent labels.",
            "Relevance is assessed by generic BART-NLI with a metalinguistic prompt.",
            "The experiment deliberately tests a single fixed threshold; no fitting.",
            "Direct and relevance hypothesis wordings differ; not a calibrated comparison.",
            "No real-review generalization or downstream emotion-accuracy test.",
        ],
    }
    (target / "summary.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report["analysis"]["overall"], indent=2))

if __name__ == "__main__":
    main()

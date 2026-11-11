#!/usr/bin/env python3
"""Real-review semantic relevance gate benchmark, two pretrained cross-encoders.

No synthetic examples, no local LLM, no trained threshold, no hardcoded answers.
Scores are sigmoid(logit), NOT calibrated probabilities. Both directions of an
emotion are included in each frozen natural-language query.
"""
from __future__ import annotations
import argparse
import collections
import json
import math
import statistics
from pathlib import Path
from stage1a_evidence_first_5 import frozen_reviews
from stage1a_panel_pilot import PILOT, sha256

ROOT = Path(__file__).resolve().parents[1]
QUERIES = {
    "calm": "Does this review passage contain evidence of a place being calm or not calm, such as quietness, tranquility, relaxing experiences, noise, stress or chaos? Both favorable and unfavorable evidence count as relevant.",
    "inviting": "Does this review passage contain evidence of a place being inviting or uninviting, such as welcome, approachability, willingness to stay or return, comfortable socializing, exclusion or hostility? Both favorable and unfavorable evidence count as relevant.",
    "safe": "Does this review passage contain evidence of a place being safe or unsafe, such as feeling protected, risks of injury, hazards, traffic danger or security concerns? Both favorable and unfavorable evidence count as relevant.",
}
MODELS = {
    "bge": "BAAI/bge-reranker-v2-m3",
    "minilm": "cross-encoder/ms-marco-MiniLM-L6-v2",
}

def make_pairs(reviews: list[dict]) -> list[dict]:
    return [{"place_id": r["place_id"], "review_index": r["review_index"],
             "source_sha256": r["source_sha256"], "unit_id": u["unit_id"],
             "start": u["start"], "end": u["end"], "emotion": e,
             "clause": u["text"], "query": QUERIES[e]}
            for r in reviews for u in r["units"] for e in PILOT]

def score_pairs(pairs: list[dict], model_id: str, batch_size: int) -> list[float]:
    import torch
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    torch.set_num_threads(2)
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    model = AutoModelForSequenceClassification.from_pretrained(model_id)
    model.eval()
    results = []
    for first in range(0, len(pairs), batch_size):
        batch = pairs[first:first + batch_size]
        encoded = tokenizer([[x["query"], x["clause"]] for x in batch],
                            padding=True, truncation=True, max_length=512,
                            return_tensors="pt")
        with torch.no_grad():
            logits = model(**encoded, return_dict=True).logits.view(-1).float()
            scores = torch.sigmoid(logits).tolist()
        if len(scores) != len(batch):
            raise RuntimeError("Score length mismatch")
        results.extend(float(x) for x in scores)
        print(f"SCORED {first + len(batch)}/{len(pairs)}", flush=True)
    return results

def anchor_audit(rows: list[dict], anchors: list[dict]) -> dict:
    indexed = {(r["place_id"], r["unit_id"], r["emotion"]): r for r in rows}
    found = []
    for a in anchors:
        key = (a["place_id"], a["unit_id"], a["emotion"])
        if key not in indexed or a["quote"] not in indexed[key]["clause"]:
            raise ValueError(f"Missing original anchor text: {key}")
        found.append({**a, "score": indexed[key]["score"]})
    retain = [r["score"] for r in found if r["must"] == "retain"]
    reject = [r["score"] for r in found if r["must"] == "reject"]
    # Anchors indicate 'do not discard'; this is NOT a gold relevance dataset.
    comparisons = [int(a > b) + 0.5 * int(a == b) for a in retain for b in reject]
    return {"anchor_scores": found,
            "retain_median": statistics.median(retain) if retain else None,
            "reject_median": statistics.median(reject) if reject else None,
            "retain_above_reject_pair_fraction": sum(comparisons) / len(comparisons) if comparisons else None,
            "warning": "Selected behavior anchors are not independent relevance truth labels."}

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", type=Path, default=ROOT / "data/processed/reviews.jsonl")
    p.add_argument("--config", type=Path, default=ROOT / "configs/stage1a_evidence_first_5.json")
    p.add_argument("--model", choices=MODELS, required=True)
    p.add_argument("--output", type=Path, default=ROOT / "reports/stage1a_crossencoder_gate_5")
    p.add_argument("--batch-size", type=int, default=4)
    p.add_argument("--prepare-only", action="store_true")
    args = p.parse_args()
    reviews, _ = frozen_reviews(args.input, args.config)
    pairs = make_pairs(reviews)
    if len(pairs) != 60:
        raise ValueError(f"Unexpected number of real clause-emotion pairs: {len(pairs)}")
    anchors = json.loads((ROOT / "data/evaluation/stage1a_gate_anchor_cases.json").read_text())["anchors"]
    indexed = {(r["place_id"], r["unit_id"], r["emotion"]): r for r in pairs}
    for a in anchors:
        k = (a["place_id"], a["unit_id"], a["emotion"])
        if k not in indexed or a["quote"] not in indexed[k]["clause"]:
            raise ValueError(f"Real-source anchor changed: {k}")
    print(f"VERIFIED 5 real reviews, 20 original clauses, {len(pairs)} pairs, {len(anchors)} anchors. Model={MODELS[args.model]}", flush=True)
    if args.prepare_only:
        return
    scores = score_pairs(pairs, MODELS[args.model], args.batch_size)
    if len(scores) != len(pairs) or not all(math.isfinite(x) and 0 <= x <= 1 for x in scores):
        raise ValueError("Invalid scores")
    rows = [{**row, "model": MODELS[args.model], "score": round(score, 7)}
            for row, score in zip(pairs, scores)]
    assert all(r["clause"] for r in rows)
    audit = anchor_audit(rows, anchors)
    # Never choose a threshold from these same examples.
    summary = {
        "model": MODELS[args.model], "n_reviews": len(reviews), "n_pairs": len(rows),
        "score_definition": "sigmoid(cross_encoder_logit); NOT probability",
        "query_sha256": sha256(json.dumps(QUERIES, sort_keys=True)),
        "overall": {"min": min(scores), "median": statistics.median(scores), "max": max(scores)},
        "per_emotion": {
            e: {"min": min(r["score"] for r in rows if r["emotion"] == e),
                "median": statistics.median(r["score"] for r in rows if r["emotion"] == e),
                "max": max(r["score"] for r in rows if r["emotion"] == e)}
            for e in PILOT},
        **audit,
        "warning": "This is a small, non-independent feasibility test with 5 reviews. No threshold chosen."
    }
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / f"{args.model}_scores.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False)+"\n" for row in rows), encoding="utf8")
    (args.output / f"{args.model}_diagnostics.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2)+"\n", encoding="utf8")
    print("SUMMARY "+json.dumps({k:v for k,v in summary.items() if k != "anchor_scores"}), flush=True)
    for r in sorted(rows, key=lambda r:r["score"], reverse=True):
        print("RANK "+json.dumps({"score":r["score"],"emotion":r["emotion"],
              "place_id":r["place_id"],"unit_id":r["unit_id"],"clause":r["clause"]},ensure_ascii=False),flush=True)

if __name__ == "__main__":
    main()

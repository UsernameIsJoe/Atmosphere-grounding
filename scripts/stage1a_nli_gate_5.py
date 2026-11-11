#!/usr/bin/env python3
"""Three-way BART MNLI gate on 5 real Google review texts (60 clause-emotion pairs).

Two PREDECLARED NLI formulations:
(1) direct emotion hypothesis, relevance = entailment + contradiction;
(2) metarelevance hypothesis, relevance = entailment.

Neither softmax result is a calibrated probability of relevance. Model eval
uses actual original clauses with immutable source review hashes, zero LLM calls.
"""
from __future__ import annotations

import argparse
import collections
import json
import math
import statistics
from pathlib import Path

from stage1a_evidence_first_5 import frozen_reviews
from stage1a_crossencoder_gate_5 import make_pairs

ROOT = Path(__file__).resolve().parents[1]
MODEL = "facebook/bart-large-mnli"
HYPOTHESES = {
    "calm": {
        "direct": "This place is calm and peaceful.",
        "meta": "This passage contains evidence about whether the place is calm or not calm.",
    },
    "inviting": {
        "direct": "This place is inviting and welcoming.",
        "meta": "This passage contains evidence about whether the place is inviting or uninviting.",
    },
    "safe": {
        "direct": "This place is safe and free from danger.",
        "meta": "This passage contains evidence about whether the place is safe or unsafe.",
    },
}
PREDECLARED = ("direct", "meta")


def build_inputs(reviews):
    inputs = make_pairs(reviews)
    assert len(inputs) == 60
    return inputs


def infer(pairs, method, batch_size):
    import torch
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    torch.set_num_threads(2)
    tokenizer = AutoTokenizer.from_pretrained(MODEL)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL).eval()
    label2id = {k.lower(): v for k, v in model.config.label2id.items()}
    needed = ("contradiction", "neutral", "entailment")
    if not all(k in label2id for k in needed):
        raise ValueError("Expected actual 3-way MNLI model, got "+str(label2id))
    results = []
    for start in range(0, len(pairs), batch_size):
        chunk = pairs[start:start+batch_size]
        inputs = tokenizer(
            [p["clause"] for p in chunk],
            [HYPOTHESES[p["emotion"]][method] for p in chunk],
            max_length=512, truncation=True, padding=True, return_tensors="pt")
        with torch.no_grad():
            prob = torch.softmax(model(**inputs).logits.float(), dim=-1)
        for row in prob:
            values = {k: float(row[label2id[k]].item()) for k in needed}
            relevance = (1-values["neutral"]) if method == "direct" else values["entailment"]
            results.append({**values, "relevance_score": relevance})
        print("SCORED", method, min(start+batch_size,len(pairs)), "/", len(pairs), flush=True)
    return results


def evaluate(rows, anchors):
    lookup = {(x["place_id"], x["unit_id"], x["emotion"]):x for x in rows}
    out = []
    for item in anchors:
        key = (item["place_id"], item["unit_id"], item["emotion"])
        if key not in lookup or item["quote"] not in lookup[key]["clause"]:
            raise ValueError("Original source anchor missing: "+str(key))
        out.append({**item, "score":lookup[key]["relevance_score"],
                    "entailment":lookup[key]["entailment"], "contradiction":lookup[key]["contradiction"],
                    "neutral":lookup[key]["neutral"]})
    retain = [x["score"] for x in out if x["must"]=="retain"]
    reject = [x["score"] for x in out if x["must"]=="reject"]
    comparisons = [int(x>y)+.5*int(x==y) for x in retain for y in reject]
    return {
        "anchor_scores":out,
        "retain_above_reject_pair_fraction":sum(comparisons)/len(comparisons) if comparisons else None,
        "retain_median":statistics.median(retain) if retain else None,
        "reject_median":statistics.median(reject) if reject else None,
        "warning":"Selection-dependent comparisons on hand-picked behavior anchors, not accuracy or out-of-sample validation",
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input",type=Path,default=ROOT/"data/processed/reviews.jsonl")
    ap.add_argument("--config",type=Path,default=ROOT/"configs/stage1a_evidence_first_5.json")
    ap.add_argument("--output",type=Path,default=ROOT/"reports/stage1a_nli_gate_5")
    ap.add_argument("--method",choices=PREDECLARED,required=True)
    ap.add_argument("--batch-size",type=int,default=4)
    ap.add_argument("--prepare-only",action="store_true")
    args=ap.parse_args()
    reviews,_=frozen_reviews(args.input,args.config)
    pairs=build_inputs(reviews)
    anchors=json.loads((ROOT/"data/evaluation/stage1a_gate_anchor_cases.json").read_text())["anchors"]
    indexed={(p["place_id"],p["unit_id"],p["emotion"]):p for p in pairs}
    for a in anchors:
        k=(a["place_id"],a["unit_id"],a["emotion"])
        if k not in indexed or a["quote"] not in indexed[k]["clause"]:
            raise ValueError("Case audit mismatch: "+str(k))
    print(f"VERIFIED 5 real reviews; 20 clauses; {len(pairs)} pair inputs; {len(anchors)} anchors; method={args.method}",flush=True)
    if args.prepare_only:
        return
    predictions=infer(pairs,args.method,args.batch_size)
    if len(predictions)!=len(pairs):
        raise ValueError("Incomplete inference")
    if not all(all(math.isfinite(v) and 0<=v<=1 for v in p.values()) and abs(sum(p[k] for k in ("entailment","neutral","contradiction"))-1)<0.0001 for p in predictions):
        raise ValueError("Malformed NLI output")
    rows=[{**pair,"method":args.method,"hypothesis":HYPOTHESES[pair["emotion"]][args.method],
           "model":MODEL,**pred} for pair,pred in zip(pairs,predictions)]
    report=evaluate(rows,anchors)
    summary={
        "method":args.method,"model":MODEL,"n_review":5,"n_pairs":len(rows),
        "score_definition":"direct: 1-P(neutral); meta: P(entailment). Uncalibrated NLI scores, not truth probabilities.",
        "score_median":statistics.median(p["relevance_score"] for p in rows),
        "score_min":min(p["relevance_score"] for p in rows),
        "score_max":max(p["relevance_score"] for p in rows),
        "per_emotion":{e:{"median":statistics.median(p["relevance_score"] for p in rows if p["emotion"]==e),
                         "min":min(p["relevance_score"] for p in rows if p["emotion"]==e),
                         "max":max(p["relevance_score"] for p in rows if p["emotion"]==e)}
                       for e in HYPOTHESES},
        **report,
        "notes":"No cutoff chosen. Source-grounded human audit anchors are not independent gold labels. No LLM calls."
    }
    args.output.mkdir(parents=True,exist_ok=True)
    (args.output/f"{args.method}_scores.jsonl").write_text(
        "".join(json.dumps(r,ensure_ascii=False)+"\n" for r in rows),encoding="utf-8")
    (args.output/f"{args.method}_diagnostics.json").write_text(
        json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("SUMMARY "+json.dumps({k:v for k,v in summary.items() if k!="anchor_scores"}),flush=True)
    for r in sorted(rows,key=lambda x:-x["relevance_score"]):
        print("RANK "+json.dumps({k:r[k] for k in ("relevance_score","entailment","contradiction","neutral","emotion","place_id","unit_id","clause")},ensure_ascii=False),flush=True)

if __name__=="__main__":
    main()

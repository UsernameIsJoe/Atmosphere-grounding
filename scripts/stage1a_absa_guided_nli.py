#!/usr/bin/env python3
"""ABSA-guided source-clause NLI, using the successful integrated pilot artifact.

No paraphrase, no hard filtering. ABSA affects which ORIGINAL clause receives
NLI, and supplies source attribution; blind segmentation is a matched control.
"""
import argparse
import collections
import json
import re
from pathlib import Path

MODEL = "facebook/bart-large-mnli"
# Only contrastive clause boundaries with a distinct conjunction or semicolon.
BOUNDARY = re.compile(r";|,?\\s+but\\s+|,?\\s+however,?\\s+|,?\\s+whereas\\s+", re.I)

def jsonl(path):
    return [json.loads(x) for x in Path(path).read_text(encoding="utf-8").splitlines() if x.strip()]

def split_original(sentence):
    """Subspans with absolute offsets; no invented text and no silent loss.

    Negations are not stripped. Contrastive delimiters remain with the
    following clause to retain contrast markers.
    """
    text, start = sentence["text"], sentence["start"]
    boundaries = [0]
    for match in BOUNDARY.finditer(text):
        # Split before the contrast marker, but keep marker in the next span.
        boundaries.append(match.start())
    boundaries.append(len(text))
    result = []
    for lo, hi in zip(boundaries, boundaries[1:]):
        fragment = text[lo:hi]
        if fragment.strip():
            ltrim = len(fragment) - len(fragment.lstrip())
            rtrim = len(fragment.rstrip())
            left, right = start+lo+ltrim, start+lo+rtrim
            result.append({"start":left,"end":right,"text":text[lo+ltrim:lo+rtrim]})
    return result or [{"start":start,"end":sentence["end"],"text":text}]

def anchors(sentence):
    """Only source-exact ABSA anchors: DeBERTa/SetFit aspect or AOS pair."""
    positions = []
    for a in sentence["aspects"]:
        if sentence["start"] <= a["start"] < a["end"] <= sentence["end"]:
            positions.append(("aspect",a["start"],a["end"],a["source"]))
    for relation in sentence["relations"]:
        a,o=relation["aspect"],relation["opinion"]
        if (sentence["start"] <= a["start"] < a["end"] <= sentence["end"]
                and sentence["start"] <= o["start"] < o["end"] <= sentence["end"]):
            positions.append(("relation",min(a["start"],o["start"]),
                              max(a["end"],o["end"]),"aos_t5"))
    return positions

def evidence_units(sentence):
    clauses = split_original(sentence)
    observed = anchors(sentence)
    units = []
    for piece in clauses:
        span_in = [x for x in observed if piece["start"] <= x[1] and x[2] <= piece["end"]]
        # AOS pair spanning two clauses remains in original whole-sentence
        # fallback rather than inventing cross-boundary relation.
        units.append({**piece,"source_sentence_index":sentence["sentence_index"],
                      "anchor_types": sorted(set(x[0] for x in span_in)),
                      "anchor_sources": sorted(set(x[3] for x in span_in)),
                      "absa_guided": bool(span_in),
                      "whole_sentence_fallback": False})
    straddles = [x for x in observed if not any(
        c["start"] <= x[1] and x[2] <= c["end"] for c in units)]
    if straddles:
        # Preserve original sentence as a fallback for unresolved spans.
        units.append({"start":sentence["start"],"end":sentence["end"],
                      "text":sentence["text"],
                      "source_sentence_index":sentence["sentence_index"],
                      "anchor_types":["cross_clause_relation"],
                      "anchor_sources":sorted(set(x[3] for x in straddles)),
                      "absa_guided":True,"whole_sentence_fallback":True})
    return units

def predict_factory():
    import torch
    from transformers import AutoTokenizer,AutoModelForSequenceClassification
    torch.set_num_threads(min(4,torch.get_num_threads()))
    tok=AutoTokenizer.from_pretrained(MODEL)
    model=AutoModelForSequenceClassification.from_pretrained(MODEL).eval()
    labels={str(v).lower():int(k) for k,v in model.config.id2label.items()}
    if set(labels)!={"entailment","neutral","contradiction"}:
        raise ValueError("Unexpected NLI label mapping")
    def predict(premise,hypothesis):
        tokens=tok(premise,hypothesis,return_tensors="pt",truncation=False)
        if tokens["input_ids"].shape[-1]>512:
            raise ValueError("NLI input exceeds 512 tokens: refusing truncation")
        with torch.inference_mode():
            p=torch.softmax(model(**tokens).logits[0],dim=-1).tolist()
        probs={k:float(p[v]) for k,v in labels.items()}
        return {"probs":probs,"label":max(probs,key=probs.get)}
    return predict

def build_records(rows,predict):
    # One set of units per review, cached to avoid repeating extraction.
    allout=[]
    for rec in rows:
        all_units=[unit for sentence in rec["claims"] for unit in evidence_units(sentence)]
        if any(rec["review"][u["start"]:u["end"]] !=u["text"] for u in all_units):
            raise ValueError("Evidence unit does not match original review")
        baseline_label=[(x["sentence_index"],x["direct_nli"]["label"]) for x in rec["claims"]]
        output=[]
        for unit in all_units:
            assessed=predict(unit["text"],rec["hypothesis"])
            output.append({**unit,"nli":assessed,
                           "absa_evidence_lane":"indexed" if unit["absa_guided"] else "unmatched"})
        # ABSA metadata determines which units are indexed, but unmatched clauses
        # are always retained in the comparison.
        anchored=[x for x in output if x["absa_guided"]]
        unanchored=[x for x in output if not x["absa_guided"]]
        allout.append({
            "row":rec["row"],"place_id":rec["place_id"],"review":rec["review"],
            "emotion":rec["emotion"],"hypothesis":rec["hypothesis"],
            "full_review_nli":rec["full_review_nli"],
            "sentence_nli":baseline_label,"units":output,
            "summary":{
                "units":len(output),"absa_indexed":len(anchored),
                "unmatched_kept":len(unanchored),
                "refined_units":sum(x["text"]!=rec["claims"][x["source_sentence_index"]]["text"]
                                    for x in output),
                "indexed_support":sum(x["nli"]["label"]=="entailment" for x in anchored),
                "indexed_contradiction":sum(x["nli"]["label"]=="contradiction" for x in anchored),
                "unmatched_support":sum(x["nli"]["label"]=="entailment" for x in unanchored),
                "unmatched_contradiction":sum(x["nli"]["label"]=="contradiction" for x in unanchored),
                "conflicting_indexed_evidence":any(x["nli"]["label"]=="entailment" for x in anchored)
                   and any(x["nli"]["label"]=="contradiction" for x in anchored),
            }
        })
    return allout

def summarize(out):
    by_emotion={}
    for emotion in ("calm","inviting","safe"):
        rr=[r for r in out if r["emotion"]==emotion]
        by_emotion[emotion]={
            "reviews":len(rr),
            "units":sum(r["summary"]["units"] for r in rr),
            "indexed":sum(r["summary"]["absa_indexed"] for r in rr),
            "unmatched_kept":sum(r["summary"]["unmatched_kept"] for r in rr),
            "units_shorter_than_sentence":sum(r["summary"]["refined_units"] for r in rr),
            "reviews_with_conflicting_indexed_evidence":sum(
                r["summary"]["conflicting_indexed_evidence"] for r in rr),
            "review_units_with_new_nli_label":sum(
                u["nli"]["label"] != dict(r["sentence_nli"])[u["source_sentence_index"]]
                for r in rr for u in r["units"]),
        }
    return {"by_emotion":by_emotion,
            "limitations":[
                "ABSA indexes source clauses; it does not establish relevance or correctness.",
                "Clause splitting is punctuation/contrast based, not a trained parser.",
                "Unmatched original clauses remain in output; no claims removed.",
                "Changed NLI outputs alone do not demonstrate improved atmosphere accuracy.",
                "AOS aspects/opinions are sparse and source matching does not guarantee semantic validity.",
                "No final review- or location-level emotion aggregation selected.",
            ]}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",default="reports/stage1a_integrated/review_evidence.jsonl")
    p.add_argument("--output",default="reports/stage1a_absa_guided")
    args=p.parse_args()
    rows=jsonl(args.input)
    if len(rows)!=60 or len({(r["row"],r["emotion"]) for r in rows})!=60:
        raise ValueError("Expected 20 reviews x 3 emotions from integrated run")
    out=build_records(rows,predict_factory())
    target=Path(args.output)
    target.mkdir(parents=True,exist_ok=True)
    with (target/"review_evidence.jsonl").open("w",encoding="utf-8") as f:
        for row in out:
            f.write(json.dumps(row,ensure_ascii=False)+"\n")
    report=summarize(out)
    (target/"summary.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps(report["by_emotion"],indent=2))

if __name__=="__main__":
    main()

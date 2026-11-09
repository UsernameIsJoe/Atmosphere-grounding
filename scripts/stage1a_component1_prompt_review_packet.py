#!/usr/bin/env python3
"""Build side-by-side, source-aligned A0/A1/A2 human-readiness review packet.

No automatic 'winner' or fake precision / recall. Human correctness fields are
blank until evidence is independently assessed.
"""
import argparse
import csv
import json
from pathlib import Path

def read(path):
    return [json.loads(x) for x in Path(path).read_text(encoding="utf8").splitlines() if x.strip()]

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--baseline",default="reports/component1_ollama_qwen3_8b/predictions.jsonl")
    p.add_argument("--test",default="reports/component1_prompt_readiness/diagnostic/predictions.jsonl")
    p.add_argument("--output",default="reports/component1_prompt_readiness/diagnostic/review_packet.csv")
    args=p.parse_args()
    base=read(args.baseline);test=read(args.test)
    original={(x["source"]["row"],x["source"]["sentence_index"]):x for x in base}
    found={}
    for x in test:
        src=x["source"];k=(src["row"],src["sentence_index"])
        if k not in original or src["original_sentence"]!=original[k]["source"]["original_sentence"]:
            raise ValueError("Mismatch from frozen source")
        if x["condition"] not in ("A1","A2"):raise ValueError("Invalid prompt variant")
        key=(k,x["condition"])
        if key in found:raise ValueError("Duplicate prompt result")
        found[key]=x
    keys=sorted({k for k,v in found})
    if any((k,v) not in found for k in keys for v in ("A1","A2")):
        raise ValueError("Incomplete matched prompt results")
    rows=[]
    for k in keys:
        src=original[k]["source"]
        for v,obs in (("A0",original[k]["C"]["observations"]),
                      ("A1",found[k,"A1"]["observations"]),
                      ("A2",found[k,"A2"]["observations"])):
            for i,c in enumerate(obs):
                rows.append({"row":k[0],"sentence_index":k[1],
                  "source_sentence":src["original_sentence"],
                  "condition":v,"candidate_index":i,
                  "claim":c["claim"],"subject":c["subject"],"predicate":c["predicate"],
                  "object":c["object"],"qualifiers":c["qualifiers"],
                  "source_quote":c["evidence_quote"],
                  "quote_match_status":c["quote_match_status"],
                  "self_verifier":c["verifier"]["verdict"],
                  "automated_status":c["status"],
                  "human_claim_correct":"","human_relation_correct":"",
                  "human_negation_uncertainty_preserved":"",
                  "human_source_grounded":"","human_notes":""})
        rows.append({"row":k[0],"sentence_index":k[1],
          "source_sentence":src["original_sentence"],
          "condition":"HUMAN_SOURCE_OMISSIONS","candidate_index":"",
          "claim":"","subject":"","predicate":"","object":"","qualifiers":"",
          "source_quote":"","quote_match_status":"","self_verifier":"","automated_status":"",
          "human_claim_correct":"","human_relation_correct":"",
          "human_negation_uncertainty_preserved":"",
          "human_source_grounded":"","human_notes":
          "Independently record every essential observation missing from A0/A1/A2; verify source context"})
    if not rows:raise ValueError("No outputs")
    path=Path(args.output);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("w",encoding="utf-8-sig",newline="") as f:
        wr=csv.DictWriter(f,fieldnames=list(rows[0]));wr.writeheader();wr.writerows(rows)
    print(json.dumps({"source_sentences":len(keys),"candidate_review_rows":len(rows)-len(keys),
        "source_omission_review_rows":len(keys),"output":str(path),
        "human_accuracy_measured":False},indent=2))
if __name__=="__main__":main()

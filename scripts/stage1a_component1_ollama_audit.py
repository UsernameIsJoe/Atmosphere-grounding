#!/usr/bin/env python3
"""Build a real-source human audit packet for the A/B/C extraction experiment.

Never invent gold labels. Output CSV rows for independent human review,
including omissions per original sentence and direct candidate-level judgments.
"""
import argparse
import csv
import json
from pathlib import Path

def read_jsonl(path):
    return [json.loads(s) for s in Path(path).read_text(encoding="utf8").splitlines() if s.strip()]

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--ollama",required=True,help="B/C predictions.jsonl from local Ollama")
    p.add_argument("--baseline",default=None,help="Optional existing A reconciled.jsonl from GitHub Actions")
    p.add_argument("--output",default="reports/component1_ollama_human_audit.csv")
    args=p.parse_args()
    runs=read_jsonl(args.ollama)
    rows=[];seen=set()
    for r in runs:
        s=r["source"]
        key=(s["row"],s["sentence_index"])
        if key in seen:raise ValueError("Duplicate B/C sentence key")
        seen.add(key)
        text=s["original_sentence"]
        if s["original_review"][s["sentence_start"]:s["sentence_end"]]!=text:
            raise ValueError("Source offsets mismatch")
        rows.append(dict(row=s["row"],sentence_index=s["sentence_index"],
          source_sentence=text,condition="SOURCE_OMISSIONS",candidate_id="",
          subject="",predicate="",object="",claim="",evidence_quote="",
          model_check="",candidate_correct="",relationship_correct="",
          negation_attribution_preserved="",missing_observations_notes="",
          human_notes=""))
        for c in r["C"]["observations"]:
            rows.append(dict(row=s["row"],sentence_index=s["sentence_index"],
              source_sentence=text,condition="LLM_B_C",candidate_id=c["index"],
              subject=c["subject"],predicate=c["predicate"],object=c["object"],
              claim=c["claim"],evidence_quote=c["evidence_quote"],
              model_check=c["status"]+" / "+c["verifier"]["verdict"],
              candidate_correct="",relationship_correct="",
              negation_attribution_preserved="",missing_observations_notes="",
              human_notes=""))
    if args.baseline:
        base=read_jsonl(args.baseline)
        data={(r["source"]["row"],r["source"]["sentence_index"]):r for r in base}
        if set(data)!=seen:raise ValueError("A and B/C use different real sentence identities")
        for k,b in data.items():
            text=b["source"]["sentence"]
            for c in b["component1"]["claims"]:
                a=c["head"];z=c["tail"]
                rows.append(dict(row=k[0],sentence_index=k[1],
                  source_sentence=text,condition="BASELINE_A",
                  candidate_id=c["id"],subject=a["text"],predicate=c["kind"],
                  object=z["text"],claim="",evidence_quote="",
                  model_check=c["status"],candidate_correct="",
                  relationship_correct="",negation_attribution_preserved="",
                  missing_observations_notes="",human_notes=""))
    out=Path(args.output)
    out.parent.mkdir(parents=True,exist_ok=True)
    fields=["row","sentence_index","source_sentence","condition","candidate_id",
      "subject","predicate","object","claim","evidence_quote","model_check",
      "candidate_correct","relationship_correct","negation_attribution_preserved",
      "missing_observations_notes","human_notes"]
    with out.open("w",newline="",encoding="utf-8-sig") as fp:
        wr=csv.DictWriter(fp,fieldnames=fields);wr.writeheader()
        wr.writerows(sorted(rows,key=lambda r:(int(r["row"]),int(r["sentence_index"]),
                0 if r["condition"]=="SOURCE_OMISSIONS" else 1 if r["condition"]=="BASELINE_A" else 2,
                str(r["candidate_id"]))))
    print(json.dumps({"source_sentences":len(seen),"human_audit_rows":len(rows),
        "output":str(out),"human_labels_created":0,
        "note":"Fill the correctness/omissions columns by inspecting original reviews, not from model scores."},indent=2))
if __name__=="__main__":main()

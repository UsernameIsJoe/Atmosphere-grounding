#!/usr/bin/env python3
"""Stage 1A checkpoint protocol audit. Model-card examples are NOT an independent benchmark."""
import argparse, collections, json, pathlib, sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from stage1a_absa_official_sentence_inference import build_extractor
from stage1a_relation_pilot import parse_triplets
from stage1a_absa_real_review_comparison import load_jsonl, compare

AOS_CASES=[
 ("The gym is outdated and the rooms are dirty.",[("gym","outdated","negative"),("rooms","dirty","negative")]),
 ("Great location near two subway lines.",[("location","great","positive")]),
 ("Free breakfast with fresh pastries and good coffee.",[("breakfast","free","positive"),("pastries","fresh","positive"),("coffee","good","positive")]),
 ("High parking fee.",[("parking","high fee","negative")]),
 ("Front desk service was quick, although the elevator was slow.",[("front desk service","quick","positive"),("elevator","slow","negative")]),
 ("No in-room coffeemakers or flat screen TVs.",[("room amenities","no","negative")]),
]
GTS_CASES=[
 ("The Dell Inspiron 14 Plus is the most well-rounded laptop with great display and battery life that money can buy.",[("display","great","positive"),("battery life","great","positive")])
]
def norm(s):return " ".join(str(s).lower().split()).strip(" .,!?:;")
def triple(rel):
 return [str(rel["aspect"]["text"]),str(rel["opinion"]["text"]),str(rel.get("polarity",""))]
def run_card(method):
 import spacy
 predictor=build_extractor(method,spacy.blank("en"))
 cases=AOS_CASES if method=="aos_t5" else GTS_CASES
 out=[]
 for text,expected in cases:
  x=predictor(text)
  decoded=x.get("raw_generation")
  if method=="aos_t5":
   raw_pairs,_=parse_triplets(decoded or "")
   observed=[list(t) for t in raw_pairs]
  else: observed=[list(t[:3]) for t in decoded]
  hits=sum(any(all(norm(z)==norm(y) for z,y in zip(e,o)) for o in observed) for e in expected)
  out.append(dict(text=text,reference=[list(t) for t in expected],predicted=observed,raw=decoded,parsed_status=x["parse_status"],reference_triplets_recovered=hits,n_reference_triplets=len(expected)))
 return dict(method=method,source="examples from the checkpoint's own model card; not a held-out benchmark",cases=out,
             reference_recovered=sum(x["reference_triplets_recovered"] for x in out),
             reference_total=sum(x["n_reference_triplets"] for x in out))
def analyze_existing(root):
 reference=json.loads((ROOT/"data/evaluation/stage1a_absa_real_review_targets_v1.json").read_text())
 rows={name:load_jsonl(root/name/"review_cases.jsonl") for name in ("aos_t5","gts_joint_aste","dependency")}
 scored=compare(reference,rows)
 report={"reference_status":reference["status"],"models":{},"warnings":["Partial target recovery is not precision/recall/F1.","Only source-exact grounded matches qualify for existing recovery; implicit aspects are omitted.","This audit does not adjudicate semantic correctness or atmosphere relevance."]}
 for name,cases in rows.items():
  sentences=[s for c in cases for s in c["sentences"]]
  status=collections.Counter(s["extraction"]["parse_status"] for s in sentences)
  raw_unparsed=[dict(row=c["row"],sentence=s["text"],raw=s["extraction"].get("raw_generation")) for c in cases for s in c["sentences"] if s["extraction"]["parse_status"]=="unparsed_generation"]
  rels=[r for c in cases for r in c["extraction"]["relations"]]
  implicit=sum(not r.get("grounded",False) for r in rels)
  report["models"][name]=dict(status_counts=dict(status),unparsed_examples=raw_unparsed,unverified_relations=implicit,
   source_grounded_relations=sum(r.get("grounded",False) for r in rels),
   partial_reference_recovered=scored[name]["targets_recovered"],partial_reference_total=scored[name]["reference_targets"])
  audit_path=root/f"{name}_all_predictions.jsonl"
  audit_path.write_text("".join(json.dumps(dict(row=c["row"],review=c["review"],relations=c["extraction"]["relations"],sentences=c["sentences"]),ensure_ascii=False)+"\n" for c in cases))
 return report
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--card",choices=["aos_t5","gts_joint_aste"])
 p.add_argument("--existing",type=pathlib.Path)
 p.add_argument("--output",required=True,type=pathlib.Path)
 args=p.parse_args()
 args.output.mkdir(parents=True,exist_ok=True)
 if args.card: data=run_card(args.card); file=args.output/(args.card+"_card.json")
 else: data=analyze_existing(args.existing); file=args.output/"existing_real_review_audit.json"
 file.write_text(json.dumps(data,ensure_ascii=False,indent=2))
 print(json.dumps(data,ensure_ascii=False,indent=2))
if __name__=="__main__": main()

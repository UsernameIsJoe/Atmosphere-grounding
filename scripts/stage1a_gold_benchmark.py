#!/usr/bin/env python3
"""Stage 1A: reproducible real-review benchmark packet and honest scorer.

No model-generated labels are allowed as ground truth. The blank annotation
template must be completed independently before precision/F1 is claimed.
"""
import argparse, json, pathlib, sys, collections
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from stage1a_absa_official_sentence_inference import load_cases

def packet(path):
    cases,_=load_cases()
    rows=[]
    for case in cases:
        for s in case["sentences"]:
            rows.append({"row":case["row"],"place_id":case["place_id"],
              "review_index":case["review_index"],"sentence_index":s["sentence_index"],
              "sentence_start":s["start"],"text":s["text"],
              "triplets":None,"atmosphere_evidence":None,"annotator":None,
              "notes":None})
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("w") as f:
        for x in rows: f.write(json.dumps(x,ensure_ascii=False)+"\n")
    print(json.dumps({"reviews":len(cases),"sentences":len(rows),
      "annotation_status":"UNLABELED","annotation_path":str(path)},indent=2))

def key(x):
    return (int(x["row"]),int(x["sentence_index"]))

def normalized(s): return " ".join(str(s).strip().lower().split()).strip(".,;:!? ")

def extract_prediction(cases):
    out={}
    for c in cases:
        for sent in c["sentences"]:
            items=[]
            for r in sent["extraction"]["relations"]:
                items.append({"aspect":r["aspect"]["text"],"opinion":r["opinion"]["text"],
                  "polarity":r.get("polarity"),"grounded":r.get("grounded",False)})
            out[key(dict(row=c["row"],sentence_index=sent["sentence_index"]))]=items
    return out

def score(reference,predictions):
    # strict match, matching cardinality; works only on COMPLETE annotated data.
    gold={key(x):x for x in reference}
    if len(gold)!=len(reference):raise ValueError("Duplicate sentence ID")
    if any(x.get("triplets") is None or x.get("annotator") is None or x.get("atmosphere_evidence") is None for x in reference):
        raise ValueError("Incomplete reference: refusing precision, recall or F1")
    if set(predictions)!=set(gold):raise ValueError("Prediction/gold sentence identities differ")
    tp=fp=fn=0
    for k,x in gold.items():
        wanted=collections.Counter(tuple(normalized(t[v]) for v in ("aspect","opinion","polarity")) for t in x["triplets"])
        found=collections.Counter(tuple(normalized(t.get(v,"")) for v in ("aspect","opinion","polarity")) for t in predictions[k])
        matched=sum((wanted & found).values())
        tp+=matched;fp+=sum(found.values())-matched;fn+=sum(wanted.values())-matched
    precision=tp/(tp+fp) if tp+fp else 0
    recall=tp/(tp+fn) if tp+fn else 0
    return {"tp":tp,"fp":fp,"fn":fn,"precision":precision,"recall":recall,
            "f1":2*precision*recall/(precision+recall) if precision+recall else 0,
            "status":"scored only against complete human-adjudicated reference"}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--packet",type=pathlib.Path)
    p.add_argument("--gold",type=pathlib.Path)
    p.add_argument("--predictions",type=pathlib.Path)
    args=p.parse_args()
    if args.packet:packet(args.packet);return
    if not args.gold or not args.predictions:p.error("Must specify --packet or both --gold and --predictions")
    g=[json.loads(l) for l in args.gold.read_text().splitlines() if l]
    predictions=[json.loads(l) for l in args.predictions.read_text().splitlines() if l]
    print(json.dumps(score(g,extract_prediction(predictions)),indent=2))

if __name__=="__main__":main()

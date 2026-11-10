#!/usr/bin/env python3
"""Real Google Places review-only diagnostic of evidence type vs generic NLI.

No synthetic premises, no LLM-written paraphrases, no emotion gold labels.
Real text is copied verbatim from the Google Places API-derived reviews.jsonl.
The two NLI hypotheses per emotion are authored, explicitly documented prompts.
"""
import argparse
import collections
import hashlib
import json
import pathlib
import re
import statistics
import time

ROOT=pathlib.Path(__file__).resolve().parents[1]
MODEL="facebook/bart-large-mnli"
HYPOTHESES={
 "calm":{"direct":"The atmosphere of this location is calm.",
         "relevance":"This statement describes something about the location that is relevant to whether it feels calm."},
 "inviting":{"direct":"The atmosphere of this location is inviting.",
         "relevance":"This statement describes something about the location that is relevant to whether it feels inviting."},
 "safe":{"direct":"This location feels physically safe to visitors.",
         "relevance":"This statement describes something about the location that is relevant to whether it feels physically safe."}
}
# Heuristic pools are NOT human reference labels; do not evaluate classification
# accuracy against them. They only pre-stratify a real-review diagnostic sample.
FEEL=re.compile(r"\b(feel|feels|felt|comforted|protected)\b",re.I)
AFFECT=re.compile(r"\b(peaceful|calm|quiet|safe|protected|comforted|welcome|welcomed|comfortable|inviting|relax(?:ing|ed)?|refreshing|cozy|unsafe|anxious|scared|secure|stress(?:-free)?|peace|welcoming|reverence)\b",re.I)
ATMOS=re.compile(r"\b(peaceful|calm|quiet|cozy|inviting|welcoming|safe|unsafe|noisy|crowded|relaxing|sketchy|hectic|serene|tranquil|lively)\b",re.I)
INDIC=re.compile(r"\b(patrol(?:led)?|police|sirens?|traffic|gates?|lights?|shade|benches|trees|elevator|public|open|fence|busy|crowds?|paths?|accessible|playground|stairs|wheelchair|noise)\b",re.I)
SPLIT=re.compile(r"(?<=[.!?])\s+")

def read(path):
 return [json.loads(x) for x in pathlib.Path(path).read_text(encoding="utf8").splitlines() if x.strip()]

def collect_candidates(reviews):
 pools=collections.defaultdict(list)
 for row,review in enumerate(reviews):
  source=review["text"];position=0
  for j,part in enumerate(SPLIT.split(source)):
   if not part.strip():continue
   a=source.find(part,position)
   if a<0:raise AssertionError("Sentence not an exact source substring")
   b=a+len(part);position=b
   if len(part.split())<4 or len(part.split())>85:continue
   # The following ordering is a preregistered diagnostic sampling rule.
   if FEEL.search(part) and AFFECT.search(part):
    category="reported_experience_candidate"
   elif ATMOS.search(part):
    category="explicit_atmosphere_candidate"
   elif INDIC.search(part):
    category="environmental_indicator_candidate"
   else:category="general_or_unrelated_control"
   pools[category].append({
    "row":row,"place_id":review["place_id"],"review_index":review["review_index"],
    "publish_time":review["publish_time"],"sentence_index":j,
    "start":a,"end":b,"source_sentence":part,"category":category,
    "review_sha256":hashlib.sha256(source.encode("utf8")).hexdigest()})
 return pools

def select(reviews,per_category):
 pools=collect_candidates(reviews)
 categories=("reported_experience_candidate","explicit_atmosphere_candidate",
  "environmental_indicator_candidate","general_or_unrelated_control")
 selected=[]
 for category in categories:
  # Round robin: prefer coverage across places rather than only the first park.
  byplace=collections.defaultdict(list)
  for x in pools[category]:byplace[x["place_id"]].append(x)
  order=sorted(byplace,key=lambda p:(min(z["row"] for z in byplace[p]),p))
  n=0
  while n<per_category and any(byplace.values()):
   changed=False
   for place in order:
    if not byplace[place]:continue
    selected.append(byplace[place].pop(0));n+=1;changed=True
    if n>=per_category:break
   if not changed:break
 if len({(x["row"],x["start"],x["end"]) for x in selected})!=len(selected):
  raise ValueError("Duplicate selected sentence")
 for x in selected:
  r=reviews[x["row"]]
  if (x["place_id"]!=r["place_id"] or x["review_index"]!=r["review_index"]
      or r["text"][x["start"]:x["end"]]!=x["source_sentence"]
      or not x["place_id"].startswith("ChIJ")
      or not x["publish_time"]):
   raise ValueError("Source identity or exact quote check failed")
 return selected,{k:len(v) for k,v in pools.items()}

def score_factory(max_length):
 import torch
 from transformers import AutoTokenizer,AutoModelForSequenceClassification
 torch.set_num_threads(min(4,torch.get_num_threads()))
 print("Loading",MODEL,flush=True)
 tok=AutoTokenizer.from_pretrained(MODEL)
 model=AutoModelForSequenceClassification.from_pretrained(MODEL).eval()
 indices={str(name).lower():int(i) for i,name in model.config.id2label.items()}
 if set(indices)!={"entailment","neutral","contradiction"}:raise ValueError("Wrong native label space")
 def predict(text,hyp):
  full=tok(text,hyp,truncation=False)
  truncated=len(full["input_ids"])>max_length
  token=tok(text,hyp,truncation=True,max_length=max_length,return_tensors="pt")
  with torch.inference_mode():vals=torch.softmax(model(**token).logits[0],dim=-1).tolist()
  probs={k:round(float(vals[i]),6) for k,i in indices.items()}
  return {"label":max(probs,key=probs.get),"probs":probs,"truncated":truncated}
 return predict

def summarize(results,selection,pool_counts,review_sha,collection):
 bycategory={}
 for category in sorted(set(x["category"] for x in selection)):
  group=[x for x in results if x["case"]["category"]==category]
  detail={}
  for emotion in HYPOTHESES:
   for mode in ("direct","relevance"):
    preds=[r["scores"][emotion][mode] for r in group]
    detail[f"{emotion}_{mode}"]={
     "labels":dict(collections.Counter(p["label"] for p in preds)),
     "mean_entailment_probability":round(statistics.mean(p["probs"]["entailment"] for p in preds),4),
     "n_truncated":sum(p["truncated"] for p in preds)}
  bycategory[category]={"n":len(group),"model_diagnostics":detail}
 divergent=[]
 for r in results:
  for e in HYPOTHESES:
   a=r["scores"][e]
   if a["direct"]["label"]!=a["relevance"]["label"]:
    divergent.append({"row":r["case"]["row"],"emotion":e,"category":r["case"]["category"],
      "source_sentence":r["case"]["source_sentence"],
      "direct":a["direct"]["label"],"relevance":a["relevance"]["label"]})
 return {
  "source_provenance":"Repository processed reviews written by Google Places API collector, NOT fixtures",
  "google_api_collection_dry_run":collection["dry_run"],
  "source_reviews":collection["n_reviews"],"source_places":collection["n_places"],
  "dataset_sha256":review_sha,"selected_sentences":len(results),
  "source_review_indices":len(set(x["case"]["row"] for x in results)),
  "selected_places":len(set(x["case"]["place_id"] for x in results)),
  "pool_counts":pool_counts,"checkpoint":MODEL,
  "hypotheses":HYPOTHESES,"n_nli_pairs":len(results)*len(HYPOTHESES)*2,
  "by_category":bycategory,
  "direct_vs_relevance_label_disagreements":divergent,
  "limitations":[
   "The heuristic categories are not human-reviewed reference labels: group names are candidate types, not validated labels.",
   "All premises are exact original Google API-derived review sentences; hypotheses are authored diagnostic questions, not review text.",
   "Without manually reviewed emotion/evidence reference labels, no inference accuracy, reasoning validity, model calibration, or Component 2 gain can be claimed.",
   "Direct and meta-relevance NLI hypotheses are semantically different questions; probabilities must not be interpreted as calibrated atmosphere scores.",
   "Processed reviews are traceable to repository Google Places collector and place IDs; raw Google API response cache is not in the repository, so the original API payload cannot be independently audited in this run.",
   "A model's NLI neutral output does not show environmental evidence is irrelevant; entailment is not objective proof of place safety.",
   "This diagnostic sample is nonrandom and lexical; assess semantic errors by reading the original sentences before generalizing."
  ]
 }

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--reviews",default=str(ROOT/"data/processed/reviews.jsonl"))
 p.add_argument("--collection",default=str(ROOT/"data/processed/collect_summary.json"))
 p.add_argument("--output",default="reports/stage1a_component3_real_google_diagnostic")
 p.add_argument("--per-category",type=int,default=10)
 p.add_argument("--max-length",type=int,default=512)
 p.add_argument("--check-only",action="store_true")
 p.add_argument("--resume",action="store_true")
 args=p.parse_args()
 if args.per_category<1 or args.max_length<32:raise ValueError("Invalid configuration")
 raw=pathlib.Path(args.reviews).read_bytes();reviews=read(args.reviews)
 collection=json.loads(pathlib.Path(args.collection).read_text(encoding="utf8"))
 if collection["dry_run"] is not False or collection["n_reviews"]!=len(reviews):
  raise ValueError("Source may be fixtures, dry-run data, or different review collection")
 selected,pools=select(reviews,args.per_category)
 if args.check_only:
  print(json.dumps({"reviews":len(reviews),"places":collection["n_places"],
    "dry_run":collection["dry_run"],"sample_sentences":len(selected),
    "candidate_pool_counts":pools,
    "categories":dict(collections.Counter(x["category"] for x in selected)),
    "sample_source_indices":[{"row":x["row"],"place_id":x["place_id"],
     "category":x["category"],"original":x["source_sentence"]} for x in selected]},
    ensure_ascii=False,indent=2));return
 path=pathlib.Path(args.output);path.mkdir(parents=True,exist_ok=True)
 outfile=path/"results.jsonl"
 cfg=hashlib.sha256((hashlib.sha256(raw).hexdigest()+MODEL+
   json.dumps(HYPOTHESES,sort_keys=True)+str(args.per_category)+str(args.max_length)).encode()).hexdigest()
 if outfile.exists() and not args.resume:p.error("Existing output; pass --resume")
 previous={}
 if outfile.exists():
  for l in outfile.read_text(encoding="utf8").splitlines():
   if not l.strip():continue
   r=json.loads(l);c=r["case"];key=(c["row"],c["start"],c["end"])
   if key in previous or r.get("config_sha256")!=cfg:raise ValueError("Bad resume result")
   previous[key]=r
 expected={(c["row"],c["start"],c["end"]) for c in selected}
 if not set(previous)<=expected:raise ValueError("Stale resume result")
 score=score_factory(args.max_length)
 with outfile.open("a" if args.resume else "w",encoding="utf8") as stream:
  for i,c in enumerate(selected,1):
   key=(c["row"],c["start"],c["end"])
   if key in previous:continue
   print(f"REQUEST {i}/{len(selected)} Google row={c['row']} category={c['category']}",flush=True)
   pred={e:{name:score(c["source_sentence"],h) for name,h in forms.items()}
         for e,forms in HYPOTHESES.items()}
   r={"case":c,"scores":pred,"config_sha256":cfg}
   stream.write(json.dumps(r,ensure_ascii=False)+"\n");stream.flush()
   previous[key]=r
   print(f"OK {len(previous)}/{len(selected)}",flush=True)
 results=[previous[(x["row"],x["start"],x["end"])] for x in selected]
 summary=summarize(results,selected,pools,hashlib.sha256(raw).hexdigest(),collection)
 (path/"summary.json").write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding="utf8")
 print("RESULT_SUMMARY "+json.dumps({
  "real_sentences":len(results),"places":summary["selected_places"],
  "pairs":summary["n_nli_pairs"],
  "by_category":{k:{"n":v["n"],"calm_direct":v["model_diagnostics"]["calm_direct"]["labels"],
   "calm_relevance":v["model_diagnostics"]["calm_relevance"]["labels"],
   "inviting_direct":v["model_diagnostics"]["inviting_direct"]["labels"],
   "inviting_relevance":v["model_diagnostics"]["inviting_relevance"]["labels"],
   "safe_direct":v["model_diagnostics"]["safe_direct"]["labels"],
   "safe_relevance":v["model_diagnostics"]["safe_relevance"]["labels"]}
   for k,v in summary["by_category"].items()}},ensure_ascii=False),flush=True)

if __name__=="__main__":main()

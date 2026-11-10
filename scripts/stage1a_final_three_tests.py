#!/usr/bin/env python3
"""THREE and only three preregistered Stage 1A final audits, real Google source only.

Stage 1: fixed held-out sample, Qwen3 extraction + verification and quote fidelity
Stage 2: same-source eligibility, evidence-type and emotion relevance
Stage 3: frozen BART-MNLI NLI: full original vs selected quotes vs relevance

No synthetic review sentences, no hard evidence deletion, no threshold-fitting,
no model search. Each stage writes ONE self-contained JSON package and checkpoints
individual records for exact resume after interrupted execution.
"""
from __future__ import annotations
import argparse
import collections
import hashlib
import json
import pathlib
import re
import sys
import time

ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from stage1a_component1_ollama import (EXTRACT_SYSTEM,EXTRACTION_SCHEMA,
 VERIFY_SYSTEM,VERIFICATION_SCHEMA,call_ollama,validate_extraction,verify_decisions)
from stage1a_component2_v3 import (SYSTEM as C2_SYSTEM,SCHEMA as C2_SCHEMA,
 validate_response as validate_c2,mechanical_audit,EMOTIONS)
from stage1a_component2_eligibility_pilot import PILOT_EMOTIONS
from stage1a_component3_abc import HYPOTHESES as DIRECTIONAL
from stage1a_component3_real_google_diagnostic import HYPOTHESES as NLI_HYPOTHESES
from stage1a_relation_pilot import select_pilot
from stage1a_component3_real_google_diagnostic import select as earlier_nli_select

COLLECT=ROOT/"data/processed/collect_summary.json"
REVIEWS=ROOT/"data/processed/reviews.jsonl"
OUTPUT=ROOT/"reports/stage1a_final_three_tests"
MODEL="qwen3:8b"
NLI_MODEL="facebook/bart-large-mnli"
VERSION="final-three-stage-2026-11-10-v1"
# The natural text itself NEVER comes from these patterns. They are sample
# strata only, and NOT a gold or ground-truth evidence classification.
REPORTED=re.compile(r"\b(feel|feels|felt|peaceful|calm|safe|unsafe|protected|comforted|welcoming|welcome|inviting|relaxing|quiet)\b",re.I)
INDICATOR=re.compile(r"\b(police|patrol|siren|traffic|gate|light|shade|bench|tree|elevator|public|fence|crowd|path|stair|noisy|loud|busy|closed|playground)\b",re.I)
CATEGORIES=("reported_word_candidate","environmental_word_candidate","other_control_candidate")
QUOTA_PER_CATEGORY=6

def digest(raw):
 return hashlib.sha256(raw).hexdigest()

def canon(obj):
 return json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(",",":"))

def write(path,obj):
 path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+"\n",encoding="utf8")

def read(path):
 return json.loads(path.read_text(encoding="utf8"))

def read_lines(path):
 return [json.loads(l) for l in path.read_text(encoding="utf8").splitlines() if l.strip()]

def source_manifest():
 """Reject fixtures and previously exposed development rows."""
 raw=REVIEWS.read_bytes()
 reviews=read_lines(REVIEWS)
 collect=read(COLLECT)
 if collect.get("dry_run") is not False or collect.get("n_reviews")!=len(reviews) or len(reviews)!=214:
  raise ValueError("Wrong/unverifiable processed Google Places collection")
 old=set(select_pilot(reviews,20))
 reused={x["row"] for x in earlier_nli_select(reviews,10)[0]}
 excluded=old|reused
 pool=collections.defaultdict(list)
 # Split paragraphs at punctuation and preserve exactly matching character offsets.
 for row,rev in enumerate(reviews):
  if row in excluded:continue
  if not all(k in rev for k in ("text","place_id","review_index","publish_time")):
   raise ValueError("Missing source provenance columns")
  if not isinstance(rev["text"],str) or not rev["place_id"].startswith("ChIJ") or not rev["publish_time"]:
   raise ValueError("Not an identifiable Google Places review")
  source=rev["text"];loc=0
  for j,part in enumerate(re.split(r"(?<=[.!?])\s+",source)):
   if not part.strip():continue
   a=source.find(part,loc)
   if a<0:raise ValueError("Cannot reconstruct source offsets")
   b=a+len(part);loc=b
   if len(part.split())<5 or len(part.split())>65:continue
   if REPORTED.search(part):cat=CATEGORIES[0]
   elif INDICATOR.search(part):cat=CATEGORIES[1]
   else:cat=CATEGORIES[2]
   pool[cat].append({"row":row,"review_index":rev["review_index"],
    "place_id":rev["place_id"],"publish_time":rev["publish_time"],
    "sentence_index":j,"start":a,"end":b,
    "text":part,"category":cat,
    "review_sha256":digest(source.encode("utf8"))})
 # Deterministic place-diverse greedy sample. The held-out cases never depend
 # on model predictions, prior failures, or any emotion inference.
 chosen=[];used_rows=set();place_counts=collections.Counter()
 for cat in CATEGORIES:
  options=pool[cat]
  while len([x for x in chosen if x["category"]==cat])<QUOTA_PER_CATEGORY:
   choices=[x for x in options if x["row"] not in used_rows]
   if not choices:raise ValueError("Insufficient unexposed real Google cases in "+cat)
   x=min(choices,key=lambda x:(place_counts[x["place_id"]],x["row"],x["start"]))
   chosen.append(x);used_rows.add(x["row"]);place_counts[x["place_id"]]+=1
 if len(chosen)!=18 or len({x["row"] for x in chosen})!=18:
  raise ValueError("Unstable holdout sample")
 for case in chosen:
  rev=reviews[case["row"]]
  if rev["text"][case["start"]:case["end"]]!=case["text"] or rev["place_id"]!=case["place_id"]:
   raise ValueError("Source span mismatch")
 if len({x["place_id"] for x in chosen})<10:
  raise ValueError("Too few independent places")
 manifest={"protocol":VERSION,"source_file":"data/processed/reviews.jsonl",
  "source_sha256":digest(raw),"collection_provenance":"Google Places API-derived processed reviews",
  "source_review_count":len(reviews),"source_place_count":collect["n_places"],
  "collector_dry_run":collect["dry_run"],
  "heldout_from_previous_20_review_extraction_pilot":True,
  "heldout_from_previous_40_sentence_nli_sample":True,
  "excluded_development_review_count":len(excluded),
  "cases":chosen,"categories_are_heuristic_not_gold":True,
  "external_raw_api_payload_independently_verified":False}
 manifest["manifest_sha256"]=digest(canon(manifest).encode("utf8"))
 return manifest

def enforce_previous(stage,manifest):
 path=OUTPUT/f"test{stage}.json"
 if not path.exists():raise ValueError("Missing required previous test package: "+str(path))
 obj=read(path)
 if obj.get("manifest_sha256")!=manifest["manifest_sha256"]:
  raise ValueError("Original review corpus or locked sample changed")
 if obj.get("status")!="complete" or len(obj.get("records",[]))!=18:
  raise ValueError("Previous test incomplete; cannot silently skip cases")
 if any(r.get("error") for r in obj["records"]):
  raise ValueError("Previous test contains an inference error")
 return obj

def check_resume(records_path,manifest,stage):
 if not records_path.exists():return {}
 done={}
 for r in read_lines(records_path):
  i=r["case_index"]
  if (i in done or i<0 or i>=len(manifest["cases"])
    or r.get("manifest_sha256")!=manifest["manifest_sha256"]
    or r.get("source_sha256")!=digest(manifest["cases"][i]["text"].encode("utf8"))):
   raise ValueError("Incompatible partial output; never merge different experiments")
  done[i]=r
 return done

def execute(stage,manifest,callback):
 OUTPUT.mkdir(parents=True,exist_ok=True)
 final=OUTPUT/f"test{stage}.json"
 partial=OUTPUT/f"test{stage}_checkpoint.jsonl"
 if final.exists():
  old=read(final)
  if old.get("manifest_sha256")!=manifest["manifest_sha256"]:
   raise ValueError("Final result exists but source differs")
  print("Test",stage,"already complete: "+str(final),flush=True);return
 done=check_resume(partial,manifest,stage)
 for i,case in enumerate(manifest["cases"]):
  if i in done:continue
  print(f"TEST {stage} REQUEST {i+1}/18 Google row {case['row']} {case['category']}",flush=True)
  # Fail visibly on the first incomplete model request. Never fabricate an empty result.
  r=callback(case,i)
  out={"case_index":i,"source_sha256":digest(case["text"].encode("utf8")),
       "manifest_sha256":manifest["manifest_sha256"],"case":case,"output":r}
  with partial.open("a",encoding="utf8") as f:
   f.write(json.dumps(out,ensure_ascii=False)+"\n");f.flush()
  done[i]=out
  print(f"TEST {stage} OK {len(done)}/18",flush=True)
 allrows=[done[i] for i in range(18)]
 summary=make_summary(stage,allrows)
 package={"test":stage,"protocol":VERSION,"status":"complete",
  "manifest_sha256":manifest["manifest_sha256"],
  "manifest":manifest,"model":MODEL if stage in (1,2) else NLI_MODEL,
  "summary":summary,"records":allrows,
  "limitations":["Only source authenticity and mechanical integrity are machine-tested, not semantic accuracy.",
   "Real Google Places API-derived reviews; raw API response unavailable for independent source verification.",
   "Heuristic sample strata are not reference labels.",
   "No independent human annotated ground truth; manual semantic adjudication needed before performance claims."]}
 write(final,package)
 print("FINAL_TEST_PACKAGE",str(final),flush=True)
 print(json.dumps(summary,ensure_ascii=False,indent=2),flush=True)

def extraction(case,i,args):
 sentence=case["text"]
 answer,meta=call_ollama(args.url,MODEL,EXTRACT_SYSTEM,
  "Original review sentence, verbatim:\n"+sentence,
  EXTRACTION_SCHEMA,args.timeout,8192,think=False,num_predict=2048)
 obs=validate_extraction(answer,sentence)
 verifier={}
 if obs:
  numbered=[{k:x[k] for k in ("index","claim","subject","predicate",
              "object","qualifiers","evidence_quote")} for x in obs]
  verdict,_=call_ollama(args.url,MODEL,VERIFY_SYSTEM,
   "ORIGINAL SOURCE SENTENCE:\n"+sentence+
   "\n\nPROPOSED CLAIMS:\n"+json.dumps(numbered,ensure_ascii=False),
   VERIFICATION_SCHEMA,args.timeout,8192,think=False,num_predict=2048)
  verifier=verify_decisions(verdict,obs)
 enriched=[]
 for x in obs:
  v=verifier[x["index"]]
  ok=(x["quote_match_status"]=="exact_unique" and v["verdict"]=="supported")
  enriched.append({**x,"verifier":v,
   "status":"candidate_passed_checks" if ok else "flagged_not_accepted",
   "same_model_verification_not_gold":True})
 return {"model_meta":meta,"observations":enriched,
  "original_sentence":sentence,"n_claims":len(enriched)}

def relevance(case,i,args,previous):
 src=previous["records"][i]["output"]
 claims=src["observations"];sentence=case["text"]
 numbered=[{"index":j,"claim":c["claim"],"qualifiers":c["qualifiers"],
   "evidence_quote":c["evidence_quote"],"component1_status":c["status"]}
    for j,c in enumerate(claims)]
 if not claims:return {"decisions":[],"n_claims":0}
 pred,_=call_ollama(args.url,MODEL,C2_SYSTEM,
  "REVIEW CONTEXT (for reference only):\n"+sentence+
  "\nORIGINAL SENTENCE (authority):\n"+sentence+
  "\nEMOTION DEFINITIONS:\n"+json.dumps(PILOT_EMOTIONS,ensure_ascii=False)+
  "\nFROZEN COMPONENT 1 CANDIDATES:\n"+json.dumps(numbered,ensure_ascii=False),
  C2_SCHEMA,args.timeout,8192,think=False,num_predict=2048)
 decisions=validate_c2(pred,claims)
 rows=[]
 for j,c in enumerate(claims):
  d=decisions[j]
  audit,flags=mechanical_audit(d,c,sentence)
  # Mechanical warnings do not resolve contested conceptual labels, such as
  # direct safety evidence from police patrol; retain raw judgments.
  rows.append({"index":j,"decision":d,"routing":audit,"flags":flags,
   "original_claim":c["claim"],"component1_status":c["status"]})
 return {"decisions":rows,"n_claims":len(rows)}

def nli(case,i,args,extraction_package,relevance_package,score):
 sentence=case["text"]
 data=relevance_package["records"][i]["output"]["decisions"]
 out={}
 for emotion in EMOTIONS:
  hypothesis=DIRECTIONAL[emotion]
  relevance_hyp=NLI_HYPOTHESES[emotion]["relevance"]
  # Same exact original sentence is the reference, never the model claim.
  original=score(sentence,hypothesis)
  metarelevance=score(sentence,relevance_hyp)
  evidence=[]
  unresolved=[]
  for c in data:
   d=c["decision"]
   a=next(x for x in d["applicability"] if x["emotion"]==emotion)
   quote=a["basis_quote"]
   route=c["routing"][emotion]["route"]
   flags=c["routing"][emotion]["flags"]
   # Only a sole category-taxonomy disagreement may be overridden;
   # original source fidelity checks still control selection.
   permitted=(route=="nli_candidate" or
      (route=="needs_review" and flags==["direct_without_explicit_experience_or_atmosphere"]
       and d["place_related"]=="yes" and a["status"]=="direct"
       and c["component1_status"]=="candidate_passed_checks"))
   if permitted and quote and quote in sentence:
    evidence.append({"candidate_index":c["index"],"source_quote":quote,
     "route":route,"advisory_flags":flags,"nli":score(quote,hypothesis)})
   elif route=="needs_review":
    unresolved.append({"candidate_index":c["index"],"reason":flags})
  out[emotion]={"hypothesis":hypothesis,"original_nli":original,
   "original_relevance_nli":metarelevance,"selected_evidence":evidence,
   "unresolved_candidates":unresolved,
   "no_evidence_is_not_neutral":len(evidence)==0,
   "no_hard_source_deletion":True}
 return out

def score_builder():
 import torch
 from transformers import AutoTokenizer,AutoModelForSequenceClassification
 torch.set_num_threads(min(4,torch.get_num_threads()))
 tok=AutoTokenizer.from_pretrained(NLI_MODEL)
 model=AutoModelForSequenceClassification.from_pretrained(NLI_MODEL).eval()
 idx={str(label).lower():int(k) for k,label in model.config.id2label.items()}
 if set(idx)!={"entailment","neutral","contradiction"}:raise ValueError("Wrong checkpoint label space")
 cache={}
 def run(premise,hypothesis):
  key=(premise,hypothesis)
  if key not in cache:
   full=tok(premise,hypothesis,truncation=False)
   if len(full["input_ids"])>512:raise ValueError("NLI premise truncated: invalid test")
   tokens=tok(premise,hypothesis,truncation=False,return_tensors="pt")
   with torch.inference_mode():
    logits=model(**tokens).logits[0];p=torch.softmax(logits,dim=-1).tolist()
   dist={label:float(p[k]) for label,k in idx.items()}
   cache[key]={"label":max(dist,key=dist.get),"probs":dist}
  return cache[key]
 return run

def make_summary(stage,rows):
 if stage==1:
  claims=[c for r in rows for c in r["output"]["observations"]]
  return {"real_source_sentences":len(rows),
   "distinct_places":len({r["case"]["place_id"] for r in rows}),
   "claims":len(claims),
   "exact_unique_quotes":sum(c["quote_match_status"]=="exact_unique" for c in claims),
   "flagged_claims":sum(c["status"]!="candidate_passed_checks" for c in claims),
   "zero_claim_sentences":sum(not r["output"]["observations"] for r in rows),
   "warning":"Quote exactness and same-model verifier agreement are NOT semantic accuracy or recall."}
 if stage==2:
  cells=[x for r in rows for x in r["output"]["decisions"]]
  return {"real_source_sentences":len(rows),"candidate_claims":len(cells),
   "place_related":dict(collections.Counter(x["decision"]["place_related"] for x in cells)),
   "evidence_type":dict(collections.Counter(x["decision"]["evidence_type"] for x in cells)),
   "flagged_claims":sum(bool(x["flags"]) for x in cells),
   "per_emotion_applicability":{e:dict(collections.Counter(next(a["status"] for a in x["decision"]["applicability"]
      if a["emotion"]==e) for x in cells)) for e in EMOTIONS},
   "warning":"No gold relevance labels; label counts are not precision or recall."}
 parts=[x["output"][e] for r in rows for e in EMOTIONS for x in [r]]
 return {"real_source_sentences":len(rows),"NLI_source_emotion_pairs":len(parts),
  "original_NLI_label_counts":{e:dict(collections.Counter(r["output"][e]["original_nli"]["label"] for r in rows)) for e in EMOTIONS},
  "original_relevance_label_counts":{e:dict(collections.Counter(r["output"][e]["original_relevance_nli"]["label"] for r in rows)) for e in EMOTIONS},
  "no_selected_evidence":{e:sum(not r["output"][e]["selected_evidence"] for r in rows) for e in EMOTIONS},
  "source_vs_relevance_label_disagreement":{e:sum(
    r["output"][e]["original_nli"]["label"]!=r["output"][e]["original_relevance_nli"]["label"]
    for r in rows) for e in EMOTIONS},
  "selected_evidence_count":sum(len(p["selected_evidence"]) for p in parts),
  "warning":"No reference truth; differences between hypotheses are not correctness; absence is not neutral."}

def main():
 parser=argparse.ArgumentParser()
 parser.add_argument("--test",required=True,type=int,choices=(1,2,3))
 parser.add_argument("--url",default="http://127.0.0.1:11434")
 parser.add_argument("--timeout",type=int,default=180)
 parser.add_argument("--show-manifest",action="store_true")
 args=parser.parse_args()
 manifest=source_manifest()
 if args.show_manifest:
  print(json.dumps(manifest,indent=2,ensure_ascii=False));return
 if args.test==1:
  execute(1,manifest,lambda c,i:extraction(c,i,args))
 elif args.test==2:
  old=enforce_previous(1,manifest)
  execute(2,manifest,lambda c,i:relevance(c,i,args,old))
 else:
  old=enforce_previous(1,manifest)
  newer=enforce_previous(2,manifest)
  score=score_builder()
  execute(3,manifest,lambda c,i:nli(c,i,args,old,newer,score))

if __name__=="__main__":main()

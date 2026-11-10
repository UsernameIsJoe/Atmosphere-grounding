# Experiment scripts — frozen sources

These are the exact repository source snapshots used for the Stage 1A audit. The final runner imports supporting modules from the main repository; this document is for code review, not a standalone executable. The referenced code was not modified in this compilation.

## stage1a_final_three_tests.py

Original: [`research_audit/stage1a_final_2026-11-10/scripts/stage1a_final_three_tests.py`](https://github.com/UsernameIsJoe/Atmosphere-grounding/blob/master/research_audit/stage1a_final_2026-11-10/scripts/stage1a_final_three_tests.py)

```python
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
```

## stage1a_component1_ollama.py

Original: [`research_audit/stage1a_final_2026-11-10/scripts/stage1a_component1_ollama.py`](https://github.com/UsernameIsJoe/Atmosphere-grounding/blob/master/research_audit/stage1a_final_2026-11-10/scripts/stage1a_component1_ollama.py)

```python
#!/usr/bin/env python3
"""Stage 1A Component 1 local Ollama extraction experiment.

No synthesized reviews. B = frozen LLM output, C = EXACT SAME B candidates
plus source-span checks and second LLM verification. Neither stage infers any
of the nine target emotions. This does NOT score relevance or NLI.

Requires Ollama on localhost and existing spaCy pilot dependencies.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import pathlib
import sys
import time
import urllib.error
import urllib.request

ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from stage1a_absa_official_sentence_inference import load_cases

EXTRACTION_SCHEMA={
 "type":"object","additionalProperties":False,
 "properties":{"observations":{"type":"array","items":{
  "type":"object","additionalProperties":False,
  "properties":{
   "claim":{"type":"string"},
   "evidence_quote":{"type":"string"},
   "subject":{"type":"string"},
   "predicate":{"type":"string"},
   "object":{"type":"string"},
   "qualifiers":{"type":"string"}},
  "required":["claim","evidence_quote","subject","predicate","object","qualifiers"]}}},
 "required":["observations"]}

VERIFICATION_SCHEMA={
 "type":"object","additionalProperties":False,
 "properties":{"decisions":{"type":"array","items":{
   "type":"object","additionalProperties":False,
   "properties":{"index":{"type":"integer"},
                 "verdict":{"type":"string","enum":["supported","unsupported","uncertain"]},
                 "reason":{"type":"string"}},
   "required":["index","verdict","reason"]}}},
 "required":["decisions"]}

EXTRACT_SYSTEM="""Extract the complete essential meaning of a REAL review sentence as atomic, source-faithful observations.
Return JSON matching the schema. Do not rate emotions, atmosphere labels, relevance, or sentiment scores.
Preserve subject/object, who experienced what, negation, contrast, causation only when explicitly stated,
hedging, source attribution, temporal changes, and reported experiences.
Never infer physical safety from 'felt protected'. Distinguish a person's experience from environmental fact.
Avoid generic or unsupported claims. If a sentence has no informative observation, return [].
Each observation must include an EXACT contiguous quotation copied character-for-character
from the given sentence that entails the observation. Include sufficient context in the quote
to support the relationship; for most observations the entire sentence is acceptable.
The claim is a plain faithful paraphrase; do not silently correct typos or reword ambiguous terms
as if their interpretation were certain. Subject/predicate/object describe the link;
qualifiers preserve relevant negation, time, uncertainty and attribution. Do not add any nine-emotion
categories or predictions. Respond with JSON only."""

VERIFY_SYSTEM="""You are a conservative source-fidelity checker, not an emotion classifier.
For each numbered proposed claim, judge whether the ORIGINAL source sentence actually
supports the full claim including its subject/predicate/object, negation, qualification,
causal attribution and reported nature of feelings.
'supported' only if explicitly grounded, 'unsupported' for hallucinated, contradicted,
overgeneralized, lost negation or wrong relation, and 'uncertain' for ambiguity.
DO NOT rewrite or fix claims. Return exactly one decision per input index.
Respond with schema-conforming JSON only."""

def call_ollama(base,model,system,user,schema,timeout,num_ctx,think=None,num_predict=None):
    url=base.rstrip("/")+"/api/chat"
    request={"model":model,"messages":[{"role":"system","content":system},
                        {"role":"user","content":user}],
             "format":schema,"stream":False,"options":{"temperature":0,"num_ctx":num_ctx}}
    if think is not None:
        request["think"]=think
    if num_predict is not None:
        request["options"]["num_predict"]=num_predict
    req=urllib.request.Request(url,data=json.dumps(request,ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type":"application/json"},method="POST")
    with urllib.request.urlopen(req,timeout=timeout) as rsp:
        outer=json.loads(rsp.read().decode("utf-8"))
    message=outer.get("message",{})
    content=message.get("content","")
    if not isinstance(content,str) or not content.strip():
        raise ValueError("Empty Ollama structured output")
    payload=json.loads(content)
    return payload,{"model":outer.get("model"),"done_reason":outer.get("done_reason"),
        "prompt_eval_count":outer.get("prompt_eval_count"),
        "eval_count":outer.get("eval_count")}

def all_occurrences(text,quote):
    if not isinstance(quote,str) or not quote:return []
    starts=[];start=0
    while True:
        pos=text.find(quote,start)
        if pos<0:break
        starts.append({"start":pos,"end":pos+len(quote)})
        start=pos+1
    return starts

def validate_extraction(obj,sentence):
    if not isinstance(obj,dict) or not isinstance(obj.get("observations"),list):
        raise ValueError("Invalid extraction container")
    observations=[]
    for i,item in enumerate(obj["observations"]):
        if not isinstance(item,dict) or any(not isinstance(item.get(k),str) for k in
                ("claim","evidence_quote","subject","predicate","object","qualifiers")):
            raise ValueError("Invalid observation structure at "+str(i))
        # Never convert an absent/non-exact quotation to verified evidence.
        spans=all_occurrences(sentence,item["evidence_quote"])
        status="exact_unique" if len(spans)==1 else (
            "exact_multiple" if len(spans)>1 else "not_in_source")
        observations.append({**item,"index":i,"quote_match_status":status,
                             "sentence_offsets":spans,
                             "source_support_verified":False})
    return observations

def verify_decisions(obj,observations):
    decisions=obj.get("decisions")
    if not isinstance(decisions,list):raise ValueError("Bad verification response")
    expected=set(range(len(observations)))
    actual=[z.get("index") for z in decisions if isinstance(z,dict)]
    if set(actual)!=expected or len(actual)!=len(expected):
        raise ValueError("Verifier indices incomplete, repeated or invalid")
    out={}
    for z in decisions:
        if z.get("verdict") not in ("supported","unsupported","uncertain") or not isinstance(z.get("reason"),str):
            raise ValueError("Bad verification verdict")
        out[z["index"]]={"verdict":z["verdict"],"reason":z["reason"]}
    return out

def run_sentence(args,case,sentence):
    original=sentence["text"]
    source={"row":case["row"],"place_id":case["place_id"],
            "review_index":case["review_index"],"sentence_index":sentence["sentence_index"],
            "sentence_start":sentence["start"],"sentence_end":sentence["end"],
            "original_sentence":original,"original_review":case["review"]}
    if case["review"][sentence["start"]:sentence["end"]]!=original:
        raise ValueError("Original review offsets mismatch")
    extraction,ex_meta=call_ollama(args.url,args.model,EXTRACT_SYSTEM,
           "Original review sentence, verbatim:\n"+original,
           EXTRACTION_SCHEMA,args.timeout,args.num_ctx)
    b=validate_extraction(extraction,original)
    decisions={}
    verification_error=None
    if b:
        numbered=[{"index":x["index"],"claim":x["claim"],"subject":x["subject"],
                   "predicate":x["predicate"],"object":x["object"],
                   "qualifiers":x["qualifiers"],"evidence_quote":x["evidence_quote"]}
                   for x in b]
        try:
            v,_=call_ollama(args.url,args.model,VERIFY_SYSTEM,
                "ORIGINAL SOURCE SENTENCE:\n"+original+
                "\n\nPROPOSED CLAIMS:\n"+json.dumps(numbered,ensure_ascii=False),
                VERIFICATION_SCHEMA,args.timeout,args.num_ctx)
            decisions=verify_decisions(v,b)
        except Exception as exc:
            verification_error=repr(exc)
    c=[]
    for item in b:
        verdict=decisions.get(item["index"],{"verdict":"unverified","reason":verification_error or "Not checked"})
        passed=item["quote_match_status"]=="exact_unique" and verdict["verdict"]=="supported"
        c.append({**item,"verifier":verdict,"status":"candidate_passed_checks" if passed else "flagged_not_accepted",
                  "source_support_verified":False,
                  "checks_not_ground_truth":True})
    return {"source":source,"B":{"model":args.model,"observations":b,"generation":ex_meta},
            "C":{"observations":c,"verification_error":verification_error,
                 "accepted_candidate_count":sum(x["status"]=="candidate_passed_checks" for x in c)},
            "handoff":{"original_sentence_always_preserved":original,
                "candidates_for_future_relevance":c,"no_emotion_scoring":True},
            "experiment":{"checkpoint":args.model,"conditions":["B_local_llm","C_same_B_with_checks"],
                           "temperature":0,"num_ctx":args.num_ctx}}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--model",required=True,help="Exact locally installed Ollama model name (ollama list)")
    p.add_argument("--url",default="http://127.0.0.1:11434")
    p.add_argument("--output",default="reports/component1_ollama_pilot")
    p.add_argument("--max-reviews",type=int,default=20)
    p.add_argument("--timeout",type=int,default=300)
    p.add_argument("--num-ctx",type=int,default=8192)
    p.add_argument("--resume",action="store_true")
    p.add_argument("--check-only",action="store_true",help="Validate real input corpus and sample without Ollama calls")
    args=p.parse_args()
    if not(1<=args.max_reviews<=20):p.error("--max-reviews must be 1..20")
    cases,_=load_cases()
    cases=cases[:args.max_reviews]
    all_sentences=[(c,s) for c in cases for s in c["sentences"]]
    assert all(c["review"][s["start"]:s["end"]]==s["text"] for c,s in all_sentences)
    out=pathlib.Path(args.output)
    out.mkdir(parents=True,exist_ok=True)
    path=out/"predictions.jsonl"
    dataset_sha=hashlib.sha256(json.dumps([(c["row"],s["sentence_index"],s["text"])
          for c,s in all_sentences],ensure_ascii=False).encode("utf-8")).hexdigest()
    if args.check_only:
        print(json.dumps({"reviews":len(cases),"sentences":len(all_sentences),
          "source_sha256":dataset_sha,"first_rows":[c["row"] for c in cases]},indent=2))
        return
    if path.exists() and not args.resume:
        p.error("Output exists: specify a different --output or use --resume")
    completed={}
    if args.resume and path.exists():
        for line in path.read_text(encoding="utf8").splitlines():
            if not line.strip():continue
            row=json.loads(line);key=(row["source"]["row"],row["source"]["sentence_index"])
            if row["experiment"]["checkpoint"]!=args.model:
                p.error("Cannot resume output from another model")
            if key in completed:p.error("Duplicate existing key")
            completed[key]=row
    expected={(c["row"],s["sentence_index"]) for c,s in all_sentences}
    if not set(completed).issubset(expected):p.error("Resume output has foreign source rows")
    errors=[]
    with path.open("a" if args.resume else "w",encoding="utf8") as fh:
        for i,(case,s) in enumerate(all_sentences,1):
            key=(case["row"],s["sentence_index"])
            if key in completed:continue
            try:
                result=run_sentence(args,case,s)
                fh.write(json.dumps(result,ensure_ascii=False)+"\n")
                fh.flush()
                completed[key]=result
                print(f"OK {i}/{len(all_sentences)} row={key[0]} sentence={key[1]} "
                      f"claims={len(result['B']['observations'])} "
                      f"passed={result['C']['accepted_candidate_count']}",flush=True)
            except (urllib.error.URLError,TimeoutError,ValueError,KeyError,TypeError) as exc:
                errors.append({"row":key[0],"sentence_index":key[1],"error":repr(exc)})
                print("ERROR",key,repr(exc),file=sys.stderr,flush=True)
                # Do not skip incomplete real sentences as though no evidence exists.
                break
    summary={"model":args.model,"reviews_requested":len(cases),
      "sentences_requested":len(all_sentences),"sentences_completed":len(completed),
      "source_sha256":dataset_sha,
      "B_claim_candidates":sum(len(r["B"]["observations"]) for r in completed.values()),
      "B_exact_unique_quote_candidates":sum(
            x["quote_match_status"]=="exact_unique" for r in completed.values()
            for x in r["B"]["observations"]),
      "C_passed_checks_candidates":sum(r["C"]["accepted_candidate_count"] for r in completed.values()),
      "C_flagged_candidates":sum(len(r["C"]["observations"])-r["C"]["accepted_candidate_count"] for r in completed.values()),
      "C_verification_errors":sum(bool(r["C"]["verification_error"]) for r in completed.values()),
      "errors":errors,
      "note":"No semantic accuracy, precision, recall or downstream NLI scores. Verification is a fallible second LLM call, not independent gold."}
    (out/"summary.json").write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding="utf8")
    print(json.dumps(summary,indent=2),flush=True)
    if errors or len(completed)!=len(all_sentences):raise SystemExit(2)
if __name__=="__main__":main()
```

## stage1a_component2_v3.py

Original: [`research_audit/stage1a_final_2026-11-10/scripts/stage1a_component2_v3.py`](https://github.com/UsernameIsJoe/Atmosphere-grounding/blob/master/research_audit/stage1a_final_2026-11-10/scripts/stage1a_component2_v3.py)

```python
#!/usr/bin/env python3
"""Component 2 v3: frozen real Qwen3 claims, explicit evidence type, narrow uncertainty.

Compare against Component 2 v2. Does NOT rerun Component 1, infer emotion polarity,
run NLI, overwrite prior outputs, or delete source text/claims.
"""
import argparse
import collections
import hashlib
import json
from pathlib import Path

from stage1a_component1_ollama import call_ollama
from stage1a_component1_prompt_readiness import FIXED
from stage1a_component2_eligibility_pilot import load, source_hash, PILOT_EMOTIONS

SOURCE_SHA="144aee54fd70fdd2b440bc1e0f05fc71b63e79e26bf525b995a6260c0936d00e"
EMOTIONS=tuple(PILOT_EMOTIONS)
EVIDENCE_TYPES=(
 "explicit_place_experience",       # visitor reports their own feeling caused/situated by place
 "explicit_atmosphere_description",  # reviewer explicitly calls atmosphere welcoming etc.
 "environmental_social_indicator",   # observation, not direct feeling
 "location_access_fact",             # geographic location, access, visiting practicalities
 "general_place_evaluation",         # praise/criticism without emotion-specific basis
 "unrelated_personal",               # phone found, exam completed etc.
 "unclear_source"                     # typo, attribution or premise meaning unresolved
)
STATUSES=("direct","indirect","not_applicable","uncertain")
SCHEMA={"type":"object","additionalProperties":False,"properties":{
 "decisions":{"type":"array","items":{"type":"object","additionalProperties":False,
  "properties":{
   "index":{"type":"integer"},
   "place_related":{"type":"string","enum":["yes","no","uncertain"]},
   "evidence_type":{"type":"string","enum":list(EVIDENCE_TYPES)},
   "place_reason":{"type":"string"},
   "applicability":{"type":"array","items":{"type":"object","additionalProperties":False,
    "properties":{
     "emotion":{"type":"string","enum":list(EMOTIONS)},
     "status":{"type":"string","enum":list(STATUSES)},
     "basis_quote":{"type":"string"},
     "reason":{"type":"string"}
    },"required":["emotion","status","basis_quote","reason"]}}
  },"required":["index","place_related","evidence_type","place_reason","applicability"]}}},"required":["decisions"]}
SYSTEM="""You are Component 2 of an urban-atmosphere evidence pipeline, NOT an emotion
predictor or NLI model. Analyze each numbered extracted claim AGAINST THE ORIGINAL
SOURCE SENTENCE and review context. Return every candidate and all three emotions.

FIRST: place_related = yes if claim is about the reviewed place, its change,
physical conditions, social use, accessibility, location, or a feeling actually
attributed to visiting it; no only if clearly unrelated; uncertain only if the
attribution itself is ambiguous or extraction has made it impossible to tell.
A claim about a changed garden is place-related EVEN IF an extracted causal
explanation is unsupported. Whether it is emotion-relevant is separate.

SECOND: choose ONE evidence_type independently from emotion applicability:
- explicit_place_experience: explicitly reported visitor experience or feeling
  attributable to the place (e.g., feels protected by its layout).
- explicit_atmosphere_description: source explicitly calls the place/atmosphere
  welcoming, peaceful, unsafe, etc. (not just generally 'great' or 'cute').
- environmental_social_indicator: trees, paths, patrols, lighting, staff behavior,
  activity etc. A patrol is NOT a direct report of feeling safe.
- location_access_fact: near a destination, elevator, public access, etc.
- general_place_evaluation: nonspecific praise or criticism, charming/cute/great
  unless the source supplies a clear emotion-specific meaning.
- unrelated_personal: not attributable to the location.
- unclear_source: misspelling, uncertain referent, or unsupported extracted
  meaning that prevents dependable classification. Do NOT silently repair text.

THIRD: determine applicability to EACH supplied emotion, direction-neutrally.
'direct' ONLY when the source explicitly describes that emotion/clear synonym
as a place experience or atmosphere; it does NOT mean proven objective truth.
'indirect' when a SPECIFIC fact provides an identifiable, defensible connection
FOR OR AGAINST the emotion, even if the emotion word is absent. Explain the
specific connection without inventing causal mechanisms.
'not_applicable' when no specific evidence-based link exists. THIS IS THE
DEFAULT for generic praise, simple location facts, or unspecified associations.
'uncertain' ONLY for genuinely ambiguous language, attribution or evidence
connection; missing a clear link is NOT uncertainty.
For direct/indirect supply a short EXACT contiguous substring of the ORIGINAL
SOURCE SENTENCE as basis_quote supporting the link. For not_applicable/uncertain,
use an empty string. Preserve wording, negation and uncertainty.

Do not label all positive claims as relevant to positive emotions. Example:
'a great location' is place-related but not directly or indirectly evidence of
safety/calm/inviting, absent some more specific source detail.
'well patrolled by police' is indirect safety evidence, NOT direct safety.
'accessible by elevator' is a location/access fact and MAY be indirectly
relevant to inviting when access to entry/participation is the explicit basis,
not automatically to calm or safety. 'feels protected' can be direct evidence
of perceived safety without claiming objective safety.
If place_related=no, emotion outputs should normally be not_applicable.
Do not produce directional NLI, entailment, contradiction or intensity.
Return only schema-conforming JSON, no thinking or explanations outside JSON."""

def validate_response(obj,candidates):
 ds=obj.get("decisions") if isinstance(obj,dict) else None
 if not isinstance(ds,list) or len(ds)!=len(candidates):raise ValueError("Incomplete decisions")
 results={}
 for d in ds:
  if not isinstance(d,dict):raise ValueError("Invalid decision object")
  i=d.get("index")
  if type(i) is not int or i in results or i not in range(len(candidates)):
   raise ValueError("Missing/duplicate/foreign candidate index")
  if d.get("place_related") not in ("yes","no","uncertain"):
   raise ValueError("Invalid place-related classification")
  if d.get("evidence_type") not in EVIDENCE_TYPES or not isinstance(d.get("place_reason"),str):
   raise ValueError("Invalid evidence type or reason")
  apps=d.get("applicability")
  if not isinstance(apps,list) or len(apps)!=len(EMOTIONS):raise ValueError("Incomplete emotion applicability")
  seen=set()
  for a in apps:
   if not isinstance(a,dict) or a.get("emotion") not in EMOTIONS or a.get("emotion") in seen:
    raise ValueError("Invalid/duplicate emotion")
   seen.add(a["emotion"])
   if a.get("status") not in STATUSES or not all(isinstance(a.get(k),str) for k in ("basis_quote","reason")):
    raise ValueError("Invalid relevance result")
  results[i]=d
 return results

def mechanical_audit(decision,component1,source):
 flags=[];routes={}
 related=decision["place_related"];etype=decision["evidence_type"]
 for a in decision["applicability"]:
  name=a["emotion"];status=a["status"];quote=a["basis_quote"]
  problems=[]
  if status in ("direct","indirect") and (not quote or quote not in source):
   problems.append("no_literal_basis_in_source")
  if related=="no" and status in ("direct","indirect"):
   problems.append("unrelated_but_applicable")
  if related=="uncertain" and status in ("direct","indirect"):
   problems.append("uncertain_place_but_applicable")
  if etype in ("unrelated_personal","unclear_source") and status in ("direct","indirect"):
   problems.append("incompatible_evidence_type")
  if etype=="unrelated_personal" and related=="yes":
   problems.append("unrelated_type_but_place_related")
  if etype=="explicit_place_experience" and related=="no":
   problems.append("place_experience_but_ineligible")
  if status=="direct" and etype not in ("explicit_place_experience","explicit_atmosphere_description"):
   problems.append("direct_without_explicit_experience_or_atmosphere")
  if status in ("not_applicable","uncertain") and quote:
   problems.append("unnecessary_basis_quote")
  # Source fidelity is independent of site attribution / applicability.
  if component1.get("status")!="candidate_passed_checks":
   problems.append("component1_claim_flagged")
  flags.extend(name+":"+x for x in problems)
  if problems or related=="uncertain" or status=="uncertain":
   route="needs_review"
  elif related=="no" or status=="not_applicable":
   route="not_selected"
  else:
   route="nli_candidate"
  routes[name]={"route":route,"flags":problems,"quote_exact":bool(quote and quote in source)}
 return routes,sorted(set(flags))

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--input",default="reports/component1_ollama_qwen3_8b/predictions.jsonl")
 p.add_argument("--previous",default="reports/stage1a_component2_v2_no_think/diagnostic/decisions.jsonl")
 p.add_argument("--output",default="reports/stage1a_component2_v3")
 p.add_argument("--model",default="qwen3:8b")
 p.add_argument("--url",default="http://127.0.0.1:11434")
 p.add_argument("--timeout",type=int,default=180)
 p.add_argument("--num-ctx",type=int,default=8192)
 p.add_argument("--num-predict",type=int,default=2048)
 p.add_argument("--all",action="store_true")
 p.add_argument("--check-only",action="store_true")
 p.add_argument("--resume",action="store_true")
 args=p.parse_args()
 frozen=load(args.input)
 if len(frozen)!=56 or source_hash(frozen)!=SOURCE_SHA:
  raise ValueError("Frozen original source mismatch")
 selection=frozen if args.all else [r for r in frozen
    if (r["source"]["row"],r["source"]["sentence_index"]) in FIXED]
 if not args.all and len(selection)!=12:raise ValueError("Missing fixed diagnostic rows")
 expected={(r["source"]["row"],r["source"]["sentence_index"]) for r in selection}
 previous={}
 prev=Path(args.previous)
 if prev.exists():
  for line in prev.read_text(encoding="utf-8").splitlines():
   if not line.strip():continue
   old=json.loads(line);s=old["source"];k=(s["row"],s["sentence_index"])
   if k in expected:
    if k in previous:raise ValueError("Duplicate v2 comparison record")
    previous[k]=old
 folder=Path(args.output)/("all56" if args.all else "diagnostic")
 path=folder/"decisions.jsonl"
 config_hash=hashlib.sha256((SYSTEM+json.dumps(PILOT_EMOTIONS,sort_keys=True)+
     "|think=false|num_predict="+str(args.num_predict)).encode("utf-8")).hexdigest()
 if args.check_only:
  print(json.dumps({"sentences":len(selection),
     "candidates":sum(len(r["C"]["observations"]) for r in selection),
     "v2_matched_sentences":len(previous),"model":args.model,
     "thinking":False,"NLI_executed":False,"output":str(path)},indent=2))
  return
 if path.exists() and not args.resume:p.error("Output exists; pass --resume")
 folder.mkdir(parents=True,exist_ok=True)
 completed={}
 if path.exists():
  for line in path.read_text(encoding="utf-8").splitlines():
   if not line.strip():continue
   r=json.loads(line);s=r["source"];k=(s["row"],s["sentence_index"])
   if k in completed or k not in expected or r.get("config_sha256")!=config_hash or r.get("model")!=args.model:
    raise ValueError("Resume configuration/source mismatch")
   completed[k]=r
 error=[]
 with path.open("a" if args.resume else "w",encoding="utf-8") as file:
  for record in selection:
   source=record["source"];key=(source["row"],source["sentence_index"])
   if key in completed:continue
   claims=record["C"]["observations"]
   numbered=[{"index":i,"claim":c["claim"],"qualifiers":c["qualifiers"],
      "evidence_quote":c["evidence_quote"],"component1_status":c["status"]}
      for i,c in enumerate(claims)]
   try:
    if claims:
     print("REQUEST",key,"candidates",len(claims),"(thinking off)",flush=True)
     result,_=call_ollama(args.url,args.model,SYSTEM,
       "REVIEW CONTEXT (for reference only):\n"+source["original_review"]+
       "\nORIGINAL SENTENCE (authority):\n"+source["original_sentence"]+
       "\nEMOTION DEFINITIONS:\n"+json.dumps(PILOT_EMOTIONS,ensure_ascii=False)+
       "\nFROZEN COMPONENT 1 CANDIDATES:\n"+json.dumps(numbered,ensure_ascii=False),
       SCHEMA,args.timeout,args.num_ctx,think=False,num_predict=args.num_predict)
     decisions=validate_response(result,claims)
    else:decisions={}
    candidates=[]
    for i,c in enumerate(claims):
     d=decisions[i];routing,flags=mechanical_audit(d,c,source["original_sentence"])
     prev_row=previous.get(key)
     prior=prev_row["candidates"][i]["raw_component2_v2"] if prev_row and i<len(prev_row["candidates"]) else None
     candidates.append({"index":i,"component1":c,"raw_component2_v3":d,
       "v2_comparison":prior,"routing_by_emotion":routing,"mechanical_flags":flags})
    output={"source":source,"model":args.model,"config_sha256":config_hash,
      "candidates":candidates,"original_sentence_fallback":source["original_sentence"],
      "no_hard_deletion":True,"NLI_executed":False}
    file.write(json.dumps(output,ensure_ascii=False)+"\n");file.flush()
    completed[key]=output
    print("OK",len(completed),"/",len(selection),"row",key[0],"sentence",key[1],
          "candidates",len(candidates),flush=True)
   except Exception as exc:
    error.append({"source":key,"error":repr(exc)})
    print("ERROR",key,repr(exc),file=sys.stderr,flush=True);break
 allc=[c for r in completed.values() for c in r["candidates"]]
 summary={"sentences_selected":len(selection),"sentences_completed":len(completed),
  "candidates":len(allc),"matched_v2_sentences":len(previous),
  "eligibility":dict(collections.Counter(c["raw_component2_v3"]["place_related"] for c in allc)),
  "evidence_types":dict(collections.Counter(c["raw_component2_v3"]["evidence_type"] for c in allc)),
  "applicability":{e:dict(collections.Counter(next(a["status"] for a in c["raw_component2_v3"]["applicability"]
     if a["emotion"]==e) for c in allc)) for e in EMOTIONS},
  "mechanically_flagged_claims":sum(bool(c["mechanical_flags"]) for c in allc),
  "errors":error,"note":"No semantic accuracy, no independent gold, no downstream NLI."}
 (folder/"summary.json").write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding="utf-8")
 print(json.dumps(summary,indent=2),flush=True)
 if error or len(completed)!=len(selection):raise SystemExit(2)

if __name__=="__main__":main()
```

## stage1a_component3_abc.py

Original: [`research_audit/stage1a_final_2026-11-10/scripts/stage1a_component3_abc.py`](https://github.com/UsernameIsJoe/Atmosphere-grounding/blob/master/research_audit/stage1a_final_2026-11-10/scripts/stage1a_component3_abc.py)

```python
#!/usr/bin/env python3
"""Stage 1A controlled Component 2 -> Component 3 NLI ablation.

A: unfiltered ORIGINAL source sentence.
B: all v3 'nli_candidate' observations as original-source evidence quotations.
C: B plus flagged/uncertain/Component1-rejected observations as original-source
   sentences for review, without erasing their flags.
No synthesized text, model scoring of emotion magnitude, or accuracy claims.
"""
import argparse
import collections
import hashlib
import json
import pathlib
import statistics
import time

MODEL="facebook/bart-large-mnli"
# Freeze previously used M2c three-way NLI hypotheses; do not introduce new ones.
HYPOTHESES={
 "calm":"The atmosphere of this location is calm.",
 "inviting":"The atmosphere of this location is inviting.",
 "safe":"This location feels physically safe to visitors.",
}
EMOTIONS=tuple(HYPOTHESES)
SOURCE_SHA="144aee54fd70fdd2b440bc1e0f05fc71b63e79e26bf525b995a6260c0936d00e"
ROUTES={"nli_candidate","not_selected","needs_review"}
LABELS=("entailment","neutral","contradiction")

def read_jsonl(path):
 return [json.loads(s) for s in pathlib.Path(path).read_text(encoding="utf8").splitlines() if s.strip()]

def source_key(s):
 return (s["row"],s["sentence_index"])

def validate_and_plan(v3,baseline):
 """Plan a *paired* ablation; no model inference or implicit acceptance of claims."""
 original={source_key(r["source"]):r for r in baseline}
 if len(original)!=56 or len(baseline)!=56:
  raise ValueError("Expected exactly 56 unique original A0 sentences")
 frozen_sha=hashlib.sha256(json.dumps([
   (r["source"]["row"],r["source"]["sentence_index"],r["source"]["original_sentence"])
   for r in baseline],ensure_ascii=False).encode("utf8")).hexdigest()
 if frozen_sha!=SOURCE_SHA:raise ValueError("Frozen source hash mismatch")
 if len({source_key(x["source"]) for x in v3})!=len(v3):
  raise ValueError("Duplicate Component 2 source")
 cases=[]
 for r in v3:
  s=r["source"];key=source_key(s)
  base=original.get(key)
  if base is None or s["original_sentence"]!=base["source"]["original_sentence"]:
   raise ValueError("Component 2 original source mismatch")
  sentence=s["original_sentence"]
  if s["original_review"][s["sentence_start"]:s["sentence_end"]]!=sentence:
   raise ValueError("Unverifiable original-review offset")
  if len(r["candidates"])!=len(base["C"]["observations"]):
   raise ValueError("Candidate count mismatches original extractor")
  case={"source":s,"emotions":{}}
  for e in EMOTIONS:
   # Every condition is evaluated for the same source/emotion pair.
   # B/C use SOURCE QUOTES, not the model's potentially wrong paraphrase.
   selected=[];safeguarded=[];routing=[]
   for i,c in enumerate(r["candidates"]):
    if c["index"]!=i:raise ValueError("Nonsequential candidate indices")
    orig=base["C"]["observations"][i]
    if c["component1"]["claim"]!=orig["claim"]:
     raise ValueError("Original extraction changed")
    decision=c["raw_component2_v3"]
    if decision.get("index")!=i:raise ValueError("Bad Component2 index")
    apps=[a for a in decision["applicability"] if a["emotion"]==e]
    if len(apps)!=1:raise ValueError("Missing/duplicate emotion-specific judgment")
    route=c["routing_by_emotion"][e]["route"]
    if route not in ROUTES:raise ValueError("Unknown route")
    # Preserve the researcher's accepted reading: a source-grounded observation
    # such as police patrol may be 'direct' safety evidence even when it is an
    # environmental indicator, not a first-person feeling. The earlier v3
    # type-based warning is advisory, not an absolute eligibility veto.
    # Override ONLY this solitary taxonomy flag, never source-fidelity,
    # literal quote, place-attribution, or other mechanical failures.
    quote=apps[0]["basis_quote"]
    flags=c["routing_by_emotion"][e]["flags"]
    taxonomy_override=(
       route=="needs_review" and flags==["direct_without_explicit_experience_or_atmosphere"]
       and decision["place_related"]=="yes" and apps[0]["status"]=="direct"
       and quote and quote in sentence and orig["status"]=="candidate_passed_checks")
    effective_route="nli_candidate" if taxonomy_override else route
    if effective_route=="nli_candidate":
     if not quote or quote not in sentence:
      raise ValueError("Unverifiable selected premise")
     selected.append({"candidate_index":i,"premise":quote,
                     "evidence_kind":"exact_emotion_basis_quote",
                     "component1_status":orig["status"]})
    # Safeguard: include all flagged/uncertain cases as original source
    # (never promote their potentially unsupported extracted claim).
    if effective_route=="needs_review":
     safeguarded.append({"candidate_index":i,"premise":sentence,
                         "evidence_kind":"original_source_fallback",
                         "component1_status":orig["status"]})
    routing.append({"candidate_index":i,"route":route,"effective_route":effective_route,
                    "taxonomy_override":bool(taxonomy_override),
                    "label":apps[0]["status"],
                    "component1_status":orig["status"],
                    "mechanical_flags":c["mechanical_flags"]})
   # Duplicate selected quote spans can be attached to multiple claims. De-duplicate
   # exact premises within each condition to avoid counting repeated evidence twice.
   def unique(entries):
    seen=set();ret=[]
    for x in entries:
     if x["premise"] not in seen:
      ret.append(x);seen.add(x["premise"])
    return ret
   b=unique(selected)
   c=unique(selected+safeguarded)
   case["emotions"][e]={"hypothesis":HYPOTHESES[e],
     "A_original":[{"candidate_index":None,"premise":sentence,"evidence_kind":"original_source"}],
     "B_selected":b,"C_safeguarded":c,"routing_audit":routing,
     "selected_count":len(selected),"needs_review_count":len(safeguarded)}
  cases.append(case)
 return cases

def classifier(max_length):
 import torch
 from transformers import AutoModelForSequenceClassification, AutoTokenizer
 torch.set_num_threads(min(4,torch.get_num_threads()))
 print("Loading frozen NLI checkpoint:",MODEL,flush=True)
 tokenizer=AutoTokenizer.from_pretrained(MODEL)
 model=AutoModelForSequenceClassification.from_pretrained(MODEL).eval()
 labels={str(v).lower():int(k) for k,v in model.config.id2label.items()}
 if set(labels)!=set(LABELS):
  raise ValueError("Expected three-way NLI checkpoint; got "+repr(labels))
 def infer(premise,hypothesis):
  full=tokenizer(premise,hypothesis,truncation=False)
  truncated=len(full["input_ids"])>max_length
  tokens=tokenizer(premise,hypothesis,truncation=True,max_length=max_length,return_tensors="pt")
  with torch.inference_mode():
   probs=torch.softmax(model(**tokens).logits[0],dim=-1).tolist()
  p={k:float(probs[v]) for k,v in labels.items()}
  return {"label":max(p,key=p.get),"probs":p,"potentially_truncated":truncated}
 return infer

def evidence_result(annotations):
 """Do not turn multiple claims into an invented single emotion score."""
 labels=[x["prediction"]["label"] for x in annotations]
 if not annotations:return {"evidence_status":"no_selected_evidence",
                               "any_entailment":False,"any_contradiction":False,
                               "mixed":False,"n_evidence":0}
 return {"evidence_status":"has_evidence","any_entailment":"entailment" in labels,
         "any_contradiction":"contradiction" in labels,
         "mixed":"entailment" in labels and "contradiction" in labels,
         "n_evidence":len(annotations),"labels":dict(collections.Counter(labels))}

def aggregate(rows):
 byemo={}
 for e in EMOTIONS:
  data=[r["emotions"][e] for r in rows]
  byemo[e]={
   "sentence_emotion_pairs":len(data),
   "selected_empty":sum(not x["B_selected"] for x in data),
   "safeguarded_empty":sum(not x["C_safeguarded"] for x in data),
   "A_labels":dict(collections.Counter(x["A_original"][0]["prediction"]["label"] for x in data)),
   "B_mixed":sum(x["B_evidence_summary"]["mixed"] for x in data),
   "C_mixed":sum(x["C_evidence_summary"]["mixed"] for x in data),
   "A_non_neutral_B_empty":sum(
      x["A_original"][0]["prediction"]["label"]!="neutral" and not x["B_selected"] for x in data),
   "A_non_neutral_C_empty":sum(
      x["A_original"][0]["prediction"]["label"]!="neutral" and not x["C_safeguarded"] for x in data),
   "A_non_neutral_B_no_matching_direction":sum(
      x["A_original"][0]["prediction"]["label"] in ("entailment","contradiction") and
      not any(z["prediction"]["label"]==x["A_original"][0]["prediction"]["label"]
              for z in x["B_selected"]) for x in data),
   "A_non_neutral_C_no_matching_direction":sum(
      x["A_original"][0]["prediction"]["label"] in ("entailment","contradiction") and
      not any(z["prediction"]["label"]==x["A_original"][0]["prediction"]["label"]
              for z in x["C_safeguarded"]) for x in data),
  }
 return byemo

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--component2",default="reports/stage1a_component2_v3/diagnostic/decisions.jsonl")
 p.add_argument("--component1",default="reports/component1_ollama_qwen3_8b/predictions.jsonl")
 p.add_argument("--output",default="reports/stage1a_component3_abc")
 p.add_argument("--max-length",type=int,default=512)
 p.add_argument("--check-only",action="store_true",help="Validate sources, routing and A/B/C plan without downloading NLI model")
 p.add_argument("--resume",action="store_true")
 args=p.parse_args()
 if args.max_length<32: p.error("Max length too small")
 raw_v3=read_jsonl(args.component2)
 original=read_jsonl(args.component1)
 cases=validate_and_plan(raw_v3,original)
 output=pathlib.Path(args.output)
 plan={"n_real_sentences":len(cases),"emotion_hypotheses":HYPOTHESES,
       "n_sentence_emotion_pairs":len(cases)*len(EMOTIONS),
       "n_A_original_premises":len(cases)*len(EMOTIONS),
       "n_B_selected_premises":sum(len(c["emotions"][e]["B_selected"]) for c in cases for e in EMOTIONS),
       "n_C_safeguarded_premises":sum(len(c["emotions"][e]["C_safeguarded"]) for c in cases for e in EMOTIONS),
       "NLI_checkpoint":MODEL,"model_called":not args.check_only,
       "NLI_input_is_source_quote_not_unsupported_claim":True,
       "caveat":"Conditions have different evidence granularity; comparisons are diagnostic, not controlled semantic accuracy."}
 if args.check_only:
  print(json.dumps(plan,indent=2));return
 output.mkdir(parents=True,exist_ok=True)
 path=output/"results.jsonl"
 config_hash=hashlib.sha256(json.dumps({
   "model":MODEL,"hypotheses":HYPOTHESES,"max_length":args.max_length,
   "component2_sha":hashlib.sha256(pathlib.Path(args.component2).read_bytes()).hexdigest(),
   "component1_sha":hashlib.sha256(pathlib.Path(args.component1).read_bytes()).hexdigest()},sort_keys=True).encode()).hexdigest()
 if path.exists() and not args.resume:p.error("Output exists: use --resume or new --output")
 done={}
 if path.exists():
  for line in path.read_text(encoding="utf8").splitlines():
   if not line.strip():continue
   r=json.loads(line);k=source_key(r["source"])
   if k in done or r["config_sha256"]!=config_hash:
    raise ValueError("Resume input/config mismatch")
   done[k]=r
 expected={source_key(x["source"]) for x in cases}
 if not set(done).issubset(expected):raise ValueError("Resume contains unrelated records")
 infer=classifier(args.max_length)
 cache={}
 # Cache identical (source, hypothesis) predictions to prevent duplicate forward passes,
 # but don't change model scoring/aggregation or erase candidate provenance.
 for r in done.values():
  for e,data in r["emotions"].items():
   for cond in ("A_original","B_selected","C_safeguarded"):
    for x in data[cond]:cache[(x["premise"],data["hypothesis"])]=x["prediction"]
 begun=time.time()
 with path.open("a" if args.resume else "w",encoding="utf8") as handle:
  for i,case in enumerate(cases,1):
   key=source_key(case["source"])
   if key in done:continue
   print(f"REQUEST NLI {i}/{len(cases)} row={key[0]} sentence={key[1]}",flush=True)
   r=json.loads(json.dumps(case))
   for e,data in r["emotions"].items():
    h=data["hypothesis"]
    for cond in ("A_original","B_selected","C_safeguarded"):
     for x in data[cond]:
      k=(x["premise"],h)
      if k not in cache:cache[k]=infer(*k)
      x["prediction"]=cache[k]
    data["B_evidence_summary"]=evidence_result(data["B_selected"])
    data["C_evidence_summary"]=evidence_result(data["C_safeguarded"])
   r["config_sha256"]=config_hash
   handle.write(json.dumps(r,ensure_ascii=False)+"\n");handle.flush()
   done[key]=r
   print(f"OK NLI {len(done)}/{len(cases)}",flush=True)
 results=[done[source_key(c["source"])] for c in cases]
 summary={**plan,"sentences_completed":len(results),"seconds":round(time.time()-begun,2),
          "distinct_model_forward_pairs_in_session":len(cache),
          "by_emotion":aggregate(results),
          "limitations":[
            "No human-rated emotion gold or model correctness score.",
            "A uses whole original sentence; B uses selected original quote spans; C adds original-sentence fallbacks for flagged claims. Length/granularity differences may change NLI independently of selection.",
            "Absence of selected evidence is NOT negative, contradiction, neutral, or a low emotion intensity.",
            "Any apparent retained or lost NLI direction is agreement with model baseline, NOT accuracy.",
            "The term 'direct' is retained from v3 as an annotator choice, not enforced as a universal safety rubric.",
            "Only 3 pilot emotion hypotheses are frozen; do not infer final 9 emotions from this run."
          ]}
 (output/"summary.json").write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding="utf8")
 print(json.dumps({"sentences_completed":len(results),"by_emotion":summary["by_emotion"]},indent=2))
if __name__=="__main__":main()
```

## stage1a_component3_real_google_diagnostic.py

Original: [`research_audit/stage1a_final_2026-11-10/scripts/stage1a_component3_real_google_diagnostic.py`](https://github.com/UsernameIsJoe/Atmosphere-grounding/blob/master/research_audit/stage1a_final_2026-11-10/scripts/stage1a_component3_real_google_diagnostic.py)

```python
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
```


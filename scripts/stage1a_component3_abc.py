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
    # Route state belongs to a research experiment, NOT to an irreversible filter.
    quote=apps[0]["basis_quote"]
    if route=="nli_candidate":
     if not quote or quote not in sentence:
      raise ValueError("Unverifiable selected premise")
     selected.append({"candidate_index":i,"premise":quote,
                     "evidence_kind":"exact_emotion_basis_quote",
                     "component1_status":orig["status"]})
    # Safeguard: include all flagged/uncertain cases as original source
    # (never promote their potentially unsupported extracted claim).
    if route=="needs_review":
     safeguarded.append({"candidate_index":i,"premise":sentence,
                         "evidence_kind":"original_source_fallback",
                         "component1_status":orig["status"]})
    routing.append({"candidate_index":i,"route":route,
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

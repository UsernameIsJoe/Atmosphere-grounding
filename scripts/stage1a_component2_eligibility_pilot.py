#!/usr/bin/env python3
"""Stage 1A Component 2: REAL-review evidence eligibility and emotion applicability.

Read frozen Qwen3 Component 1 outputs. Never extract again, score emotional
direction, run NLI, or discard source sentences. All model decisions are
candidate annotations. Pilot uses 3 historically configured emotions only;
nine final emotion definitions must be supplied and validated separately.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from stage1a_component1_ollama import call_ollama
from stage1a_component1_prompt_readiness import FIXED

PILOT_EMOTIONS={
 "calm":"Whether the setting is peaceful, low-stimulation, or disturbing; direct feelings and plausible environmental clues count.",
 "inviting":"Whether the setting welcomes or discourages approach, entry, participation, or staying; direct experiences and environmental/social clues count.",
 "safe":"Whether the setting creates a perception of physical safety or threat; do not equate subjective comfort with proven objective safety."
}
SCHEMA={"type":"object","additionalProperties":False,"properties":{
 "decisions":{"type":"array","items":{"type":"object","additionalProperties":False,"properties":{
  "index":{"type":"integer"},
  "location_eligibility":{"type":"string","enum":["yes","no","uncertain"]},
  "attribution_type":{"type":"string","enum":["environment","place_experience","place_social","unrelated_personal","uncertain"]},
  "location_reason":{"type":"string"},
  "applicability":{"type":"array","items":{"type":"object","additionalProperties":False,"properties":{
   "emotion":{"type":"string","enum":list(PILOT_EMOTIONS)},
   "status":{"type":"string","enum":["direct","indirect","not_applicable","uncertain"]},
   "reason":{"type":"string"}
  },"required":["emotion","status","reason"]}}
 },"required":["index","location_eligibility","attribution_type","location_reason","applicability"]}}},"required":["decisions"]}
SYSTEM="""Annotate evidence selection for urban place reviews. This is Component 2, NOT inference of emotion scores.
For every numbered extracted observation, first decide whether its meaning is about
the reviewed place, its physical environment, social use, or an experience caused by
or explicitly situated in the place. Personal events unrelated to the setting are 'no'.
If source attribution is ambiguous, mark 'uncertain'; DO NOT invent attribution.
For each listed emotion, independently classify applicability: 'direct' for an explicit
experience or description about that emotion; 'indirect' when the fact may be evidence
for OR AGAINST the emotion; 'not_applicable' for no useful relation; 'uncertain' if
evidence/attribution cannot be resolved. Relevance is DIRECTION-NEUTRAL:
traffic noise may be relevant to calmness even when evidence is against calmness.
Do not assert entailment, contradiction, emotional intensity, polarity or accuracy.
Examine the ORIGINAL SOURCE SENTENCE, not just a model paraphrase; retain ambiguity,
negation, hedges and attribution. A prior extractor/verifier status is NOT ground truth.
Every candidate must receive one eligibility and exactly one applicability for
each specified emotion. Return JSON only."""
def load(path):
 records=[json.loads(s) for s in Path(path).read_text(encoding="utf8").splitlines() if s.strip()]
 keys=set()
 for r in records:
  s=r["source"]; k=(s["row"],s["sentence_index"])
  if k in keys: raise ValueError("duplicate source")
  keys.add(k)
  if s["original_review"][s["sentence_start"]:s["sentence_end"]]!=s["original_sentence"]:
   raise ValueError("invalid review source span "+str(k))
  if r.get("B",{}).get("model")!="qwen3:8b":raise ValueError("Expected frozen A0 qwen3:8b extraction")
 return records
def source_hash(records):
 return hashlib.sha256(json.dumps([(r["source"]["row"],r["source"]["sentence_index"],r["source"]["original_sentence"]) for r in records],ensure_ascii=False).encode("utf8")).hexdigest()
def validate(decisions,candidates):
 if not isinstance(decisions,list) or len(decisions)!=len(candidates):raise ValueError("Incomplete component2 response")
 seen=set()
 for row in decisions:
  idx=row.get("index")
  if not isinstance(idx,int) or idx in seen or idx not in range(len(candidates)):raise ValueError("Duplicate/invalid index")
  seen.add(idx)
  if row.get("location_eligibility") not in ("yes","no","uncertain"):raise ValueError("invalid eligibility")
  if row.get("attribution_type") not in ("environment","place_experience","place_social","unrelated_personal","uncertain"):raise ValueError("invalid attribution")
  if not isinstance(row.get("location_reason"),str):raise ValueError("missing reason")
  applications=row.get("applicability")
  if not isinstance(applications,list) or len(applications)!=len(PILOT_EMOTIONS):raise ValueError("incomplete emotion applicability")
  if {a.get("emotion") for a in applications}!=set(PILOT_EMOTIONS):raise ValueError("unexpected/duplicate emotion")
  for a in applications:
   if a.get("status") not in ("direct","indirect","not_applicable","uncertain") or not isinstance(a.get("reason"),str):
    raise ValueError("invalid applicability")
 return {row["index"]:row for row in decisions}
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--input",default="reports/component1_ollama_qwen3_8b/predictions.jsonl")
 p.add_argument("--output",default="reports/stage1a_component2_eligibility_pilot")
 p.add_argument("--model",default="qwen3:8b")
 p.add_argument("--url",default="http://127.0.0.1:11434")
 p.add_argument("--timeout",type=int,default=300)
 p.add_argument("--num-ctx",type=int,default=8192)
 p.add_argument("--all",action="store_true",help="Run all 56 sentences; default 12 frozen diagnostic sentences")
 p.add_argument("--check-only",action="store_true")
 p.add_argument("--resume",action="store_true")
 a=p.parse_args()
 base=load(a.input);sha=source_hash(base)
 if len(base)!=56:raise ValueError("Expected 56 original A0 sentences")
 if sha!="144aee54fd70fdd2b440bc1e0f05fc71b63e79e26bf525b995a6260c0936d00e":
  raise ValueError("Source hash differs from frozen 56-sentence corpus")
 chosen=base if a.all else [r for r in base if (r["source"]["row"],r["source"]["sentence_index"]) in FIXED]
 if not a.all and len(chosen)!=12:raise ValueError("Fixed diagnostic subset incomplete")
 dest=Path(a.output)/("all56" if a.all else "diagnostic")
 path=dest/"decisions.jsonl"
 config_hash=hashlib.sha256((SYSTEM+json.dumps(PILOT_EMOTIONS,sort_keys=True)).encode("utf8")).hexdigest()
 if a.check_only:
  print(json.dumps({"original_sentences":len(base),"selected":len(chosen),
   "observations":sum(len(r["C"]["observations"]) for r in chosen),
   "emotion_labels":list(PILOT_EMOTIONS),"source_sha256":sha,
   "candidate_nli_results":False,"output":str(path)},indent=2))
  return
 if path.exists() and not a.resume:p.error("Output exists; use --resume or new --output")
 dest.mkdir(parents=True,exist_ok=True)
 existing={}
 if path.exists():
  for line in path.read_text(encoding="utf8").splitlines():
   if not line.strip():continue
   row=json.loads(line); k=(row["source"]["row"],row["source"]["sentence_index"])
   if k in existing or row.get("config_sha256")!=config_hash or row.get("model")!=a.model:
    raise ValueError("Existing results duplicated or config/model changed")
   existing[k]=row
 chosenkeys={(r["source"]["row"],r["source"]["sentence_index"]) for r in chosen}
 if not set(existing).issubset(chosenkeys):raise ValueError("Unexpected resume source")
 errors=[]
 with path.open("a" if a.resume else "w",encoding="utf8") as handle:
  for record in chosen:
   s=record["source"];key=(s["row"],s["sentence_index"])
   if key in existing:continue
   claims=record["C"]["observations"]
   numbered=[{"index":i,"claim":c["claim"],"source_quote":c["evidence_quote"],
     "extractor_flag":c["status"],"qualifiers":c["qualifiers"]} for i,c in enumerate(claims)]
   try:
    if claims:
     response,_=call_ollama(a.url,a.model,SYSTEM,
      "REVIEW CONTEXT (for attribution only):\n"+s["original_review"]+
      "\nORIGINAL SENTENCE (authority):\n"+s["original_sentence"]+
      "\nEMOTION DEFINITIONS:\n"+json.dumps(PILOT_EMOTIONS)+
      "\nNUMBERED CANDIDATES:\n"+json.dumps(numbered,ensure_ascii=False),
      SCHEMA,a.timeout,a.num_ctx)
     decisions=validate(response["decisions"],claims)
    else:decisions={}
    output={"source":s,"model":a.model,"config_sha256":config_hash,
     "candidates":[{"index":i,"component1":c,"component2":decisions[i]} for i,c in enumerate(claims)],
     "original_sentence_fallback":s["original_sentence"],
     "no_hard_deletion":True,"component3_nli_ran":False,
     "claims_are_unverified":True}
    handle.write(json.dumps(output,ensure_ascii=False)+"\n");handle.flush();existing[key]=output
    print("OK",len(existing),"/",len(chosen),"row",key[0],"sentence",key[1],
      "candidates",len(claims),flush=True)
   except Exception as exc:
    errors.append({"source":key,"error":repr(exc)})
    print("ERROR",key,repr(exc),file=sys.stderr,flush=True);break
 counts={"source_sentences":len(chosen),"sentences_completed":len(existing),
  "candidates":sum(len(x["candidates"]) for x in existing.values()),
  "eligibility":{k:sum(c["component2"]["location_eligibility"]==k for x in existing.values() for c in x["candidates"]) for k in ("yes","no","uncertain")},
  "by_emotion":{e:{s:sum(any(a["emotion"]==e and a["status"]==s for a in c["component2"]["applicability"]) for x in existing.values() for c in x["candidates"]) for s in ("direct","indirect","not_applicable","uncertain")} for e in PILOT_EMOTIONS},
  "errors":errors,"note":"Model-generated eligibility/applicability; no independent relevance accuracy or NLI results. No candidates deleted."}
 (dest/"summary.json").write_text(json.dumps(counts,indent=2,ensure_ascii=False),encoding="utf8")
 print(json.dumps(counts,indent=2),flush=True)
 if errors or len(existing)!=len(chosen):raise SystemExit(2)
if __name__=="__main__":main()

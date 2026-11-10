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

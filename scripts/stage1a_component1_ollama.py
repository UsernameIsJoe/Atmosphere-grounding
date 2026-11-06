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

def call_ollama(base,model,system,user,schema,timeout,num_ctx):
    url=base.rstrip("/")+"/api/chat"
    request={"model":model,"messages":[{"role":"system","content":system},
                        {"role":"user","content":user}],
             "format":schema,"stream":False,"options":{"temperature":0,"num_ctx":num_ctx}}
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

#!/usr/bin/env python3
"""Controlled readiness test: fixed qwen3:8b, same 56 REAL sentences, two prompts.

Read preexisting local A0 predictions.jsonl. Never modifies A0.
A1 ambiguity/attribution discipline; A2 evidence-first discipline.
Use same schema, temperature, and source sentence for all variants. This is
an experiment, not a verified improvement, and does not change Component 2/3.
"""
import argparse
import hashlib
import json
import pathlib
import sys
import time
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from stage1a_component1_ollama import (
  EXTRACTION_SCHEMA, EXTRACT_SYSTEM, VERIFICATION_SCHEMA, VERIFY_SYSTEM,
  call_ollama, validate_extraction, verify_decisions)

A1=EXTRACT_SYSTEM+"""
CRITICAL ADDITION FOR AMBIGUITY AND ATTRIBUTION:
1. Never resolve a misspelling, unusual adjective or ambiguous referent by guessing.
   Preserve the literal phrase and put uncertainty in qualifiers.
2. Do not convert subjective feelings into objective site properties.
3. Keep speculation, questions, rhetorical clauses, conditional/hedged claims,
   change-of-state and loss/absence exactly within the meaning of each claim.
4. Preserve who or what is responsible for an experience; do not invent a causal link.
5. For each clause, capture its core predicate and only the source-supported modifiers.
These rules concern semantic fidelity, NOT emotion categories.
"""

A2=EXTRACT_SYSTEM+"""
CRITICAL ADDITION FOR EVIDENCE-FIRST CLAIM ASSEMBLY:
1. First locate the smallest EXACT contiguous source quotation that contains a
   complete assertion, including its subject and negation/hedging/attribution.
2. Compose one atomic claim only after selecting that quotation; it must entail
   your claim without unstated contextual assumptions. Whole sentence permitted
   when shorter quote loses the connection.
3. Preserve literal unusual or misspelled words; do not silently normalize them.
   If a relation is ambiguous, keep the ambiguity in qualifiers rather than guessing.
4. Extract independent coexisting assertions separately when supported by distinct
   clauses, but do not fabricate implied objects or causes.
5. Preserve explicitly reported experiences and their environmental attribution;
   don't convert them into universal site facts.
No nine-emotion label or relevance score.
"""

FIXED=((55,0),(55,1),(55,2),(74,0),(74,1),(97,0),
       (97,2),(113,0),(123,0),(139,0),(181,0),(187,0))

def read_baseline(path):
    records=[json.loads(s) for s in pathlib.Path(path).read_text(encoding="utf8").splitlines() if s.strip()]
    keys=set()
    for r in records:
        src=r["source"];k=(src["row"],src["sentence_index"])
        if k in keys:raise ValueError("Duplicate baseline source key")
        keys.add(k)
        if src["original_review"][src["sentence_start"]:src["sentence_end"]]!=src["original_sentence"]:
            raise ValueError("Source mismatch in baseline")
        if r["B"]["model"]!="qwen3:8b":
            raise ValueError("Baseline must be original qwen3:8b, not "+r["B"]["model"])
    if len(records)!=56:raise ValueError("Expected all 56 original sentences: got "+str(len(records)))
    return records

def fingerprint(records):
    payload=[(r["source"]["row"],r["source"]["sentence_index"],r["source"]["original_sentence"]) for r in records]
    return hashlib.sha256(json.dumps(payload,ensure_ascii=False).encode("utf8")).hexdigest()

def experiment_one(args,baseline,variant):
    original=baseline["source"]["original_sentence"]
    sys_prompt={"A1":A1,"A2":A2}[variant]
    data,meta=call_ollama(args.url,args.model,sys_prompt,
        "Original review sentence, verbatim:\n"+original,
        EXTRACTION_SCHEMA,args.timeout,args.num_ctx)
    candidates=validate_extraction(data,original)
    verifier_error=None
    decisions={}
    if candidates:
        numbered=[{"index":x["index"],"claim":x["claim"],"subject":x["subject"],
          "predicate":x["predicate"],"object":x["object"],
          "qualifiers":x["qualifiers"],"evidence_quote":x["evidence_quote"]}
          for x in candidates]
        try:
            obj,_=call_ollama(args.url,args.model,VERIFY_SYSTEM,
                  "ORIGINAL SOURCE SENTENCE:\n"+original+
                  "\n\nPROPOSED CLAIMS:\n"+json.dumps(numbered,ensure_ascii=False),
                  VERIFICATION_SCHEMA,args.timeout,args.num_ctx)
            decisions=verify_decisions(obj,candidates)
        except Exception as exc:
            verifier_error=repr(exc)
    enriched=[]
    for c in candidates:
        v=decisions.get(c["index"],{"verdict":"unverified","reason":verifier_error or "Not checked"})
        passed=(c["quote_match_status"]=="exact_unique" and v["verdict"]=="supported")
        enriched.append({**c,"verifier":v,
          "status":"candidate_passed_checks" if passed else "flagged_not_accepted",
          "checks_not_ground_truth":True})
    return {"source":baseline["source"],"condition":variant,"model":args.model,
      "observations":enriched,"generation":meta,"verification_error":verifier_error,
      "original_sentence_retained":original,
      "experiment":{"temperature":0,"num_ctx":args.num_ctx,
                    "prompt_sha256":hashlib.sha256(sys_prompt.encode("utf8")).hexdigest()}}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--baseline",default="reports/component1_ollama_qwen3_8b/predictions.jsonl")
    p.add_argument("--output",default="reports/component1_prompt_readiness")
    p.add_argument("--model",default="qwen3:8b")
    p.add_argument("--url",default="http://127.0.0.1:11434")
    p.add_argument("--timeout",type=int,default=300)
    p.add_argument("--num-ctx",type=int,default=8192)
    p.add_argument("--full",action="store_true",help="Run on all 56 sentences; default is fixed 12-sentence diagnostic set")
    p.add_argument("--check-only",action="store_true",help="Verify source and selection only")
    p.add_argument("--resume",action="store_true")
    args=p.parse_args()
    if args.model!="qwen3:8b":
        p.error("Controlled prompt ablation requires SAME qwen3:8b as baseline")
    base=read_baseline(args.baseline)
    sha=fingerprint(base)
    selection=base if args.full else [r for r in base if (r["source"]["row"],r["source"]["sentence_index"]) in FIXED]
    if not args.full and len(selection)!=len(FIXED):
        raise ValueError("Missing diagnostic source cases")
    output=pathlib.Path(args.output)/("full" if args.full else "diagnostic")
    keys=[(r["source"]["row"],r["source"]["sentence_index"],v)
          for r in selection for v in ("A1","A2")]
    if args.check_only:
        print(json.dumps({"corpus_sha256":sha,"baseline_sentences":len(base),
             "selected_source_sentences":len(selection),"model_calls_extraction_plus_verifier_max":len(keys)*2,
             "conditions":["A0 frozen original","A1 ambiguity","A2 evidence_first"],
             "target_directory":str(output)},indent=2))
        return
    output.mkdir(parents=True,exist_ok=True)
    file=output/"predictions.jsonl"
    if file.exists() and not args.resume:
        p.error("Result file already exists; use --resume or a new --output")
    done={}
    if file.exists():
        for line in file.read_text(encoding="utf8").splitlines():
            if not line.strip():continue
            r=json.loads(line);key=(r["source"]["row"],r["source"]["sentence_index"],r["condition"])
            if key in done:raise ValueError("Duplicate candidate result")
            if r["model"]!=args.model or r["original_sentence_retained"]!=r["source"]["original_sentence"]:
                raise ValueError("Invalid resume record")
            expectedsha=hashlib.sha256({"A1":A1,"A2":A2}[r["condition"]].encode("utf8")).hexdigest()
            if r["experiment"]["prompt_sha256"]!=expectedsha or r["experiment"]["num_ctx"]!=args.num_ctx:
                raise ValueError("Resume prompt/config mismatch")
            done[key]=r
    if not set(done).issubset(set(keys)):raise ValueError("Resume output contains unrelated cases")
    errors=[]
    with file.open("a" if args.resume else "w",encoding="utf8") as handle:
        for record in selection:
            for variant in ("A1","A2"):
                key=(record["source"]["row"],record["source"]["sentence_index"],variant)
                if key in done:continue
                try:
                    r=experiment_one(args,record,variant)
                    handle.write(json.dumps(r,ensure_ascii=False)+"\n");handle.flush()
                    done[key]=r
                    print("OK",variant,key[:2],"claims",len(r["observations"]),flush=True)
                except Exception as exc:
                    errors.append({"key":key,"error":repr(exc)})
                    print("ERROR",key,repr(exc),file=sys.stderr,flush=True)
                    break
            if errors:break
    counts={}
    for v in ("A1","A2"):
        subset=[r for k,r in done.items() if k[2]==v]
        claims=[c for r in subset for c in r["observations"]]
        counts[v]={"sentences":len(subset),"candidate_claims":len(claims),
              "quote_exact_unique":sum(c["quote_match_status"]=="exact_unique" for c in claims),
              "passed_self_checks":sum(c["status"]=="candidate_passed_checks" for c in claims),
              "flagged":sum(c["status"]!="candidate_passed_checks" for c in claims),
              "verifier_errors":sum(bool(r["verification_error"]) for r in subset)}
    result={"model":args.model,"source_sha256":sha,"scope":"all_56" if args.full else "12_fixed_diagnostic",
           "selected_sentences":len(selection),"expected_variant_results":len(keys),
           "variant_results_completed":len(done),"counts":counts,"errors":errors,
           "accuracy_claim":"NONE: source quotes, same-model verification and output volume are not accuracy"}
    (output/"summary.json").write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding="utf8")
    print(json.dumps(result,indent=2,ensure_ascii=False),flush=True)
    if errors or len(done)!=len(keys):raise SystemExit(2)
if __name__=="__main__":main()

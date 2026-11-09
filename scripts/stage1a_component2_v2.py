#!/usr/bin/env python3
"""Stage 1A Component 2 v2: place eligibility + directional-neutral emotion applicability.

Read original frozen Qwen3 A0 output, never regenerate Component 1 or call NLI.
Preserve every source sentence, candidate, raw label, and flagged inconsistency.
The selection is a provisional high-recall NLI input suggestion, NOT a gold label.
"""
import argparse
import collections
import hashlib
import json
import pathlib
import sys

from stage1a_component1_ollama import call_ollama
from stage1a_component1_prompt_readiness import FIXED
from stage1a_component2_eligibility_pilot import load, source_hash, PILOT_EMOTIONS

SOURCE_SHA = "144aee54fd70fdd2b440bc1e0f05fc71b63e79e26bf525b995a6260c0936d00e"
LABELS = ("direct", "indirect", "not_applicable", "uncertain")

# Eligibility and relevance are deliberately two different questions.
# Evidence quote must be a literal substring of original review sentence.
SCHEMA = {
 "type": "object", "additionalProperties": False,
 "properties": {
  "decisions": {"type": "array", "items": {
   "type": "object", "additionalProperties": False,
   "properties": {
    "index": {"type": "integer"},
    "place_related": {"type": "string", "enum": ["yes","no","uncertain"]},
    "place_reason": {"type": "string"},
    "applicability": {"type": "array", "items": {
     "type": "object", "additionalProperties": False,
     "properties": {
      "emotion": {"type": "string", "enum": list(PILOT_EMOTIONS)},
      "status": {"type": "string", "enum": list(LABELS)},
      "basis_quote": {"type": "string"},
      "reason": {"type": "string"}
     },
     "required": ["emotion","status","basis_quote","reason"]
    }}
   },
   "required": ["index","place_related","place_reason","applicability"]
  }}
 },
 "required": ["decisions"]
}
SYSTEM = """You annotate TWO separate tasks for evidence extracted from REAL reviews of a place.
You are NOT deciding whether an emotion is true, positive, negative, entailed, or contradicted.

TASK 1 — PLACE ELIGIBILITY:
'yes': observation reports an attribute, condition, use, accessibility, social interaction,
or stated feeling/experience AT or ABOUT the reviewed location. This includes subjective
reviews of the site, changes to the site, and evaluations like 'inspiring place' even
if emotion relevance is uncertain. A place fact need not have an emotional adjective.
'no': clearly an event, activity or fact unrelated to that location, despite appearing
in the same review.
'uncertain': ambiguous location attribution, unresolved reference, or suspect extraction.
DO NOT call an observation ineligible merely because it is vague, not a physical feature,
or unrelated to a target emotion. Do not force uncertain observations to 'yes'.

TASK 2 — APPLICABILITY TO EACH EMOTION independently:
'direct': the ORIGINAL source explicitly reports that atmosphere/experience or a
clear synonymous expression, AND attributes it to the place. Example: explicitly feeling
protected is direct to subjective feelings of safety, NOT proof of objectively safe conditions.
'indirect': a specific, source-grounded physical/social fact or experience has a defensible,
non-generic relation to the emotion, either SUPPORTING OR CONTRADICTING it; this is not
a sentiment classification. A police patrol is indirect evidence to perceived safety,
not direct proof of feeling safe.
'not_applicable': no specific link can be defended from the source; generic adjectives
like 'great' or 'good', prestige or proximity alone do not automatically apply to every emotion.
'uncertain': the potential connection depends on an unclear or speculative interpretation,
or the source/extracted claim may be malformed or unsupported.

For direct and indirect, copy a verbatim, contiguous source phrase in basis_quote that
actually establishes the claimed connection. If evidence is ambiguous, choose uncertain.
For not_applicable or uncertain, basis_quote may be empty. Never manufacture quotations.
DO NOT use 'direct' for descriptions that merely imply an emotion (e.g. cozy can
indirectly suggest inviting, but is not a literal visitor report of feeling welcomed).
Do not silently repair misspellings or certainty. Be conservative about causal claims.
When place eligibility is 'no', emotion applicability should normally be not_applicable;
when 'uncertain', avoid confident direct/indirect labels (use uncertain instead).
Return every indexed candidate, and one applicability record for each emotion.
No other labels, analysis, NLI decisions, or scores. Return JSON only."""

def validate_response(data, candidates, sentence):
    decisions=data.get("decisions") if isinstance(data,dict) else None
    if not isinstance(decisions,list) or len(decisions)!=len(candidates):
        raise ValueError("Incomplete or malformed decisions")
    results={}
    for d in decisions:
        if not isinstance(d,dict):raise ValueError("Non-object decision")
        i=d.get("index")
        if type(i) is not int or i in results or i<0 or i>=len(candidates):
            raise ValueError("Duplicate/invalid candidate index")
        if d.get("place_related") not in ("yes","no","uncertain") or not isinstance(d.get("place_reason"),str):
            raise ValueError("Invalid place eligibility")
        values=d.get("applicability")
        if not isinstance(values,list) or len(values)!=len(PILOT_EMOTIONS):
            raise ValueError("Missing applicability labels")
        byemotion={}
        for a in values:
            if not isinstance(a,dict):raise ValueError("Invalid emotion record")
            name=a.get("emotion")
            if name not in PILOT_EMOTIONS or name in byemotion or a.get("status") not in LABELS:
                raise ValueError("Wrong/duplicate emotion or invalid status")
            if not isinstance(a.get("reason"),str) or not isinstance(a.get("basis_quote"),str):
                raise ValueError("Missing reason or quote")
            byemotion[name]=a
        if len(byemotion)!=len(PILOT_EMOTIONS):raise ValueError("Missing emotion")
        results[i]=d
    return results

def check_and_handoff(d, sentence):
    """Mechanical safety checks, not semantic validation.

    Do not overwrite raw model judgments. A conflict means review-required;
    unverified labels are never quietly corrected into confident NLI selection.
    """
    flags=[]
    out={}
    eligibility=d["place_related"]
    for a in d["applicability"]:
        e=a["emotion"];status=a["status"];quote=a["basis_quote"]
        problems=[]
        if status in ("direct","indirect"):
            if not quote or quote not in sentence:
                problems.append("missing_or_nonliteral_evidence_quote")
        if eligibility=="no" and status in ("direct","indirect"):
            problems.append("ineligible_but_relevant")
        if eligibility=="uncertain" and status in ("direct","indirect"):
            problems.append("uncertain_attribution_but_confident_relevance")
        if problems:
            flags.extend(e+":"+problem for problem in problems)
        # Not a hard deletion: this is a proposed NLI routing, always
        # retaining the original sentence and all original candidates.
        if problems or eligibility=="uncertain" or status=="uncertain":
            route="needs_review"
        elif eligibility=="no" or status=="not_applicable":
            route="not_selected"
        else:
            route="nli_candidate"  # no directional inference has been run
        out[e]={"route":route,"flags":problems,
                "quote_exact_in_original":bool(quote and quote in sentence)}
    return out,flags

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",default="reports/component1_ollama_qwen3_8b/predictions.jsonl")
    p.add_argument("--previous",default="reports/stage1a_component2_eligibility_pilot/diagnostic/decisions.jsonl")
    p.add_argument("--output",default="reports/stage1a_component2_v2")
    p.add_argument("--model",default="qwen3:8b")
    p.add_argument("--url",default="http://127.0.0.1:11434")
    p.add_argument("--timeout",type=int,default=900)
    p.add_argument("--num-ctx",type=int,default=8192)
    p.add_argument("--all",action="store_true")
    p.add_argument("--check-only",action="store_true")
    p.add_argument("--resume",action="store_true")
    a=p.parse_args()
    base=load(a.input)
    if len(base)!=56 or source_hash(base)!=SOURCE_SHA:
        raise ValueError("Input differs from frozen 56-sentence Qwen3 dataset")
    selected=base if a.all else [r for r in base if (r["source"]["row"],r["source"]["sentence_index"]) in FIXED]
    if not a.all and len(selected)!=len(FIXED):raise ValueError("Diagnostic subset mismatch")
    keys={(r["source"]["row"],r["source"]["sentence_index"]) for r in selected}
    prior={}
    prev=pathlib.Path(a.previous)
    if prev.exists():
        for line in prev.read_text(encoding="utf8").splitlines():
            if not line.strip():continue
            r=json.loads(line);s=r["source"];k=(s["row"],s["sentence_index"])
            if k in keys:
                if k in prior:raise ValueError("Duplicate old records")
                prior[k]=r
    output=pathlib.Path(a.output)/("all56" if a.all else "diagnostic")
    path=output/"decisions.jsonl"
    config_sha=hashlib.sha256((SYSTEM+json.dumps(PILOT_EMOTIONS,sort_keys=True)).encode("utf8")).hexdigest()
    if a.check_only:
        print(json.dumps({"selected_sentences":len(selected),
          "candidate_claims":sum(len(r["C"]["observations"]) for r in selected),
          "prior_matched_sentences":len(prior),"emotion_definitions":PILOT_EMOTIONS,
          "preserves_all_source_and_claims":True,"NLI_ran":False,
          "target_file":str(path)},indent=2))
        return
    if path.exists() and not a.resume:p.error("Existing outputs; use --resume to continue safely")
    output.mkdir(parents=True,exist_ok=True)
    completed={}
    if path.exists():
        for line in path.read_text(encoding="utf8").splitlines():
            if not line.strip():continue
            r=json.loads(line);s=r["source"];k=(s["row"],s["sentence_index"])
            if k in completed or k not in keys or r.get("config_sha256")!=config_sha or r.get("model")!=a.model:
                raise ValueError("Cannot resume mismatched or duplicated result")
            completed[k]=r
    errors=[]
    with path.open("a" if a.resume else "w",encoding="utf8") as file:
        for record in selected:
            s=record["source"];key=(s["row"],s["sentence_index"])
            if key in completed:continue
            claims=record["C"]["observations"]
            numbered=[{"index":i,"claim":c["claim"],"qualifiers":c["qualifiers"],
               "evidence_quote":c["evidence_quote"],"extractor_status":c["status"]}
               for i,c in enumerate(claims)]
            try:
                if claims:
                    obj,_=call_ollama(a.url,a.model,SYSTEM,
                        "REVIEW CONTEXT FOR ATTRIBUTION ONLY:\n"+s["original_review"]+
                        "\nORIGINAL SOURCE SENTENCE (AUTHORITY):\n"+s["original_sentence"]+
                        "\nEMOTIONS:\n"+json.dumps(PILOT_EMOTIONS,ensure_ascii=False)+
                        "\nCANDIDATE OBSERVATIONS:\n"+json.dumps(numbered,ensure_ascii=False),
                        SCHEMA,a.timeout,a.num_ctx)
                    decisions=validate_response(obj,claims,s["original_sentence"])
                else:decisions={}
                rows=[]
                for i,c in enumerate(claims):
                    d=decisions[i];handoff,flags=check_and_handoff(d,s["original_sentence"])
                    prior_decision=None
                    old=prior.get(key)
                    if old and i<len(old["candidates"]):
                        prior_decision=old["candidates"][i].get("component2")
                    rows.append({"index":i,"component1":c,"raw_component2_v2":d,
                                 "routing_by_emotion":handoff,"consistency_flags":flags,
                                 "prior_component2_v1":prior_decision})
                out={"source":s,"model":a.model,"config_sha256":config_sha,
                     "candidates":rows,"original_sentence_fallback":s["original_sentence"],
                     "non_destructive":True,"no_nli_executed":True,
                     "selection_is_not_accuracy":True}
                file.write(json.dumps(out,ensure_ascii=False)+"\n");file.flush()
                completed[key]=out
                print("OK",len(completed),"/",len(selected),"row",key[0],
                      "sentence",key[1],"candidates",len(rows),flush=True)
            except Exception as exc:
                errors.append({"row":key[0],"sentence_index":key[1],"error":repr(exc)})
                print("ERROR",key,repr(exc),file=sys.stderr,flush=True)
                break
    candidates=[c for r in completed.values() for c in r["candidates"]]
    byemo={e:dict(collections.Counter(c["raw_component2_v2"]["applicability"][j]["status"]
                for c in candidates)) for j,e in enumerate(PILOT_EMOTIONS)}
    summary={"selected_sentences":len(selected),"sentences_completed":len(completed),
        "candidates":len(candidates),
        "place_related":dict(collections.Counter(c["raw_component2_v2"]["place_related"] for c in candidates)),
        "applicability":byemo,
        "consistency_flagged_candidates":sum(bool(c["consistency_flags"]) for c in candidates),
        "matched_v1_source_sentences":len(prior),
        "errors":errors,
        "note":"Model-generated candidate routing, not accuracy; original claims and source retained; Component 3 NLI not run."}
    (output/"summary.json").write_text(json.dumps(summary,indent=2),encoding="utf8")
    print(json.dumps(summary,indent=2),flush=True)
    if errors or len(completed)!=len(selected):raise SystemExit(2)
if __name__=="__main__":main()

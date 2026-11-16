#!/usr/bin/env python3
"""Frozen matched prompt/codebook repeat benchmark, 2 models x 2 prompts x 3 repetitions x 12 target segments.
Stage 1A codebook v0.1 is EXPLICITLY experimental; all prior audit files remain unchanged.
"""
from __future__ import annotations
import argparse, csv, hashlib, json, re, sys, time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import stage1a_runpod_firstlook_12reviews as base
import stage1a_stage2_reduced_20261113 as previous

MODELS=("gemma4:31b-it-bf16","qwen3.8:27b")
CONDITIONS=("original","codebook_v01")
CATEGORIES=("calm","inviting","safe")
VERDICTS=("supports","opposes","none","uncertain")
CODEBOOK=ROOT/"Docs/STAGE1A_PILOT_CODEBOOK_V0_1_2026-11-15.md"
PROMPT=ROOT/"Docs/STAGE1A_PILOT_PROMPT_V0_1_2026-11-15.md"
SCHEMA=ROOT/"configs/stage1a_pilot_verdict_schema_v0_1.json"
REFERENCE=ROOT/"research_audit/stage1a_stage2_context_live_2026-11-13/TARGET_SEGMENT_REFERENCE_AND_PREDICTIONS.csv"
OUT=ROOT/"reports/stage1a_codebook_v01_repeat_2026-11-16"
LATEST_BLIND={
"K01:calm":"mixed","K01:inviting":"supports","K02:calm":"none","K02:safe":"none",
"K03:calm":"opposes","K03:inviting":"opposes","K04:inviting":"supports","K05:safe":"opposes",
"K06:inviting":"opposes","U01:calm":"opposes","U02:inviting":"opposes","U04:inviting":"supports",
"U05:inviting":"mixed","U06:calm":"supports"}
OPTIONS={"temperature":0,"seed":42,"num_ctx":8192,"num_predict":2048}
FENCE=chr(96)*3

def h(x):
    if not isinstance(x,str):x=json.dumps(x,ensure_ascii=False,sort_keys=True)
    return hashlib.sha256(x.encode("utf-8")).hexdigest()

def load_cases():
    all_data=base.cases()
    base.verify_corpus(all_data)
    for x in all_data:
        assert previous.TARGET[x["case_id"]] in x["text"], x["case_id"]
    return all_data

def prompt_for(condition):
    if condition=="original":
        return base.SYSTEM+previous.SEGMENT_ADD,base.SCHEMA
    txt=PROMPT.read_text(encoding="utf-8")
    section=txt.split("## Exact system message (replace placeholder before use)",1)[1]
    template=section.split(FENCE+"text",1)[1].split(FENCE,1)[0].strip()
    assert template.count("{{CODEBOOK_TEXT}}")==1
    codebook=CODEBOOK.read_text(encoding="utf-8")
    system=template.replace("{{CODEBOOK_TEXT}}",codebook)
    assert "CODEBOOK (immutable for this run)" in system
    schema=json.loads(SCHEMA.read_text(encoding="utf-8"))
    return system,schema

def validate_new(obj,target):
    if not isinstance(obj,dict) or set(obj)!={"codebook_version","evidence","assessments"}:
        raise ValueError("Wrong top-level fields")
    if obj["codebook_version"]!="0.1":raise ValueError("Wrong codebook version")
    ev=obj["evidence"]; ass=obj["assessments"]
    if not isinstance(ev,list) or not isinstance(ass,list) or len(ass)!=3:
        raise ValueError("Bad evidence/assessment arrays")
    ids={};clean=[]
    for e in ev:
        if not isinstance(e,dict) or set(e)!={"id","quote","track","referent","emotion","direction","reason"}:
            raise ValueError("Bad evidence record")
        if not all(isinstance(v,str) for v in e.values()):
            raise ValueError("Nonstring evidence field")
        if not re.fullmatch(r"e[1-9][0-9]*",e["id"]) or e["id"] in ids:
            raise ValueError("Bad/duplicate evidence ID")
        if e["track"] not in ("E","T") or e["emotion"] not in CATEGORIES or e["direction"] not in ("supports","opposes"):
            raise ValueError("Bad evidence tags")
        if e["referent"] not in base.REFERENTS or not e["quote"] or not e["reason"]:
            raise ValueError("Bad evidence referent/content")
        ids[e["id"]]=e
        clean.append({**e,"source_exact":e["quote"] in target})
    cats=[]
    for a in ass:
        if not isinstance(a,dict) or set(a)!={"emotion","verdict","support_ids","oppose_ids","reason"}:
            raise ValueError("Bad assessment fields")
        if a["emotion"] not in CATEGORIES or a["verdict"] not in VERDICTS or not isinstance(a["reason"],str):
            raise ValueError("Bad assessment tags")
        for direction,field in (("supports","support_ids"),("opposes","oppose_ids")):
            ref=a[field]
            if not isinstance(ref,list) or len(ref)!=len(set(ref)):
                raise ValueError("Bad evidence references")
            for i in ref:
                if i not in ids or ids[i]["emotion"]!=a["emotion"] or ids[i]["direction"]!=direction:
                    raise ValueError("Unknown/mislinked evidence ID "+str(i))
        if a["verdict"]=="none" and (a["support_ids"] or a["oppose_ids"]):
            raise ValueError("None cannot claim directional evidence")
        if a["verdict"]=="supports" and not a["support_ids"]:
            raise ValueError("Supports without support quote")
        if a["verdict"]=="opposes" and not a["oppose_ids"]:
            raise ValueError("Opposes without oppose quote")
        cats.append(a["emotion"])
    if cats!=list(CATEGORIES):raise ValueError("Assessment order/duplication")
    return {"evidence":clean,"assessments":ass}

def read_rows(path):
    if not path.exists():return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

def append(path,record):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("a",encoding="utf-8") as f:
        f.write(json.dumps(record,ensure_ascii=False,separators=(",",":"))+"\n")

def run(a):
    data=load_cases()
    system,schema=prompt_for(a.condition)
    digest=base.installed_digest(a.base,a.model)
    folder=OUT/a.model.replace(":","_")/a.condition/("repeat_"+str(a.repeat))
    folder.mkdir(parents=True,exist_ok=True)
    manifest={"protocol":"stage1a_codebook_v01_repeat_20261116","model":a.model,"model_digest":digest,
      "condition":a.condition,"repeat":a.repeat,"codebook_sha256":h(CODEBOOK.read_text(encoding="utf-8")),
      "prompt_file_sha256":h(PROMPT.read_text(encoding="utf-8")),
      "system_prompt_sha256":h(system),"schema_sha256":h(schema),
      "source_case_sha256":h(data),"target_segments_sha256":h(previous.TARGET),
      "options":OPTIONS,"think":False,"keep_alive":"20m"}
    mf=folder/"manifest.json"
    if mf.exists() and json.loads(mf.read_text(encoding="utf-8"))!=manifest:
        raise ValueError("Manifest drift")
    if not mf.exists():mf.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
    done={x["case_id"] for x in read_rows(folder/"predictions.jsonl")}
    for x in data[:a.limit] if a.limit else data:
        if x["case_id"] in done:continue
        target=previous.TARGET[x["case_id"]]
        user={"target_segment":target,"full_review_context":x["text"]}
        payload={"model":a.model,"messages":[
          {"role":"system","content":system},{"role":"user","content":json.dumps(user,ensure_ascii=False)}],
          "format":schema,"stream":False,"think":False,"options":OPTIONS,"keep_alive":"20m"}
        start=time.monotonic();raw="";err="";meta={}
        try:
            result=base.request(a.base,"/api/chat",payload,timeout=300)
            raw=result.get("message",{}).get("content","")
            obj=json.loads(raw)
            pred=base.validate(obj,target) if a.condition=="original" else validate_new(obj,target)
            meta={k:result.get(k) for k in ("eval_count","prompt_eval_count","total_duration","done_reason")}
        except Exception as exc:
            err=repr(exc)
        rec={"case_id":x["case_id"],"model":a.model,"condition":a.condition,"repeat":a.repeat,
             "target":target,"elapsed_seconds":round(time.monotonic()-start,2),"meta":meta}
        append(folder/"raw_responses.jsonl",{**rec,"raw":raw,"error":err or None})
        if err:append(folder/"errors.jsonl",{**rec,"error":err})
        else:append(folder/"predictions.jsonl",{**rec,"result":pred})
        print(a.model,a.condition,a.repeat,x["case_id"],"ERROR "+err[:170] if err else "OK",
              rec["elapsed_seconds"],flush=True)
    good=len(read_rows(folder/"predictions.jsonl"))
    if good!=12:raise RuntimeError(f"Incomplete run {folder}: {good}/12 valid")

def reference():
    gold={}
    with REFERENCE.open(encoding="utf-8-sig",newline="") as f:
        for row in csv.DictReader(f):
            gold[row["case_id"]+":"+row["emotion"]]=row["reference"]
    assert len(gold)==36
    gold.update(LATEST_BLIND)
    return gold

def summarize():
    gold=reference()
    detail=[];stats={}
    for model in MODELS:
      for cond in CONDITIONS:
        per_run=[]
        for rep in (1,2,3):
          folder=OUT/model.replace(":","_")/cond/("repeat_"+str(rep))
          preds={p["case_id"]:p for p in read_rows(folder/"predictions.jsonl")}
          if len(preds)!=12:raise ValueError(f"{folder}: {len(preds)}/12 valid")
          recs=read_rows(folder/"raw_responses.jsonl")
          assessments={};nonexact=0;totalquotes=0;trackcounts={}
          for case_id,p in preds.items():
            result=p["result"]
            labels=result["emotions"] if cond=="original" else result["assessments"]
            for e in labels:
                key=case_id+":"+e["category" if cond=="original" else "emotion"]
                assessments[key]=e["verdict"]
            for e in result["evidence"]:
                totalquotes+=1
                nonexact+=not e["source_exact"]
                track=e["kind"] if cond=="original" else e["track"]
                trackcounts[track]=trackcounts.get(track,0)+1
          assert len(assessments)==36
          unambig={k:v for k,v in gold.items() if v!="mixed"}
          matches=sum(assessments[k]==v for k,v in unambig.items())
          counts={v:sum(x==v for x in assessments.values()) for v in ("supports","opposes","none","uncertain","mixed")}
          per_run.append(assessments)
          stats[f"{model}|{cond}|r{rep}"]={"valid_cases":len(preds),"matches_comparable":matches,"denominator":len(unambig),
            "verdict_counts":counts,"evidence_quotes":totalquotes,"nonexact_quotes":nonexact,
            "tracks":trackcounts,"model_json_errors_retried":len([e for e in recs if e["error"]])}
          for k,v in assessments.items():
            detail.append({"model":model,"condition":cond,"repeat":rep,"case_id":k.split(":")[0],
              "emotion":k.split(":")[1],"verdict":v,"latest_user_blind_reference_or_original":gold[k],
              "reference_ambiguity":gold[k]=="mixed"})
        unanimous=sum(len({per_run[0][k],per_run[1][k],per_run[2][k]})==1 for k in gold)
        changed=[k for k in gold if len({per_run[0][k],per_run[1][k],per_run[2][k]})>1]
        stats[f"{model}|{cond}|repeatability"]={"unanimous_over_3":unanimous,"out_of":36,"unstable_keys":changed}
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/"summary.json").write_text(json.dumps(stats,ensure_ascii=False,indent=2),encoding="utf-8")
    with (OUT/"verdicts.csv").open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(detail[0]));w.writeheader();w.writerows(detail)
    print(json.dumps(stats,ensure_ascii=False,indent=2))

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--stage",choices=("prepare","run","report"),required=True)
    p.add_argument("--model",choices=MODELS,default=MODELS[0])
    p.add_argument("--condition",choices=CONDITIONS,default=CONDITIONS[0])
    p.add_argument("--repeat",type=int,choices=(1,2,3),default=1)
    p.add_argument("--base",default="http://127.0.0.1:11434")
    p.add_argument("--limit",type=int,default=0)
    a=p.parse_args()
    if a.stage=="prepare":
        cases=load_cases()
        for cond in CONDITIONS:
            prompt,schema=prompt_for(cond)
            print(cond,"cases",len(cases),"system_sha",h(prompt),"schema_sha",h(schema),"length",len(prompt))
        assert len(reference())==36
    elif a.stage=="run":run(a)
    else:summarize()

if __name__=="__main__":main()

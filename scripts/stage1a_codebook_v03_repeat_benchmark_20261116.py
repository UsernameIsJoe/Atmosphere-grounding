#!/usr/bin/env python3
"""Codebook v0.3 controlled run ONLY; 2 models x 3 repetitions x 12 original segments.
Never rerun archived original/v0.1 conditions. No invalid-response retry.
"""
import sys, json, time, hashlib, argparse
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import stage1a_runpod_firstlook_12reviews as base
import stage1a_codebook_v01_repeat_benchmark_20261116 as prev
import stage1a_stage2_reduced_20261113 as targets

MODELS=("qwen3.8:27b","gemma4:31b-it-bf16")
EXPECTED={
 "qwen3.8:27b":"aaee06c39dcf2437cde036998d960e1fc1494b8191be7cc9657d01e509097813",
 "gemma4:31b-it-bf16":"df1661a2a6aaa94faf24bbaf23a691877a27d0e6052598f105a225618a079e76"
}
CATS=("calm","inviting","safe")
OPTIONS={"temperature":0,"seed":42,"num_ctx":8192,"num_predict":2048}
CODEBOOK=ROOT/"Docs/STAGE1A_PILOT_CODEBOOK_V0_3_2026-11-16.md"
PROMPT=ROOT/"Docs/STAGE1A_PILOT_PROMPT_V0_3_2026-11-16.md"
SCHEMA=ROOT/"configs/stage1a_pilot_verdict_schema_v0_3.json"
OUT=ROOT/"reports/stage1a_codebook_v03_repeat_2026-11-16"

def sha(s):
    if not isinstance(s,str):s=json.dumps(s,ensure_ascii=False,sort_keys=True)
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def prompt():
    document=PROMPT.read_text(encoding="utf-8")
    fence=chr(96)*3
    segment=document.split("## Exact system message",1)[1].split(fence+"text",1)[1].split(fence,1)[0].strip()
    assert segment.count("{{CODEBOOK_TEXT}}")==1
    system=segment.replace("{{CODEBOOK_TEXT}}",CODEBOOK.read_text(encoding="utf-8"))
    schema=json.loads(SCHEMA.read_text(encoding="utf-8"))
    assert schema["properties"]["codebook_version"]["const"]=="0.3"
    return system,schema

def validate(obj,target):
    if not isinstance(obj,dict) or set(obj)!={"codebook_version","assessments"} or obj["codebook_version"]!="0.3":
        raise ValueError("top-level structure/version invalid")
    a=obj["assessments"]
    if not isinstance(a,list) or len(a)!=3:raise ValueError("three assessments required")
    for i,x in enumerate(a):
        if not isinstance(x,dict) or set(x)!={"emotion","verdict","reason","evidence"}:
            raise ValueError("bad assessment structure")
        v=x["verdict"]
        if x["emotion"]!=CATS[i] or v not in ("supports","opposes","none","uncertain") or not isinstance(x["reason"],str) or not x["reason"].strip():
            raise ValueError("bad emotion/verdict/reason")
        es=x["evidence"]
        if not isinstance(es,list):raise ValueError("evidence must be an array")
        if v=="none" and es:raise ValueError("none has directional evidence")
        found=False
        for e in es:
            if not isinstance(e,dict) or set(e)!={"quote","direction","track","referent"}:raise ValueError("bad evidence record")
            if not all(isinstance(z,str) for z in e.values()):raise ValueError("nonstring evidence")
            if not e["quote"] or e["quote"] not in target:raise ValueError("non-exact target quote")
            if e["direction"] not in ("supports","opposes") or e["track"] not in ("E","T") or e["referent"] not in base.REFERENTS:
                raise ValueError("incorrect evidence tag")
            found|=(v==e["direction"])
        if v in ("supports","opposes") and not found:
            raise ValueError("directional verdict lacks matching evidence")
    return obj

def file_for(model,rep):
    return OUT/(model.replace(":","_")+"__repeat"+str(rep)+".json")

def run(model,host):
    data=prev.load_cases();system,schema=prompt()
    digest=base.installed_digest(host,model)
    if digest!=EXPECTED[model]:
        raise RuntimeError(f"MODEL DIGEST DRIFT {model}: {digest}")
    manifest={
      "protocol":"stage1a_v03_matched","model":model,"model_digest":digest,
      "codebook_sha256":sha(CODEBOOK.read_text(encoding="utf-8")),
      "prompt_sha256":sha(PROMPT.read_text(encoding="utf-8")),
      "system_sha256":sha(system),"schema_sha256":sha(schema),
      "cases_sha256":sha(data),"target_sha256":sha(targets.TARGET),
      "options":OPTIONS,"think":False,"keep_alive":"20m","version":"0.3","no_retry":True}
    OUT.mkdir(parents=True,exist_ok=True)
    for rep in (1,2,3):
        fp=file_for(model,rep)
        full_manifest={**manifest,"repeat":rep}
        if fp.exists():
            old=json.loads(fp.read_text(encoding="utf-8"))
            if old["manifest"]!=full_manifest:raise RuntimeError("manifest drift "+str(fp))
            records=old["cases"]
        else:records=[]
        done={x["case_id"] for x in records}
        for x in data:
            case=x["case_id"]
            if case in done:continue
            seg=targets.TARGET[case]
            body={
              "model":model,
              "messages":[
                {"role":"system","content":system},
                {"role":"user","content":json.dumps({"target_segment":seg,"full_review_context":x["text"]},ensure_ascii=False)}
              ],
              "format":schema,"stream":False,"think":False,
              "options":OPTIONS,"keep_alive":"20m"}
            raw="";validated=None;err=None;metadata={};start=time.monotonic()
            try:
                result=base.request(host,"/api/chat",body,timeout=300)
                raw=result.get("message",{}).get("content","")
                validated=validate(json.loads(raw),seg)
                metadata={k:result.get(k) for k in ("eval_count","prompt_eval_count","total_duration","done_reason")}
            except Exception as e:err=repr(e)
            record={"case_id":case,"target":seg,"raw":raw,"result":validated,"error":err,
                    "elapsed_seconds":round(time.monotonic()-start,2),"metadata":metadata}
            records.append(record)
            fp.write_text(json.dumps({"manifest":full_manifest,"cases":records},ensure_ascii=False,separators=(",",":")),encoding="utf-8")
            print(model,"r"+str(rep),case,"OK" if not err else "ERROR "+err,record["elapsed_seconds"],flush=True)
        if len(records)!=12:raise RuntimeError("incomplete repetition")
        print("COMPLETE",model,rep,"valid",sum(x["result"] is not None for x in records),"/12",flush=True)

def report():
    d=[]
    for model in MODELS:
        sets=[]
        for rep in (1,2,3):
            file=json.loads(file_for(model,rep).read_text(encoding="utf-8"))
            rows=file["cases"]
            good=[x for x in rows if x["result"] is not None]
            total=sum(len(x["result"]["assessments"]) for x in good)
            none=sum(x["verdict"]=="none" for row in good for x in row["result"]["assessments"])
            tracks={}
            for row in good:
                for x in row["result"]["assessments"]:
                    for e in x["evidence"]:tracks[e["track"]]=tracks.get(e["track"],0)+1
            d.append({"model":model,"repeat":rep,"valid":len(good),"total":len(rows),"none":none,"judgements":total,
              "errors":{x["case_id"]:x["error"] for x in rows if x["error"]},"tracks":tracks})
            sets.append({x["case_id"]:{a["emotion"]:a["verdict"] for a in x["result"]["assessments"]} for x in good})
        shared=set.intersection(*(set(s) for s in sets))
        total=stable=0;diff=[]
        for c in sorted(shared):
            for emotion in CATS:
                vs=[s[c][emotion] for s in sets]
                total+=1;stable+=len(set(vs))==1
                if len(set(vs))!=1:diff.append([c,emotion,vs])
        d.append({"model":model,"repeatability_valid_shared":f"{stable}/{total}","unstable":diff})
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/"summary.json").write_text(json.dumps(d,indent=2,ensure_ascii=False),encoding="utf-8")
    print(json.dumps(d,indent=2,ensure_ascii=False))

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--stage",choices=("prepare","run","report"),required=True)
    ap.add_argument("--model",choices=MODELS,default=MODELS[0])
    ap.add_argument("--host",default="http://127.0.0.1:11434")
    args=ap.parse_args()
    if args.stage=="prepare":
        print("CASES",len(prev.load_cases()),"PROMPT_CHARS",len(prompt()[0]),"SCHEMA",sha(prompt()[1]),"MODEL_DIGESTS",EXPECTED)
    elif args.stage=="run":run(args.model,args.host)
    else:report()

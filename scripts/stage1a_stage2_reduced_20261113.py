#!/usr/bin/env python3
"""Frozen Stage 2 context comparison: 2 models x 3 inputs x 12 authentic reviews."""
import argparse,json,time,hashlib,csv,random
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).parent))
import stage1a_runpod_firstlook_12reviews as base
MODELS=("qwen3.6:27b-bf16","gemma4:31b-it-bf16")
MODES=("segment","segment_context","full_review")
TARGET={
"K01":"It was so stressful but her humanity made everything so much better!",
"K02":"Lights in the small box were years away- it was completely dark.",
"K03":"I wouldn't go here if your looking for walk.",
"K04":"What made this visit extra special was how surprisingly uncrowded it was.",
"K05":"If the owner of the chickens sees it, he yells from his home and asks if you are feeding poison to them.",
"K06":"It’s not closed to the street though so you have to keep an eye on your kids.",
"U01":"1/2 of the space was empty to become a dance floor later in the night.",
"U02":"The three exhibits on display were quite underwhelming…",
"U03":"It is hard to get the sound of the Memorial Drive cars out of your head as they are only a few yards from this park with no real barriers blocking the sound.",
"U04":"This museum is fun for all ages.",
"U05":"This station is epic and famous, but not the cleanest.",
"U06":"Lovely sitting under the fairy lights in a comfy Adirondack chair, while a busker played songs from the 70s."
}
OUT=base.ROOT/"reports/stage1a_stage2_context_2026-11-13"
SEGMENT_ADD="""\nYou are assessing ONLY the specified TARGET SEGMENT. In evidence, quote text strictly from that segment. Do not import outside evidence. If full review is supplied, it may only clarify references or scope, not add evidence. Make each verdict about the TARGET SEGMENT, not the whole review."""
FULL_ADD="""\nAssess the COMPLETE REVIEW as written. Identify evidence throughout the review without privileged target. Preserve scope, negation, and source quotes."""
def read(path):
    return [json.loads(z) for z in path.read_text().splitlines() if z.strip()] if path.exists() else []
def write(path,item):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("a") as f: f.write(json.dumps(item,ensure_ascii=False)+"\n")
def prepare():
    data=base.cases()
    base.verify_corpus(data)
    for x in data:
        if TARGET[x["case_id"]] not in x["text"]:raise ValueError("Bad target "+x["case_id"])
    return data
def run(args):
    data=prepare()
    system=base.SYSTEM+(FULL_ADD if args.mode=="full_review" else SEGMENT_ADD)
    digest=base.installed_digest(args.base,args.model)
    folder=OUT/args.model.replace(":","_")/args.mode
    manifest={"protocol":"stage2_context_v1","model":args.model,"mode":args.mode,"digest":digest,"prompt_sha":base.sha(system),"cases_sha":base.sha(data),"targets_sha":base.sha(TARGET),"temperature":0,"seed":42,"think":False,"num_ctx":8192,"num_predict":2048}
    mf=folder/"manifest.json"
    if mf.exists() and json.loads(mf.read_text())!=manifest:raise ValueError("Manifest changed")
    folder.mkdir(parents=True,exist_ok=True)
    if not mf.exists():mf.write_text(json.dumps(manifest,indent=2))
    seen={r["case_id"] for r in read(folder/"predictions.jsonl")+read(folder/"errors.jsonl")}
    for x in data[:args.limit] if args.limit else data:
        if x["case_id"] in seen:continue
        target=TARGET[x["case_id"]]
        user=({"review":x["text"]} if args.mode=="full_review" else
              {"target_segment":target} if args.mode=="segment" else
              {"target_segment":target,"full_review_context":x["text"]})
        payload={"model":args.model,"messages":[{"role":"system","content":system},{"role":"user","content":json.dumps(user,ensure_ascii=False)}],"format":base.SCHEMA,"stream":False,"think":False,"options":{"temperature":0,"seed":42,"num_ctx":8192,"num_predict":2048},"keep_alive":"1m"}
        t=time.monotonic();raw="";error=None;meta={}
        try:
            res=base.request(args.base,"/api/chat",payload,timeout=300)
            raw=res.get("message",{}).get("content","")
            pred=base.validate(json.loads(raw),x["text"] if args.mode=="full_review" else target)
            meta={k:res.get(k) for k in ("eval_count","prompt_eval_count","total_duration","done_reason")}
        except Exception as exc:
            error=str(exc)
        common={"case_id":x["case_id"],"model":args.model,"mode":args.mode,"target":target,"elapsed_seconds":round(time.monotonic()-t,2),"meta":meta}
        write(folder/"raw_responses.jsonl",{**common,"raw":raw,"error":error})
        write(folder/("errors.jsonl" if error else "predictions.jsonl"),{**common,**({"error":error} if error else {"result":pred})})
        print(args.model,args.mode,x["case_id"],"ERROR "+error if error else "OK",common["elapsed_seconds"],flush=True)
def report():
    rows=[];summary={}
    for x in prepare():
        row={"case_id":x["case_id"],"target":TARGET[x["case_id"]],"full_review":x["text"]}
        for mode in MODES:
            order=list(MODELS);random.Random(20261113+sum(map(ord,x["case_id"]))+MODES.index(mode)).shuffle(order)
            for letter,model in zip(("A","B"),order):
                found=next((r for r in read(OUT/model.replace(":","_")/mode/"predictions.jsonl") if r["case_id"]==x["case_id"]),None)
                row[f"{mode}_{letter}_result"]=json.dumps(found["result"],ensure_ascii=False) if found else ""
                row[f"{mode}_{letter}_model"]=model
        rows.append(row)
    with (OUT/"comparison.csv").open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    for model in MODELS:
        for mode in MODES:
            p=OUT/model.replace(":","_")/mode
            summary[model+"/"+mode]={"valid":len(read(p/"predictions.jsonl")),"errors":len(read(p/"errors.jsonl"))}
    (OUT/"summary.json").write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary,indent=2))
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--stage",choices=("prepare","run","report"),required=True)
    p.add_argument("--model",choices=MODELS,default=MODELS[0])
    p.add_argument("--mode",choices=MODES,default=MODES[0])
    p.add_argument("--base",default="http://127.0.0.1:11434")
    p.add_argument("--limit",type=int,default=0)
    a=p.parse_args()
    if a.stage=="prepare":print("Frozen",len(prepare()),"real reviews",len(TARGET),"verified targets")
    elif a.stage=="run":run(a)
    else:report()

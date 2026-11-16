#!/usr/bin/env python3
"""Compare 2026-11-16 v0.3 outputs with archived original and v0.1;
report within-case paired agreement and non-none reference recall.
The provisional reference is *not* a gold set.
"""
import json,sys,csv
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import stage1a_codebook_v01_repeat_benchmark_20261116 as base
import stage1a_codebook_v03_repeat_benchmark_20261116 as run
ARCH=ROOT/"research_audit/stage1a_codebook_v01_repeat_live_2026-11-16"
OUT=run.OUT
CATS=("calm","inviting","safe")

def load_existing(model,condition,rep):
    name=model.replace(":","_")+"__"+condition+"__repeat"+str(rep)+".json"
    blob=json.loads((ARCH/name).read_text(encoding="utf-8"))
    ans={}
    for p in blob["predictions"]:
        a=p["result"]["emotions" if condition=="original" else "assessments"]
        ans[p["case_id"]]={x["category" if condition=="original" else "emotion"]:x["verdict"] for x in a}
    return ans

def main():
    gold=base.reference()
    rows=[];details=[]
    for model in run.MODELS:
        for rep in (1,2,3):
            cur=json.loads(run.file_for(model,rep).read_text(encoding="utf-8"))
            complete={r["case_id"]:{a["emotion"]:a["verdict"] for a in r["result"]["assessments"]}
                    for r in cur["cases"] if r["result"] is not None}
            old={cond:load_existing(model,cond,rep) for cond in ("original","codebook_v01")}
            for cond in old:
                shared=sorted(set(complete)&set(old[cond]))
                counts=Counter()
                for case in shared:
                    for emotion in CATS:
                        key=case+":"+emotion
                        ref=gold[key]
                        o=old[cond][case][emotion]
                        n=complete[case][emotion]
                        counts["joint_judgments"]+=1
                        counts["old_none"]+=o=="none"
                        counts["new_none"]+=n=="none"
                        counts["changed"]+=o!=n
                        if ref!="mixed":
                            counts["comparable"]+=1
                            counts["old_hits"]+=o==ref
                            counts["new_hits"]+=n==ref
                            if ref in ("supports","opposes"):
                                counts["reference_directional"]+=1
                                counts["old_directional_hits"]+=o==ref
                                counts["new_directional_hits"]+=n==ref
                        details.append({"model":model,"rep":rep,"case_id":case,
                           "emotion":emotion,"reference":ref,"previous_condition":cond,
                           "previous_verdict":o,"v03_verdict":n,"changed":o!=n})
                rows.append({"model":model,"rep":rep,"comparison_with":cond,
                  "v03_valid_cases":len(complete),"previous_valid_cases":len(old[cond]),
                  **dict(counts)})
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/"paired_comparisons.json").write_text(json.dumps(rows,indent=2,ensure_ascii=False),encoding="utf-8")
    with (OUT/"paired_verdicts.csv").open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(details[0]));w.writeheader();w.writerows(details)
    print(json.dumps(rows,indent=2,ensure_ascii=False))
if __name__=="__main__":main()

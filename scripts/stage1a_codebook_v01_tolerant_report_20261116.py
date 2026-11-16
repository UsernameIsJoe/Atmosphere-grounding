#!/usr/bin/env python3
"""Report completed v0.1 prompt experiment without hiding invalid/missing outputs.
Read-only reporting. Two disputed human "mixed" references are excluded from directional agreement.
"""
import csv,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import stage1a_codebook_v01_repeat_benchmark_20261116 as b
from collections import Counter

def rows(path):
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()] if path.exists() else []

def main():
    root=b.OUT
    gold=b.reference()
    out=[]
    verdict_rows=[]
    for model in b.MODELS:
      for condition in b.CONDITIONS:
        repetitions=[]
        for repeat in (1,2,3):
          folder=root/model.replace(":","_")/condition/("repeat_"+str(repeat))
          predictions=rows(folder/"predictions.jsonl")
          attempts=rows(folder/"raw_responses.jsonl")
          errors=rows(folder/"errors.jsonl")
          judgements={}
          quote_count=0;nonexact=0;animal_referent=0
          for p in predictions:
            catkey="category" if condition=="original" else "emotion"
            evalkey="emotions" if condition=="original" else "assessments"
            for e in p["result"][evalkey]:
              key=p["case_id"]+":"+e[catkey]
              judgements[key]=e["verdict"]
              verdict_rows.append({"model":model,"condition":condition,"repeat":repeat,"case_id":p["case_id"],
                                    "emotion":e[catkey],"verdict":e["verdict"],"reference":gold[key]})
            for e in p["result"]["evidence"]:
              quote_count+=1;nonexact+=int(not e["source_exact"])
              if e["referent"]=="animals" and not any(s in e["quote"].lower() for s in ("chicken","animal","bird")):
                animal_referent+=1
          comparable={k:v for k,v in gold.items() if v!="mixed" and k in judgements}
          exact=sum(judgements[k]==v for k,v in comparable.items())
          verdicts=Counter(judgements.values())
          row={"model":model,"condition":condition,"repeat":repeat,
               "valid_cases":len(predictions),"attempts":len(attempts),"invalid_attempts":sum(bool(x["error"]) for x in attempts),
               "distinct_invalid_cases":len(set(x["case_id"] for x in errors)),
               "reference_match":exact,"reference_denominator":len(comparable),
               "evidence_quotes":quote_count,"nonexact_quotes":nonexact,
               "suspect_animal_referents":animal_referent,
               "supports":verdicts["supports"],"opposes":verdicts["opposes"],
               "none":verdicts["none"],"uncertain":verdicts["uncertain"],"mixed":verdicts["mixed"]}
          out.append(row)
          repetitions.append(judgements)
        both=set.intersection(*(set(x) for x in repetitions))
        stable=sum(len({x[k] for x in repetitions})==1 for k in both)
        out.append({"model":model,"condition":condition,"repeat":"all3",
                    "shared_judgments":len(both),"stable_judgments":stable,
                    "unstable_ids":sorted(k for k in both if len({x[k] for x in repetitions})>1),
                    "missing_from_all3":sorted(set(gold)-both)})
    root.mkdir(parents=True,exist_ok=True)
    (root/"validity_and_repeatability.json").write_text(json.dumps(out,indent=2,ensure_ascii=False),encoding="utf-8")
    with (root/"verdicts_with_missing.csv").open("w",encoding="utf-8",newline="") as f:
      w=csv.DictWriter(f,fieldnames=["model","condition","repeat","case_id","emotion","verdict","reference"])
      w.writeheader();w.writerows(verdict_rows)
    print(json.dumps(out,indent=2,ensure_ascii=False))
if __name__=="__main__":main()

#!/usr/bin/env python3
"""Frozen, matched original-review Component 1 candidate audit. No ground truth."""
import json,re,pathlib
BASE=pathlib.Path("reports/component1_lock_inputs")
OUT=pathlib.Path("reports/component1_lock_audit")
def load(method,name):
 f=list((BASE/method).rglob(name))
 assert len(f)==1,(method,name,f)
 return [json.loads(s) for s in f[0].read_text().splitlines() if s]
def spans(src,t):
 if not isinstance(t,str) or not t.strip():return []
 return [(m.start(),m.end()) for m in re.finditer(re.escape(t.strip()),src,re.I)]
def valid(src,s):
 a,b=s.get("start"),s.get("end")
 return isinstance(a,int) and isinstance(b,int) and 0<=a<b<=len(src) and src[a:b]==s.get("text")
def main():
 raw={}
 for m in ("gts","aos"):
  data=load(m,"review_cases.jsonl")
  assert len(data)==20
  raw[m]={(c["row"],s["sentence_index"]):(c,s) for c in data for s in c["sentences"]}
 p=load("pyabsa","raw_results.jsonl")
 raw["pyabsa"]={(c["row"],s["sentence_index"]):(c,s) for c in p for s in c["sentences"]}
 g=load("gliner","predictions.jsonl")
 raw["gliner"]={(s["row"],s["sentence_index"]):(None,s) for s in g}
 n=load("nuextract","predictions.jsonl")
 raw["nuextract"]={(s["row"],s["sentence_index"]):(None,s) for s in n}
 keys=list(raw["gts"])
 assert len(keys)==56
 assert all(set(raw[x])==set(keys) for x in ("aos","pyabsa","gliner"))
 assert len(raw["nuextract"])==8 and set(raw["nuextract"])<=set(keys)
 rows=[]
 for key in keys:
  case,s=raw["gts"][key];txt=s["text"]
  assert case["review"][s["start"]:s["end"]]==txt
  row={"row":key[0],"sentence_index":key[1],"place_id":case["place_id"],
       "source_start":s["start"],"source_end":s["end"],"sentence":txt,"models":{}}
  for model in ("gts","aos","pyabsa","gliner","nuextract"):
   if key not in raw[model]:
    row["models"][model]={"status":"not_tested","relations":[],"entities":[]};continue
   c,x=raw[model][key]
   assert x["text"]==txt,(key,model)
   links=[];ents=[];error=None
   if model in ("gts","aos"):
    for z in x["extraction"]["relations"]:
     a,o=z["aspect"],z["opinion"]
     ok=(valid(case["review"],a) and valid(case["review"],o)
         and s["start"]<=a["start"]<a["end"]<=s["end"]
         and s["start"]<=o["start"]<o["end"]<=s["end"])
     links.append({"aspect":a["text"],"opinion":o["text"],
                   "polarity":z.get("polarity"),"source_exact":ok})
   elif model=="pyabsa":
    obj=x["raw_prediction"];error=obj.get("error")
    for z in obj.get("Triplets",[]) if isinstance(obj.get("Triplets"),list) else []:
     a,o=z.get("Aspect"),z.get("Opinion")
     if isinstance(a,str) and isinstance(o,str):
      links.append({"aspect":a,"opinion":o,"polarity":z.get("Polarity"),
                    "source_exact":len(spans(txt,a))==1 and len(spans(txt,o))==1})
   elif model=="gliner":
    error=x.get("error")
    if "entities" in x:
     for lab,zs in x["entities"]["entities"].items():
      for z in zs:ents.append({"label":lab,"text":z["text"],"source_exact":valid(txt,z)})
    if "relations" in x:
     for lab,zs in x["relations"]["relation_extraction"].items():
      for z in zs:
       a,o=z["head"],z["tail"]
       links.append({"aspect":a["text"],"opinion":o["text"],"type":lab,
                     "source_exact":valid(txt,a) and valid(txt,o)})
   else:
    error=x.get("error")
    obj=x.get("extraction")
    for obs in obj.get("observations",[]) if isinstance(obj,dict) else []:
     if not isinstance(obs,dict):continue
     for lab in ("physical_feature","description","felt_experience"):
      v=obs.get(lab)
      if v:ents.append({"label":lab,"text":v,"source_exact":bool(spans(txt,v))})
   row["models"][model]={"status":"error" if error else "ok","error":error,
                          "relations":links,"entities":ents}
  rows.append(row)
 out={"sample":{"reviews":20,"sentences":len(rows),"nuextract_pilot_sentences":8},
      "methods":{},"not_accuracy":True,
      "limitations":["Source exactness is not semantic correctness.",
      "Models have different output schemas; relation counts are not directly comparable.",
      "No independent annotated complete gold. No valid F1 or precision.",
      "NuExtract ran 8 cases only, so no coverage comparison over all 56.",
      "Component 2 relevance and Component 3 NLI are NOT evaluated by this extraction audit."]}
 for m in ("gts","aos","pyabsa","gliner","nuextract"):
  x=[r["models"][m] for r in rows if r["models"][m]["status"]!="not_tested"]
  links=[z for a in x for z in a["relations"]]
  ents=[z for a in x for z in a["entities"]]
  out["methods"][m]={"sentences_tested":len(x),"errors":sum(bool(a.get("error")) for a in x),
   "sentences_with_relations":sum(bool(a["relations"]) for a in x),
   "sentences_with_any_annotations":sum(bool(a["relations"] or a["entities"]) for a in x),
   "relations":len(links),"source_exact_relations":sum(bool(z["source_exact"]) for z in links),
   "entities":len(ents),"source_exact_entities":sum(bool(z["source_exact"]) for z in ents)}
 OUT.mkdir(parents=True,exist_ok=True)
 (OUT/"summary.json").write_text(json.dumps(out,indent=2))
 (OUT/"matched_predictions.jsonl").write_text("".join(json.dumps(x,ensure_ascii=False)+"\n" for x in rows))
 print("MATCHED AUDIT",json.dumps(out,indent=2))
 # Full set of earlier, explicitly preselected diagnostic rows, not cherry-picked.
 for r in rows:
  if r["row"] not in (55,74,97,113,123,139,181,187):continue
  print("CASE",json.dumps({"row":r["row"],"idx":r["sentence_index"],"text":r["sentence"],
   "models":{m:{"error":v.get("error"),
       "links":[[z["aspect"],z["opinion"],z.get("type"),z["source_exact"]] for z in v["relations"]],
       "entities":[[z["label"],z["text"]] for z in v["entities"]]}
       for m,v in r["models"].items()}},ensure_ascii=False))
if __name__=="__main__":main()

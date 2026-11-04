import json,pathlib,collections,re
root=pathlib.Path(__file__).resolve().parents[1]
raw=list((root/"reports"/"pyabsa").rglob("raw_results.jsonl"))
assert len(raw)==1,raw
cases=[json.loads(s) for s in raw[0].read_text().splitlines() if s]
refs=json.loads((root/"data/evaluation/stage1a_absa_real_review_targets_v1.json").read_text())["cases"]
target={x["row"]:x["pairs"] for x in refs}
def core(v):
 v=" ".join(v.strip().lower().split())
 v=re.sub(r"^(?:not|never|no)\s+","",v)
 return v.rstrip(" ,;:.!?").strip()
total=grounded=invalid=error=hits=0
detail=[]
for row in cases:
 predicted=set()
 for s in row["sentences"]:
  obj=s["raw_prediction"]
  if obj.get("error"):error+=1
  triples=obj.get("Triplets")
  if not isinstance(triples,list):continue
  for t in triples:
   if not isinstance(t,dict):continue
   a,o=t.get("Aspect",""),t.get("Opinion","")
   if not isinstance(a,str) or not isinstance(o,str):continue
   total+=1
   aa=core(a);oo=core(o)
   if aa and oo and aa in core(row["review"]) and oo in core(row["review"]):
    grounded+=1
    predicted.add((aa,oo))
   else:invalid+=1
 expected={(core(a),core(o)) for a,o in target[row["row"]]}
 n=len(expected&predicted);hits+=n
 detail.append({"row":row["row"],"model_triplets":sum(len(s["raw_prediction"].get("Triplets",[])) if isinstance(s["raw_prediction"].get("Triplets"),list) else 0 for s in row["sentences"]),"partial_target_hits":n,"partial_target_total":len(expected)})
result={"reviews":len(cases),"sentences":sum(len(c["sentences"]) for c in cases),
"total_model_triplets":total,"source_phrase_present_triplets":grounded,
"phrase_not_present_triplets":invalid,"sentence_errors":error,
"partial_reference_hits":hits,"partial_reference_total":sum(len(v) for v in target.values()),
"per_review":detail,
"warnings":["Source phrase containment is not semantic correctness or precise offset alignment.","Partial reference recovery is NOT precision, recall, accuracy or F1.","Model returns many plausible and implausible combinatorial relationships; evaluate false positives independently.","Error outcomes are failures, NOT empty valid predictions."]}
out=root/"reports"/"pyabsa"/"diagnostic.json"
out.write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))

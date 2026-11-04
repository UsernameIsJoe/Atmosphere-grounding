import json,pathlib,collections
root=pathlib.Path("reports/pyabsa")
files=list(root.rglob("raw_results.jsonl"))
assert len(files)==1,files
rows=[json.loads(x) for x in files[0].read_text().splitlines() if x]
assert len(rows)==20
sentences=[s for r in rows for s in r["sentences"]]
assert len(sentences)==56
keys=collections.Counter()
errors=[]
out=[]
for r in rows:
 for s in r["sentences"]:
  prediction=s["raw_prediction"]
  if isinstance(prediction,dict):
   keys.update(prediction.keys())
   if "error" in str(prediction).lower():errors.append({"row":r["row"],"sentence":s["text"],"prediction":prediction})
  out.append({"row":r["row"],"text":s["text"],"prediction":prediction})
report={"n_reviews":len(rows),"n_sentences":len(sentences),"prediction_python_types":dict(collections.Counter(type(s["raw_prediction"]).__name__ for s in sentences)),"keys":dict(keys),"errors":errors,"first_predictions":out[:12],"warnings":["No independently annotated accuracy claimed","PyABSA may swallow internal sentence errors even when ignore_error=False; inspect stored output"]}
print(json.dumps(report,indent=2,ensure_ascii=False,default=str)[:24000])
pathlib.Path("reports/pyabsa/raw_audit.json").write_text(json.dumps(report,indent=2,ensure_ascii=False,default=str))

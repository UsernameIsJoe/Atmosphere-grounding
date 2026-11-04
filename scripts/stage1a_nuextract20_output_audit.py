import json,pathlib,collections
files=list(pathlib.Path("reports/nuextract_audit").rglob("predictions.jsonl"))
assert len(files)==1,files
rows=[json.loads(x) for x in files[0].read_text().splitlines() if x]
print(json.dumps({"sentences":len(rows),"status_counts":dict(collections.Counter(x["status"] for x in rows)),"outputs":[{"row":r["row"],"sentence":r["text"],"extraction":r["extraction"],"raw":r["raw"]} for r in rows]},indent=2,ensure_ascii=False))

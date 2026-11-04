import json,pathlib,collections
files=list(pathlib.Path("reports/gliner_audit").rglob("predictions.jsonl"))
assert len(files)==1,files
rows=[json.loads(x) for x in files[0].read_text().splitlines() if x]
assert len(rows)==56
counts=collections.Counter()
examples=[]
for row in rows:
 entities=row.get("entities",{}).get("entities",{})
 relations=row.get("relations",{}).get("relation_extraction",{})
 counts.update({"relation_"+k:len(v) for k,v in relations.items()})
 if row["row"] in (55,57,33):
  examples.append({"row":row["row"],"sentence":row["text"],"entities":entities,"relations":relations})
print(json.dumps({"n_rows":len(rows),"relation_type_totals":dict(counts),"focused_examples":examples},indent=2,ensure_ascii=False)[:37000])

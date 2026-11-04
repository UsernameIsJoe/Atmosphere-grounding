#!/usr/bin/env python3
"""Component 1 practical extractor lock: source-preserving GLiNER+GTS replay.

NO claim of semantic accuracy. Full source retained. Candidate labels/links only.
NO relevance or NLI model changes. NO synthetic review text.
"""
import collections,json,pathlib,re,sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
IN=ROOT/"reports/component1_lock_audit/matched_predictions.jsonl"
OUT=ROOT/"reports/component1_contract"

def load_jsonl(path):
 return [json.loads(x) for x in path.read_text(encoding="utf8").splitlines() if x.strip()]
def occurrences(src,phrase):
 if not isinstance(phrase,str) or not phrase.strip():return []
 return [{"start":m.start(),"end":m.end(),"text":src[m.start():m.end()]}
    for m in re.finditer(re.escape(phrase.strip()),src,re.I)]
def source_ref(src,phrase,start):
 loc=occurrences(src,phrase)
 if len(loc)==1:
  r=loc[0];r["start"]+=start;r["end"]+=start
  return {**r,"status":"unique"}
 return {"text":phrase,"start":None,"end":None,
         "status":"missing" if not loc else "ambiguous","occurrences":len(loc)}
def build(data,reviews):
 assert len(data)==56 and len({(r["row"],r["sentence_index"]) for r in data})==56
 records=[];audit=collections.Counter()
 for r in data:
  original=reviews[r["row"]]["text"]
  assert original[r["source_start"]:r["source_end"]]==r["sentence"]
  assert reviews[r["row"]]["place_id"]==r["place_id"]
  g=r["models"]["gliner"];t=r["models"]["gts"]
  assert g["status"]=="ok" and t["status"]=="ok"
  annotations=[]
  for ent in g["entities"]:
   ref=source_ref(r["sentence"],ent["text"],r["source_start"])
   annotations.append({"source":"gliner2.5","kind":"evidence_span",
       "label":ent["label"],"span":ref,
       "candidate_only":True})
  links=[]
  for model,items in (("gliner2.5",g["relations"]),("gts_aste",t["relations"])):
   for item in items:
    a=source_ref(r["sentence"],item["aspect"],r["source_start"])
    o=source_ref(r["sentence"],item["opinion"],r["source_start"])
    links.append({"source":model,"kind":item.get("type","aspect_opinion"),
       "aspect":a,"opinion":o,"polarity":item.get("polarity"),
       "candidate_only":True,
       "unambiguous_source_spans":a["status"]=="unique" and o["status"]=="unique"})
  record={"row":r["row"],"place_id":r["place_id"],
      "sentence_index":r["sentence_index"],
      "original_review":original,
      "sentence":{"text":r["sentence"],"start":r["source_start"],"end":r["source_end"]},
      "component1":{"spans":annotations,"links":links,
      "no_annotations":not bool(annotations or links),
      "candidate_only":True,
      "no_automatic_filter":True},
      "handoff":{"relevance_input":r["sentence"],
        "relevance_emotion_dependent":True,
        "nli_original_text_fallback":r["sentence"]}}
  for a in annotations:
   z=a["span"]
   if z["status"]=="unique":
    assert original[z["start"]:z["end"]]==z["text"]
  for z in links:
   for p in ("aspect","opinion"):
    ref=z[p]
    if ref["status"]=="unique":
     assert original[ref["start"]:ref["end"]]==ref["text"]
  audit["sentences"]+=1
  audit["gliner_annotated"]+=bool(g["entities"] or g["relations"])
  audit["gts_linked"]+=bool(t["relations"])
  audit["union_annotated"]+=bool(g["entities"] or g["relations"] or t["relations"])
  audit["gts_adds_to_gliner_coverage"]+=bool(t["relations"]) and not bool(g["entities"] or g["relations"])
  audit["gts_adds_to_gliner_relation_coverage"]+=bool(t["relations"]) and not bool(g["relations"])
  audit["sentences_with_no_annotations"]+=not bool(annotations or links)
  audit["unresolved_spans"]+=sum(a["span"]["status"]!="unique" for a in annotations)
  audit["unresolved_links"]+=sum(not l["unambiguous_source_spans"] for l in links)
  records.append(record)
 assert audit["sentences"]==56
 assert audit["sentences_with_no_annotations"]+audit["union_annotated"]==56
 assert all(x["handoff"]["relevance_input"]==x["sentence"]["text"] for x in records)
 assert all(x["handoff"]["nli_original_text_fallback"]==x["sentence"]["text"] for x in records)
 return records,dict(audit)
def main():
 rows=load_jsonl(IN);reviews=load_jsonl(ROOT/"data/processed/reviews.jsonl")
 outputs,audit=build(rows,reviews)
 OUT.mkdir(exist_ok=True,parents=True)
 (OUT/"component1_evidence.jsonl").write_text("".join(json.dumps(x,ensure_ascii=False)+"\n" for x in outputs),encoding="utf8")
 s={"decision":"provisional engineering contract, not independently validated semantic accuracy",
 "primary":"GLiNER2.5 evidence spans",
 "supplementary":"GTS-BERT aspect-opinion candidate links; retain but never assert as facts",
 "all_original_sentences_retained":True,
 "semantic_filters":"none",
 "relevance":"separate emotion-dependent stage; no component-1 emotion scoring",
 "nli":"separate downstream stage; unchanged original text preserved",
 "counts":audit,
 "limitations":["No independent gold labels. Candidate relations are not guaranteed correct.",
 "Source-exact strings do not establish direction or semantic validity.",
 "GLiNER relation categories (including has_feature) must be treated as unverified.",
 "An unlabeled sentence may still contain important atmospheric evidence.",
 "Component 2/3 inference outcomes are not yet causally improved."]}
 (OUT/"summary.json").write_text(json.dumps(s,indent=2,ensure_ascii=False))
 print(json.dumps(s,indent=2))
if __name__=="__main__":main()

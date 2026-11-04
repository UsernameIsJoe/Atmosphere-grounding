#!/usr/bin/env python3
"""GLiNER2.5 official AutoExtractor test on frozen real review sentences."""
import argparse,json,pathlib,sys,time
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from stage1a_absa_official_sentence_inference import load_cases
MODEL="fastino/gliner2.5-base-v1"
ENTITY_LABELS={
 "physical_environment":"A physical feature of a public place, such as trees, benches, paths, buildings, or lighting",
 "spatial_quality":"A description of the arrangement, enclosure, or physical character of a place",
 "felt_experience":"A feeling or sensory experience explicitly reported by a visitor",
 "descriptive_quality":"An explicit descriptive term applied to a place or its feature"
}
RELATION_LABELS=["described_as","has_feature","induces_experience"]
def main():
 p=argparse.ArgumentParser();p.add_argument("--output",type=pathlib.Path,required=True);a=p.parse_args()
 from gliner2 import AutoExtractor
 model=AutoExtractor.from_pretrained(MODEL,map_location="cpu")
 cases,_=load_cases();a.output.mkdir(parents=True,exist_ok=True)
 output=[];errors=[]
 for c in cases:
  for s in c["sentences"]:
   item={k:c[k] for k in ("row","place_id","review_index")}
   item.update({k:s[k] for k in ("sentence_index","start","end","text")})
   try:
    item["entities"]=model.extract_entities(s["text"],ENTITY_LABELS,include_spans=True,include_confidence=True)
    item["relations"]=model.extract_relations(s["text"],RELATION_LABELS,include_spans=True,include_confidence=True)
   except Exception as e:
    item["error"]=str(e);errors.append(item["row"])
   output.append(item)
  print("GLiNER2.5 completed review",c["row"],flush=True)
 (a.output/"predictions.jsonl").write_text("".join(json.dumps(x,ensure_ascii=False,default=str)+"\n" for x in output))
 ent=sum(len(x["entities"]["entities"].get(label,[])) for x in output if "entities" in x for label in ENTITY_LABELS)
 rel=sum(len(x["relations"]["relation_extraction"].get(label,[])) for x in output if "relations" in x for label in RELATION_LABELS)
 summary={"checkpoint":MODEL,"reviews":len(cases),"sentences":len(output),"entities":ent,"relations":rel,"errors":len(errors),
 "protocol":"Official AutoExtractor extract_entities/extract_relations with predeclared labels, spans and confidence",
 "limitations":"No complete human gold; NOT precision, recall, F1. Labels are task hypotheses, not training labels."}
 (a.output/"summary.json").write_text(json.dumps(summary,indent=2))
 print(json.dumps(summary,indent=2))
if __name__=="__main__":main()

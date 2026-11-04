#!/usr/bin/env python3
"""Controlled Component 1 task formulation test on frozen actual reviews.

A = existing typed JointIE sentence outputs (external immutable artifact).
B = claim-oriented schema, same GLiNER checkpoint, sentence input.
C = same schema as B, full review input; map predictions by exact offsets.
D = post-hoc deterministic merge with frozen GTS predictions (separate audit).
No invented texts, emotion categories, fine tuning, or inferred ground truth.
"""
import argparse
import json
import pathlib
import sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from stage1a_absa_official_sentence_inference import load_cases
MODEL="fastino/gliner2.5-base-v1"
def schema_for(joint):
    return (joint.create_schema()
      .entities({
       "place_or_subject":"The particular place, site, built element or other object being described",
       "physical_feature":"An explicitly mentioned physical element, such as trees, paths, light, benches or buildings",
       "environmental_condition":"A quoted spatial arrangement, sensory condition, state, event or descriptive phrase about the setting, including negation",
       "reported_experience":"A quoted feeling, perception, bodily sensation or experience explicitly reported by a person"
      })
      .relation("contains",head="place_or_subject",tail="physical_feature",
          description="The described subject explicitly includes or contains this physical feature")
      .relation("has_condition",head=["place_or_subject","physical_feature"],
          tail="environmental_condition",
          description="The source directly attributes this quoted condition or description to the subject")
      .relation("induces_experience",head=["place_or_subject","physical_feature","environmental_condition"],
          tail="reported_experience",
          description="The original text explicitly says this condition or subject makes a visitor experience the feeling")
      .no_self_loops())
def verify_graph(text,graph):
    entities=graph.get("entities",[])
    ids=set()
    for x in entities:
        a,b=x["start"],x["end"]
        if not (isinstance(a,int) and isinstance(b,int) and 0<=a<b<=len(text) and text[a:b]==x["text"]):
            raise ValueError("Entity not verbatim source-aligned")
        if x["id"] in ids:raise ValueError("Repeated entity ID")
        ids.add(x["id"])
    for r in graph.get("relations",[]):
        if r["head"] not in ids or r["tail"] not in ids:
            raise ValueError("Unresolved relation endpoint")
def get_pred(joint,schema,config,text):
    try:
        result=joint.extract(text,schema,config=config)
        graph=result.to_dict()
        verify_graph(text,graph)
        return {"graph":graph,"feasible":bool(result.feasible),"error":None}
    except Exception as e:
        return {"graph":{"entities":[],"relations":[]},"feasible":False,"error":repr(e)}
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",type=pathlib.Path,required=True)
    args=p.parse_args()
    from gliner2.joint_ie import JointIE,JointIEConfig
    joint=JointIE.from_pretrained(MODEL)
    schema=schema_for(joint)
    config=JointIEConfig(optimizer="beam",beam_size=32)
    cases,_=load_cases()
    rows=[];count={"B":0,"C":0}
    for c in cases:
        review=c["review"]
        # Full review context held constant across all its sentence predictions.
        whole=get_pred(joint,schema,config,review)
        whole["input_scope"]="full_review"
        whole["input_text"]=review
        whole["row"]=c["row"];whole["place_id"]=c["place_id"]
        whole["condition"]="C"
        rows.append(whole)
        count["C"]+=1
        for sent in c["sentences"]:
            item=get_pred(joint,schema,config,sent["text"])
            item.update({"condition":"B","input_scope":"sentence",
                "input_text":sent["text"],"text":sent["text"],
                "row":c["row"],"place_id":c["place_id"],
                "sentence_index":sent["sentence_index"],"start":sent["start"],
                "end":sent["end"]})
            rows.append(item)
            count["B"]+=1
        print("Completed B and C on real review",c["row"],flush=True)
    assert count=={"B":56,"C":20}
    args.output.mkdir(parents=True,exist_ok=True)
    (args.output/"predictions.jsonl").write_text(
        "".join(json.dumps(x,ensure_ascii=False)+"\n" for x in rows),encoding="utf8")
    summary={"checkpoint":MODEL,"schema":"claim-oriented fixed for B and C",
       "conditions":{"B":"sentence claim schema","C":"full review same claim schema"},
       "B_inputs":56,"C_inputs":20,
       "feasible_B":sum(x["feasible"] for x in rows if x["condition"]=="B"),
       "feasible_C":sum(x["feasible"] for x in rows if x["condition"]=="C"),
       "errors":[{"row":x["row"],"condition":x["condition"],"error":x["error"]}
                 for x in rows if x["error"]],
       "graph_entities_B":sum(len(x["graph"]["entities"]) for x in rows if x["condition"]=="B"),
       "graph_entities_C":sum(len(x["graph"]["entities"]) for x in rows if x["condition"]=="C"),
       "graph_relations_B":sum(len(x["graph"]["relations"]) for x in rows if x["condition"]=="B"),
       "graph_relations_C":sum(len(x["graph"]["relations"]) for x in rows if x["condition"]=="C"),
       "warning":"Graph counts are not accuracy. C input is entire review; comparison must map to same sentence spans."}
    (args.output/"summary.json").write_text(json.dumps(summary,indent=2,ensure_ascii=False))
    print("FORMULATION_SUMMARY",json.dumps(summary,indent=2),flush=True)
if __name__=="__main__":main()

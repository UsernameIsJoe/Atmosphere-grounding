#!/usr/bin/env python3
"""Run official constrained GLiNER2.5 JointIE on the FROZEN real review sentences.

This is a controlled schema/decoding comparison with prior independent
GLiNER2.5, not new training or human-rated accuracy.
"""
import argparse
import hashlib
import json
import pathlib
import sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from stage1a_absa_official_sentence_inference import load_cases

CHECKPOINT="fastino/gliner2.5-base-v1"
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",type=pathlib.Path,required=True)
    args=p.parse_args()
    from gliner2.joint_ie import JointIE,JointIEConfig
    joint=JointIE.from_pretrained(CHECKPOINT)
    # Types reflect original review wording, not any of the nine emotion labels.
    schema=(joint.create_schema()
        .entities({
            "place":"The park, plaza, street or other place being reviewed",
            "physical_feature":"An observable physical object or environmental feature",
            "spatial_quality":"A described spatial arrangement or physical spatial character",
            "descriptive_quality":"An adjective or evaluation explicitly describing a place or feature",
            "reported_experience":"An explicit human sensation or feeling reported in this place"
        })
        .relation("has_feature",head="place",tail="physical_feature",
                  description="A place explicitly contains or has the physical feature")
        .relation("described_as",head=["place","physical_feature"],tail=["spatial_quality","descriptive_quality"],
                  description="The place or feature is explicitly described with a quality")
        .relation("evokes_experience",head=["place","physical_feature","spatial_quality"],tail="reported_experience",
                  description="The text explicitly attributes this experience to the environment")
        .no_self_loops())
    config=JointIEConfig(optimizer="beam",beam_size=32)
    cases,_=load_cases()
    args.output.mkdir(parents=True,exist_ok=True)
    outputs=[]
    for case in cases:
        for s in case["sentences"]:
            item={"row":case["row"],"place_id":case["place_id"],
                  "sentence_index":s["sentence_index"],"start":s["start"],
                  "end":s["end"],"text":s["text"]}
            try:
                result=joint.extract(s["text"],schema,config=config)
                item["feasible"]=bool(result.feasible)
                item["graph"]=result.to_dict()
                item["error"]=None
                for ent in item["graph"].get("entities",[]):
                    a,b=ent["start"],ent["end"]
                    if s["text"][a:b]!=ent["text"]:
                        raise ValueError("Joint entity not source-exact")
            except Exception as e:
                item["feasible"]=False
                item["graph"]={"entities":[],"relations":[]}
                item["error"]=repr(e)
            outputs.append(item)
        print("JointIE completed original review",case["row"],flush=True)
    assert len(outputs)==56
    path=args.output/"predictions.jsonl"
    path.write_text("".join(json.dumps(x,ensure_ascii=False)+"\n" for x in outputs))
    summary={
        "checkpoint":CHECKPOINT,"reviews":len(cases),"sentences":len(outputs),
        "feasible":sum(x["feasible"] for x in outputs),
        "errors":sum(bool(x["error"]) for x in outputs),
        "entity_candidates":sum(len(x["graph"].get("entities",[])) for x in outputs),
        "relation_candidates":sum(len(x["graph"].get("relations",[])) for x in outputs),
        "input":"56 verbatim original sentence spans from frozen 20-review pilot",
        "method":"official JointIE with typed endpoints and no-self-loop schema",
        "not_accuracy":True}
    (args.output/"summary.json").write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary,indent=2),flush=True)
if __name__=="__main__":main()

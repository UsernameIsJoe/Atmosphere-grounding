#!/usr/bin/env python3
"""Fixed real-review ABSA transfer comparison using prior AOS/dependency outputs.

Partial, assistant-authored source relation targets support *target recovery*
only. This is NOT a precision, F1, or independently validated accuracy test.
"""
import argparse
import json
import re
from pathlib import Path

from stage1a_gts_joint_aste_probe import make_predictor, standardize


def load_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line]


def core(value):
    value = re.sub(r"\s+", " ", value.strip().lower())
    value = re.sub(r"^(?:not|never|no)\s+", "", value)
    return value.rstrip(" ,;:.!?").strip()


def source_valid(text, relation):
    if not relation.get("grounded"):
        return False
    for name in ("aspect", "opinion"):
        item = relation[name]
        a,b = item.get("start"), item.get("end")
        if not isinstance(a,int) or not isinstance(b,int) or not (0 <= a < b <= len(text)):
            return False
        if text[a:b] != item["text"]:
            return False
    return True


def compare(reference, records):
    targets = {r["row"]:r for r in reference["cases"]}
    outputs = {}
    expected_rows=set(targets)
    for method,cases in records.items():
        indexed = {int(r["row"]):r for r in cases}
        if set(indexed)!=expected_rows:
            raise ValueError(f"{method}: row mismatch {set(indexed)^expected_rows}")
        per_review=[]
        count=0
        aligned_count=0
        recovered=0
        for row,ref in sorted(targets.items()):
            case=indexed[row]
            text=case["review"]
            predictions=case["extraction"]["relations"]
            valid=[r for r in predictions if source_valid(text,r)]
            expected=[(core(a),core(o)) for a,o in ref["pairs"]]
            available={(core(r["aspect"]["text"]),core(r["opinion"]["text"])) for r in valid}
            hits=[(a,o) in available for a,o in expected]
            count+=len(expected)
            recovered+=sum(hits)
            aligned_count+=len(valid)
            per_review.append({
                "row":row,"review":text,
                "targets":[{"aspect":a,"opinion":o,"recovered":hit}
                           for (a,o),hit in zip(ref["pairs"],hits)],
                "relations":predictions,
                "verified_relationships":len(valid),
                "unverified_relationships":len(predictions)-len(valid),
                "has_source_text":True,
            })
        outputs[method]={
            "n_reviews":len(indexed),"reference_targets":count,
            "targets_recovered":recovered,
            "target_recovery_fraction":round(recovered/count,4),
            "verified_relationships":aligned_count,
            "per_review":per_review,
        }
    return outputs


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--references",required=True)
    ap.add_argument("--aos",required=True)
    ap.add_argument("--dependency",required=True)
    ap.add_argument("--gts",required=True)
    ap.add_argument("--output",required=True)
    args=ap.parse_args()
    refs=json.loads(Path(args.references).read_text(encoding="utf-8"))
    cases={
        "aos_t5":load_jsonl(args.aos),
        "dependency_rules":load_jsonl(args.dependency),
        "gts_joint_aste":load_jsonl(args.gts),
    }
    standard={int(r["row"]):r["review"] for r in cases["aos_t5"]}
    for method,rows in cases.items():
        if {int(r["row"]):r["review"] for r in rows} != standard:
            raise ValueError(f"{method}: review identity/text does not match frozen AOS inputs")
    outputs=compare(refs,cases)
    out=Path(args.output)
    out.mkdir(parents=True,exist_ok=True)
    summary={
        "reference_status":refs["status"],
        "sample_rows":sorted(standard),
        "n_reviews":len(standard),
        "n_reference_targets":sum(len(r["pairs"]) for r in refs["cases"]),
        "methods":{m:{k:v for k,v in d.items() if k!="per_review"} for m,d in outputs.items()},
        "limitations":[
            "Reference targets are assistant-authored, partial and not independently adjudicated.",
            "Target recovery is NOT full recall, precision, F1, semantic correctness or generalizable model accuracy.",
            "Some opinion spans encode negation/quantity incompletely, especially '0 adequate bike parking'.",
            "Unverified/ambiguous spans are not credited; all raw model relations remain in output.",
            "AOS and dependency predictions are frozen previous runs; GTS model executes on the same reviews.",
            "The GTS checkpoint may truncate long reviews to its maximum input token length.",
        ]
    }
    (out/"summary.json").write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding="utf-8")
    with (out/"side_by_side.jsonl").open("w",encoding="utf-8") as f:
        for row in sorted(standard):
            f.write(json.dumps({"row":row,"review":standard[row],
                "methods":{m:next(x for x in d["per_review"] if x["row"]==row)
                           for m,d in outputs.items()}},ensure_ascii=False)+"\n")
    print(json.dumps(summary["methods"],indent=2))


if __name__=="__main__":
    main()

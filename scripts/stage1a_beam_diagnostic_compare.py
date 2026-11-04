import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from stage1a_absa_real_review_comparison import compare, load_jsonl
root=pathlib.Path(__file__).resolve().parents[1]
refs=json.loads((root/"data/evaluation/stage1a_absa_real_review_targets_v1.json").read_text())
result={}
for beam in ("1","3","5"):
    candidates=list((root/"reports"/"beam_inputs"/beam).rglob("review_cases.jsonl"))
    if len(candidates)!=1: raise ValueError(f"Expected one artifact for beam {beam}, got {candidates}")
    records=load_jsonl(candidates[0])
    score=compare(refs,{"aos_t5":records})["aos_t5"]
    result[beam]={"partial_reference_hits":score["targets_recovered"],
                  "partial_reference_total":score["reference_targets"]}
print(json.dumps({"diagnostic_only_not_accuracy":result},indent=2))

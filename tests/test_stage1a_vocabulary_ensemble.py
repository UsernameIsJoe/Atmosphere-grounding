import json
import pathlib
import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
from stage1a_vocabulary_ensemble import load_registry, ensemble, majority_label, mean_distribution, median_distribution, trimmed_distribution

ROOT = pathlib.Path(__file__).resolve().parents[1]

def p(s,c,u):
    return {"S": s, "C": c, "U": u}

def test_registry():
    data = load_registry(ROOT / "configs/stage1a_hypothesis_vocabulary_draft.json")
    records = data["candidates"]
    assert len(records) == 60
    assert {x["emotion"] for x in records} == {"calm", "inviting", "safe"}
    for emotion in ("calm", "inviting", "safe"):
        subset = [x for x in records if x["emotion"] == emotion]
        assert len(subset) == 20
        assert sum(x["role"] == "core" for x in subset) == 6

def test_tied_majority_abstains():
    assert majority_label(["S", "C", "U"]) == "ABSTAIN"
    assert majority_label(["U", "U", "S"]) == "U"

def test_ensembles_and_loo():
    data = [
        {"label": "S", "probs": p(.8,.1,.1)},
        {"label": "S", "probs": p(.7,.1,.2)},
        {"label": "S", "probs": p(.9,.05,.05)},
        {"label": "U", "probs": p(.2,.1,.7)},
        {"label": "S", "probs": p(.6,.1,.3)},
        {"label": "S", "probs": p(.8,.1,.1)},
    ]
    out = ensemble(data)
    assert out["mean"]["label"] == "S"
    assert out["majority"]["label"] == "S"
    assert out["leave_one_out_stable"]
    assert not out["unanimous"]
    for method in ("mean","median","trimmed"):
        assert abs(sum(out[method]["probs"].values())-1)<1e-8

def test_no_mutation_of_source_probs():
    probs = [p(.9,.05,.05),p(.7,.1,.2),p(.8,.1,.1)]
    before = json.dumps(probs)
    mean_distribution(probs)
    median_distribution(probs)
    trimmed_distribution(probs)
    assert json.dumps(probs) == before

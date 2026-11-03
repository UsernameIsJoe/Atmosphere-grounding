import json
import pathlib
import sys
from types import SimpleNamespace

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
from stage1a_nli_checkpoint_screen import select_rows, label_space, summarize

def test_screening_selection_is_deterministic_and_covers_places():
    rows = [{"place_id": f"place_{i%43}", "text": "example " * (i%7+1)}
            for i in range(214)]
    a=select_rows(rows,50)
    assert len(a)==50
    assert a==select_rows(rows,50)
    assert len({rows[i]["place_id"] for i in a})==43
    assert set([55,81,113,139,181,187,123]).issubset(set(a))

def test_native_binary_labels_never_conflate_classes():
    labels,space=label_space(SimpleNamespace(config=SimpleNamespace(
        id2label={0:"not_entailment",1:"entailment"})))
    assert space=="binary"
    assert labels=={0:"not_entailment",1:"entailment"}

def test_native_three_way_labels():
    labels,space=label_space(SimpleNamespace(config=SimpleNamespace(
        id2label={0:"contradiction",1:"neutral",2:"entailment"})))
    assert space=="three_way"

def test_unknown_label_rejected():
    import pytest
    with pytest.raises(ValueError):
        label_space(SimpleNamespace(config=SimpleNamespace(id2label={0:"LABEL_0",1:"LABEL_1"})))

def test_binary_robustness_summary():
    cores=[{"id":f"a{i}","emotion":"calm","role":"core"} for i in range(3)]
    entries={x["id"]:{"label":"entailment","probs":{"entailment":0.7,"not_entailment":0.3}} for x in cores}
    rows=[{"row":1,"emotions":{"calm":entries}}]
    summary=summarize(rows,cores,"binary")["calm"]
    assert summary["core_unanimity"]==1.0
    assert summary["leave_one_core_out_stability"]==1.0

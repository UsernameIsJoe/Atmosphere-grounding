import pathlib
import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]/"scripts"))
from stage1a_absa_relation_benchmark import norm, verified, score


def relation():
    return {"grounded": True,
            "aspect": {"text": "park", "start": 4, "end": 8},
            "opinion": {"text": "nice", "start": 12, "end": 16}}


def test_source_span_and_normalization():
    assert norm(" GOOD   park ") == "good park"
    assert verified("The park is nice.", relation())
    r = relation()
    r["opinion"]["text"] = "great"
    assert not verified("The park is nice.", r)


def test_pair_quality_not_span_quantity():
    data = {"x": {"id": "x", "text": "The park is nice.",
                  "extraction": {"relations": [relation()]}}}
    refs = {"cases": [{"id": "x", "pairs": [["park", "nice"]], "negated": []}]}
    assert score(refs, data)["correct"] == 1
    refs["cases"][0]["pairs"] = [["garden", "nice"]]
    other = score(refs, data)
    assert (other["correct"], other["false_relations"], other["missed"]) == (0, 1, 1)


def test_no_gold_means_emitted_relation_is_extra():
    refs = {"cases": [{"id": "x", "pairs": [], "negated": []}]}
    data = {"x": {"id": "x", "text": "The park is nice.",
                  "extraction": {"relations": [relation()]}}}
    assert score(refs, data)["false_relations"] == 1


def test_incomplete_case_sets_fail():
    try:
        score({"cases": [{"id": "x", "pairs": [], "negated": []}]}, {})
        raise AssertionError("Expected failure")
    except ValueError:
        pass

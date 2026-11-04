import pathlib
import sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"scripts"))
from stage1a_absa_real_review_comparison import core, compare, source_valid


def example(row=2):
    text="The park is nice."
    return {"row":row,"review":text,
            "extraction":{"relations":[{
                "grounded":True,"aspect":{"text":"park","start":4,"end":8},
                "opinion":{"text":"nice","start":12,"end":16}}]}}


def test_real_review_target_recovery_and_provenance():
    refs={"cases":[{"row":2,"pairs":[["park","nice"]]}]}
    x=compare(refs,{"aos": [example()]})
    assert x["aos"]["targets_recovered"] == 1
    assert x["aos"]["reference_targets"] == 1


def test_reference_is_partial_not_claimed_precision():
    refs={"cases":[{"row":2,"pairs":[["park","beautiful"]]}]}
    x=compare(refs,{"dependency":[example()]})
    assert x["dependency"]["targets_recovered"] == 0
    assert x["dependency"]["verified_relationships"] == 1
    assert "precision" not in x["dependency"]


def test_invalid_offset_rejected():
    r=example()["extraction"]["relations"][0]
    r["opinion"]["end"]=15
    assert not source_valid("The park is nice.",r)


def test_missing_record_fails():
    try:
        compare({"cases":[{"row":2,"pairs":[]}]},{"x":[]})
        raise AssertionError("Expected row mismatch")
    except ValueError:
        pass


def test_negation_opinion_lexical_core():
    assert core("not quiet;")=="quiet"

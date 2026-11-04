import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from stage1a_m2b_claim_nli import dataset, structured, evidence_set, mean_probs, HYPOTHESES

def test_cases_and_source_offsets():
    cases = dataset()
    assert len(cases) == 18
    assert len({x["id"] for x in cases}) == 18
    assert sum(len(x["claims"]) > 1 for x in cases) == 7
    for case in cases:
        for claim in case["claims"]:
            assert case["review"].count(claim["text"]) == 1
            for key in ("aspect", "opinion"):
                part = claim[key]
                assert claim["text"][part["start"]:part["end"]] == part["text"]

def test_all_swaps_change_structure_if_eligible():
    for case in dataset():
        original = structured(case["claims"])
        swapped = structured(case["claims"], swap=True)
        assert (original != swapped) == (len(case["claims"]) > 1)

def test_negation_and_quantity_are_preserved():
    cases = {x["id"]: x for x in dataset()}
    assert "not quiet" in structured(cases["quiet_no"]["claims"])
    assert "zero adequate" in structured(cases["parking_zero"]["claims"])
    assert "not welcoming" in structured(cases["welcome_no"]["claims"])
    assert "does not feel safe" in structured(cases["safe_no"]["claims"])

def test_mixed_evidence_not_averaged_away():
    claims = [{"label": "entailment"}, {"label": "contradiction"}]
    x = evidence_set(claims)
    assert x["any_support"] and x["any_contradiction"] and x["mixed_evidence"]
    assert not x["all_neutral"]

def test_probability_mean_is_a_separate_control():
    a = [{"probs": {"entailment": .9, "contradiction": .05, "neutral": .05}},
         {"probs": {"entailment": .05, "contradiction": .9, "neutral": .05}}]
    m = mean_probs(a)
    assert round(sum(m.values()), 8) == 1.
    assert m["entailment"] == m["contradiction"]

def test_fixed_three_emotions():
    assert set(HYPOTHESES) == {"calm", "safe", "inviting"}

import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from stage1a_m2c_relevance_gate import authored_cases, relevance_hypothesis, summarize, ORDER


def test_fixed_sample_and_attribution_controls():
    cases=authored_cases()
    assert len(cases)==20
    assert len({c["id"] for c in cases})==20
    data={c["id"]:c for c in cases}
    assert set(ORDER)=={"calm","inviting","safe"}
    assert data["calm_after_exam"]["expected"]["calm"]=="N"
    assert data["calm_by_lake"]["expected"]["calm"]=="D"
    assert data["comfortable_benches"]["expected"]["safe"]=="N"
    assert data["safe_path"]["expected"]["safe"]=="D"
    assert data["zero_bikes"]["expected"]["inviting"]=="N"


def test_hypotheses_are_relevance_not_direct_emotion():
    assert "relevant" in relevance_hypothesis("calm")
    assert "location" in relevance_hypothesis("physically safe")


def test_summary_threshold_and_false_positives():
    rows=[]
    for case in authored_cases():
        for emotion in ORDER:
            expected=case["expected"][emotion]
            p=.8 if expected!="N" else .2
            def make(prob):
                return {"probs":{"entailment":prob,"neutral":1-prob,"contradiction":0}}
            rows.append({"emotion":emotion,"expected":expected,
                         "relevance":make(p),"direct":make(p)})
    result=summarize(rows)
    assert result["overall"]["relevant_retained"]==result["overall"]["relevant_expected"]
    assert result["overall"]["irrelevant_retained"]==0
    assert result["overall"]["relevant_expected"] + result["overall"]["irrelevant_expected"]==60

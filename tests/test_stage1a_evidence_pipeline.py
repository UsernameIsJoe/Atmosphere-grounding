import json
import pathlib
import sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"scripts"))
from stage1a_evidence_pipeline import evidence_tier, interpret, summarize_claims, build


def claim(aspects,relations,relevant,label):
    return {"sentence_index":0,"start":0,"end":4,"text":"Park",
            "aspects":aspects,"relations":relations,"relevance_flag":relevant,
            "relevance_nli":{"label":"entailment" if relevant else "neutral"},
            "direct_nli":{"label":label}}


def test_absa_is_not_an_emotion_label():
    assert evidence_tier(claim([{"text":"Park"}],[],True,"contradiction"))=="aspect_only"


def test_unmatched_relevant_evidence_is_never_dropped():
    c=interpret(claim([],[],True,"entailment"))
    assert c["rescued_unmatched"] and not c["combined_selected"]


def test_conflict_not_erased():
    x=interpret(claim([{"text":"Park"}],[],True,"entailment"))
    y=interpret(claim([],[],False,"contradiction"))
    out=summarize_claims([x,y])
    assert out["all_sentences"]["total"]==2
    assert out["all_sentences"]["contradict"]==1
    assert out["relevance_only"]["contradict"]==0
    assert out["all_sentences"]["support"]==1


def test_source_offsets_fail_closed():
    r={"review":"Park","emotion":"calm","row":2,"place_id":"loc",
       "hypothesis":"The location is calm.","full_review_nli":{"label":"neutral"},
       "claims":[claim([{"start":0,"end":4,"text":"Other"}],[],True,"entailment")]}
    records=[{**r,"emotion":e,"row":row}
             for row in range(20) for e in ("calm","inviting","safe")]
    try:
        build(records)
        raise AssertionError("Expected invalid source span to be rejected")
    except ValueError as err:
        assert "source" in str(err).lower() or "ABSA" in str(err)

import pathlib
import sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"scripts"))
from stage1a_m2_structured_nli import (verified_relations,verified_aspects,
    annotations,construct_premise,premised_conditions,CONDITIONS)


def test_grounded_relation_only_and_offset_check():
    review="The trees are beautiful."
    record={"review":review,"extraction":{"relations":[
        {"grounded":True,"aspect":{"text":"trees","start":4,"end":9},
         "opinion":{"text":"beautiful","start":14,"end":23}},
        {"grounded":True,"aspect":{"text":"ghost","start":4,"end":9},
         "opinion":{"text":"beautiful","start":14,"end":23}},
        {"grounded":False,"aspect":{"text":"trees","start":4,"end":9},
         "opinion":{"text":"beautiful","start":14,"end":23}}
    ]}}
    assert len(verified_relations(record))==1


def test_aspect_spans_from_original_source():
    rec={"review":"A quiet park.","extraction":{"aspects":[
        {"aspect":"park","start":8,"end":12},
        {"aspect":"madeup","start":2,"end":8}]}}
    assert verified_aspects(rec)==[("park",8)]


def test_swapped_control_is_not_same_annotations():
    text="Gardens are beautiful and traffic is loud."
    a={"grounded":True,"aspect":{"text":"Gardens","start":0,"end":7},
       "opinion":{"text":"beautiful","start":12,"end":21}}
    b={"grounded":True,"aspect":{"text":"traffic","start":26,"end":33},
       "opinion":{"text":"loud","start":37,"end":41}}
    record={"review":text,"extraction":{"relations":[a,b]}}
    normal=annotations(record,"dependency")
    swapped=annotations(record,"dependency",swapped=True)
    assert normal!=swapped
    assert len(swapped)==2


def test_full_review_always_preserved():
    review="There is loud traffic."
    x=construct_premise(review,["aspect='traffic'; described_as='loud'"])
    assert review in x
    assert "unverified interpretations" in x
    assert construct_premise(review,[])==review


def test_conditions_are_distinct_inputs_when_data_available():
    review="Trees are beautiful."
    relation={"grounded":True,
      "aspect":{"text":"Trees","start":0,"end":5},
      "opinion":{"text":"beautiful","start":10,"end":19}}
    fake={}
    for source in ("dependency","aos_t5"):
        fake[source]={0:{"review":review,"extraction":{"relations":[relation]}}}
    for source in ("deberta_absa","setfit_absa"):
        fake[source]={0:{"review":review,"extraction":{"aspects":[{"aspect":"Trees","start":0,"end":5}]}}}
    p,meta=premised_conditions(fake,0)
    assert set(p)==set(CONDITIONS)
    assert all(review in text for text in p.values())
    assert p["aos_t5_swapped"]==p["aos_t5"]
    assert meta["aos_t5_swapped"]["eligible"] is False

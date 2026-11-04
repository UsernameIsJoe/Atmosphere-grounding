import pathlib
import sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"scripts"))
from stage1a_integrated_absa_nli import (
    sentences_from_source, assign_annotations, evidence_summary, verify_span, load_artifacts,
    run, EMOTIONS,
)


def fixture():
    text = "The park is quiet.\n#Hashtag\nThe stairs are dangerous."
    first = {"start":0,"end":18,"text":"The park is quiet."}
    second = {"start":28,"end":53,"text":"The stairs are dangerous."}
    row = 7
    base = {"row":row,"place_id":"test-location","review":text}
    deb = {**base,"extraction":{"all_sentences":[first,second],
           "aspects":[{"aspect":"park","start":4,"end":8,"polarity":"positive"}]}}
    setfit = {**base,"extraction":{"aspects":[
       {"aspect":"stairs","start":32,"end":38,"polarity":"ASP-Negative"},
       {"aspect":"ghost","start":32,"end":38,"polarity":"positive"}]}}
    aos = {**base,"extraction":{"relations":[]}}
    return text,{"deberta_absa":{row:deb},"setfit_absa":{row:setfit},"aos_t5":{row:aos}},row


def test_verified_source_spans():
    assert verify_span("The park",{"aspect":"park","start":4,"end":8})
    assert not verify_span("The park",{"aspect":"ghost","start":4,"end":8})


def test_gap_is_preserved_not_silently_dropped():
    text,tables,row=fixture()
    claims=sentences_from_source(tables["deberta_absa"][row])
    assert len(claims)==3
    assert claims[1]["text"]=="#Hashtag"
    assert claims[1]["segmentation"]=="unsegmented_gap"
    assert all(text[s["start"]:s["end"]]==s["text"] for s in claims)


def test_aspects_are_annotations_not_rewritten_claims():
    text,tables,row=fixture()
    claims=sentences_from_source(tables["deberta_absa"][row])
    diagnostics=assign_annotations(text,claims,tables,row)
    assert diagnostics["deberta_absa_assigned_aspect"]==1
    assert diagnostics["setfit_absa_assigned_aspect"]==1
    assert diagnostics["setfit_absa_invalid_aspect"]==1
    assert all(c["text"]==text[c["start"]:c["end"]] for c in claims)
    assert not claims[1]["aspects"]


def test_conflict_kept_and_missing_aspect_counted():
    claims=[
        {"sentence_index":0,"aspects":[],"direct_nli":{"label":"entailment"},"relevance_flag":True},
        {"sentence_index":1,"aspects":[{"text":"path"}],"direct_nli":{"label":"contradiction"},"relevance_flag":False},
        {"sentence_index":2,"aspects":[],"direct_nli":{"label":"neutral"},"relevance_flag":False},
    ]
    s=evidence_summary(claims)
    assert s["conflict_in_nli_labels"]
    assert s["support_sentence_indices"]==[0]
    assert s["contradict_sentence_indices"]==[1]
    assert s["n_without_absa_aspects"]==2


def test_emotions_fixed():
    assert set(EMOTIONS)=={"calm","inviting","safe"}

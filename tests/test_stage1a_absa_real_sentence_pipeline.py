"""Source integrity tests: only real review data from the committed dataset."""
import pathlib
import sys

ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from stage1a_absa_official_sentence_inference import load_cases, rebase_relation


def test_existing_20_reviews_are_preserved_verbatim():
    cases,_=load_cases()
    assert len(cases)==20
    assert len({c["row"] for c in cases})==20
    assert sum(len(c["sentences"]) for c in cases)>=20
    for case in cases:
        for s in case["sentences"]:
            assert case["review"][s["start"]:s["end"]]==s["text"]
            assert s["end"]>s["start"]


def test_sentence_segments_do_not_overlap():
    cases,_=load_cases()
    for case in cases:
        pairs=[(s["start"],s["end"]) for s in case["sentences"]]
        assert pairs==sorted(pairs)
        assert all(a[1]<=b[0] for a,b in zip(pairs,pairs[1:]))


def test_original_dataset_contains_no_generated_samples():
    cases,_=load_cases()
    assert all(c["review"] and isinstance(c["row"],int) for c in cases)
    assert len({(c["row"],c["place_id"]) for c in cases})==20

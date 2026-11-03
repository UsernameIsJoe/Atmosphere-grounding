import pathlib
import sys
from types import SimpleNamespace
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"scripts"))
from stage1a_absa_extractor_screen import (align_setfit, attach_sentences,
    sentences, annotate, summarize)

def test_setfit_unique_span_alignment():
    p=align_setfit("The park feels lovely.",[{"span":"park","polarity":"positive"}])
    assert p[0]["start"]==4 and p[0]["end"]==8
    assert p[0]["alignment"]=="unique"

def test_repeated_aspect_is_explicitly_ambiguous():
    x=align_setfit("Park, park.",[{"span":"park","polarity":"positive"}])
    assert x[0]["alignment"]=="ambiguous_order_assumption"

def test_unaligned_span_is_not_fabricated():
    x=align_setfit("The park is nice.",[{"span":"street","polarity":"negative"}])
    assert x[0]["start"] is None and x[0]["alignment"]=="unmatched"

def test_exact_substring_verification():
    import pytest
    with pytest.raises(ValueError):
        attach_sentences("Calm park.",[{"aspect":"nope","start":0,"end":4}],sentences("Calm park."))

def test_unmatched_sentence_remains_visible():
    def fake_extract(text):
        return [{"aspect":"Benches","start":0,"end":7,"polarity":"positive"}]
    text="Benches are nice. But the sirens are very loud."
    x=annotate(text,fake_extract,None)
    assert x["sentences_with_aspects"]==1
    assert x["total_sentences"]==2
    assert "sirens" in x["sentences_without_aspects"][0]["text"]

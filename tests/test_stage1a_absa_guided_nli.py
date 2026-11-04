import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from stage1a_absa_guided_nli import split_original, anchors, evidence_units, build_records, summarize

def sample():
    text="The gardens are beautiful but the traffic is not quiet."
    return {"start":0,"end":len(text),"text":text,"sentence_index":0,
       "aspects":[{"source":"deberta_absa","start":4,"end":11,"text":"gardens"},
                  {"source":"setfit_absa","start":34,"end":41,"text":"traffic"}],
       "relations":[{"source":"aos_t5",
          "aspect":{"start":4,"end":11,"text":"gardens"},
          "opinion":{"start":16,"end":25,"text":"beautiful"}}]}

def test_contrastive_split_preserves_verbatim_and_negation():
    s=sample()
    parts=split_original(s)
    assert len(parts)==2
    assert "not quiet" in parts[1]["text"]
    assert all(s["text"][p["start"]:p["end"]]==p["text"] for p in parts)
    assert parts[0]["text"].endswith("beautiful")

def test_absa_indexes_only_source_aligned_subclauses():
    s=sample()
    pieces=evidence_units(s)
    assert len(pieces)==2
    assert all(p["absa_guided"] for p in pieces)
    assert "relation" in pieces[0]["anchor_types"]
    assert "relation" not in pieces[1]["anchor_types"]

def test_unmatched_clause_is_never_dropped():
    s=sample()
    s["aspects"]=s["aspects"][:1]
    parts=evidence_units(s)
    assert len(parts)==2
    assert parts[1]["absa_guided"] is False
    assert parts[1]["text"].endswith("not quiet.")

def test_cross_clause_relation_falls_back_to_original():
    s=sample()
    s["relations"]=[{"source":"aos_t5",
      "aspect":{"start":4,"end":11,"text":"gardens"},
      "opinion":{"start":49,"end":54,"text":"quiet"}}]
    units=evidence_units(s)
    assert any(u["whole_sentence_fallback"] for u in units)
    assert any(u["text"]==s["text"] for u in units)

def test_nli_scoring_compares_original_sentence_without_new_labels():
    s=sample()
    h="The atmosphere of this location is calm."
    record={"row":1,"place_id":"loc","review":s["text"],"emotion":"calm",
       "hypothesis":h,"claims":[{**s,"direct_nli":{"label":"neutral"}}],
       "full_review_nli":{"label":"neutral"}}
    def fake_score(text,hyp):
        return {"label":"contradiction" if "not quiet" in text else "neutral",
                "probs":{"contradiction":0.8,"neutral":0.1,"entailment":0.1}}
    out=build_records([record],fake_score)
    assert len(out)==1
    assert out[0]["summary"]["units"]==2
    assert out[0]["summary"]["refined_units"]==2
    assert out[0]["summary"]["absa_indexed"]==2
    assert summarize(out)["by_emotion"]["calm"]["units"]==2


def test_no_punctuation_only_unit_after_parenthetical_split():
    # Reproduces the real row 97 case from completed run 41893335588.
    text="), but it is still a neat spot to visit."
    sentence={"text":text,"start":223,"end":223+len(text)}
    pieces=split_original(sentence)
    assert len(pieces)==1
    assert pieces[0]["text"]==text
    assert all(any(ch.isalnum() for ch in p["text"]) for p in pieces)

"""No-inference gate checks on the frozen five REAL Google reviews."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from stage1a_relevance_gate import gate
from stage1a_evidence_first_5 import frozen_reviews
from stage1a_panel_pilot import PILOT


def test_all_19_original_review_anchor_expectations():
    reviews, _ = frozen_reviews(ROOT / "data/processed/reviews.jsonl",
                                ROOT / "configs/stage1a_evidence_first_5.json")
    by_place = {r["place_id"]: r for r in reviews}
    anchor_file = json.loads((ROOT / "data/evaluation/stage1a_gate_anchor_cases.json").read_text())
    assert len(anchor_file["anchors"]) == 19
    for item in anchor_file["anchors"]:
        clause = by_place[item["place_id"]]["units"][item["unit_id"]]["text"]
        assert item["quote"] in clause
        observed = gate(clause, item["emotion"])["decision"]
        assert observed in ("keep", "review", "reject")
        if item["must"] == "retain":
            assert observed != "reject", (item, observed)
        elif item["must"] == "reject":
            assert observed == "reject", (item, observed)


def test_five_reviews_generate_60_triage_items_and_preserve_uncertain_cases():
    reviews, _ = frozen_reviews(ROOT / "data/processed/reviews.jsonl",
                                ROOT / "configs/stage1a_evidence_first_5.json")
    cases = [(u["text"], emotion) for r in reviews for u in r["units"] for emotion in PILOT]
    assert len(reviews) == 5 and len(cases) == 60
    labels = [gate(clause, emotion)["decision"] for clause, emotion in cases]
    assert set(labels) == {"keep", "review", "reject"}
    assert labels.count("review") > 0


def test_relevance_only_not_polarity_and_high_recall_examples():
    assert gate("The sides are extremely slippery.", "safe")["decision"] == "keep"
    assert gate("I feel safe and protected.", "safe")["decision"] == "keep"
    assert gate("There are quite a few seating areas.", "calm")["decision"] == "reject"
    assert gate("There are quite a few seating areas.", "inviting")["decision"] == "review"
    assert gate("The spongy hardtop material forms a nice hill,", "safe")["decision"] == "review"

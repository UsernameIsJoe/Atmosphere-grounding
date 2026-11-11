"""Offline tests: no Ollama calls, no invented evaluation reviews."""
import importlib.util
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import stage1a_evidence_first_5 as trial


def test_frozen_real_reviews_match_existing_baseline():
    reviews, _ = trial.frozen_reviews(
        ROOT / "data/processed/reviews.jsonl",
        ROOT / "configs/stage1a_evidence_first_5.json",
    )
    assert len(reviews) == 5
    assert [len(r["units"]) for r in reviews] == [2, 12, 2, 1, 3]
    assert sum(len(r["units"]) for r in reviews) == 20
    assert all(r["review_index"] == 0 for r in reviews)


def test_frozen_hash_rejects_modified_review(tmp_path):
    original = (ROOT / "data/processed/reviews.jsonl").read_text(encoding="utf-8")
    corrupted = tmp_path / "reviews.jsonl"
    corrupted.write_text(original.replace("Nice place to unwind", "Bad edit to unwind", 1),
                         encoding="utf-8")
    with pytest.raises(ValueError, match="mismatch"):
        trial.frozen_reviews(corrupted, ROOT / "configs/stage1a_evidence_first_5.json")


def test_evidence_grounding_preserves_original_text():
    clause = "It’s a really quiet   spot for reading."
    grounded, mode = trial.ground_span("IT'S A REALLY QUIET spot for reading.", clause)
    assert mode == "normalized"
    assert grounded == clause
    assert trial.validate_answer({
        "rationale": "Describes a quiet setting",
        "evidence_span": "quiet", "relevance": "supports",
    }, clause)["relevance"] == "supports"


def test_grounding_rejects_paraphrases_and_elsewhere():
    clause = "It's chaotic here."
    assert trial.ground_span("a quiet setting", clause)[0] is None
    assert trial.ground_span("quiet somewhere else", clause)[0] is None
    with pytest.raises(ValueError, match="ungrounded"):
        trial.validate_answer({"rationale": "Hazard here",
                               "evidence_span": "dangerous slides",
                               "relevance": "opposes"}, clause)


def test_schema_reason_before_label_and_one_emotion_only():
    keys = list(trial.SCHEMA["properties"])
    assert keys == ["rationale", "evidence_span", "relevance"]
    assert "labels" not in trial.SCHEMA["properties"]
    assert trial.SCHEMA["properties"]["rationale"]["maxLength"] <= 240
    assert trial.PROMPT.find("First explain") < trial.PROMPT.find("Last choose")

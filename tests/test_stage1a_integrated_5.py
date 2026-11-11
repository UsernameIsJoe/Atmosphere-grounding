"""Offline no-inference checks for integrated Stage 1A trial."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import stage1a_integrated_5 as integrated
from stage1a_evidence_first_5 import frozen_reviews


def mechanically_valid_stage1(tmp_path):
    """Mechanics-only labels on REAL source clauses; never research evaluation data."""
    reviews, _ = frozen_reviews(ROOT / "data/processed/reviews.jsonl",
                                ROOT / "configs/stage1a_evidence_first_5.json")
    rows = []
    for rev in reviews:
        for unit in rev["units"]:
            for model in ("qwen3:8b", "gemma3:4b"):
                for emotion in integrated.EMOTIONS:
                    rows.append({
                        "place_id": rev["place_id"], "review_index": rev["review_index"],
                        "unit_id": unit["unit_id"], "emotion": emotion, "model": model,
                        "source_sha256": rev["source_sha256"], "clause": unit["text"],
                        "rationale": "No evidence asserted for mechanics-only test.",
                        "relevance": "not_relevant", "evidence_span": "",
                    })
    p = tmp_path / "annotations.jsonl"
    p.write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in rows),
                 encoding="utf-8")
    return reviews, p


def test_full_source_check_120_existing_items(tmp_path):
    reviews, source = mechanically_valid_stage1(tmp_path)
    rows = integrated.load_extractions(source, reviews, ["qwen3:8b", "gemma3:4b"])
    assert len(rows) == 120
    assert not any(integrated.direction_job(x) for x in rows)


def test_no_missing_or_tampered_stage1_votes(tmp_path):
    reviews, source = mechanically_valid_stage1(tmp_path)
    rows = [json.loads(s) for s in source.read_text().splitlines()]
    rows[0]["source_sha256"] = "changed"
    source.write_text("".join(json.dumps(x) + "\n" for x in rows))
    with pytest.raises(ValueError, match="provenance mismatch"):
        integrated.load_extractions(source, reviews, ["qwen3:8b", "gemma3:4b"])


def test_no_partial_source_allowed(tmp_path):
    reviews, source = mechanically_valid_stage1(tmp_path)
    source.write_text("\n".join(source.read_text().splitlines()[1:]) + "\n")
    with pytest.raises(ValueError, match="incomplete"):
        integrated.load_extractions(source, reviews, ["qwen3:8b", "gemma3:4b"])


def test_reconstruction_and_direction_mapping():
    item = {"place_id": "ChIJ_source", "review_index": 0, "unit_id": 1,
            "emotion": "safe", "model": "gemma3:4b", "source_sha256": "hash",
            "clause": "slippery path", "evidence_span": "slippery",
            "relevance": "supports", "rationale": "Prior label, do not reuse"}
    assert integrated.reconstruct(item, "opposes")["final_relevance"] == "opposes"
    assert integrated.reconstruct(item, "neither")["final_relevance"] == "not_relevant"
    assert integrated.reconstruct(item, "ambiguous")["final_relevance"] == "uncertain"
    with pytest.raises(ValueError, match="Missing direction"):
        integrated.reconstruct(item, None)
    item["evidence_span"] = ""
    assert integrated.reconstruct(item, None)["final_relevance"] == "not_relevant"
    item["relevance"] = "uncertain"
    assert integrated.reconstruct(item, None)["final_relevance"] == "uncertain"


def test_classifier_receives_only_span_clause_and_emotion():
    # Inspect built-in call site: old relevance or rationale must not leak.
    import inspect
    src = inspect.getsource(integrated.run)
    assert 'direction_input = {"emotion": item["emotion"], "clause": item["clause"],' in src
    assert 'classify_direction(args.ollama_url, item["model"], direction_input' in src

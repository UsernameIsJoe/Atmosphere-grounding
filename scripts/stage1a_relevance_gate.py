#!/usr/bin/env python3
"""Standalone deterministic relevance gate, without LLM inference.

This is a conservative rule baseline, not a learned or validated classifier.
KEEP means direct cue detected, REVIEW means abstain, REJECT means narrowly
identified irrelevant factual inventory. Never interpret KEEP as supports.
"""
from __future__ import annotations
import argparse
import collections
import json
import re
from pathlib import Path
from stage1a_panel_pilot import PILOT
from stage1a_evidence_first_5 import frozen_reviews

ROOT = Path(__file__).resolve().parents[1]
CUES = {
    "calm": (r"\b(?:calm|peace(?:ful)?|quiet|tranquil|seren(?:e|ity)|relax(?:ing|ed|ation)?|unwind|meditat\w*|chill(?:ing)?|rest(?:ful|ing)?|stress(?:ful|ed)?|chaos|chaotic|nois\w*|loud|crowd\w*|hectic|sooth\w*)\b",),
    "inviting": (r"\b(?:invit\w*|welcom\w*|gather\w*|linger\w*|cozy|cosy|comfort\w*|hostil\w*|exclud\w*|unwelcom\w*|belong\w*|friend\w*|social\w*|approach\w*|wish to visit|would return|want to return)\b",),
    "safe": (r"\b(?:safe(?:ty)?|unsafe|protect\w*|secur\w*|danger\w*|risk\w*|hazard\w*|injur\w*|slip\w*|slippery|hurt|hit their head|accident\w*|traffic|cars?|street|worr\w*|threat\w*|violence|crime|drain\w*|broken|stuck)\b",),
}
BARE_FACT = re.compile(
    r"^(?:there (?:are|is) (?:quite a few|some|a few|several|many|[\d]+) "
    r"(?:seating areas|benches|tables|courts|playgrounds|parking spaces)|"
    r"also next to (?:the )?[^.!?]+|"
    r"(?:located|situated) (?:near|next to|in) [^.!?]+|"
    r"(?:the )?(?:spongy )?(?:hardtop )?material forms a nice hill|"
    r"(?:it (?:has|is) )?(?:a lot of|lots of) (?:interesting|great) ideas)"
    r"[,;.!?]*$", re.I
)
REFERENCE = re.compile(r"^(?:but|however|yet|although|while|it\b|this\b|that\b|then\b|and\b)", re.I)

def gate(clause: str, emotion: str) -> dict:
    if emotion not in PILOT:
        raise ValueError(f"Unknown emotion: {emotion}")
    if any(re.search(pattern, clause, re.I) for pattern in CUES[emotion]):
        return {"decision": "keep", "reason": "explicit_category_indicator"}
    if BARE_FACT.fullmatch(clause.strip()) and not REFERENCE.match(clause.strip()):
        if emotion == "inviting" and re.search(r"\b(seating|benches|tables|courts|playgrounds)\b", clause, re.I):
            return {"decision": "review", "reason": "possible_indirect_social_affordance"}
        if emotion == "safe" and re.search(r"\b(hardtop|material|hill)\b", clause, re.I):
            return {"decision": "review", "reason": "possible_indirect_surface_condition"}
        return {"decision": "reject", "reason": "bare_inventory_or_location_fact"}
    return {"decision": "review", "reason": "insufficient_evidence_to_reject"}

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "data/processed/reviews.jsonl")
    parser.add_argument("--config", type=Path, default=ROOT / "configs/stage1a_evidence_first_5.json")
    parser.add_argument("--output", type=Path, default=ROOT / "reports/stage1a_relevance_gate_5")
    args = parser.parse_args()
    reviews, _ = frozen_reviews(args.input, args.config)
    rows = []
    for review in reviews:
        for unit in review["units"]:
            for emotion in PILOT:
                result = gate(unit["text"], emotion)
                rows.append({"place_id": review["place_id"], "review_index": review["review_index"],
                             "source_sha256": review["source_sha256"], "unit_id": unit["unit_id"],
                             "emotion": emotion, "clause": unit["text"], **result})
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "gate_decisions.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
    counts = collections.Counter(row["decision"] for row in rows)
    anchors = json.loads((ROOT / "data/evaluation/stage1a_gate_anchor_cases.json").read_text(encoding="utf-8"))
    indexed = {(row["place_id"], row["unit_id"], row["emotion"]): row for row in rows}
    misses = []
    for anchor in anchors["anchors"]:
        key = (anchor["place_id"], anchor["unit_id"], anchor["emotion"])
        if key not in indexed or anchor["quote"] not in indexed[key]["clause"]:
            raise ValueError("Real-source anchor missing or changed: " + str(key))
        actual = indexed[key]["decision"]
        wanted = anchor["must"]
        if (wanted == "retain" and actual == "reject") or (wanted == "reject" and actual != "reject"):
            misses.append({"key": key, "expected": wanted, "actual": actual, "quote": anchor["quote"]})
    report = {"reviews": len(reviews), "clauses": sum(len(r["units"]) for r in reviews),
              "clause_emotion_pairs": len(rows), "decisions": dict(counts),
              "anchor_count": len(anchors["anchors"]), "anchor_misses": misses,
              "status": "NOT VALIDATED: hand-picked anchors are not a gold accuracy benchmark",
              "policy": "Only reject may be filtered; keep and review proceed to later stages",
              "inference_calls": 0}
    (args.output / "gate_diagnostics.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    if misses:
        raise SystemExit("Gate anchor failures detected; do not connect downstream models.")

if __name__ == "__main__":
    main()

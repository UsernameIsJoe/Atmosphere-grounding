#!/usr/bin/env python3
"""Stage 1A / 4A: ONE emotion-agnostic, high-recall atmosphere relevance gate.

Uses a real pretrained sentence-embedding model. No emotion is supplied as an
input or emitted as an output. Returns a continuous semantic score per ORIGINAL
review clause, with adjacent original clauses as optional context.

Do NOT mistake the bounded cosine similarity score for a calibrated probability.
The gate removes only text judged unrelated to *any* atmosphere-relevant
environmental condition or experience; a downstream LLM assigns emotions and
direction. No LLM inference is performed here.
"""
from __future__ import annotations

import argparse
import collections
import json
import math
import statistics
from pathlib import Path

from stage1a_panel_pilot import load_real_reviews, prepare, sha256
from stage1a_evidence_first_5 import frozen_reviews

ROOT = Path(__file__).resolve().parents[1]
MODEL = "sentence-transformers/all-mpnet-base-v2"

# Predeclared SEMANTIC coverage descriptors, NOT synthetic evaluation comments,
# model-generated labels, or a fixed rule/keyword matcher. Distinct kinds of
# place-attributed evidence matter, including negative and indirect evidence.
DESCRIPTIONS = (
    "How a place feels to visit, spend time in, walk through, or remain in.",
    "The atmosphere and sensory experience of a public place or outdoor space.",
    "Peace, calmness, quietness, relaxation, disturbance, stressful noise or chaos at a place.",
    "Feeling welcomed or unwelcome, comfortable or uncomfortable, wanting to stay or leave a place.",
    "Social experience, community activity, gathering, inclusion or exclusion in public space.",
    "Feeling safe, protected or unsafe in a space, or being worried about visiting it.",
    "Physical safety conditions, slippery surfaces, falling, collisions, injuries and hazards in a place.",
    "Condition, maintenance, cleanliness, unpleasantness or disrepair affecting the use of a place.",
    "Crowding, traffic, noise, lighting, enclosure, movement and accessibility affecting experience.",
    "Environmental qualities such as shade, greenery, enclosure, visibility and openness affecting experience.",
    "Activities people enjoy or dislike doing in a place, such as walking, playing, sitting or relaxing.",
    "Features or spatial arrangements that enable or prevent how people use and experience a place.",
)
VERSION = "stage1a_agnostic_embedding_gate_v1"


def source_reviews(corpus: Path, config: Path | None, max_reviews: int) -> list[dict]:
    if config is not None:
        reviews, _ = frozen_reviews(corpus, config)
        return reviews
    source = load_real_reviews(corpus, 0)
    if max_reviews:
        source = source[:max_reviews]
    return prepare(source)


def prepare_units(reviews: list[dict]) -> list[dict]:
    rows = []
    for review in reviews:
        units = review["units"]
        for i, unit in enumerate(units):
            neighbor = [u["text"] for u in units[max(0, i - 1):min(len(units), i + 2)]]
            rows.append({
                "place_id": review["place_id"], "review_index": review["review_index"],
                "source_sha256": review["source_sha256"], "unit_id": unit["unit_id"],
                "start": unit["start"], "end": unit["end"],
                "clause": unit["text"],
                "local_context": " ".join(neighbor),
            })
    return rows


def calculate_scores(rows: list[dict], model_name: str, batch_size: int) -> list[dict]:
    import numpy as np
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(model_name, device="cpu")
    templates = model.encode(list(DESCRIPTIONS), convert_to_numpy=True,
                             normalize_embeddings=True, batch_size=batch_size, show_progress_bar=False)
    texts = model.encode([r["clause"] for r in rows], convert_to_numpy=True,
                         normalize_embeddings=True, batch_size=batch_size, show_progress_bar=False)
    contexts = model.encode([r["local_context"] for r in rows], convert_to_numpy=True,
                            normalize_embeddings=True, batch_size=batch_size, show_progress_bar=False)
    if len(texts) != len(rows) or len(contexts) != len(rows):
        raise ValueError("Missing embedding result")
    scores = []
    for row, vector, ctx in zip(rows, texts, contexts):
        direct = np.matmul(templates, vector)
        context = np.matmul(templates, ctx)
        # Context is for *ambiguous references* only, not for overriding the
        # target clause: contribute a bounded fraction of neighborhood signal.
        # No negative cosine is treated as atmospheric evidence.
        direct_score = max(0.0, float(np.max(direct)))
        context_score = max(0.0, float(np.max(context)))
        score = min(1.0, max(0.0, 0.8 * direct_score + 0.2 * context_score))
        if not math.isfinite(score):
            raise ValueError("Nonfinite relevance score")
        scores.append({**row, "relevance_score": round(score, 7),
                       "direct_similarity": round(direct_score, 7),
                       "context_similarity": round(context_score, 7),
                       "closest_descriptor_id": int(np.argmax(direct))})
    return scores


def audit_anchors(rows: list[dict], audit_path: Path) -> dict:
    # Project's existing original-review anchor set is emotion-specific. Drop
    # its emotion column: the new gate makes ONE decision PER CLAUSE, and must
    # retain a clause if it is relevant to ANY emotion.
    spec = json.loads(audit_path.read_text(encoding="utf8"))
    original = {(r["place_id"], r["unit_id"]): r for r in rows}
    mandatory = {}
    negatives = {}
    for anchor in spec["anchors"]:
        key = (anchor["place_id"], anchor["unit_id"])
        if key not in original or anchor["quote"] not in original[key]["clause"]:
            raise ValueError(f"Source quotation mismatch {key}")
        if anchor["must"] == "retain":
            mandatory[key] = original[key]
        else:
            negatives[key] = original[key]
    # An example negative for one emotion is NOT a valid overall negative.
    # It may describe something relevant to *another* emotion. Retain only
    # cross-emotion-uncontested negatives as descriptive probes, not gold labels.
    negatives = {k: v for k, v in negatives.items() if k not in mandatory}
    retaining = list(mandatory.values())
    unrelated = list(negatives.values())
    min_retain = min((r["relevance_score"] for r in retaining), default=None)
    return {"must_retain_unique_clauses": len(retaining),
            "must_retain_min_score": min_retain,
            "must_retain_median": statistics.median(r["relevance_score"] for r in retaining) if retaining else None,
            "descriptive_negative_unique_clauses": len(unrelated),
            "descriptive_negative_median": statistics.median(r["relevance_score"] for r in unrelated) if unrelated else None,
            "mandatory_case_scores": [{"place_id": r["place_id"], "unit_id": r["unit_id"],
                                       "score": r["relevance_score"], "text": r["clause"]}
                                      for r in retaining],
            "candidate_negative_scores": [{"place_id": r["place_id"], "unit_id": r["unit_id"],
                                           "score": r["relevance_score"], "text": r["clause"]}
                                          for r in unrelated],
            "warning": "Hand-picked review anchor probes, NOT independent labels or an accuracy estimate."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "data/processed/reviews.jsonl")
    parser.add_argument("--config", type=Path, default=None,
                        help="Optional frozen-five selection file; default scores entire real-review corpus")
    parser.add_argument("--max-reviews", type=int, default=0,
                        help="0 = all actual reviews")
    parser.add_argument("--output", type=Path, default=ROOT / "reports/stage1a_agnostic_gate")
    parser.add_argument("--model", default=MODEL)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--threshold", type=float, default=None,
                        help="Optional research cutoff; default does not filter any unit")
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args()
    if args.threshold is not None and not 0 <= args.threshold <= 1:
        parser.error("threshold must be between 0 and 1")
    reviews = source_reviews(args.input, args.config, args.max_reviews)
    rows = prepare_units(reviews)
    if not rows or len({(r["place_id"],r["review_index"],r["unit_id"]) for r in rows}) != len(rows):
        raise ValueError("Duplicate or missing original clauses")
    print(f"VERIFIED {len(reviews)} real reviews across {len({r['place_id'] for r in reviews})} places; "
          f"{len(rows)} original clauses, ONE relevance score each, zero emotion-specific calls",
          flush=True)
    if args.prepare_only:
        return
    scored = calculate_scores(rows, args.model, args.batch_size)
    if len(scored) != len(rows):
        raise ValueError("Incorrect score count")
    for row in scored:
        row["decision"] = ("pass_to_llm" if args.threshold is None or
                           row["relevance_score"] >= args.threshold else "filtered_candidate")
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output/"scores.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False)+"\n" for row in scored), encoding="utf-8")
    chosen_five = ROOT/"configs/stage1a_evidence_first_5.json"
    audit = {}
    if args.config is not None and args.config.resolve() == chosen_five.resolve():
        audit = audit_anchors(scored, ROOT/"data/evaluation/stage1a_gate_anchor_cases.json")
    summary = {
        "version": VERSION,"model":args.model,"n_reviews":len(reviews),
        "n_places":len({r["place_id"] for r in reviews}),"n_clauses":len(rows),
        "n_emotion_specific_scores":0, "n_llm_calls":0,
        "score_definition":"0.8*max_clipped_cosine(clause,12 atmospheric descriptors) + 0.2*max_clipped_cosine(adjacent original clauses,12 descriptors). Not probability.",
        "descriptor_sha256":sha256(json.dumps(DESCRIPTIONS)),
        "threshold":args.threshold,"decision_counts":dict(collections.Counter(r["decision"] for r in scored)),
        "score_min":min(r["relevance_score"] for r in scored),
        "score_median":statistics.median(r["relevance_score"] for r in scored),
        "score_max":max(r["relevance_score"] for r in scored),
        "audit":audit,"status":"Research prototype. Threshold must be validated against independent annotated real clauses before use as a hard filter."
    }
    (args.output/"diagnostics.json").write_text(json.dumps(summary,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("SUMMARY "+json.dumps({k:v for k,v in summary.items() if k != "audit"},ensure_ascii=False),flush=True)
    for row in sorted(scored,key=lambda r:r["relevance_score"]):
        print("RANK "+json.dumps({"score":row["relevance_score"],"place_id":row["place_id"],
                                 "review_index":row["review_index"],"unit_id":row["unit_id"],
                                 "clause":row["clause"]},ensure_ascii=False),flush=True)


if __name__ == "__main__":
    main()

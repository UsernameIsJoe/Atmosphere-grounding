#!/usr/bin/env python3
"""Fixed ABSA -> relevance -> NLI evidence ledger on frozen real-review outputs.

ABSA indexes source text; relevance prioritizes; NLI judges the original
passage. No model reruns, hard filtering, invented text, or intensity score.
This is a component audit, not an accuracy evaluation.
"""
import argparse
import json
from pathlib import Path

EMOTIONS = ("calm", "inviting", "safe")


def load_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def evidence_tier(claim):
    if claim["relations"]:
        return "aspect_opinion_relation"
    if claim["aspects"]:
        return "aspect_only"
    return "unmatched"


def check_provenance(record, claim):
    review = record["review"]
    if review[claim["start"]:claim["end"]] != claim["text"]:
        raise ValueError("Source sentence offset failed")
    for aspect in claim["aspects"]:
        if review[aspect["start"]:aspect["end"]] != aspect["text"]:
            raise ValueError("ABSA aspect is not original-source grounded")
    for relation in claim["relations"]:
        for item in (relation["aspect"], relation["opinion"]):
            if review[item["start"]:item["end"]] != item["text"]:
                raise ValueError("AOS relation is not original-source grounded")


def interpret(claim):
    tier = evidence_tier(claim)
    relevant = claim["relevance_flag"]
    return {
        "sentence_index": claim["sentence_index"],
        "start": claim["start"], "end": claim["end"], "text": claim["text"],
        "absa_tier": tier, "aspects": claim["aspects"], "relations": claim["relations"],
        "absa_indexed": tier != "unmatched", "relevance_selected": relevant,
        "combined_selected": relevant and tier != "unmatched",
        "rescued_unmatched": relevant and tier == "unmatched",
        "relevance_nli": claim["relevance_nli"],
        "emotion_nli": claim["direct_nli"],
        "needs_review": (tier == "unmatched" and relevant)
                        or (tier != "unmatched" and not relevant
                            and claim["direct_nli"]["label"] != "neutral"),
    }


def summarize_claims(claims):
    def counts(subset):
        return {
            "total":len(subset),
            "support":sum(c["emotion_nli"]["label"] == "entailment" for c in subset),
            "contradict":sum(c["emotion_nli"]["label"] == "contradiction" for c in subset),
            "neutral":sum(c["emotion_nli"]["label"] == "neutral" for c in subset)
        }
    all_claims = list(claims)
    return {
        "all_sentences":counts(all_claims),
        "absa_only":counts([c for c in all_claims if c["absa_indexed"]]),
        "relevance_only":counts([c for c in all_claims if c["relevance_selected"]]),
        "absa_and_relevance":counts([c for c in all_claims if c["combined_selected"]]),
        "rescued_unmatched":counts([c for c in all_claims if c["rescued_unmatched"]]),
        "flagged_disagreements":sum(c["needs_review"] for c in all_claims),
    }


def build(rows):
    if len(rows) != 60 or len({(r["row"],r["emotion"]) for r in rows}) != 60:
        raise ValueError("Expected exactly 20 reviews x 3 emotions")
    output = []
    for record in rows:
        if record["emotion"] not in EMOTIONS:
            raise ValueError("Unexpected emotion")
        for claim in record["claims"]:
            check_provenance(record, claim)
        claims = [interpret(c) for c in record["claims"]]
        output.append({
            "row": record["row"], "place_id": record["place_id"],
            "emotion": record["emotion"], "hypothesis": record["hypothesis"],
            "review": record["review"], "direct_review_nli":record["full_review_nli"],
            "evidence":claims, "comparison":summarize_claims(claims)
        })
    totals={}
    for emotion in EMOTIONS:
        group=[r for r in output if r["emotion"]==emotion]
        claims=[c for r in group for c in r["evidence"]]
        totals[emotion]={
            **summarize_claims(claims),
            "reviews":len(group),
            "reviews_with_no_relevance_selected":sum(
                not any(c["relevance_selected"] for c in r["evidence"]) for r in group),
            "indexed_relations":sum(c["absa_tier"] == "aspect_opinion_relation" for c in claims),
        }
    return output, {
        "n_reviews":20,"n_emotion_records":len(output),
        "n_unique_source_sentences":sum(len(r["evidence"]) for r in output)//3,
        "by_emotion":totals,
        "decisions":{
            "absa":"Source-grounded aspect/opinion indexing, not emotion prediction",
            "relevance":"Frozen BART metarelevance hypothesis; priority flag only",
            "nli":"Frozen BART original sentence entailment/neutral/contradiction",
            "no_hard_filter":True,"no_automatic_emotion_score":True
        },
        "caveat":"Component contribution audit, not measured correctness or a validated emotion predictor",
    }


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--input",required=True)
    parser.add_argument("--output",required=True)
    args=parser.parse_args()
    records,summary=build(load_jsonl(args.input))
    dest=Path(args.output)
    dest.mkdir(parents=True,exist_ok=True)
    (dest/"evidence_ledger.jsonl").write_text(
        "".join(json.dumps(r,ensure_ascii=False)+"\n" for r in records),encoding="utf-8")
    (dest/"summary.json").write_text(
        json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(summary["by_emotion"],indent=2))


if __name__=="__main__":
    main()

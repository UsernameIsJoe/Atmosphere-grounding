#!/usr/bin/env python3
"""Compare sentence-level ABSA inference on real reviews against prior whole-review runs.

Partial reference recovery is a diagnostic only; no fabricated gold labels,
synthetic review inputs, or claims of independent precision/recall.
"""
import argparse
import json
from pathlib import Path

from stage1a_absa_real_review_comparison import load_jsonl, compare


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--aos",required=True)
    p.add_argument("--gts",required=True)
    p.add_argument("--dependency",required=True)
    p.add_argument("--references",required=True)
    p.add_argument("--prior-audit",required=True)
    p.add_argument("--output",required=True)
    args=p.parse_args()
    rows={
        "aos_t5":load_jsonl(args.aos),
        "dependency_rules":load_jsonl(args.dependency),
        "gts_joint_aste":load_jsonl(args.gts),
    }
    reference=json.loads(Path(args.references).read_text(encoding="utf-8"))
    previous=json.loads(Path(args.prior_audit).read_text(encoding="utf-8"))
    ids={method:{int(x["row"]):x["review"] for x in cases} for method,cases in rows.items()}
    if not (ids["aos_t5"]==ids["dependency_rules"]==ids["gts_joint_aste"]):
        raise ValueError("Model inputs differ; refusing unpaired comparison")
    scored=compare(reference,rows)
    report={
        "n_original_reviews":len(ids["aos_t5"]),
        "n_original_sentences":len([s for x in rows["aos_t5"] for s in x["sentences"]]),
        "n_reference_target_pairs":sum(len(c["pairs"]) for c in reference["cases"]),
        "reference_status":reference["status"],
        "per_model":{},
        "warnings":[
            "Prior whole-review and new sentence-level model runs use identical reviews but different input units.",
            "References are partial assistant-authored target pairs, not independently annotated full gold data.",
            "Recovery of lexical reference pairs is NOT precision, full recall, or emotion-inference accuracy.",
            "A paraphrase or overlapping target span may be semantically valid but count as missing.",
            "Polarity labels and negation are preserved for separate adjudication, not deemed correct.",
            "All inputs are verbatim actual review sentences, with the original review and offsets retained.",
        ],
    }
    for method,d in scored.items():
        old=previous["methods"][method]
        sentence=rows[method]
        total_sent=sum(len(x["sentences"]) for x in sentence)
        report["per_model"][method]={
            "whole_review_reference_target_recovered":old["targets_recovered"],
            "sentence_level_reference_target_recovered":d["targets_recovered"],
            "reference_target_count":d["reference_targets"],
            "delta_targets":d["targets_recovered"]-old["targets_recovered"],
            "sentence_level_source_grounded_relations":d["verified_relationships"],
            "sentence_count":total_sent,
            "sentences_with_extraction":sum(bool(s["extraction"]["relations"]) for x in sentence for s in x["sentences"]),
            "sentences_truncated":sum(s["extraction"]["input_truncated"] for x in sentence for s in x["sentences"]),
            "sentences_unparsed":sum(s["extraction"]["parse_status"]=="unparsed_generation" for x in sentence for s in x["sentences"]),
        }
    dest=Path(args.output)
    dest.mkdir(parents=True,exist_ok=True)
    (dest/"comparison.json").write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
    with (dest/"review_comparison.jsonl").open("w",encoding="utf-8") as handle:
        for row in sorted(ids["aos_t5"]):
            handle.write(json.dumps({
                "row":row,"review":ids["aos_t5"][row],
                "models":{m:next(r for r in d["per_review"] if r["row"]==row)
                          for m,d in scored.items()},
            },ensure_ascii=False)+"\n")
    print(json.dumps(report["per_model"],indent=2))


if __name__=="__main__":
    main()

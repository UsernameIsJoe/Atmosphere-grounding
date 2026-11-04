#!/usr/bin/env python3
"""Frozen ABSA aspect-opinion comparison on predeclared controlled references.

Not independently labeled accuracy. Reuse prior model output, never silently
equate literal source matching with semantically correct relationships.
"""
import argparse
import json
import re
from pathlib import Path


def norm(value):
    return re.sub(r"\s+", " ", value.strip().lower())


def records(path):
    return {x["id"]: x for x in json.loads(Path(path).read_text(encoding="utf-8"))}


def verified(text, relation):
    if not relation.get("grounded"):
        return False
    for name in ("aspect", "opinion"):
        span = relation[name]
        a, b = span.get("start"), span.get("end")
        if not isinstance(a, int) or not isinstance(b, int):
            return False
        if not (0 <= a < b <= len(text)) or text[a:b] != span["text"]:
            return False
    return True


def score(refs, predictions):
    gold = {case["id"]: case for case in refs["cases"]}
    if gold.keys() != predictions.keys():
        raise ValueError("Missing or extra reference cases")
    tp = fp = fn = negated_hits = unverified = 0
    rows = []
    for name, case in gold.items():
        obj = predictions[name]
        relations = obj["extraction"]["relations"]
        good = [r for r in relations if verified(obj["text"], r)]
        unverified += len(relations) - len(good)
        expected = {tuple(norm(x) for x in pair) for pair in case["pairs"]}
        predicted = {(norm(r["aspect"]["text"]), norm(r["opinion"]["text"])) for r in good}
        right = expected & predicted
        extras = predicted - expected
        missing = expected - predicted
        tp += len(right)
        fp += len(extras)
        fn += len(missing)
        for aspect, opinion in case.get("negated", []):
            negated_hits += int(any(
                (norm(r["aspect"]["text"]), norm(r["opinion"]["text"])) ==
                (norm(aspect), norm(opinion))
                and re.search(r"\b(?:not|never|no)\b", r["opinion"]["text"], re.I)
                for r in good
            ))
        rows.append({
            "id": name, "expected": sorted(map(list, expected)),
            "predicted": sorted(map(list, predicted)),
            "correct": len(right), "extra": len(extras), "missed": len(missing),
            "false_relations": sorted(map(list, extras)),
            "missed_relations": sorted(map(list, missing)),
            "unverified": len(relations) - len(good),
            "implicit": bool(case.get("implicit")),
        })
    precision = tp/(tp+fp) if tp+fp else 0.0
    recall = tp/(tp+fn) if tp+fn else 0.0
    f1 = 2*precision*recall/(precision+recall) if precision+recall else 0.0
    return {
        "correct": tp, "false_relations": fp, "missed": fn,
        "diagnostic_precision": round(precision, 4),
        "diagnostic_recall": round(recall, 4),
        "diagnostic_f1": round(f1, 4),
        "negated_opinion_preserved": negated_hits,
        "negated_opinion_cases": sum(len(c.get("negated", [])) for c in refs["cases"]),
        "unverified_source_relations": unverified, "cases": rows,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--references", required=True)
    parser.add_argument("--aos", required=True)
    parser.add_argument("--dependency", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    refs = json.loads(Path(args.references).read_text(encoding="utf-8"))
    scored = {
        "aos_t5": score(refs, records(args.aos)),
        "dependency_rules": score(refs, records(args.dependency)),
    }
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    report = {
        "reference_status": refs["status"], "models": scored,
        "limitations": [
            "Reference pairs are researcher-authored controlled diagnostics, NOT independent labels.",
            "Only eight controlled sentences; no estimates of real-review generalization.",
            "Exact pair matching deliberately does not award paraphrase credit.",
            "Implicit adjective-only evidence is not scored as an explicit aspect pair.",
            "Reuses previously executed model outputs, not new checkpoint inference.",
            "Polarity is not evidence of correct negation scope.",
        ],
    }
    (out/"score.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (out/"errors.jsonl").write_text("".join(
        json.dumps({"model": name, **row})+"\n"
        for name, result in scored.items() for row in result["cases"]
    ), encoding="utf-8")
    for name, result in scored.items():
        print(name, {k:v for k,v in result.items() if k != "cases"})


if __name__ == "__main__":
    main()

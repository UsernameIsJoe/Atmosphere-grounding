#!/usr/bin/env python3
"""Evaluate Stage 1A v2 against independent local-LLM silver labels."""
from __future__ import annotations
import argparse
import collections
import json
import re

import yaml

from stage1a_v2 import (EMOTIONS, NLI_MODELS, OUT, ROOT, NLIScorer, _model_slug,
                         load_items, read_json, read_jsonl)

OLD_HYPOTHESES = {
    "calm": "The atmosphere of this location is calm.",
    "inviting": "The atmosphere of this location is inviting.",
    "safe": "This location feels physically safe to visitors.",
}
TAUS = (0.1, 0.2, 0.3)
RELEVANT = {"supports", "opposes", "mixed", "relevant_but_unresolved"}
ABSTAINS = {"uncertain", "abstain", "relevant_but_unresolved"}


def key(source):
    return (source["row"], source["start"], source["end"])


def indexed(rows):
    return {key(r["source"]): r for r in rows}


def load_lexicon(path):
    data = yaml.safe_load(path.read_text(encoding="utf8"))
    names = set(data.get("atmospheres", []))
    structured = data.get("terms", {}) if isinstance(data, dict) else {}
    terms = {}
    for e in EMOTIONS:
        if e not in names:
            raise ValueError(f"{e} missing from lexicon {path}")
        custom = structured.get(e) if isinstance(structured, dict) else None
        terms[e] = [str(x).lower() for x in custom] if isinstance(custom, list) and custom else [e]
    return terms


def lexicon_predict(sentence, emotion, terms):
    supports = opposes = False
    lower = sentence.lower()
    for term in terms[emotion]:
        for m in re.finditer(r"\b" + re.escape(term) + r"\b", lower):
            prefix = lower[max(0, m.start() - 32):m.start()]
            negated = bool(re.search(r"(?:\bnot\b|\bnever\b|\bno\b|n't)\W+(?:\w+\W+){0,2}$", prefix))
            if negated:
                opposes = True
            else:
                supports = True
    if supports and opposes:
        return {"label": "mixed", "type": "explicit", "span": ""}
    if opposes:
        return {"label": "opposes", "type": "explicit", "span": ""}
    if supports:
        return {"label": "supports", "type": "explicit", "span": ""}
    return {"label": "not_relevant", "type": None, "span": ""}


def old_nli_predictions(sources):
    scorer = NLIScorer("facebook/bart-large-mnli")
    out = {}
    for source in sources:
        per = {}
        for e in EMOTIONS:
            pred = scorer.score(source["sentence"], OLD_HYPOTHESES[e])
            label = {"entailment": "supports", "contradiction": "opposes", "neutral": "not_relevant"}[pred["label"]]
            per[e] = {"label": label, "type": None, "span": "", "nli": pred}
        out[key(source)] = per
    return out


def step_a_prediction(record, emotion):
    x = record["emotions"][emotion]
    if not x["valid_for_downstream"]:
        return {"label": "abstain", "type": None, "span": ""}
    return {"label": x["relevance"], "type": x["type"], "span": x["evidence_span"]}


def step_b_prediction(a_record, b_record, emotion, tau):
    a = step_a_prediction(a_record, emotion)
    if a["label"] in ("abstain", "not_relevant", "uncertain", "mixed"):
        return a
    b = b_record["emotions"][emotion]
    if b.get("skipped"):
        return {"label": "relevant_but_unresolved", "type": a["type"], "span": a["span"]}
    s = b["s"]
    if abs(s) < tau:
        label = "relevant_but_unresolved"
    else:
        label = "supports" if s > 0 else "opposes"
    return {"label": label, "type": a["type"], "span": a["span"]}


def token_f1(a, b):
    ta = re.findall(r"\w+|[^\w\s]", a.lower())
    tb = re.findall(r"\w+|[^\w\s]", b.lower())
    if not ta or not tb:
        return 0.0
    ca, cb = collections.Counter(ta), collections.Counter(tb)
    overlap = sum((ca & cb).values())
    if overlap == 0:
        return 0.0
    p, r = overlap / len(ta), overlap / len(tb)
    return 2 * p * r / (p + r)


def metrics_for(emotion, predictions, silver_rows):
    tp = fp = fn = 0
    direction_correct = direction_total = 0
    explicit_hit = explicit_total = 0
    type_hits = {t: 0 for t in ("explicit", "direct_indicator", "indirect")}
    type_totals = {t: 0 for t in type_hits}
    leak_hit = leak_total = 0
    spans = []
    abstain = scored = 0
    for s in silver_rows:
        cell = s["emotions"][emotion]
        gold = cell["silver_relevance"]
        if gold is None:
            continue
        pred = predictions[key(s["source"])][emotion]
        plabel = pred["label"]
        pred_rel = plabel in RELEVANT
        gold_rel = gold in ("supports", "opposes", "mixed")
        tp += pred_rel and gold_rel
        fp += pred_rel and not gold_rel
        fn += (not pred_rel) and gold_rel
        scored += 1
        abstain += plabel in ABSTAINS
        if gold_rel:
            direction_total += 1
            direction_correct += plabel == gold
        stype = cell["silver_type"]
        if stype == "explicit":
            explicit_total += 1
            explicit_hit += pred_rel
        if stype in type_totals:
            type_totals[stype] += 1
            type_hits[stype] += pred.get("type") == stype
        if gold == "not_relevant" and s["source"].get("rating") in (1, 2):
            leak_total += 1
            leak_hit += plabel == "opposes"
        if cell["span_overlap"] and pred.get("span"):
            j1, j2 = cell["judge_spans"]
            spans.append((token_f1(pred["span"], j1) + token_f1(pred["span"], j2)) / 2)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "relevance_precision": precision,
        "relevance_recall": recall,
        "relevance_f1": f1,
        "direction_accuracy": direction_correct / direction_total if direction_total else None,
        "explicit_recall": explicit_hit / explicit_total if explicit_total else None,
        "type_accuracy": {t: type_hits[t] / type_totals[t] if type_totals[t] else None for t in type_hits},
        "leakage_rate": leak_hit / leak_total if leak_total else None,
        "leakage_denominator_negative_rating_proxy": leak_total,
        "span_token_f1": sum(spans) / len(spans) if spans else None,
        "abstention_rate": abstain / scored if scored else None,
        "n_silver": scored,
        "n_direction": direction_total,
    }


def aggregate_metric(per_emotion, name):
    vals = [per_emotion[e][name] for e in EMOTIONS if per_emotion.get(e) and per_emotion[e][name] is not None]
    return sum(vals) / len(vals) if vals else None


def choose_tau(a_idx, b_idx, silver, stable_emotions):
    best = None
    for tau in TAUS:
        correct = total = unresolved = 0
        for s in silver:
            k = key(s["source"])
            for e in stable_emotions:
                gold = s["emotions"][e]["silver_relevance"]
                if gold not in ("supports", "opposes", "mixed"):
                    continue
                p = step_b_prediction(a_idx[k], b_idx[k], e, tau)["label"]
                total += 1
                correct += p == gold
                unresolved += p == "relevant_but_unresolved"
        acc = correct / total if total else -1.0
        abst = unresolved / total if total else 1.0
        candidate = (acc, -abst, -tau, tau)
        if best is None or candidate > best:
            best = candidate
    return best[-1]


def fmt(v):
    return "—" if v is None else f"{v:.3f}"


def table_markdown(results, stable_emotions, contested):
    lines = ["agreement with independent LLM judges, not human-validated accuracy.", "",
             "| system | emotion | rel-F1 | direction | explicit recall | leakage | span F1 | abstain |",
             "|---|---|---:|---:|---:|---:|---:|---:|"]
    for system, per in results.items():
        for e in EMOTIONS:
            if e not in stable_emotions:
                lines.append(f"| {system} | {e} | definition unstable | — | — | — | — | — |")
                continue
            m = per[e]
            lines.append(f"| {system} | {e} | {fmt(m['relevance_f1'])} | {fmt(m['direction_accuracy'])} | "
                         f"{fmt(m['explicit_recall'])} | {fmt(m['leakage_rate'])} | {fmt(m['span_token_f1'])} | {fmt(m['abstention_rate'])} |")
    lines.append("")
    lines.append(f"Contested judge labels excluded from main metrics: {contested}.")
    lines.append("Leakage uses source review rating 1–2 as a transparent negative-sentiment proxy; no human sentiment labels are added.")
    return "\n".join(lines) + "\n"


def sample_records(step_a, b_by_model, judges, n=10):
    j_idx = indexed(judges)
    out = []
    for r in step_a[:n]:
        k = key(r["source"])
        out.append({
            "sentence": r["source"]["sentence"],
            "step_a": r["emotions"],
            "nli_score": {m: {e: b_by_model[m][k]["emotions"][e].get("s") for e in EMOTIONS} for m in NLI_MODELS},
            "judge_labels": {model: {e: j_idx[k]["judgments"][model]["emotions"][e]["relevance"] for e in EMOTIONS}
                             for model in j_idx[k]["judge_models"]},
        })
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--split", choices=("dev", "holdout"), default="dev")
    p.add_argument("--lexicon", default="configs/lexicon.yaml")
    p.add_argument("--allow-holdout", action="store_true")
    args = p.parse_args()
    if args.split == "holdout" and not args.allow_holdout:
        p.error("holdout is locked; use --allow-holdout only after the researcher confirms the gates")
    items, _ = load_items(args.split)
    outdir = OUT / args.split
    step_a = read_jsonl(outdir / "step_a.jsonl")
    silver = read_jsonl(outdir / "silver.jsonl")
    judges = read_jsonl(outdir / "judges.jsonl")
    judge_summary = read_json(outdir / "judge_summary.json")
    if not (len(step_a) == len(silver) == len(items)):
        raise ValueError("system/judge outputs are incomplete for this split")
    a_idx = indexed(step_a)
    b_by_model = {}
    for m in NLI_MODELS:
        rows = read_jsonl(outdir / f"step_b_{_model_slug(m)}.jsonl")
        if len(rows) != len(items):
            raise ValueError(f"Step B incomplete for {m}")
        b_by_model[m] = indexed(rows)
    stable = [e for e in EMOTIONS if e not in set(judge_summary["definition_unstable"])]
    if not stable:
        raise ValueError("all emotion definitions are unstable; no system scores are permitted")

    if args.split == "dev":
        taus = {m: choose_tau(a_idx, b_by_model[m], silver, stable) for m in NLI_MODELS}
        (outdir / "selected_tau.json").write_text(json.dumps(taus, indent=2) + "\n", encoding="utf8")
    else:
        taus = read_json(OUT / "dev/selected_tau.json")

    terms = load_lexicon(ROOT / args.lexicon)
    s0 = {key(x): {e: lexicon_predict(x["sentence"], e, terms) for e in EMOTIONS} for x in items}
    s1 = old_nli_predictions(items)
    s2 = {key(r["source"]): {e: step_a_prediction(r, e) for e in EMOTIONS} for r in step_a}
    systems = {"S0 lexicon": s0, "S1 old BART": s1, "S2 Step A": s2}
    for m in NLI_MODELS:
        systems[f"S3 {m}"] = {k: {e: step_b_prediction(a_idx[k], b_by_model[m][k], e, taus[m]) for e in EMOTIONS}
                                for k in a_idx}

    results = {name: {e: metrics_for(e, pred, silver) for e in EMOTIONS} for name, pred in systems.items()}
    contested = judge_summary["contested_count"]
    report = table_markdown(results, stable, contested)
    (outdir / "evaluation.md").write_text(report, encoding="utf8")

    aggregate = {}
    for name, per in results.items():
        aggregate[name] = {
            "direction_accuracy": aggregate_metric({e: per[e] for e in stable}, "direction_accuracy"),
            "explicit_recall": aggregate_metric({e: per[e] for e in stable}, "explicit_recall"),
            "leakage_rate": aggregate_metric({e: per[e] for e in stable}, "leakage_rate"),
        }
    nli_value = {}
    for m in NLI_MODELS:
        s3 = aggregate[f"S3 {m}"]
        s2a = aggregate["S2 Step A"]
        nli_value[m] = {
            "tau": taus[m],
            "beats_S2_direction": (s3["direction_accuracy"] is not None and s2a["direction_accuracy"] is not None and
                                    s3["direction_accuracy"] > s2a["direction_accuracy"]),
            "beats_S2_leakage": (s3["leakage_rate"] is not None and s2a["leakage_rate"] is not None and
                                  s3["leakage_rate"] < s2a["leakage_rate"]),
        }
        nli_value[m]["keep_nli"] = nli_value[m]["beats_S2_direction"] or nli_value[m]["beats_S2_leakage"]

    gates = {}
    if args.split == "dev":
        for name in ["S2 Step A", *[f"S3 {m}" for m in NLI_MODELS]]:
            a = aggregate[name]
            gates[name] = {
                "explicit_recall_ge_0_90": a["explicit_recall"] is not None and a["explicit_recall"] >= 0.90,
                "direction_accuracy_ge_0_85": a["direction_accuracy"] is not None and a["direction_accuracy"] >= 0.85,
                "leakage_le_0_10": a["leakage_rate"] is not None and a["leakage_rate"] <= 0.10,
            }
            gates[name]["all_provisional_gates"] = all(gates[name].values())

    result_obj = {
        "label": "agreement with independent LLM judges, not human-validated accuracy.",
        "stable_emotions": stable,
        "definition_unstable": judge_summary["definition_unstable"],
        "selected_tau": taus,
        "metrics": results,
        "aggregate": aggregate,
        "nli_value": nli_value,
        "provisional_dev_gates": gates,
        "contested_count": contested,
        "leakage_note": "negative sentiment is proxied by source review rating 1-2; no human sentiment labels were introduced",
    }
    (outdir / "evaluation.json").write_text(json.dumps(result_obj, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    samples = sample_records(step_a, b_by_model, judges, 10) if args.split == "dev" else []
    if samples:
        (outdir / "ten_sample_records.json").write_text(json.dumps(samples, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    print(report)
    print("SELECTED_TAU", json.dumps(taus))
    print("NLI_VALUE", json.dumps(nli_value))
    if gates:
        print("PROVISIONAL_GATES", json.dumps(gates))
        print("TEN_SAMPLE_RECORDS")
        print(json.dumps(samples, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

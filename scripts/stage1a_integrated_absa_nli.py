#!/usr/bin/env python3
"""Stage 1A integrated ABSA -> source evidence -> NLI baseline.

Fixed architecture, using previously executed artifact outputs. No generative
paraphrasing or aspect hard-filter. Claim-level NLI operates on verbatim source
sentences. Relevance is a non-destructive diagnostic, never a hard drop.
"""
import argparse
import collections
import json
from pathlib import Path

MODEL = "facebook/bart-large-mnli"
EMOTIONS = {
    "calm": ("calm", "The atmosphere of this location is calm."),
    "inviting": ("inviting", "This location has an inviting atmosphere."),
    "safe": ("physically safe", "This location feels physically safe for visitors."),
}
SOURCES = ("deberta_absa", "setfit_absa", "aos_t5")
THRESHOLD = 0.5  # diagnostic relevance flag only: not calibrated or trained


def load_jsonl(path):
    return [json.loads(x) for x in Path(path).read_text(encoding="utf-8").splitlines() if x.strip()]


def load_artifacts(root):
    base = Path(root)
    tables = {k: {r["row"]: r for r in load_jsonl(base/k/"review_cases.jsonl")} for k in SOURCES}
    common = sorted(set.intersection(*(set(x) for x in tables.values())))
    if len(common) != 20:
        raise ValueError(f"Expected 20 aligned reviews, found {len(common)}")
    for row in common:
        if len({tables[k][row]["review"] for k in SOURCES}) != 1:
            raise ValueError(f"Review mismatch on row {row}")
        if len({tables[k][row]["place_id"] for k in SOURCES}) != 1:
            raise ValueError(f"Location mismatch on row {row}")
    return tables, common


def verify_span(text, span):
    try:
        start, end = int(span["start"]), int(span["end"])
        phrase = span.get("text", span.get("aspect"))
        return 0 <= start < end <= len(text) and text[start:end] == phrase
    except (KeyError, TypeError, ValueError):
        return False


def sentences_from_source(record):
    text = record["review"]
    source = record["extraction"]["all_sentences"]
    chunks = []
    for item in source:
        if not verify_span(text, item):
            raise ValueError("Invalid sentence source offsets")
        chunks.append({"start": item["start"], "end": item["end"], "text": item["text"],
                       "aspects": [], "relations": []})
    chunks.sort(key=lambda s: s["start"])
    if not chunks:
        raise ValueError("No source sentences")
    # Require sentence segmentation to retain every non-whitespace character.
    cursor = 0
    for chunk in chunks:
        if text[cursor:chunk["start"]].strip():
            raise ValueError("Uncovered review text before source sentence")
        cursor = chunk["end"]
    if text[cursor:].strip():
        raise ValueError("Uncovered review text after final sentence")
    return chunks


def assign_annotations(review, sentences, tables, row):
    diagnostics = collections.Counter()
    for method in ("deberta_absa", "setfit_absa"):
        for a in tables[method][row]["extraction"]["aspects"]:
            if not verify_span(review, a):
                diagnostics[f"{method}_invalid_aspect"] += 1
                continue
            target = next((s for s in sentences if s["start"] <= a["start"] and a["end"] <= s["end"]), None)
            if target is None:
                diagnostics[f"{method}_unassigned_aspect"] += 1
                continue
            target["aspects"].append({"source": method, "text": review[a["start"]:a["end"]],
                                       "start": a["start"], "end": a["end"],
                                       "polarity": a.get("polarity")})
            diagnostics[f"{method}_assigned_aspect"] += 1
    for relation in tables["aos_t5"][row]["extraction"]["relations"]:
        a, o = relation["aspect"], relation["opinion"]
        if not relation.get("grounded") or not verify_span(review, a) or not verify_span(review, o):
            diagnostics["aos_invalid_relation"] += 1
            continue
        target = next((s for s in sentences if
                       s["start"] <= a["start"] and a["end"] <= s["end"] and
                       s["start"] <= o["start"] and o["end"] <= s["end"]), None)
        if target is None:
            diagnostics["aos_cross_sentence_relation"] += 1
            continue
        target["relations"].append({"source": "aos_t5", "aspect": a,
                                    "opinion": o, "polarity": relation.get("polarity"),
                                    "candidate_only": True})
        diagnostics["aos_assigned_relation"] += 1
    return dict(diagnostics)


def nli_model():
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    import torch
    torch.set_num_threads(min(4, torch.get_num_threads()))
    tokenizer = AutoTokenizer.from_pretrained(MODEL)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL).eval()
    indices = {str(name).lower(): int(i) for i, name in model.config.id2label.items()}
    if set(indices) != {"entailment", "contradiction", "neutral"}:
        raise ValueError("Unexpected NLI label map " + str(indices))

    def predict(premise, hypothesis):
        batch = tokenizer(premise, hypothesis, return_tensors="pt",
                          truncation=True, max_length=512)
        if batch["input_ids"].shape[-1] == 512:
            # Fail closed instead of silently scoring truncated evidence.
            uncut = tokenizer(premise, hypothesis, return_tensors="pt", truncation=False)
            if uncut["input_ids"].shape[-1] > 512:
                raise ValueError("Truncated NLI evidence")
        with torch.inference_mode():
            prob = torch.softmax(model(**batch).logits[0], dim=-1).tolist()
        output = {label: float(prob[i]) for label, i in indices.items()}
        return {"label": max(output, key=output.get), "probs": output}
    return predict


def relevance_hypothesis(attribute):
    return ("This statement describes something about the location "
            "that is relevant to whether it feels " + attribute + ".")


def evidence_summary(scored):
    # No forced average / final intensity: preserve support and contradiction.
    positive = [x for x in scored if x["direct_nli"]["label"] == "entailment"]
    negative = [x for x in scored if x["direct_nli"]["label"] == "contradiction"]
    return {
        "n_sentences": len(scored),
        "support_sentence_indices": [x["sentence_index"] for x in positive],
        "contradict_sentence_indices": [x["sentence_index"] for x in negative],
        "n_relevance_flagged": sum(x["relevance_flag"] for x in scored),
        "n_without_absa_aspects": sum(not x["aspects"] for x in scored),
        "conflict_in_nli_labels": bool(positive and negative),
        "no_supporting_or_contradicting_claim": not positive and not negative,
    }


def run(root, output, scorer):
    tables, rows = load_artifacts(root)
    dest = Path(output)
    dest.mkdir(parents=True, exist_ok=True)
    records = []
    with (dest/"review_evidence.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            record = tables["deberta_absa"][row]
            text = record["review"]
            sentences = sentences_from_source(record)
            diagnostics = assign_annotations(text, sentences, tables, row)
            for emotion, (attribute, hypothesis) in EMOTIONS.items():
                claims = []
                for i, sentence in enumerate(sentences):
                    claim = dict(sentence)
                    claim["sentence_index"] = i
                    claim["direct_nli"] = scorer(sentence["text"], hypothesis)
                    claim["relevance_nli"] = scorer(sentence["text"], relevance_hypothesis(attribute))
                    claim["relevance_flag"] = (
                        claim["relevance_nli"]["probs"]["entailment"] >= THRESHOLD)
                    claims.append(claim)
                result = {
                    "row": row, "place_id": record["place_id"], "review": text,
                    "emotion": emotion, "hypothesis": hypothesis,
                    "full_review_nli": scorer(text, hypothesis),
                    "claims": claims, "evidence_summary": evidence_summary(claims),
                    "extraction_diagnostics": diagnostics,
                }
                records.append(result)
                handle.write(json.dumps(result, ensure_ascii=False)+"\n")
                handle.flush()
            print(f"Integrated {row}: {len(sentences)} sentences", flush=True)
    summary = {
        "method": "ABSA source annotations + original clause NLI + non-destructive relevance",
        "n_reviews": len(rows), "n_review_emotions": len(records),
        "n_sentences": sum(len(x["claims"]) for x in records)//len(EMOTIONS),
        "n_nli_inferences": sum(1+2*len(x["claims"]) for x in records),
        "n_emotion_conflict_cases": {emotion: sum(
            x["evidence_summary"]["conflict_in_nli_labels"]
            for x in records if x["emotion"]==emotion) for emotion in EMOTIONS},
        "n_cases_with_unmatched_absa_sentences": sum(
            x["evidence_summary"]["n_without_absa_aspects"]>0 for x in records)//len(EMOTIONS),
        "caveats": [
            "All statements remain in output; no hard ABSA or relevance filtering.",
            "AOS/ABSA extracted information is metadata, not asserted in NLI premise.",
            "NLI entailment/contradiction flags are model outputs, not ground-truth emotional evidence.",
            "No final intensity score or positive/negative aggregation is asserted.",
            "Fixed 20-review exploratory subset is not independent research validation.",
            "Sentence boundaries may include multiple clauses and indirect attribution.",
            "BART generic NLI and metarelevance still need domain-specific reliability evaluation.",
        ],
    }
    (dest/"summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", default="reports/stage1a_integrated_inputs")
    parser.add_argument("--output", default="reports/stage1a_integrated")
    args = parser.parse_args()
    summary = run(args.inputs, args.output, nli_model())
    print(json.dumps({k:summary[k] for k in ("n_reviews","n_review_emotions","n_nli_inferences")},
                     indent=2), flush=True)


if __name__ == "__main__":
    main()

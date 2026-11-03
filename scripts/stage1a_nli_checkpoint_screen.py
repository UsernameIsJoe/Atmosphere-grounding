#!/usr/bin/env python3
"""Stage 1A zero-shot NLI checkpoint screening; no human-rated ground truth.

Use a frozen 50-review screening sample covering all locations and BART
high-disagreement examples. Evaluate the identical versioned 60 hypotheses
for each checkpoint. Preserve native label spaces (especially two-class
entailment/not_entailment); never equate not-entailment with contradiction.
"""
import argparse
import collections
import hashlib
import json
import math
import pathlib
import statistics
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
MODEL_IDS = {
    "deberta": "MoritzLaurer/deberta-v3-large-zeroshot-v2.0",
    "modernbert": "MoritzLaurer/ModernBERT-large-zeroshot-v2.0",
    "bart": "facebook/bart-large-mnli",
}
# Fixed before new-checkpoint results. Previously observed disagreement rows.
BART_DIAGNOSTIC_ROWS = (55, 81, 113, 139, 181, 187, 123)


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def select_rows(reviews, target=50):
    """One median-word-count review per place, plus preset BART disagreement cases.
    Add length-diverse rows only if needed. Deterministic, no model outputs used.
    """
    grouped = collections.defaultdict(list)
    for idx, record in enumerate(reviews):
        grouped[record["place_id"]].append(idx)
    chosen = set()
    for place in sorted(grouped):
        indices = grouped[place]
        lengths = sorted(len(reviews[i]["text"].split()) for i in indices)
        median = statistics.median(lengths)
        representative = min(indices, key=lambda i: (abs(len(reviews[i]["text"].split()) - median), i))
        chosen.add(representative)
    for i in BART_DIAGNOSTIC_ROWS:
        if i < len(reviews):
            chosen.add(i)
    if len(chosen) > target:
        raise ValueError("Target too small to fit all place representatives and BART diagnostic rows")
    if len(chosen) < target:
        candidates = [i for i in range(len(reviews)) if i not in chosen]
        candidates.sort(key=lambda i: (-len(reviews[i]["text"].split()), i))
        chosen.update(candidates[:target-len(chosen)])
    if len(chosen) != min(target, len(reviews)):
        raise RuntimeError("Unexpected screening sample size")
    return sorted(chosen)


def label_space(model):
    mapping = {int(i): str(label).lower().replace("-", "_").replace(" ", "_")
               for i, label in model.config.id2label.items()}
    vals = set(mapping.values())
    if vals == {"entailment", "not_entailment"}:
        return mapping, "binary"
    if vals == {"entailment", "contradiction", "neutral"}:
        return mapping, "three_way"
    raise ValueError(f"Unsupported checkpoint labels: {mapping}. Do not infer label meanings.")


def forward_pairs(tok, model, premise, hypotheses, torch, mapping, max_length, batch_size=8):
    outputs = []
    total = 0
    truncated = 0
    for start in range(0, len(hypotheses), batch_size):
        group = hypotheses[start:start+batch_size]
        original = tok([premise]*len(group), group, truncation=False, add_special_tokens=True)
        truncated += sum(len(ids) > max_length for ids in original["input_ids"])
        total += len(group)
        tokens = tok([premise]*len(group), group, padding=True, truncation=True,
                     max_length=max_length, return_tensors="pt")
        with torch.inference_mode():
            logits = model(**tokens).logits
        for vector in torch.softmax(logits, dim=-1).tolist():
            probs = {mapping[i]: float(p) for i, p in enumerate(vector)}
            outputs.append({"probs": probs, "label": max(probs, key=probs.get)})
    return outputs, truncated, total


def summarize(rows, registry, space):
    result = {}
    for emotion in sorted(set(c["emotion"] for c in registry)):
        cores = [c["id"] for c in registry if c["emotion"] == emotion and c["role"] == "core"]
        observations = [r["emotions"][emotion] for r in rows]
        per_review_agreement = []
        ranges = []
        loo = []
        distributions = []
        for preds in observations:
            vals = [preds[cid]["probs"]["entailment"] for cid in cores]
            classifications = [preds[cid]["label"] for cid in cores]
            per_review_agreement.append(len(set(classifications)) == 1)
            ranges.append(max(vals)-min(vals))
            mean = statistics.mean(vals)
            # Binary: threshold only for internal robustness, not classification truth.
            # Three-way: full-class mean to establish label sensitivity.
            if space == "binary":
                base = mean >= .5
                loo.append(all((statistics.mean(vals[:i]+vals[i+1:]) >= .5) == base
                               for i in range(len(vals))))
            else:
                classes = ("entailment","neutral","contradiction")
                avg = {k: statistics.mean(preds[cid]["probs"][k] for cid in cores) for k in classes}
                base = max(avg, key=avg.get)
                loo.append(all(
                    max({k: statistics.mean(preds[cid]["probs"][k] for j,cid in enumerate(cores) if j != i)
                         for k in classes}, key=lambda k:
                        statistics.mean(preds[cid]["probs"][k] for j,cid in enumerate(cores) if j != i)) == base
                    for i in range(len(cores))))
            distributions.append(dict(collections.Counter(classifications)))
        pairwise = {}
        for i, ca in enumerate(cores):
            for cb in cores[i+1:]:
                pairwise[ca+"|"+cb] = {
                    "label_agreement": round(sum(o[ca]["label"] == o[cb]["label"] for o in observations)/len(observations), 4),
                    "mean_abs_entailment_difference": round(statistics.mean(
                        abs(o[ca]["probs"]["entailment"]-o[cb]["probs"]["entailment"]) for o in observations), 4),
                }
        result[emotion] = {
            "n":len(observations),
            "core_unanimity":round(statistics.mean(per_review_agreement),4),
            "mean_entailment_range":round(statistics.mean(ranges),4),
            "leave_one_core_out_stability":round(statistics.mean(loo),4),
            "core_prediction_label_counts":dict(collections.Counter(
                o[cid]["label"] for o in observations for cid in cores)),
            "core_pairwise": pairwise,
            "top_disagreement_rows":[{"row":row["row"],"range":round(span,4)}
                                     for row,span in sorted(zip(rows,ranges),key=lambda p:p[1],reverse=True)[:10]],
        }
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", choices=MODEL_IDS, required=True)
    ap.add_argument("--output", default=None)
    ap.add_argument("--limit", type=int, default=50)
    ap.add_argument("--batch-size", type=int, default=8)
    ap.add_argument("--max-length", type=int, default=512)
    args = ap.parse_args()
    if args.limit < 1 or args.batch_size < 1 or args.max_length < 8:
        raise ValueError("Invalid screening configuration")
    import torch
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    torch.set_num_threads(min(4, torch.get_num_threads()))
    registry_path = ROOT / "configs/stage1a_hypothesis_vocabulary_draft.json"
    registry_bytes = registry_path.read_bytes()
    candidates = json.loads(registry_bytes)["candidates"]
    reviews = read_jsonl(ROOT / "data/processed/reviews.jsonl")
    selected = select_rows(reviews, args.limit)
    dest = ROOT / (args.output or f"reports/stage1a_nli_screen_{args.model}")
    dest.mkdir(parents=True, exist_ok=True)
    manifest = {
        "model": MODEL_IDS[args.model], "model_alias":args.model,
        "registry_sha256": hashlib.sha256(registry_bytes).hexdigest(),
        "selected_rows":selected,
        "selection_policy":"One median-length review per location plus 7 pre-registered BART disagreement rows; length-diverse fill",
        "review_count":len(selected),
        "place_count":len({reviews[i]["place_id"] for i in selected}),
        "candidate_count":len(candidates),
        "no_ground_truth":True,
    }
    (dest/"sample_manifest.json").write_text(json.dumps(manifest,indent=2), encoding="utf-8")
    tok = AutoTokenizer.from_pretrained(MODEL_IDS[args.model])
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_IDS[args.model]).eval()
    labels, space = label_space(model)
    manifest["native_label_space"] = space
    manifest["native_id2label"] = labels
    (dest/"sample_manifest.json").write_text(json.dumps(manifest,indent=2), encoding="utf-8")
    results=[]
    start_time=time.perf_counter()
    truncated=0
    evaluated=0
    outfile=dest/"review_cases.jsonl"
    with outfile.open("w",encoding="utf-8") as handle:
        for n,idx in enumerate(selected,1):
            r=reviews[idx]
            rec={"row":idx, "place_id":r["place_id"], "review_index":r["review_index"],
                 "review":r["text"], "emotions":{}}
            for emotion in sorted(set(x["emotion"] for x in candidates)):
                subset=[x for x in candidates if x["emotion"]==emotion]
                preds,t,num=forward_pairs(tok,model,r["text"],[x["text"] for x in subset],
                                          torch,labels,args.max_length,args.batch_size)
                truncated+=t
                evaluated+=num
                rec["emotions"][emotion]={x["id"]:p for x,p in zip(subset,preds)}
            results.append(rec)
            handle.write(json.dumps(rec,ensure_ascii=False)+"\n")
            handle.flush()
            if n%5==0: print(f"Completed {n}/{len(selected)} reviews", flush=True)
    summary={
        **manifest,
        "pairs_evaluated": evaluated,
        "potentially_truncated_pairs": truncated,
        "elapsed_seconds":round(time.perf_counter()-start_time,1),
        "by_emotion":summarize(results,candidates,space),
        "limitations":[
            "No human-rated ground truth, so no accuracy, correctness or calibration inferred.",
            "Binary not_entailment combines contradiction and neutral; it is NOT either class.",
            "Raw entailment softmax values across checkpoints are not automatically calibrated or directly comparable.",
            "Screening sample intentionally includes prior BART-disagreement cases and thus is not a representative random sample.",
            "Core family semantic equivalence is provisional; different interpretations may be legitimate.",
            "Review input pairs longer than token limit are truncated and counted.",
        ],
    }
    (dest/"summary.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")
    print(json.dumps({"model":summary["model"],"labels":space,"reviews":len(selected),
                      "places":manifest["place_count"],"pairs":evaluated,
                      "seconds":summary["elapsed_seconds"],
                      "potentially_truncated_pairs":truncated,
                      "metrics":{e:{"unanimity":v["core_unanimity"],"mean_range":v["mean_entailment_range"]}
                                 for e,v in summary["by_emotion"].items()}},indent=2),flush=True)


if __name__=="__main__":
    main()

#!/usr/bin/env python3
"""Stage 1A M2 screening: Does structured ABSA evidence change BART NLI?

Input artifacts are already-executed M1 AOS/dependency (20 reviews) and
earlier 50-review DeBERTa/SetFitABSA screens. Full original reviews remain
in EVERY NLI premise; do not treat extracted claims as established truths.
No new labels, fine-tuning, or accuracy claims.
"""
import argparse
import collections
import json
import pathlib
import random
import statistics
import time

EMOTIONS = {
    "calm": "The atmosphere of this location is calm.",
    "inviting": "This location has an inviting atmosphere.",
    "safe": "This location feels physically safe for visitors.",
}
SOURCES = ("aos_t5", "dependency", "deberta_absa", "setfit_absa")
CONDITIONS = ("full", "duplicate", "aos_t5", "dependency", "deberta_absa",
              "setfit_absa", "aos_t5_swapped", "dependency_swapped")
MODEL = "facebook/bart-large-mnli"


def load_jsonl(path):
    return [json.loads(x) for x in pathlib.Path(path).read_text(encoding="utf-8").splitlines() if x.strip()]


def read_sources(folder):
    root = pathlib.Path(folder)
    inputs = {
        key: {r["row"]: r for r in load_jsonl(root/key/"review_cases.jsonl")}
        for key in SOURCES
    }
    anchor = inputs["aos_t5"]
    if len(anchor) != 20 or sorted(anchor) != sorted(inputs["dependency"]):
        raise ValueError("M1 sample must be 20 matched rows")
    if any(row not in inputs["deberta_absa"] or row not in inputs["setfit_absa"]
           for row in anchor):
        raise ValueError("M1 rows must be contained within the previous ABSA-50 sample")
    for row in anchor:
        texts = {inputs[k][row]["review"] for k in SOURCES}
        if len(texts) != 1:
            raise ValueError(f"Source review content differs at row {row}")
    return inputs


def verified_relations(record):
    text = record["review"]
    result = []
    for relation in record["extraction"]["relations"]:
        if not relation.get("grounded"):
            continue
        a, o = relation["aspect"], relation["opinion"]
        if any(not isinstance(x.get("start"), int) or not isinstance(x.get("end"), int)
               or text[x["start"]:x["end"]] != x["text"] for x in (a,o)):
            continue
        result.append((a["text"],o["text"],a["start"],o["start"]))
    return result


def verified_aspects(record):
    text = record["review"]
    found = []
    for a in record["extraction"]["aspects"]:
        if not isinstance(a.get("start"),int) or not isinstance(a.get("end"),int):
            continue
        if text[a["start"]:a["end"]] == a["aspect"]:
            found.append((a["aspect"],a["start"]))
    return found


def annotations(record, kind, swapped=False):
    if kind in ("aos_t5","dependency"):
        pairs = verified_relations(record)[:10]
        if swapped and len(pairs) > 1:
            # Fixed, deterministic mismatched pairing: rotate opinion terms.
            opinions = [p[1] for p in pairs]
            pairs = [(p[0],opinions[(i+1)%len(pairs)],p[2],p[3])
                     for i,p in enumerate(pairs)]
        # Separate metadata from the review: these are machine predictions.
        return [f"aspect={a!r}; described_as={o!r}" for a,o,_,_ in pairs]
    return [f"aspect={a!r}" for a,_ in verified_aspects(record)[:10]]


def construct_premise(review, lines=None, duplicate=False):
    if duplicate:
        return "Original review:\n" + review + "\nRepeated review text:\n" + review
    if not lines:
        return review
    return ("Original review:\n" + review +
            "\nMachine-extracted candidate observations (unverified interpretations, "
            "not additional factual evidence):\n" + "\n".join(lines))


def premised_conditions(inputs, row):
    text = inputs["aos_t5"][row]["review"]
    payload = {"full":text,"duplicate":construct_premise(text,duplicate=True)}
    meta = {}
    for name in SOURCES:
        lines = annotations(inputs[name][row],name)
        payload[name] = construct_premise(text,lines)
        meta[name] = {"n_annotations":len(lines),"annotations":lines}
        if name in ("aos_t5","dependency"):
            swapped = annotations(inputs[name][row],name,swapped=True)
            # If no swap is possible, keep original and record ineligible status.
            key = name+"_swapped"
            payload[key] = construct_premise(text,swapped)
            meta[key] = {"eligible":len(lines)>1,"n_annotations":len(swapped),
                         "annotations":swapped}
    return payload,meta


def evaluate(tok,model,torch,premise,hypothesis):
    inputs=tok(premise,hypothesis,return_tensors="pt",truncation=True,max_length=512)
    with torch.inference_mode():
        scores=torch.softmax(model(**inputs).logits[0],dim=-1).tolist()
    labels={str(model.config.id2label[i]).lower():float(p) for i,p in enumerate(scores)}
    if set(labels)!={"entailment","neutral","contradiction"}:
        raise ValueError(f"Expected 3-way NLI checkpoint; got {labels}")
    return {"probs":labels,"label":max(labels,key=labels.get)}


def summarize(records):
    by_emotion={}
    for emotion in EMOTIONS:
        subset=[r for r in records if r["emotion"]==emotion]
        root=[r["outputs"]["full"] for r in subset]
        stats={}
        for c in CONDITIONS:
            values=[r["outputs"][c] for r in subset]
            stats[c]={
                "changed_label_from_full":sum(a["label"]!=b["label"] for a,b in zip(root,values)),
                "mean_abs_entailment_difference":round(statistics.mean(
                    abs(a["probs"]["entailment"]-b["probs"]["entailment"])
                    for a,b in zip(root,values)),4),
                "label_counts":dict(collections.Counter(v["label"] for v in values)),
                "identical_premise_to_full":sum(r["premises"][c]==r["premises"]["full"] for r in subset),
            }
        by_emotion[emotion]=stats
    return by_emotion


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--inputs",default="reports/m2_inputs")
    p.add_argument("--output",default="reports/stage1a_m2_structured")
    args=p.parse_args()
    sources=read_sources(args.inputs)
    dest=pathlib.Path(args.output)
    dest.mkdir(parents=True,exist_ok=True)
    from transformers import AutoTokenizer,AutoModelForSequenceClassification
    import torch
    torch.set_num_threads(min(4,torch.get_num_threads()))
    tok=AutoTokenizer.from_pretrained(MODEL)
    model=AutoModelForSequenceClassification.from_pretrained(MODEL).eval()
    start=time.monotonic()
    results=[]
    with (dest/"review_cases.jsonl").open("w",encoding="utf-8") as handle:
        for idx,row in enumerate(sorted(sources["aos_t5"])):
            premises,metadata=premised_conditions(sources,row)
            for emotion,hypothesis in EMOTIONS.items():
                results_row={"row":row,"place_id":sources["aos_t5"][row]["place_id"],
                             "review":sources["aos_t5"][row]["review"],"emotion":emotion,
                             "hypothesis":hypothesis,"premises":premises,"metadata":metadata,
                             "outputs":{c:evaluate(tok,model,torch,premises[c],hypothesis)
                                        for c in CONDITIONS}}
                results.append(results_row)
                handle.write(json.dumps(results_row,ensure_ascii=False)+"\n")
                handle.flush()
            print(f"Completed {idx+1}/20 reviews",flush=True)
    summary={
        "n_reviews":len(sources["aos_t5"]),"n_review_emotion_pairs":len(results),
        "n_inferences":len(results)*len(CONDITIONS),
        "nli_checkpoint":MODEL,
        "hypotheses":EMOTIONS,
        "conditions":CONDITIONS,
        "seconds":round(time.monotonic()-start,2),
        "by_emotion":summarize(results),
        "caveats":[
            "Changing the NLI output is not evidence of improving its correctness.",
            "The original review is present in every condition; annotation strings are unverified predictions.",
            "Swapped controls are informative only where >=2 grounded relations exist; otherwise unchanged.",
            "AOS relation coverage is sparse; previous ABSA methods do not supply opinion links.",
            "Repeated-text control tests sensitivity to extra tokens, not perfectly token-length-matched annotations.",
            "The fixed hypotheses were selected for a diagnostic test, not validated as atmosphere truth.",
            "No independent annotations, no emotion prediction accuracy, no final model selection.",
        ],
    }
    (dest/"summary.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")
    print(json.dumps({"n_review_emotion_pairs":len(results),"n_inferences":summary["n_inferences"],
                      "seconds":summary["seconds"]},indent=2),flush=True)


if __name__=="__main__":
    main()

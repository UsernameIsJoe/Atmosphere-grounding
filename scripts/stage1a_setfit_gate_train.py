#!/usr/bin/env python3
"""Train SetFit on 75 user-labeled real excerpts, evaluate once on 25 held-out places.

IMPORTANT: no test data in train, no test threshold tuning, no label rewriting.
Positive class = user R (potentially atmospheric); negative = user I.
Thresholds .20 and .50 are PREDECLARED, not chosen after test inspection.
"""
from __future__ import annotations
import argparse
import collections
import json
import random
from pathlib import Path
from stage1a_setfit_audit import load_verified, summarize

ROOT=Path(__file__).resolve().parents[1]
DEFAULT_BASE="BAAI/bge-small-en-v1.5"
THRESHOLDS=(0.20,0.50)


def metrics(rows, threshold):
    tp=sum(x["label"]=="R" and x["relevance_score"]>=threshold for x in rows)
    fn=sum(x["label"]=="R" and x["relevance_score"]<threshold for x in rows)
    tn=sum(x["label"]=="I" and x["relevance_score"]<threshold for x in rows)
    fp=sum(x["label"]=="I" and x["relevance_score"]>=threshold for x in rows)
    return {
        "threshold":threshold,"true_positive_relevant":tp,"false_negative_relevant":fn,
        "true_negative_irrelevant":tn,"false_positive_irrelevant":fp,
        "relevant_recall":tp/(tp+fn) if tp+fn else None,
        "irrelevant_rejection_rate":tn/(tn+fp) if tn+fp else None,
        "irrelevant_retention_rate":fp/(tn+fp) if tn+fp else None,
        "relevant_false_rejection_rate":fn/(tp+fn) if tp+fn else None,
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--model",default=DEFAULT_BASE)
    p.add_argument("--out",type=Path,default=ROOT/"reports/stage1a_setfit_gate")
    p.add_argument("--audit-only",action="store_true")
    p.add_argument("--epochs",type=int,default=1)
    p.add_argument("--num-iterations",type=int,default=10)
    a=p.parse_args()
    train,test=load_verified()
    report=summarize(train,test)
    print("DATASET_AUDIT "+json.dumps(report),flush=True)
    if a.audit_only:
        return
    import numpy as np
    import torch
    from datasets import Dataset
    from setfit import SetFitModel, Trainer, TrainingArguments
    torch.set_num_threads(2)
    torch.manual_seed(42); random.seed(42); np.random.seed(42)
    dataset=Dataset.from_dict({
        "text":[x["text"] for x in train],
        "label":[int(x["label"]=="R") for x in train],
    })
    model=SetFitModel.from_pretrained(a.model,labels=["irrelevant","relevant"])
    args=TrainingArguments(
        batch_size=8,
        num_epochs=a.epochs,
        num_iterations=a.num_iterations,
        seed=42,
        report_to="none",
    )
    trainer=Trainer(model=model,args=args,train_dataset=dataset)
    trainer.train()
    # Only after training is completely finished, touch held-out text.
    probabilities=np.asarray(model.predict_proba([x["text"] for x in test],as_numpy=True))
    if probabilities.shape != (25,2):
        raise ValueError(f"Wrong probabilities: {probabilities.shape}")
    if not np.isfinite(probabilities).all():
        raise ValueError("Nonfinite predictions")
    if not np.allclose(probabilities.sum(axis=1),1.0,atol=1e-3):
        raise ValueError("Probabilities do not sum to 1")
    # Explicit integer-class mapping from 0=I to 1=R; if a class-aware head
    # is present, verify that its class order is 0,1 (not alphabetic strings).
    head=getattr(model,"model_head",None)
    classes=getattr(head,"classes_",None)
    if classes is not None and list(classes)!=[0,1]:
        raise ValueError(f"Unexpected probability class order: {classes}")
    rows=[
        {**x,"relevance_score":round(float(probs[1]),7),
         "irrelevant_score":round(float(probs[0]),7)}
        for x,probs in zip(test,probabilities)
    ]
    scores=sorted(rows,key=lambda x:x["relevance_score"])
    results={
        "status":"completed",
        "experiment":"Stage1A SetFit frozen training vs place-grouped untouched heldout",
        "base_model":a.model,
        "train":{"epoch":a.epochs,"num_iterations":a.num_iterations,"seed":42},
        "data":report,"score_interpretation":"SetFit class score; not independently calibrated relevance probability.",
        "thresholds_frozen_before_testing":list(THRESHOLDS),
        "threshold_metrics":[metrics(rows,t) for t in THRESHOLDS],
        "chance_baseline_always_relevant":{
            "relevant_recall":1.0,
            "irrelevant_rejection_rate":0.0,
            "number_total":len(test),
        },
        "all_false_rejections_at_threshold_020":[x for x in rows if x["label"]=="R" and x["relevance_score"]<.20],
        "all_false_rejections_at_threshold_050":[x for x in rows if x["label"]=="R" and x["relevance_score"]<.50],
        "caution":"25 selected held-out excerpts include only five irrelevant cases. No threshold selection from test; evaluation uncertainty is high.",
    }
    a.out.mkdir(parents=True,exist_ok=True)
    (a.out/"heldout_predictions.jsonl").write_text(
        "".join(json.dumps(x,ensure_ascii=False)+"\n" for x in rows),encoding="utf8")
    (a.out/"evaluation.json").write_text(
        json.dumps(results,indent=2,ensure_ascii=False)+"\n",encoding="utf8")
    print("RESULTS "+json.dumps({k:v for k,v in results.items() if not k.startswith("all_false")}),flush=True)
    for x in scores:
        print("PRED "+json.dumps({"id":x["id"],"gold_label":x["label"],
                                  "score":x["relevance_score"],"text":x["text"]},
                                  ensure_ascii=False),flush=True)


if __name__=="__main__":
    main()

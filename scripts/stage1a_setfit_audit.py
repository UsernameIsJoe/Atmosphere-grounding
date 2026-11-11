#!/usr/bin/env python3
"""Audit user-authored SetFit labels against original corpus, strictly no relabeling.

All 100 are source-exact excerpts. Training and held-out sets are disjoint by
PLACE, not merely by review. Fails closed on any mismatch or duplicate.
"""
import collections
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LABEL_DIR = ROOT / "data/evaluation"
REVIEW_PATH = ROOT / "data/processed/reviews.jsonl"


def load_verified():
    all_labels = []
    for batch in range(1, 6):
        path = LABEL_DIR / f"setfit_atmosphere_gate_user_labels_batch{batch}.jsonl"
        data = [json.loads(line) for line in path.read_text(encoding="utf8").splitlines() if line.strip()]
        if len(data) != 20 or [x["id"] for x in data] != [f"B{batch}-{n:02d}" for n in range(1,21)]:
            raise ValueError(f"Wrong batch ID count/order: {path}")
        all_labels.extend(data)
    if len(all_labels) != 100:
        raise ValueError("100 annotations required")
    corpus = {}
    for line in REVIEW_PATH.read_text(encoding="utf8").splitlines():
        row = json.loads(line)
        k=(row["place_id"],row["review_index"])
        if k in corpus:
            raise ValueError("Duplicated review source keys")
        corpus[k] = row["text"]
    seen = set()
    train, test = [], []
    for x in all_labels:
        if x["label"] not in {"R","I"}:
            raise ValueError(f"Unreviewed label in {x['id']}")
        if x.get("source") != "data/processed/reviews.jsonl" or x.get("annotator") != "user":
            raise ValueError("Missing provenance")
        key=(x["place_id"],x["review_index"])
        if key not in corpus or x["text"] not in corpus[key]:
            raise ValueError(f"Text not an EXACT contiguous substring of original review: {x['id']}")
        unique=key+(x["text"],)
        if unique in seen:
            raise ValueError(f"Duplicate excerpt: {x['id']}")
        seen.add(unique)
        if x["split"] == "train":
            train.append(x)
        elif x["split"] == "test":
            test.append(x)
        else:
            raise ValueError("Invalid split")
    if len(train) != 75 or len(test) != 25:
        raise ValueError(f"Expected 75/25, got {len(train)}/{len(test)}")
    train_places={x["place_id"] for x in train}
    test_places={x["place_id"] for x in test}
    if train_places & test_places:
        raise ValueError("Train/test place leakage")
    if len(train_places)!=12 or len(test_places)!=5:
        raise ValueError("Unexpected number of distinct places")
    for split in (train,test):
        if {x["label"] for x in split}!={"R","I"}:
            raise ValueError("Both classes required in each split")
    return train,test


def summarize(train,test):
    return {
        "total":len(train)+len(test),
        "train":len(train),"test":len(test),
        "train_places":len({x["place_id"] for x in train}),
        "test_places":len({x["place_id"] for x in test}),
        "train_labels":dict(collections.Counter(x["label"] for x in train)),
        "test_labels":dict(collections.Counter(x["label"] for x in test)),
        "source_exact":True,"duplicates":0,"place_overlap":0,
        "annotations_modified":False,
    }


if __name__ == "__main__":
    train,test=load_verified()
    print("DATASET_AUDIT",json.dumps(summarize(train,test)),flush=True)

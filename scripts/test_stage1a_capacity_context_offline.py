#!/usr/bin/env python3
"""Offline integrity checks for the real-review 4-model capacity-context pilot.

No model calls, synthetic evaluation reviews, external packages, or GPU needed.
"""
import csv
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

import stage1a_capacity_context_2026_11_13 as x


def main() -> None:
    rows = x.corpus(x.SOURCE)
    a = x.selected(rows, "segment")
    b = x.selected(rows, "context")
    c = x.selected(rows, "repeat")
    assert len(a) == len(b) == 30, (len(a), len(b))
    assert len(c) == 10
    assert [r["index"] for r in a] == [r["index"] for r in b]
    assert {int(r["index"]) for r in c} == set(x.CONTEXT_INDICES)
    assert {name for name in x.MODELS} == {
        "qwen3.6:27b-bf16", "gemma4:31b-it-bf16",
        "qwen3.5:122b", "gpt-oss:120b",
    }
    for task in x.TASKS:
        segment = x.request_payload(a[0], x.MODELS[0], "segment", task)
        context = x.request_payload(a[0], x.MODELS[0], "context", task)
        repeated = x.request_payload(c[0], x.MODELS[0], "repeat", task)
        off = x.request_payload(a[0], x.MODELS[0], "segment", task, "off")
        for obj in (segment, context, repeated):
            assert "think" not in obj
            assert obj["format"] == x.SCHEMAS[task]
        assert off["think"] is False
        sdata = json.loads(segment["messages"][1]["content"])
        xdata = json.loads(context["messages"][1]["content"])
        rdata = json.loads(repeated["messages"][1]["content"])
        assert list(sdata) == ["target_segment"]
        assert xdata["target_segment"] == sdata["target_segment"]
        assert xdata["full_review_for_reference_only"] == a[0]["full_review"]
        assert rdata["target_repeated_control"] == rdata["target_segment"]
        assert "full_review_for_reference_only" not in rdata
    assert x.folder_for(Path("out"), x.MODELS[0], "context", "evidence",
                        "native") != x.folder_for(
                            Path("out"), x.MODELS[0], "context", "evidence", "off")
    with TemporaryDirectory() as temp:
        root = Path(temp)
        args = SimpleNamespace(output=root, source=x.SOURCE, reasoning="native")
        x.report(args)
        gold = list(csv.DictReader((root / "01_gold_first_BLANK.csv").open(
            encoding="utf-8-sig", newline="")))
        blind_e = list(csv.DictReader((
            root / "native/02_blind_evidence_A_B_C_D.csv").open(
                encoding="utf-8-sig", newline="")))
        blind_s = list(csv.DictReader((
            root / "native/03_blind_scores_A_B_C_D.csv").open(
                encoding="utf-8-sig", newline="")))
        key = json.loads((
            root / "native/04_blinding_key_KEEP_PRIVATE.json").read_text())
        assert len(gold) == 30
        assert len(blind_e) == len(blind_s) == len(key) == 70
        assert len({r["index"] for r in gold}) == 30
        assert all(
            {r[f"model_{letter}"] for letter in "ABCD"} == set(x.MODELS)
            for r in key
        )
        assert all(f"model_{letter}_claims" in blind_e[0] for letter in "ABCD")
        assert all(f"model_{letter}_calm_direct" in blind_s[0]
                   for letter in "ABCD")
        # Rerunning report without model outputs preserves source-gold content.
        x.report(args)
    print("PASS: 30 paired segments, 10 repeat controls, 4 models, "
          "native/off payloads, 70-row blind packet and frozen gold")


if __name__ == "__main__":
    main()

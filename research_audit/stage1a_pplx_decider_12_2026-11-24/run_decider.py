#!/usr/bin/env python3
"""Frozen 12-review calm diagnostic using the official PPLX-Decider v1.2 reference path."""
import gc
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parent
CHECKPOINT = Path(os.environ.get("DECIDER_CHECKPOINT", "/workspace/pplx_decider_checkpoint"))
STATES = ("neither", "support_only", "opposition_only", "both")


def write(name, obj):
    (ROOT / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n")


def append(name, obj):
    with (ROOT / name).open("a") as f:
        f.write(json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "\n")


def main():
    started = time.time()
    sys.path.insert(0, str(CHECKPOINT / "source/src"))
    import numpy as np
    import torch
    from pplx_decider import Decider
    from pplx_decider.protocol import answer

    random.seed(42)
    np.random.seed(42)
    torch.manual_seed(42)
    torch.cuda.manual_seed_all(42)
    requests = [json.loads(l) for l in (ROOT / "requests.jsonl").read_text().splitlines()]
    assert len(requests) == 48
    config = json.loads((CHECKPOINT / "decision_config.json").read_text())
    model_manifest = json.loads((ROOT / "model_source_manifest.json").read_text())
    runtime = {
        "start_time": started, "checkpoint": str(CHECKPOINT),
        "model_repo": model_manifest["repo"], "model_revision": model_manifest["revision"],
        "torch": torch.__version__, "cuda_runtime": torch.version.cuda,
        "gpu_name": torch.cuda.get_device_name(0),
        "gpu": subprocess.check_output(["nvidia-smi", "--query-gpu=name,driver_version,memory.total", "--format=csv,noheader"], text=True).strip(),
        "package_versions": {k: importlib.metadata.version(k) for k in ["torch", "torchvision", "transformers", "safetensors", "pillow", "huggingface-hub"]},
        "saved_temperature": config["temperature"], "fast": False, "batch_size": 1,
        "max_length": 8192, "seed": 42,
        "deterministic_algorithms": torch.are_deterministic_algorithms_enabled(),
        "qualification": "Official reference path; use_cache=False is enforced by model source. No FP8, quantization, packing or compilation. Native criterion reordering jointly changes positions and internal answer codes.",
    }
    write("runtime.json", runtime)
    load_start = time.monotonic()
    decider = Decider.from_pretrained(CHECKPOINT, device="cuda", fast=False, max_length=8192, batch_tokens=8192)
    torch.cuda.synchronize()
    runtime["load_seconds"] = time.monotonic() - load_start
    assert abs(decider.temperature - float(config["temperature"])) < 1e-12
    encoded = []
    for item in requests:
        plan = decider.encoder.plan(item["request"], 8192)
        assert len(plan) == 1 and len(plan[0].keys) == 1
        encoded.append({"case_id": item["case_id"], "order_id": item["order_id"],
                        "request_sha256": item["request_sha256"],
                        "rendered_prompt": decider.encoder.text(item["request"]),
                        "input_token_ids": plan[0].input_ids.tolist(),
                        "readout_markers": plan[0].markers.tolist(), "input_tokens": plan[0].length})
    write("rendered_requests.json", encoded)
    runtime["min_input_tokens"] = min(x["input_tokens"] for x in encoded)
    runtime["max_input_tokens"] = max(x["input_tokens"] for x in encoded)
    write("runtime.json", runtime)
    print("MODEL_LOADED", runtime["load_seconds"], "TOKENS", runtime["min_input_tokens"], runtime["max_input_tokens"], flush=True)

    # A normal official decide call is checked against the public logits API plus
    # the exact published float32 softmax and answer formatter, twelve anchors.
    # Every main readout records raw logits and native probabilities from one
    # model forward pass; no second generation/readout is substituted.
    def readout(item, phase, repeat, native_check=False):
        t0 = time.monotonic()
        req = item["request"]
        raw = decider.logits([req])[0]["calm"]
        assert len(raw) == 4 and all(np.isfinite(raw))
        z = torch.tensor(raw, dtype=torch.float32)
        native = answer(req["questions"]["calm"], (z / decider.temperature).softmax(-1).tolist())
        original_scale = answer(req["questions"]["calm"], z.softmax(-1).tolist())
        q = native["probabilities"]
        assert set(q) == set(STATES) and abs(sum(q.values()) - 1) < 1e-10
        rec = {"phase": phase, "repeat": repeat, "case_id": item["case_id"], "order_id": item["order_id"],
               "state_order": item["state_order"], "request_sha256": item["request_sha256"],
               "raw_logits": dict(zip(item["state_order"], raw)), "native_temperature": decider.temperature,
               "probabilities": q, "selected_state": native["choice"], "native_confidence": native["confidence"],
               "probabilities_T1": original_scale["probabilities"], "elapsed_seconds": time.monotonic() - t0}
        if native_check:
            actual = decider.decide(req)
            ref = actual["answers"]["calm"]
            rec["native_decide_alignment"] = {"response": actual,
                "max_probability_difference": max(abs(q[s] - ref["probabilities"][s]) for s in STATES),
                "chosen_state_agrees": native["choice"] == ref["choice"]}
        append("readouts.jsonl", rec)
        return rec

    count = 0
    for rep in range(10):
        order = list(range(48)); random.Random(20261124 + rep).shuffle(order)
        for index in order:
            if time.time() - started > 1500:
                raise TimeoutError("Bounded inference budget reached; preserving partial readouts")
            item = requests[index]
            rec = readout(item, "main", rep, rep == 0 and item["order_id"] == "order_0")
            count += 1
            print("READOUT", count, item["case_id"], item["order_id"], rep, rec["selected_state"], round(max(rec["probabilities"].values()), 6), flush=True)
        write("progress.json", {"phase": "main", "completed_readouts": count, "completed_blocks": rep + 1, "time": time.time()})

    # Reload the same checkpoint once, retaining the exact serial reference path.
    del decider
    gc.collect(); torch.cuda.empty_cache(); torch.cuda.synchronize()
    reload_start = time.monotonic()
    decider = Decider.from_pretrained(CHECKPOINT, device="cuda", fast=False, max_length=8192, batch_tokens=8192)
    torch.cuda.synchronize()
    runtime["reload_seconds"] = time.monotonic() - reload_start
    reload_count = 0
    for item in requests:
        if item["order_id"] != "order_0":
            continue
        rec = readout(item, "reloaded", 0)
        reload_count += 1
        print("RELOADED", item["case_id"], rec["selected_state"], flush=True)
    runtime["end_time"] = time.time()
    runtime["peak_gpu_memory_bytes"] = torch.cuda.max_memory_allocated()
    write("runtime.json", runtime)
    write("RUN_COMPLETE.json", {"main_readouts": count, "reloaded_readouts": reload_count,
                                "native_decide_alignment_checks": 12, "time": time.time()})
    print("COMPLETE", count, reload_count, flush=True)


if __name__ == "__main__":
    try:
        main()
    except BaseException as exc:
        write("RUN_FAILED.json", {"time": time.time(), "error": repr(exc), "traceback": traceback.format_exc()})
        traceback.print_exc()
        raise

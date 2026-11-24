#!/usr/bin/env python3
"""Install the author's pinned stack and run the frozen decision-model diagnostic."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parent
CHECKPOINT = Path("/workspace/pplx_decider_checkpoint")


def status(stage, **extra):
    (ROOT / "bootstrap_status.json").write_text(json.dumps({"stage": stage, "time": time.time(), **extra}, indent=2))
    print("STAGE", stage, extra, flush=True)


try:
    os.environ.update({"HF_HOME": "/workspace/hf_cache", "HF_HUB_DISABLE_TELEMETRY": "1",
                       "HF_HUB_DISABLE_XET": "1", "TOKENIZERS_PARALLELISM": "false",
                       "DECIDER_CHECKPOINT": str(CHECKPOINT), "PYTHONUNBUFFERED": "1"})
    if sys.version_info < (3, 12):
        raise RuntimeError("Official checkpoint requires Python 3.12 or later")
    status("installing_author_requirements", python=sys.version)
    subprocess.run([sys.executable, "-m", "pip", "install", "--disable-pip-version-check", "--no-cache-dir",
                    "-r", str(ROOT / "frozen_model_source/requirements.txt")], check=True)
    from huggingface_hub import snapshot_download
    manifest = json.loads((ROOT / "model_source_manifest.json").read_text())
    status("downloading_checkpoint", repo=manifest["repo"], revision=manifest["revision"])
    snapshot_download(manifest["repo"], revision=manifest["revision"], local_dir=CHECKPOINT, max_workers=8)
    status("verifying_checkpoint")
    release = json.loads((CHECKPOINT / "release-manifest.json").read_text())
    observed = {}
    # Compare all weights against the release's checksums; the source audit
    # checksum is also checked, so local code cannot silently drift after pinning.
    names = {k for k in release["files"] if k.endswith(".safetensors")}
    names.update(manifest["files"])
    for name in sorted(names):
        p = CHECKPOINT / name
        h = hashlib.sha256()
        with p.open("rb") as f:
            for block in iter(lambda: f.read(16 * 1024 * 1024), b""):
                h.update(block)
        item = {"bytes": p.stat().st_size, "sha256": h.hexdigest()}
        expected = manifest["files"].get(name) or release["files"].get(name)
        if expected and item != {k: expected[k] for k in ("bytes", "sha256")}:
            raise ValueError("Checkpoint integrity mismatch: " + name)
        observed[name] = item
    (ROOT / "checkpoint_integrity.json").write_text(json.dumps(observed, indent=2))
    status("running_diagnostic")
    subprocess.run([sys.executable, "-u", str(ROOT / "run_decider.py")], check=True)
    status("complete")
except BaseException as exc:
    (ROOT / "BOOTSTRAP_FAILED.json").write_text(json.dumps({"time": time.time(), "error": repr(exc), "traceback": traceback.format_exc()}, indent=2))
    status("failed", error=repr(exc))
    traceback.print_exc()
    raise

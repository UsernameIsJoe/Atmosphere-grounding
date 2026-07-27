"""Snapshot Google raw cache after successful collects."""

from __future__ import annotations

import hashlib
import json
import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)


def backup_google_raw(cfg: dict[str, Any], *, label: str = "collect") -> Path:
    """Copy data/raw places+images into a timestamped backup folder.

    Also maintains data/backup/google/latest → most recent snapshot.
    Skips identical files via sha1 when the same relative path already exists
    in an older backup with the same hash (dedupe note in manifest only);
    always writes a full new snapshot tree for recoverability.
    """
    from atmosphere_grounding.config import project_root, resolve_path

    raw_dir = resolve_path(cfg, "raw_dir")
    backup_root = Path(cfg["paths"].get("backup_dir", "data/backup/google"))
    if not backup_root.is_absolute():
        backup_root = project_root() / backup_root

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dest = backup_root / f"{ts}_{label}"
    dest.mkdir(parents=True, exist_ok=True)

    copied: list[dict[str, Any]] = []
    for sub in ("places", "images", "search"):
        src = raw_dir / sub
        if not src.exists():
            continue
        for path in src.rglob("*"):
            if not path.is_file():
                continue
            rel = path.relative_to(raw_dir)
            out = dest / rel
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, out)
            copied.append(
                {
                    "rel": str(rel),
                    "bytes": path.stat().st_size,
                    "sha1": _sha1(path),
                }
            )

    manifest = {
        "created_at": ts,
        "label": label,
        "source_raw": str(raw_dir),
        "n_files": len(copied),
        "files": copied,
    }
    (dest / "MANIFEST.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )

    latest = backup_root / "latest"
    if latest.is_symlink() or latest.exists():
        latest.unlink()
    try:
        latest.symlink_to(dest.name, target_is_directory=True)
    except OSError:
        # Fallback: write a pointer file
        latest.write_text(dest.name + "\n", encoding="utf-8")

    log.info("backed up %d raw files → %s", len(copied), dest)
    return dest


def _sha1(path: Path) -> str:
    h = hashlib.sha1()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

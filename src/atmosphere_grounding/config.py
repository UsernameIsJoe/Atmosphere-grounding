"""Shared config, paths, and IO helpers."""

from __future__ import annotations

import json
import os
import random
from pathlib import Path
from typing import Any

import numpy as np
import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]


def project_root() -> Path:
    return ROOT


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    load_dotenv(ROOT / ".env")
    cfg_path = Path(path) if path else ROOT / "configs" / "cambridge_pilot.yaml"
    if not cfg_path.is_absolute():
        cfg_path = ROOT / cfg_path
    with cfg_path.open(encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    lex_rel = cfg.get("atmospheres", {}).get("lexicon_path", "configs/lexicon.yaml")
    lex_path = Path(lex_rel)
    if not lex_path.is_absolute():
        lex_path = ROOT / lex_path
    with lex_path.open(encoding="utf-8") as f:
        lexicon = yaml.safe_load(f)
    cfg["lexicon"] = lexicon
    cfg["_config_path"] = str(cfg_path)
    return cfg


def resolve_path(cfg: dict[str, Any], key: str) -> Path:
    rel = cfg["paths"][key]
    p = Path(rel)
    return p if p.is_absolute() else ROOT / p


def ensure_dirs(cfg: dict[str, Any]) -> None:
    for key in ("raw_dir", "processed_dir", "graph_dir"):
        resolve_path(cfg, key).mkdir(parents=True, exist_ok=True)
    (resolve_path(cfg, "raw_dir") / "places").mkdir(parents=True, exist_ok=True)
    (resolve_path(cfg, "raw_dir") / "images").mkdir(parents=True, exist_ok=True)
    (resolve_path(cfg, "processed_dir") / "atmosphere_profiles").mkdir(
        parents=True, exist_ok=True
    )


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    try:
        import torch

        torch.manual_seed(seed)
    except ImportError:
        pass


def api_key() -> str | None:
    return os.getenv("GOOGLE_MAPS_API_KEY") or None


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def append_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def active_atmospheres(cfg: dict[str, Any]) -> list[str]:
    return list(cfg["atmospheres"]["active"])

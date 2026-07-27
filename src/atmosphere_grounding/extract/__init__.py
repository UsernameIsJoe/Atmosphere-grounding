"""Ollama-based lexicon atmosphere extraction from reviews."""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

import requests

from atmosphere_grounding.config import (
    active_atmospheres,
    ensure_dirs,
    read_jsonl,
    resolve_path,
    write_json,
    write_jsonl,
)

log = logging.getLogger(__name__)


SYSTEM_PROMPT = """You extract visual atmosphere evidence from place reviews.
Only use atmospheres from this fixed lexicon: {atmospheres}.
Glosses: {glosses}
Rules:
- Only English visual/spatial evidence (what one could see in a photo).
- Ignore service, smell, taste, price, staff personality, and memory claims.
- Map each hit to exactly one lexicon atmosphere (or skip).
- Extract concrete visual nouns (bench, tree, path, fence, lighting, water, ...).
- Return STRICT JSON only, no markdown. Prefer a JSON array of objects.
  Each object: {{"atmosphere": str, "phrase": str, "nouns": [str], "visual_confidence": float}}
- If only one match, still return a one-element array. If nothing matches, return [].
"""


def _glosses_for(cfg: dict[str, Any], atmospheres: list[str]) -> dict[str, str]:
    all_g = (cfg.get("lexicon") or {}).get("glosses") or {}
    return {a: all_g.get(a, a) for a in atmospheres}


def _parse_json_array(text: str) -> list[dict[str, Any]]:
    text = text.strip()
    # Strip markdown fences if present
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return [x for x in data if isinstance(x, dict)]
        if isinstance(data, dict):
            # Single match object
            if "atmosphere" in data or "phrase" in data:
                return [data]
            for key in ("items", "matches", "results", "extractions"):
                if isinstance(data.get(key), list):
                    return [x for x in data[key] if isinstance(x, dict)]
            # Any list value
            for v in data.values():
                if isinstance(v, list) and v and isinstance(v[0], dict):
                    return [x for x in v if isinstance(x, dict)]
    except json.JSONDecodeError:
        pass
    # Fallback: find first [...] or {...} block
    m = re.search(r"\[[\s\S]*\]", text)
    if m:
        try:
            data = json.loads(m.group(0))
            if isinstance(data, list):
                return [x for x in data if isinstance(x, dict)]
        except json.JSONDecodeError:
            pass
    m = re.search(r"\{[\s\S]*\}", text)
    if m:
        try:
            data = json.loads(m.group(0))
            if isinstance(data, dict) and ("atmosphere" in data or "phrase" in data):
                return [data]
        except json.JSONDecodeError:
            return []
    return []


def heuristic_extract(
    text: str,
    atmospheres: list[str],
    place_id: str,
    review_index: int,
) -> list[dict[str, Any]]:
    """Keyword fallback when Ollama is unavailable (fixtures / smoke)."""
    lower = text.lower()
    # Synonym stems → lexicon
    stems: dict[str, list[str]] = {
        "inviting": ["inviting", "welcoming", "welcome", "friendly entrance", "approachable"],
        "safe": ["safe", "safety", "well-lit", "well lit", "secure", "watched", "family-friendly"],
        "calm": ["calm", "peaceful", "quiet", "serene", "tranquil", "relaxing"],
    }
    noun_candidates = [
        "tree",
        "trees",
        "bench",
        "benches",
        "path",
        "paths",
        "fence",
        "lighting",
        "lights",
        "water",
        "fountain",
        "lawn",
        "grass",
        "playground",
        "gate",
        "shade",
        "canopy",
        "plaza",
        "walkway",
    ]
    found_nouns = [n for n in noun_candidates if re.search(rf"\b{re.escape(n)}\b", lower)]
    out: list[dict[str, Any]] = []
    for atm in atmospheres:
        keys = stems.get(atm, [atm])
        if any(k in lower for k in keys):
            # pick a short supporting phrase
            phrase = text.strip()
            if len(phrase) > 160:
                phrase = phrase[:157] + "..."
            out.append(
                {
                    "place_id": place_id,
                    "review_index": review_index,
                    "atmosphere": atm,
                    "phrase": phrase,
                    "nouns": found_nouns[:8],
                    "visual_confidence": 0.55,
                    "extractor": "heuristic",
                }
            )
    return out


def ollama_extract(
    text: str,
    atmospheres: list[str],
    glosses: dict[str, str],
    model: str,
    temperature: float,
    timeout_s: int,
) -> list[dict[str, Any]]:
    host = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
    system = SYSTEM_PROMPT.format(
        atmospheres=", ".join(atmospheres),
        glosses=json.dumps(glosses),
    )
    payload = {
        "model": model,
        "stream": False,
        "format": "json",
        "options": {"temperature": temperature},
        "messages": [
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": f"Review text:\n{text}\n\nReturn JSON array of matches.",
            },
        ],
    }
    resp = requests.post(f"{host}/api/chat", json=payload, timeout=timeout_s)
    resp.raise_for_status()
    content = (resp.json().get("message") or {}).get("content") or ""
    items = _parse_json_array(content)
    # Sometimes models wrap as {"matches": [...]}
    if not items:
        try:
            obj = json.loads(content)
            if isinstance(obj, dict):
                for v in obj.values():
                    if isinstance(v, list):
                        items = [x for x in v if isinstance(x, dict)]
                        break
        except json.JSONDecodeError:
            items = []
    cleaned: list[dict[str, Any]] = []
    allowed = set(atmospheres)
    for it in items:
        atm = str(it.get("atmosphere", "")).strip().lower()
        if atm not in allowed:
            continue
        nouns = it.get("nouns") or []
        if not isinstance(nouns, list):
            nouns = []
        try:
            conf = float(it.get("visual_confidence", 0.5))
        except (TypeError, ValueError):
            conf = 0.5
        cleaned.append(
            {
                "atmosphere": atm,
                "phrase": str(it.get("phrase") or "").strip(),
                "nouns": [str(n).lower().strip() for n in nouns if str(n).strip()],
                "visual_confidence": max(0.0, min(1.0, conf)),
                "extractor": "ollama",
            }
        )
    return cleaned


def run_extract(
    cfg: dict[str, Any],
    *,
    use_heuristic: bool = False,
) -> list[dict[str, Any]]:
    ensure_dirs(cfg)
    processed = resolve_path(cfg, "processed_dir")
    reviews = read_jsonl(processed / "reviews.jsonl")
    atmospheres = active_atmospheres(cfg)
    glosses = _glosses_for(cfg, atmospheres)
    model_cfg = cfg["models"]["ollama"]

    mentions: list[dict[str, Any]] = []
    ollama_ok = not use_heuristic
    consecutive_failures = 0
    if ollama_ok:
        try:
            host = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
            requests.get(f"{host}/api/tags", timeout=3).raise_for_status()
        except Exception as e:
            log.warning("Ollama unavailable (%s); falling back to heuristic extractor", e)
            ollama_ok = False

    for rev in reviews:
        lang = (rev.get("language") or "en").lower()
        if not lang.startswith("en"):
            continue
        text = rev.get("text") or ""
        if not text.strip():
            continue
        place_id = rev["place_id"]
        idx = int(rev.get("review_index", 0))
        if ollama_ok:
            try:
                items = ollama_extract(
                    text,
                    atmospheres,
                    glosses,
                    model=model_cfg["model"],
                    temperature=float(model_cfg["temperature"]),
                    timeout_s=int(model_cfg["timeout_s"]),
                )
                consecutive_failures = 0
                for it in items:
                    mentions.append(
                        {
                            "place_id": place_id,
                            "review_index": idx,
                            **it,
                        }
                    )
                continue
            except Exception as e:
                consecutive_failures += 1
                log.warning("Ollama extract failed for %s#%s: %s", place_id, idx, e)
                if consecutive_failures >= 3:
                    log.warning("Too many Ollama failures; switching to heuristic for remaining reviews")
                    ollama_ok = False
        mentions.extend(heuristic_extract(text, atmospheres, place_id, idx))

    write_jsonl(processed / "mentions.jsonl", mentions)
    write_json(
        processed / "extract_summary.json",
        {
            "n_reviews": len(reviews),
            "n_mentions": len(mentions),
            "atmospheres": atmospheres,
            "backend": "ollama" if (not use_heuristic and consecutive_failures < 3) else "heuristic",
        },
    )

    if cfg.get("extract", {}).get("run_fusion_pass", True):
        fused = run_fusion_pass(cfg, mentions, use_heuristic=use_heuristic)
        return fused
    return mentions


FUSION_PROMPT = """You refine atmosphere labels using BOTH a place review and an independent image-object list.
Lexicon only: {atmospheres}.
Glosses: {glosses}
Rules:
- Start from the review text (primary). Use image objects only to confirm, add concrete nouns, or flag mismatches.
- Do NOT invent atmospheres unsupported by the review just because an object appears.
- If review is non-visual, return [].
- Return JSON array of:
  {{"atmosphere": str, "phrase": str, "nouns": [str], "visual_confidence": float,
    "supported_by_objects": [str], "conflict_note": str}}
"""


def run_fusion_pass(
    cfg: dict[str, Any],
    comment_mentions: list[dict[str, Any]] | None = None,
    *,
    use_heuristic: bool = False,
) -> list[dict[str, Any]]:
    """Pass B: fuse comment-only mentions with image object lists (keeps Pass A intact)."""
    ensure_dirs(cfg)
    processed = resolve_path(cfg, "processed_dir")
    atmospheres = active_atmospheres(cfg)
    glosses = _glosses_for(cfg, atmospheres)
    model_cfg = cfg["models"]["ollama"]

    if comment_mentions is None:
        comment_mentions = read_jsonl(processed / "mentions.jsonl")
    reviews = {(r["place_id"], int(r.get("review_index", 0))): r for r in read_jsonl(processed / "reviews.jsonl")}

    place_objects_path = processed / "place_objects.json"
    objects_by_place: dict[str, list[str]] = {}
    if place_objects_path.exists():
        from atmosphere_grounding.config import read_json

        for row in read_json(place_objects_path):
            objects_by_place[row["place_id"]] = list(row.get("object_list") or [])

    if not objects_by_place:
        log.warning("fusion: no place_objects.json — copy comment mentions as fused")
        write_jsonl(processed / "mentions_fused.jsonl", comment_mentions)
        return comment_mentions

    ollama_ok = not use_heuristic
    if ollama_ok:
        try:
            host = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
            requests.get(f"{host}/api/tags", timeout=3).raise_for_status()
        except Exception as e:
            log.warning("fusion: Ollama unavailable (%s)", e)
            ollama_ok = False

    fused: list[dict[str, Any]] = []
    # Group comment mentions by review
    by_rev: dict[tuple[str, int], list[dict[str, Any]]] = {}
    for m in comment_mentions:
        key = (m["place_id"], int(m.get("review_index", 0)))
        by_rev.setdefault(key, []).append(m)

    # Also fuse reviews that had zero comment mentions but have objects — skip (Pass A primacy)
    for (place_id, idx), ms in by_rev.items():
        rev = reviews.get((place_id, idx)) or {}
        text = rev.get("text") or ""
        obj_list = objects_by_place.get(place_id) or []
        if not ollama_ok:
            for m in ms:
                fused.append(
                    {
                        **m,
                        "extractor": "fusion_heuristic",
                        "supported_by_objects": [
                            n for n in (m.get("nouns") or []) if n in obj_list
                        ],
                        "image_objects": obj_list,
                    }
                )
            continue

        system = FUSION_PROMPT.format(
            atmospheres=", ".join(atmospheres),
            glosses=json.dumps(glosses),
        )
        user = (
            f"Review text:\n{text}\n\n"
            f"Image-detected objects at this place: {obj_list}\n"
            f"Pass-A comment-only extractions: {json.dumps(ms, ensure_ascii=False)}\n"
            "Return refined JSON array."
        )
        try:
            host = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
            payload = {
                "model": model_cfg["model"],
                "stream": False,
                "format": "json",
                "options": {"temperature": float(model_cfg["temperature"])},
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            }
            resp = requests.post(
                f"{host}/api/chat", json=payload, timeout=int(model_cfg["timeout_s"])
            )
            resp.raise_for_status()
            content = (resp.json().get("message") or {}).get("content") or ""
            items = _parse_json_array(content)
            allowed = set(atmospheres)
            if not items:
                # keep pass A
                for m in ms:
                    fused.append({**m, "extractor": "fusion_fallback_passa", "image_objects": obj_list})
                continue
            for it in items:
                atm = str(it.get("atmosphere", "")).strip().lower()
                if atm not in allowed:
                    continue
                nouns = it.get("nouns") or []
                if not isinstance(nouns, list):
                    nouns = []
                supported = it.get("supported_by_objects") or []
                if not isinstance(supported, list):
                    supported = []
                try:
                    conf = float(it.get("visual_confidence", 0.5))
                except (TypeError, ValueError):
                    conf = 0.5
                fused.append(
                    {
                        "place_id": place_id,
                        "review_index": idx,
                        "atmosphere": atm,
                        "phrase": str(it.get("phrase") or "").strip(),
                        "nouns": [str(n).lower().strip() for n in nouns if str(n).strip()],
                        "visual_confidence": max(0.0, min(1.0, conf)),
                        "supported_by_objects": [str(n).lower() for n in supported],
                        "conflict_note": str(it.get("conflict_note") or ""),
                        "image_objects": obj_list,
                        "extractor": "fusion_ollama",
                    }
                )
        except Exception as e:
            log.warning("fusion failed for %s#%s: %s", place_id, idx, e)
            for m in ms:
                fused.append({**m, "extractor": "fusion_error_passa", "image_objects": obj_list})

    write_jsonl(processed / "mentions_fused.jsonl", fused)
    write_json(
        processed / "fusion_summary.json",
        {
            "n_pass_a": len(comment_mentions),
            "n_fused": len(fused),
            "n_places_with_objects": len(objects_by_place),
        },
    )
    return fused

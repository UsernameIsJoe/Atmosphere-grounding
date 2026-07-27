"""Place-level comment ↔ image correlation."""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from atmosphere_grounding.config import (
    active_atmospheres,
    ensure_dirs,
    project_root,
    read_jsonl,
    resolve_path,
    write_json,
    write_jsonl,
)

log = logging.getLogger(__name__)


def _resolve_image(imeta: dict[str, Any]) -> Path | None:
    path = Path(imeta.get("path") or "")
    if path.exists():
        return path
    alt = project_root() / (imeta.get("rel_path") or "")
    return alt if alt.exists() else None


def _set_jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 0.0
    return len(a & b) / max(1, len(a | b))


def _norm_noun(n: str) -> str:
    n = n.lower().strip()
    parts = re.split(r"[\s/_-]+", n)
    return " ".join(p for p in parts if p)


def _expand_nouns(nouns: list[str]) -> set[str]:
    out: set[str] = set()
    for n in nouns:
        base = _norm_noun(str(n))
        if not base:
            continue
        out.add(base)
        for tok in base.split():
            if len(tok) < 3:
                continue
            if tok.endswith("ies") and len(tok) > 5:
                out.add(tok[:-3] + "y")
            elif tok.endswith("es") and len(tok) > 5:
                out.add(tok[:-2])
            elif tok.endswith("s") and len(tok) > 4 and not tok.endswith("ss"):
                out.add(tok[:-1])
            else:
                out.add(tok)
    return out


def _zscores(values: list[float]) -> list[float]:
    arr = np.asarray(values, dtype=np.float64)
    if len(arr) == 0:
        return []
    mu = float(arr.mean())
    sd = float(arr.std())
    if sd < 1e-8:
        return [0.0 for _ in values]
    return [float((v - mu) / sd) for v in values]


def run_correlation(cfg: dict[str, Any], vision: Any | None = None) -> list[dict[str, Any]]:
    """Compute place-level alignment between reviews and images.

    Default mismatch signal is SigLIP review↔photo cosine, with places at/below
    a chosen percentile (default P10) flagged as mismatches. Noun Jaccard is
    diagnostic only.
    """
    ensure_dirs(cfg)
    processed = resolve_path(cfg, "processed_dir")
    atmospheres = active_atmospheres(cfg)
    corr_cfg = cfg.get("correlation") or {}
    distractors = list(corr_cfg.get("atmosphere_distractors") or [])
    mismatch_mode = str(corr_cfg.get("mismatch_mode") or "cosine_percentile")
    z_thr = float(corr_cfg.get("mismatch_z_threshold", -0.75))
    pct_thr = float(corr_cfg.get("mismatch_percentile", 10))
    abs_thr = corr_cfg.get("mismatch_cosine_threshold")
    abs_thr_f = float(abs_thr) if abs_thr is not None else None

    reviews = read_jsonl(processed / "reviews.jsonl")
    mentions = read_jsonl(processed / "mentions.jsonl")
    images = read_jsonl(processed / "images.jsonl")
    objects = read_jsonl(processed / "objects.jsonl")

    reviews_by_place: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in reviews:
        reviews_by_place[r["place_id"]].append(r)

    mentions_by_place: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for m in mentions:
        mentions_by_place[m["place_id"]].append(m)

    images_by_place: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for im in images:
        images_by_place[im["place_id"]].append(im)

    objects_by_place: dict[str, list[str]] = defaultdict(list)
    for o in objects:
        objects_by_place[o["place_id"]].append(_norm_noun(str(o.get("noun") or "")))

    backend = cfg["models"].get("vision_backend", "heuristic")
    if vision is None and backend == "transformers":
        try:
            from atmosphere_grounding.ground import TransformersVision

            vision = TransformersVision(cfg)
        except Exception as e:
            log.warning("correlation: transformers unavailable (%s)", e)
            vision = None

    rows: list[dict[str, Any]] = []
    place_ids = sorted(
        set(reviews_by_place) | set(images_by_place) | set(mentions_by_place)
    )

    for pid in place_ids:
        raw_text_nouns: list[str] = []
        for m in mentions_by_place.get(pid, []):
            raw_text_nouns.extend(m.get("nouns") or [])
        if not raw_text_nouns:
            for r in reviews_by_place.get(pid, []):
                for tok in re.findall(r"[a-zA-Z]{3,}", (r.get("text") or "").lower()):
                    if tok in {
                        "tree",
                        "trees",
                        "bench",
                        "benches",
                        "path",
                        "park",
                        "grass",
                        "fence",
                        "water",
                        "playground",
                        "shade",
                        "gate",
                        "lighting",
                    }:
                        raw_text_nouns.append(tok)
        text_nouns = _expand_nouns(raw_text_nouns)
        img_nouns = _expand_nouns(objects_by_place.get(pid, []))
        jaccard = _set_jaccard(text_nouns, img_nouns)
        coverage_text = len(text_nouns & img_nouns) / max(1, len(text_nouns))
        coverage_image = len(text_nouns & img_nouns) / max(1, len(img_nouns))

        place_imgs = images_by_place.get(pid, [])
        review_texts = [
            (r.get("text") or "").strip()[:300]
            for r in reviews_by_place.get(pid, [])
            if (r.get("text") or "").strip()
        ]
        phrase_img_scores: list[float] = []
        atm_support: dict[str, float] = {}

        loaded: list[tuple[dict[str, Any], Image.Image]] = []
        for imeta in place_imgs:
            path = _resolve_image(imeta)
            if path:
                loaded.append((imeta, Image.open(path).convert("RGB")))

        # Primary score: SigLIP cosine — each review vs each photo; keep best photo
        if vision is not None and loaded and review_texts:
            for text in review_texts[:8]:
                snippet = text[:120]
                per_img: list[float] = []
                for _, img in loaded:
                    scores = vision.phrase_scores(img, [snippet])
                    if scores:
                        per_img.append(float(scores[0]))
                if per_img:
                    phrase_img_scores.append(max(per_img))

        # Diagnostic: atmosphere word vs distractors on images
        labels = atmospheres + [d for d in distractors if d not in atmospheres]
        if vision is not None and loaded:
            per_atm: dict[str, list[float]] = defaultdict(list)
            for _, img in loaded:
                scores = vision.phrase_scores(img, labels)
                for lab, s in zip(labels, scores):
                    per_atm[lab].append(float(s))
            for lab, vals in per_atm.items():
                atm_support[lab] = float(np.mean(vals)) if vals else 0.0

        mentioned_atms = {
            m["atmosphere"] for m in mentions_by_place.get(pid, []) if m.get("atmosphere")
        }
        consistency: dict[str, Any] = {}
        for atm in mentioned_atms:
            own = atm_support.get(atm)
            if own is None:
                continue
            others = [atm_support[a] for a in atm_support if a != atm]
            margin = own - (max(others) if others else 0.0)
            consistency[atm] = {
                "image_score": round(own, 4),
                "margin_vs_best_other": round(margin, 4),
                "supported": bool(margin > 0),
            }

        mean_align = float(np.mean(phrase_img_scores)) if phrase_img_scores else None
        rows.append(
            {
                "place_id": pid,
                "n_reviews": len(reviews_by_place.get(pid, [])),
                "n_images": len(place_imgs),
                "text_nouns": sorted(text_nouns),
                "image_nouns": sorted(img_nouns),
                "noun_jaccard": round(jaccard, 4),
                "noun_coverage_text": round(coverage_text, 4),
                "noun_coverage_image": round(coverage_image, 4),
                "review_image_align_mean": None
                if mean_align is None
                else round(mean_align, 4),
                "atmosphere_image_scores": {k: round(v, 4) for k, v in atm_support.items()},
                "mentioned_atmospheres": sorted(mentioned_atms),
                "atmosphere_consistency": consistency,
                "likely_mismatch": False,
                "mismatch_reason": "",
                "mismatch_mode": mismatch_mode,
            }
        )

    # Second pass: apply mismatch rule on place-level cosine scores
    align_vals = [
        float(r["review_image_align_mean"])
        for r in rows
        if r.get("review_image_align_mean") is not None
    ]
    z_by_pid: dict[str, float] = {}
    if align_vals:
        zs = _zscores(align_vals)
        i = 0
        for r in rows:
            if r.get("review_image_align_mean") is not None:
                z_by_pid[r["place_id"]] = zs[i]
                i += 1

    # Percentile cut on this run's place cosines (P10 → bottom 10%)
    pct_cut = None
    if align_vals and mismatch_mode == "cosine_percentile":
        pct_cut = float(np.percentile(align_vals, pct_thr))

    for r in rows:
        align = r.get("review_image_align_mean")
        jaccard = float(r.get("noun_jaccard") or 0.0)
        coverage_text = float(r.get("noun_coverage_text") or 0.0)
        z = z_by_pid.get(r["place_id"])
        r["review_image_align_z"] = None if z is None else round(z, 4)

        mismatch = False
        reason = ""
        if mismatch_mode == "legacy_noun":
            cons = r.get("atmosphere_consistency") or {}
            atm_fail = any(not v.get("supported") for v in cons.values()) if cons else False
            weak_overlap = jaccard < 0.05 and coverage_text < 0.15
            if atm_fail and weak_overlap:
                mismatch = True
                reason = "legacy_noun_overlap"
            elif align is not None and align < 0.0 and jaccard < 0.05:
                mismatch = True
                reason = "legacy_neg_align"
        elif mismatch_mode == "cosine_absolute":
            cut = abs_thr_f if abs_thr_f is not None else -0.0162  # default ≈ pair P10
            if align is None:
                mismatch = True
                reason = "missing_cosine"
            elif align <= cut:
                mismatch = True
                reason = f"cosine<={cut}"
        elif mismatch_mode == "cosine_percentile":
            if align is None:
                mismatch = True
                reason = "missing_cosine"
            elif pct_cut is not None and align <= pct_cut:
                mismatch = True
                reason = f"cosine<=P{pct_thr:g}({pct_cut:.4f})"
        else:
            # cosine_relative (legacy z-score mode)
            if align is None:
                mismatch = True
                reason = "missing_cosine"
            elif z is not None and z < z_thr:
                mismatch = True
                reason = f"low_cosine_z<{z_thr}"
            elif align is not None and align < 0.02:
                mismatch = True
                reason = "low_cosine_abs<0.02"

        r["likely_mismatch"] = mismatch
        r["mismatch_reason"] = reason
        if pct_cut is not None:
            r["mismatch_cosine_threshold"] = round(pct_cut, 6)
        elif mismatch_mode == "cosine_absolute" and abs_thr_f is not None:
            r["mismatch_cosine_threshold"] = abs_thr_f

    write_jsonl(processed / "place_correlation.jsonl", rows)
    n_mismatch = sum(1 for r in rows if r.get("likely_mismatch"))
    scored = [
        r["review_image_align_mean"]
        for r in rows
        if r.get("review_image_align_mean") is not None
    ]
    summary = {
        "n_places": len(rows),
        "n_likely_mismatch": n_mismatch,
        "mismatch_mode": mismatch_mode,
        "mismatch_percentile": pct_thr if mismatch_mode == "cosine_percentile" else None,
        "mismatch_cosine_threshold": None
        if pct_cut is None and abs_thr_f is None
        else round(pct_cut if pct_cut is not None else float(abs_thr_f), 6),
        "mismatch_z_threshold": z_thr if mismatch_mode == "cosine_relative" else None,
        "mean_noun_jaccard": round(
            float(np.mean([r["noun_jaccard"] for r in rows] or [0.0])), 4
        ),
        "mean_review_image_align": None
        if not scored
        else round(float(np.mean(scored)), 4),
        "mismatch_rate": round(n_mismatch / max(1, len(rows)), 4),
        "mismatch_reasons": {
            k: sum(1 for r in rows if r.get("mismatch_reason") == k)
            for k in sorted(
                {str(r.get("mismatch_reason") or "") for r in rows if r.get("likely_mismatch")}
            )
        },
    }
    write_json(processed / "correlation_summary.json", summary)
    log.info("correlation summary: %s", summary)
    return rows

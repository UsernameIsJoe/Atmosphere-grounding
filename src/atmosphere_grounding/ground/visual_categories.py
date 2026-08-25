"""Visual-category extractors: DINO / SigLIP / segmentation / image metrics."""

from __future__ import annotations

import logging
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import yaml
from PIL import Image

from atmosphere_grounding.config import (
    ensure_dirs,
    project_root,
    read_jsonl,
    resolve_path,
    write_json,
    write_jsonl,
)

log = logging.getLogger(__name__)


def load_visual_ontology(cfg: dict[str, Any] | None = None) -> dict[str, Any]:
    rel = (cfg or {}).get("models", {}).get(
        "visual_categories_path", "configs/visual_categories_v1.yaml"
    )
    path = Path(rel)
    if not path.is_absolute():
        path = project_root() / path
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def iter_families(onto: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for cat in onto.get("categories") or []:
        for fam in cat.get("families") or []:
            rows.append(
                {
                    "category_id": cat["id"],
                    "category_name": cat.get("name"),
                    "family_id": fam["id"],
                    "extractors": list(fam.get("extractors") or []),
                    "soft": bool(fam.get("soft")),
                }
            )
    return rows


def all_dino_phrases(onto: dict[str, Any]) -> list[str]:
    phrases_map = onto.get("phrases") or {}
    out: list[str] = []
    seen: set[str] = set()
    for fam in iter_families(onto):
        if "dino" not in fam["extractors"]:
            continue
        for p in phrases_map.get(fam["family_id"]) or [fam["family_id"].replace("_", " ")]:
            k = p.strip().lower()
            if k and k not in seen:
                seen.add(k)
                out.append(p)
    return out


def compute_image_metrics(img: Image.Image) -> dict[str, float]:
    arr = np.asarray(img.convert("RGB"), dtype=np.float32) / 255.0
    gray = arr.mean(axis=2)
    gx = np.abs(np.diff(gray, axis=1)).mean()
    gy = np.abs(np.diff(gray, axis=0)).mean()
    lum = (gray * 255).astype(np.uint8)
    hist, _ = np.histogram(lum, bins=256, range=(0, 256))
    p = hist / max(1, hist.sum())
    p = p[p > 0]
    return {
        "mean_luminance": float(gray.mean()),
        "luminance_std": float(gray.std()),
        "channel_std_mean": float(arr.std(axis=(0, 1)).mean()),
        "gradient_edge_density": float((gx + gy) / 2.0),
        "color_entropy_norm": float(-(p * np.log2(p)).sum() / 8.0),
    }


def ground_height_bias(seg_fracs: dict[str, float], mask_rows: np.ndarray | None) -> float | None:
    """Mean normalized row of ground-like pixels (0=top, 1=bottom). None if unavailable."""
    if mask_rows is None or mask_rows.size == 0:
        return None
    return float(mask_rows.mean())


class SegmentationBackend:
    """Mask2Former ADE20K semantic segmentation → label fractions."""

    def __init__(self, model_name: str) -> None:
        self.ok = False
        self.error: str | None = None
        self.model_name = model_name
        try:
            import torch
            from transformers import pipeline

            device = 0 if torch.cuda.is_available() else -1
            self.pipe = pipeline(
                "image-segmentation",
                model=model_name,
                device=device,
            )
            self.ok = True
            log.info("segmentation ready: %s", model_name)
        except Exception as e:
            self.error = str(e)
            log.warning("segmentation unavailable: %s", e)

    @classmethod
    def disabled(cls, model_name: str, reason: str) -> "SegmentationBackend":
        obj = cls.__new__(cls)
        obj.ok = False
        obj.error = reason
        obj.model_name = model_name
        return obj

    def analyze(self, img: Image.Image) -> tuple[dict[str, float], dict[str, np.ndarray]]:
        """Return (label→fraction, label→boolean mask)."""
        if not self.ok:
            return {}, {}
        segs = self.pipe(img)
        h, w = img.size[1], img.size[0]
        total = float(h * w)
        fracs: dict[str, float] = defaultdict(float)
        masks: dict[str, np.ndarray] = {}
        for s in segs:
            label = str(s.get("label", "")).lower()
            mask = s.get("mask")
            if mask is None:
                continue
            m = np.asarray(mask)
            if m.dtype != bool:
                m = m > 0
            area = float(m.sum())
            fracs[label] += area / total
            if label in masks:
                masks[label] = np.logical_or(masks[label], m)
            else:
                masks[label] = m
        return dict(fracs), masks

    def family_fraction(self, fracs: dict[str, float], labels: list[str]) -> float:
        return float(sum(fracs.get(k, 0.0) for k in labels))


def _phrase_key(p: str) -> str:
    return p.strip().lower()


def _match_detection_to_family(
    noun: str, phrase_to_family: dict[str, str]
) -> str | None:
    n = _phrase_key(noun)
    if n in phrase_to_family:
        return phrase_to_family[n]
    # Partial match: detected label contained in or contains a phrase
    for phrase, fid in phrase_to_family.items():
        if phrase in n or n in phrase:
            return fid
    return None


def _resolve_image_path(imeta: dict[str, Any]) -> Path | None:
    path = Path(imeta.get("path") or "")
    if path.exists():
        return path
    alt = project_root() / (imeta.get("rel_path") or "")
    return alt if alt.exists() else None


def extract_image_features(
    img: Image.Image,
    onto: dict[str, Any],
    *,
    vision: Any | None = None,
    seg: SegmentationBackend | None = None,
    cfg: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run all assigned extractors for one image; return family-keyed feature dict."""
    settings = dict(onto.get("extractor_settings") or {})
    if cfg:
        models = cfg.get("models") or {}
        if models.get("grounding_box_threshold") is not None:
            settings.setdefault("dino_box_threshold", models["grounding_box_threshold"])
        if models.get("segmentation_model"):
            settings["segmentation_model"] = models["segmentation_model"]
        if models.get("dino_phrase_chunk_size"):
            settings["dino_phrase_chunk_size"] = models["dino_phrase_chunk_size"]

    families = iter_families(onto)
    phrases_map: dict[str, list[str]] = onto.get("phrases") or {}
    seg_maps: dict[str, list[str]] = onto.get("seg_class_maps") or {}
    metric_formulas: dict[str, str] = onto.get("metric_formulas") or {}
    thr_by_fam: dict[str, float] = settings.get("dino_box_threshold_by_family") or {}
    default_thr = float(settings.get("dino_box_threshold", 0.25))
    chunk = int(settings.get("dino_phrase_chunk_size", 20))

    metrics = compute_image_metrics(img)
    seg_fracs: dict[str, float] = {}
    seg_masks: dict[str, np.ndarray] = {}
    if seg is not None and seg.ok:
        seg_fracs, seg_masks = seg.analyze(img)

    # Build phrase→family for DINO families
    phrase_to_family: dict[str, str] = {}
    dino_phrases: list[str] = []
    for fam in families:
        if "dino" not in fam["extractors"]:
            continue
        for p in phrases_map.get(fam["family_id"]) or []:
            phrase_to_family[_phrase_key(p)] = fam["family_id"]
            dino_phrases.append(p)

    fam_dets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    if dino_phrases and vision is not None:
        dets = vision.ground_nouns(img, dino_phrases, chunk_size=chunk)
        for d in dets:
            fid = _match_detection_to_family(str(d.get("noun", "")), phrase_to_family)
            if fid:
                fam_dets[fid].append(d)
    elif dino_phrases:
        from atmosphere_grounding.ground import heuristic_ground_nouns

        for d in heuristic_ground_nouns(img, dino_phrases[:12]):
            fid = _match_detection_to_family(str(d.get("noun", "")), phrase_to_family)
            if fid:
                fam_dets[fid].append(d)

    # SigLIP: batch all soft/siglip phrases once
    siglip_phrases: list[str] = []
    siglip_phrase_family: dict[str, str] = {}
    for fam in families:
        if "siglip" not in fam["extractors"]:
            continue
        for p in phrases_map.get(fam["family_id"]) or []:
            siglip_phrases.append(p)
            siglip_phrase_family[_phrase_key(p)] = fam["family_id"]

    fam_siglip: dict[str, list[tuple[str, float]]] = defaultdict(list)
    if siglip_phrases:
        if vision is not None:
            scores = vision.phrase_scores(img, siglip_phrases)
        else:
            from atmosphere_grounding.ground import heuristic_phrase_scores

            scores = heuristic_phrase_scores(img, siglip_phrases)
        for p, s in zip(siglip_phrases, scores):
            fid = siglip_phrase_family.get(_phrase_key(p))
            if fid:
                fam_siglip[fid].append((p, float(s)))

    # Ground-height rows for slope_grade
    ground_labels = set()
    for labels in (seg_maps.get("soft_ground") or []) + (seg_maps.get("path_walkway") or []):
        ground_labels.add(labels)
    ground_rows = None
    if seg_masks and ground_labels:
        combined = None
        for lab in ground_labels:
            m = seg_masks.get(lab)
            if m is None:
                continue
            combined = m if combined is None else np.logical_or(combined, m)
        if combined is not None and combined.any():
            ys, _xs = np.where(combined)
            ground_rows = ys.astype(np.float32) / max(1, combined.shape[0] - 1)

    out_families: dict[str, Any] = {}
    for fam in families:
        fid = fam["family_id"]
        feats: dict[str, Any] = {
            "category_id": fam["category_id"],
            "extractors": fam["extractors"],
            "soft": fam["soft"],
        }

        if "dino" in fam["extractors"]:
            thr = float(thr_by_fam.get(fid, default_thr))
            dets = fam_dets.get(fid, [])
            hits = [d for d in dets if float(d.get("score") or 0) >= thr]
            best = max((float(d.get("score") or 0) for d in dets), default=0.0)
            feats["dino"] = {
                "n_hits": len(hits),
                "best_score": best,
                "threshold": thr,
                "labels": [d.get("noun") for d in hits[:5]],
                "boxes": [d.get("box") for d in hits[:5]],
            }

        if "siglip" in fam["extractors"]:
            items = fam_siglip.get(fid, [])
            if items:
                # Softmax within family for comparative soft phrases
                scores = np.array([s for _, s in items], dtype=np.float64)
                # Shift for numerical stability; use relative ranking
                ex = np.exp(scores - scores.max())
                probs = ex / max(1e-8, ex.sum())
                i = int(np.argmax(scores))
                feats["siglip"] = {
                    "best_score": float(scores[i]),
                    "best_prob": float(probs[i]),
                    "top_phrase": items[i][0],
                    "scores": {p: float(s) for p, s in items},
                }
            else:
                feats["siglip"] = {"best_score": 0.0, "best_prob": 0.0, "top_phrase": None}

        if "seg" in fam["extractors"]:
            labels = seg_maps.get(fid) or []
            frac = float(sum(seg_fracs.get(k, 0.0) for k in labels)) if seg_fracs else 0.0
            feats["seg"] = {
                "fraction": frac,
                "labels": labels,
                "backend_ok": bool(seg and seg.ok),
            }

        if "metric" in fam["extractors"]:
            formula = metric_formulas.get(fid)
            value: float | None = None
            if formula == "ground_height_bias":
                value = ground_height_bias(seg_fracs, ground_rows)
            elif formula:
                value = metrics.get(formula)
            feats["metric"] = {"formula": formula, "value": value}

        out_families[fid] = feats

    return {
        "families": out_families,
        "image_metrics": metrics,
        "seg_label_fractions": seg_fracs,
        "seg_ok": bool(seg and seg.ok),
    }


def run_visual_categories(
    cfg: dict[str, Any],
    *,
    vision: Any | None = None,
    force: bool = False,
    max_images: int | None = None,
) -> list[dict[str, Any]]:
    """Extract visual-category features for all processed images."""
    ensure_dirs(cfg)
    processed = resolve_path(cfg, "processed_dir")
    out_path = processed / "visual_features.jsonl"
    if out_path.exists() and not force:
        existing = read_jsonl(out_path)
        if existing:
            log.info("reusing %d cached visual features (%s)", len(existing), out_path)
            return existing

    onto = load_visual_ontology(cfg)
    settings = onto.get("extractor_settings") or {}
    model_name = (cfg.get("models") or {}).get("segmentation_model") or settings.get(
        "segmentation_model", "facebook/mask2former-swin-small-ade-semantic"
    )

    backend_name = cfg["models"].get("vision_backend", "heuristic")
    if vision is None and backend_name == "transformers":
        try:
            from atmosphere_grounding.ground import TransformersVision

            vision = TransformersVision(cfg)
        except Exception as e:
            log.warning("transformers vision unavailable (%s); heuristic", e)
            vision = None

    seg: SegmentationBackend
    if backend_name == "transformers":
        seg = SegmentationBackend(model_name)
    else:
        seg = SegmentationBackend.disabled(model_name, "skipped_non_transformers")

    images = read_jsonl(processed / "images.jsonl")
    if max_images is not None:
        images = images[: max(0, int(max_images))]

    rows: list[dict[str, Any]] = []
    for i, imeta in enumerate(images):
        path = _resolve_image_path(imeta)
        if not path:
            continue
        log.info("visual categories %d/%d %s", i + 1, len(images), path.name)
        img = Image.open(path).convert("RGB")
        feats = extract_image_features(img, onto, vision=vision, seg=seg, cfg=cfg)
        rows.append(
            {
                "place_id": imeta.get("place_id"),
                "image_index": imeta.get("image_index"),
                "image_path": imeta.get("rel_path") or str(path),
                "families": feats["families"],
                "image_metrics": feats["image_metrics"],
                "seg_label_fractions": feats["seg_label_fractions"],
                "seg_ok": feats["seg_ok"],
            }
        )

    write_jsonl(out_path, rows)

    # Place-level aggregates (mean metrics / max dino / mean seg)
    by_place: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        by_place[str(r.get("place_id"))].append(r)

    place_rows: list[dict[str, Any]] = []
    for pid, imgs in sorted(by_place.items()):
        fam_agg: dict[str, Any] = {}
        # Union of family ids
        fids = set()
        for im in imgs:
            fids.update((im.get("families") or {}).keys())
        for fid in sorted(fids):
            dino_hits = []
            dino_best = []
            seg_fracs = []
            sig_best = []
            metric_vals = []
            for im in imgs:
                f = (im.get("families") or {}).get(fid) or {}
                if "dino" in f:
                    dino_hits.append(int(f["dino"].get("n_hits") or 0))
                    dino_best.append(float(f["dino"].get("best_score") or 0))
                if "seg" in f:
                    seg_fracs.append(float(f["seg"].get("fraction") or 0))
                if "siglip" in f:
                    sig_best.append(float(f["siglip"].get("best_score") or 0))
                if "metric" in f and f["metric"].get("value") is not None:
                    metric_vals.append(float(f["metric"]["value"]))
            fam_agg[fid] = {
                "dino_hit_images": sum(1 for h in dino_hits if h > 0),
                "dino_mean_best": float(np.mean(dino_best)) if dino_best else None,
                "seg_mean_fraction": float(np.mean(seg_fracs)) if seg_fracs else None,
                "siglip_mean_best": float(np.mean(sig_best)) if sig_best else None,
                "metric_mean": float(np.mean(metric_vals)) if metric_vals else None,
                "n_images": len(imgs),
            }
        place_rows.append({"place_id": pid, "n_images": len(imgs), "families": fam_agg})

    write_json(processed / "place_visual_features.json", place_rows)
    write_json(
        processed / "visual_features_summary.json",
        {
            "n_images": len(rows),
            "n_places": len(place_rows),
            "n_families": len(iter_families(onto)),
            "seg_ok": any(r.get("seg_ok") for r in rows),
            "ontology_version": onto.get("version"),
        },
    )
    log.info("wrote visual features for %d images / %d places", len(rows), len(place_rows))
    return rows

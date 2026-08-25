#!/usr/bin/env python3
"""Benchmark visual-category extractors on pilot images (batched per image)."""

from __future__ import annotations

import json
import logging
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import yaml
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from atmosphere_grounding.config import load_config, project_root, read_jsonl  # noqa: E402
from atmosphere_grounding.ground import TransformersVision  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("benchmark_vc")

FAMILY_PHRASES: dict[str, list[str]] = {
    "seating": ["bench", "chair", "seat wall"],
    "play": ["playground", "swing", "slide"],
    "service_amenity": ["trash can", "fountain", "restroom"],
    "bike_facilities": ["bicycle rack", "bike rack"],
    "other_amenity": ["picnic table", "umbrella", "kiosk"],
    "tree": ["tree", "large tree"],
    "canopy_shade_plant": ["tree canopy", "shade tree"],
    "lawn_groundcover": ["grass", "lawn", "meadow"],
    "planting_bed": ["flower bed", "garden bed", "planted flowers"],
    "shrub": ["bush", "shrub", "hedge plant"],
    "path_walkway": ["path", "walkway", "sidewalk"],
    "plaza_hardscape": ["plaza", "paved square", "courtyard"],
    "stairs": ["stairs", "steps"],
    "entrance_threshold": ["entrance", "gate entrance", "doorway"],
    "crossing": ["crosswalk", "pedestrian crossing"],
    "fence": ["fence", "metal fence", "wooden fence"],
    "wall": ["wall", "stone wall", "brick wall"],
    "gate": ["gate", "iron gate"],
    "railing": ["railing", "handrail", "metal railing"],
    "hedge": ["hedge", "hedgerow"],
    "building_mass": ["building", "large building"],
    "facade_frontage": ["building facade", "storefront", "building front"],
    "opening": ["window", "door", "glass door"],
    "canopy_awning": ["awning", "canopy", "overhang"],
    "light_fixture": ["street lamp", "lamp post", "park light"],
    "lit_area_soft": [
        "well-lit area",
        "illuminated path at night",
        "brightly lit plaza",
    ],
    "paving_type": ["brick pavement", "concrete pavement", "asphalt path"],
    "soft_ground": ["dirt path", "mulch", "unpaved ground"],
    "hard_vertical": ["brick wall", "glass facade", "stone wall", "metal fence"],
    "water_surface": ["water surface", "reflecting pool", "pond water"],
    "fountain": ["fountain", "water fountain"],
    "water_body": ["pond", "lake", "river"],
    "slope_grade": ["sloped ground", "hill", "steep path"],
    "rock_landform": ["rock", "boulder", "rock formation"],
    "people": ["people", "person", "pedestrian"],
    "bicycle": ["bicycle", "bike"],
    "gathering_cluster_soft": [
        "group of people gathering",
        "crowd of people in a park",
        "people sitting together outdoors",
    ],
    "sky_openness": [
        "open sky",
        "wide open sky above",
        "enclosed space with little sky",
    ],
    "building_enclosure": [
        "tall buildings enclosing the street",
        "open area with few buildings",
    ],
    "vegetation_enclosure": [
        "tree-lined path",
        "open lawn with few trees",
    ],
    "ground_openness": [
        "wide open paved plaza",
        "narrow enclosed walkway",
    ],
    "focal_dominance_soft": [
        "single dominant object in the scene",
        "busy cluttered scene with many elements",
    ],
    "slope_grade": [
        "sloped ground",
        "flat level ground",
        "steep hill in park",
    ],
    "sign": ["sign", "street sign", "park sign"],
    "landmark_object": ["statue", "monument", "clock tower", "distinctive landmark"],
    "map_board": ["map board", "information board", "park map"],
}

SEG_LABEL_GROUPS: dict[str, list[str]] = {
    "sky_openness": ["sky"],
    "building_enclosure": ["building", "house", "skyscraper", "wall", "fence", "railing"],
    "vegetation_enclosure": ["tree", "grass", "plant", "flower", "palm", "field"],
    "ground_openness": ["road", "sidewalk", "floor", "path", "earth", "sand", "runway", "stairs"],
    "tree": ["tree", "palm"],
    "lawn_groundcover": ["grass", "field"],
    "path_walkway": ["road", "sidewalk", "path", "floor"],
    "plaza_hardscape": ["road", "sidewalk", "floor", "path"],
    "building_mass": ["building", "house", "skyscraper"],
    "facade_frontage": ["building", "house", "wall", "window", "door"],
    "paving_type": ["road", "sidewalk", "floor", "path"],
    "soft_ground": ["earth", "sand", "field", "grass"],
    "water_surface": ["water", "sea", "river", "pool"],
    "water_body": ["water", "river", "pool", "sea"],
}

METRIC_KEYS = {
    "brightness_level": "brightness_level",
    "luminance_contrast": "luminance_contrast",
    "color_variety": "color_variety",
    "edge_complexity": "edge_complexity",
    "focal_dominance_soft": "edge_complexity",
}


def load_ontology(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def iter_families(onto: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for cat in onto["categories"]:
        for fam in cat["families"]:
            rows.append(
                {
                    "category_id": cat["id"],
                    "category_name": cat["name"],
                    "family_id": fam["id"],
                    "extractors": list(fam.get("extractors") or []),
                    "soft": bool(fam.get("soft")),
                }
            )
    return rows


def sample_images(n: int = 15) -> list[Path]:
    rows = read_jsonl(project_root() / "data" / "processed" / "images.jsonl")
    paths: list[Path] = []
    for r in rows:
        p = Path(r.get("path") or "")
        if not p.exists():
            alt = project_root() / (r.get("rel_path") or "")
            p = alt if alt.exists() else p
        if p.exists():
            paths.append(p)
    if not paths:
        paths = list((project_root() / "data" / "fixtures" / "images").rglob("*.jpg"))
    step = max(1, len(paths) // n)
    return [paths[i] for i in range(0, len(paths), step)][:n]


def compute_metrics(img: Image.Image) -> dict[str, float]:
    arr = np.asarray(img.convert("RGB"), dtype=np.float32) / 255.0
    gray = arr.mean(axis=2)
    gx = np.abs(np.diff(gray, axis=1)).mean()
    gy = np.abs(np.diff(gray, axis=0)).mean()
    lum = (gray * 255).astype(np.uint8)
    hist, _ = np.histogram(lum, bins=256, range=(0, 256))
    p = hist / max(1, hist.sum())
    p = p[p > 0]
    return {
        "brightness_level": float(gray.mean()),
        "luminance_contrast": float(gray.std()),
        "color_variety": float(arr.std(axis=(0, 1)).mean()),
        "edge_complexity": float((gx + gy) / 2.0),
        "color_entropy_norm": float(-(p * np.log2(p)).sum() / 8.0),
    }


class SegmentationBackend:
    def __init__(self) -> None:
        self.ok = False
        self.error: str | None = None
        try:
            import torch
            from transformers import pipeline

            device = 0 if torch.cuda.is_available() else -1
            self.pipe = pipeline(
                "image-segmentation",
                model="facebook/mask2former-swin-small-ade-semantic",
                device=device,
            )
            self.ok = True
            log.info("segmentation ready")
        except Exception as e:
            self.error = str(e)
            log.warning("segmentation unavailable: %s", e)

    def fractions(self, img: Image.Image) -> dict[str, float]:
        if not self.ok:
            return {}
        segs = self.pipe(img)
        total = img.size[0] * img.size[1]
        acc: dict[str, float] = defaultdict(float)
        for s in segs:
            label = str(s.get("label", "")).lower()
            mask = s.get("mask")
            if mask is None:
                continue
            m = np.asarray(mask)
            area = float(m.sum()) if m.dtype != bool else float(m.astype(np.uint8).sum())
            acc[label] += area / total
        return dict(acc)

    def family_fraction(self, fracs: dict[str, float], family_id: str) -> float:
        keys = SEG_LABEL_GROUPS.get(family_id, [])
        return float(sum(fracs.get(k, 0.0) for k in keys))


def phrase_key(phrase: str) -> str:
    return phrase.strip().lower()


def chunked(items: list[str], size: int) -> list[list[str]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


def run_dino_batched(
    vision: TransformersVision, img: Image.Image, phrases: list[str], chunk_size: int = 20
) -> list[dict[str, Any]]:
    all_dets: list[dict[str, Any]] = []
    for batch in chunked(phrases, chunk_size):
        all_dets.extend(vision.ground_nouns(img, batch))
    return all_dets

    return phrase.strip().lower()


def build_phrase_index(families: list[dict[str, Any]]) -> tuple[dict[str, str], dict[str, list[str]]]:
    """Map phrase -> family_id; family_id -> phrases for dino and siglip."""
    dino_map: dict[str, str] = {}
    siglip_map: dict[str, str] = {}
    dino_by_family: dict[str, list[str]] = {}
    siglip_by_family: dict[str, list[str]] = {}

    for fam in families:
        fid = fam["family_id"]
        phrases = FAMILY_PHRASES.get(fid, [fid.replace("_", " ")])
        dino_by_family[fid] = []
        siglip_by_family[fid] = []
        for ext in fam["extractors"]:
            if ext == "dino":
                for p in phrases:
                    k = phrase_key(p)
                    dino_map[k] = fid
                    dino_by_family[fid].append(p)
            elif ext == "siglip":
                for p in phrases:
                    k = phrase_key(p)
                    siglip_map[k] = fid
                    siglip_by_family[fid].append(p)
    return (
        {"dino": dino_map, "siglip": siglip_map},
        {"dino": dino_by_family, "siglip": siglip_by_family},
    )


def aggregate_dino(per_image: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(per_image)
    hit = sum(1 for r in per_image if r.get("n_hits", 0) > 0)
    bests = [r.get("best_score", 0.0) for r in per_image]
    return {
        "extractor": "dino",
        "images_with_detection": hit,
        "hit_rate": hit / max(1, n),
        "mean_best_score": float(np.mean(bests)) if bests else 0.0,
        "max_best_score": float(np.max(bests)) if bests else 0.0,
    }


def aggregate_siglip(per_image: list[dict[str, Any]]) -> dict[str, Any]:
    bests = [r.get("best_score", 0.0) for r in per_image]
    return {
        "extractor": "siglip",
        "mean_best_score": float(np.mean(bests)) if bests else 0.0,
        "std_best_score": float(np.std(bests)) if bests else 0.0,
        "min_best": float(np.min(bests)) if bests else 0.0,
        "max_best": float(np.max(bests)) if bests else 0.0,
    }


def aggregate_metric(per_image: list[dict[str, Any]]) -> dict[str, Any]:
    vals = [r.get("value") for r in per_image if r.get("value") is not None]
    n = len(per_image)
    return {
        "extractor": "metric",
        "mean": float(np.mean(vals)) if vals else None,
        "std": float(np.std(vals)) if vals else None,
        "always_numeric": len(vals) == n,
    }


def aggregate_seg(per_image: list[dict[str, Any]]) -> dict[str, Any]:
    fracs = [r.get("fraction", 0.0) for r in per_image]
    return {
        "extractor": "seg",
        "mean_fraction": float(np.mean(fracs)) if fracs else 0.0,
        "std_fraction": float(np.std(fracs)) if fracs else 0.0,
        "seg_backend_ok": per_image[0].get("seg_ok", False) if per_image else False,
    }


def verdict(agg: dict[str, Any], extractor: str) -> str:
    if extractor == "dino":
        hr = agg.get("hit_rate", 0)
        if hr >= 0.30:
            return "OK"
        if hr >= 0.12:
            return "WEAK"
        return "FAIL"
    if extractor == "siglip":
        if agg.get("std_best_score", 0) >= 0.015 and agg.get("max_best", 0) >= 0.04:
            return "OK"
        if agg.get("max_best", 0) >= 0.025:
            return "WEAK"
        return "FAIL"
    if extractor == "metric":
        return "OK" if agg.get("always_numeric") else "FAIL"
    if extractor == "seg":
        if not agg.get("seg_backend_ok"):
            return "FAIL_BACKEND"
        if agg.get("std_fraction", 0) >= 0.015 or agg.get("mean_fraction", 0) >= 0.04:
            return "OK"
        return "WEAK"
    return "UNKNOWN"


def recommendations(results: dict[str, Any]) -> list[str]:
    recs: list[str] = []
    fails = []
    weak = []
    seg_fail = False
    for fid, fr in results["families"].items():
        for ext, agg in fr["extractors"].items():
            v = agg.get("verdict")
            if v == "FAIL":
                fails.append((fid, ext, agg))
            elif v == "WEAK":
                weak.append((fid, ext, agg))
            elif v == "FAIL_BACKEND":
                seg_fail = True

    if seg_fail:
        recs.append(
            "Segmentation backend failed to load — wire Mask2Former (ADE20K) into pipeline "
            "and run with writable HF cache; seg families cannot be evaluated until fixed."
        )
    else:
        recs.append(
            "Segmentation: Mask2Former ADE20K works for coarse fractions (sky/building/veg/ground). "
            "Add label-group mapping module; consider Cityscapes for road/sidewalk if ADE20K too coarse."
        )

    dino_fails = [f for f, e, _ in fails if e == "dino"]
    if dino_fails:
        recs.append(
            f"DINO weak/fail on {len(dino_fails)} families ({', '.join(dino_fails[:8])}"
            f"{'...' if len(dino_fails) > 8 else ''}): tune phrase lists, lower box_threshold "
            "for rare objects, or add OWL-ViT fallback for small amenities."
        )

    siglip_weak = [f for f, e, _ in weak + fails if e == "siglip"]
    if siglip_weak:
        recs.append(
            "SigLIP soft spatial families (enclosure, openness, focal dominance) show limited "
            "separation — use comparative phrase pairs + softmax within family, or upgrade to "
            "siglip-so400m; consider CLIP spatial pooling for enclosure."
        )

    recs.append(
        "Image metrics (brightness/contrast/edge) are reliable and cheap — implement as "
        "first-class extractors in ground/ module; add horizon/sky line ratio via seg when available."
    )
    recs.append(
        "Pipeline gap: configs/visual_categories_v1.yaml has empty phrases:{} — populate from "
        "FAMILY_PHRASES probe lists after this benchmark; batch DINO per image not per family."
    )
    recs.append(
        "Performance: batch all DINO phrases per image (~1 forward pass) and all SigLIP phrases "
        "per image; cache seg + metrics per image. CPU: ~15 images sufficient for pilot QA."
    )
    return recs


def main() -> None:
    cfg = load_config()
    onto = load_ontology(project_root() / "configs" / "visual_categories_v1.yaml")
    families = iter_families(onto)
    images = sample_images(n=15)
    log.info("benchmarking %d families on %d images", len(families), len(images))

    phrase_maps, by_family = build_phrase_index(families)
    dino_phrases = list(dict.fromkeys(
        p for fam in families for p in FAMILY_PHRASES.get(fam["family_id"], [fam["family_id"].replace("_", " ")])
        if "dino" in fam["extractors"]
    ))
    siglip_phrases = list(dict.fromkeys(
        p for fam in families for p in FAMILY_PHRASES.get(fam["family_id"], [fam["family_id"].replace("_", " ")])
        if "siglip" in fam["extractors"]
    ))

    vision = TransformersVision(cfg)
    seg = SegmentationBackend()
    dino_thr = float(cfg["models"].get("grounding_box_threshold", 0.25))

    # family_id -> extractor -> list of per-image stats
    store: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))

    for i, img_path in enumerate(images):
        log.info("image %d/%d %s", i + 1, len(images), img_path.name)
        img = Image.open(img_path).convert("RGB")
        metrics = compute_metrics(img)
        seg_fracs = seg.fractions(img) if seg.ok else {}

        # --- DINO batch ---
        if dino_phrases:
            dets = run_dino_batched(vision, img, dino_phrases)
            fam_dets: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for d in dets:
                noun = phrase_key(str(d.get("noun", "")))
                fid = phrase_maps["dino"].get(noun)
                if fid:
                    fam_dets[fid].append(d)
            for fid in by_family["dino"]:
                hits = [d for d in fam_dets.get(fid, []) if d.get("score", 0) >= dino_thr]
                best = max((d.get("score", 0) for d in fam_dets.get(fid, [])), default=0.0)
                store[fid]["dino"].append(
                    {"best_score": float(best), "n_hits": len(hits), "labels": [d.get("noun") for d in hits[:3]]}
                )

        # --- SigLIP batch ---
        if siglip_phrases:
            scores = vision.phrase_scores(img, siglip_phrases)
            fam_scores: dict[str, list[tuple[str, float]]] = defaultdict(list)
            for phrase, score in zip(siglip_phrases, scores):
                fid = phrase_maps["siglip"].get(phrase_key(phrase))
                if fid:
                    fam_scores[fid].append((phrase, float(score)))
            for fid in by_family["siglip"]:
                items = fam_scores.get(fid, [])
                if items:
                    best_p, best_s = max(items, key=lambda x: x[1])
                    store[fid]["siglip"].append({"best_score": best_s, "top_phrase": best_p})
                else:
                    store[fid]["siglip"].append({"best_score": 0.0, "top_phrase": None})

        # --- metrics + seg per family ---
        for fam in families:
            fid = fam["family_id"]
            for ext in fam["extractors"]:
                if ext == "metric":
                    key = METRIC_KEYS.get(fid, fid)
                    store[fid]["metric"].append({"value": metrics.get(key)})
                elif ext == "seg":
                    frac = seg.family_fraction(seg_fracs, fid) if seg.ok else 0.0
                    store[fid]["seg"].append({"fraction": frac, "seg_ok": seg.ok})

    results: dict[str, Any] = {
        "n_images": len(images),
        "n_families": len(families),
        "image_paths": [str(p) for p in images],
        "models": {
            "grounding_dino": cfg["models"]["grounding_dino_model"],
            "siglip": cfg["models"]["siglip_model"],
            "segmentation": "facebook/mask2former-swin-small-ade-semantic",
            "segmentation_error": seg.error,
        },
        "families": {},
    }

    for fam in families:
        fid = fam["family_id"]
        fam_out: dict[str, Any] = {"meta": fam, "extractors": {}}
        for ext in fam["extractors"]:
            per_img = store[fid].get(ext, [])
            if ext == "dino":
                agg = aggregate_dino(per_img)
            elif ext == "siglip":
                agg = aggregate_siglip(per_img)
            elif ext == "metric":
                agg = aggregate_metric(per_img)
            elif ext == "seg":
                agg = aggregate_seg(per_img)
            else:
                agg = {"extractor": ext}
            agg["verdict"] = verdict(agg, ext)
            fam_out["extractors"][ext] = agg
        results["families"][fid] = fam_out

    results["recommendations"] = recommendations(results)

    out_dir = project_root() / "Docs" / "visual_categories"
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "phase4_extractor_benchmark.json"
    json_path.write_text(json.dumps(results, indent=2), encoding="utf-8")

    by_v: dict[str, list[str]] = defaultdict(list)
    for fid, fr in results["families"].items():
        for ext, agg in fr["extractors"].items():
            by_v[agg.get("verdict", "?")].append(f"{fid} [{ext}]")

    lines = [
        "=" * 78,
        "PHASE 4 — Visual category extractor benchmark",
        "=" * 78,
        f"Images: {len(images)} pilot photos",
        f"DINO: {cfg['models']['grounding_dino_model']}",
        f"SigLIP: {cfg['models']['siglip_model']}",
        f"Seg: mask2former-swin-small-ade-semantic (ok={seg.ok})",
        "",
        "Verdict: OK = usable pilot signal; WEAK = noisy/low recall; FAIL = unreliable",
        "",
    ]
    for v in ["OK", "WEAK", "FAIL", "FAIL_BACKEND"]:
        if v in by_v:
            lines.append(f"--- {v} ({len(by_v[v])}) ---")
            for item in sorted(by_v[v]):
                lines.append(f"  {item}")
            lines.append("")

    lines.append("--- RECOMMENDATIONS ---")
    for r in results["recommendations"]:
        lines.append(f"  • {r}")
    lines.append("")

    lines.append("Per-family summary:")
    for fid, fr in sorted(results["families"].items()):
        parts = {k: v.get("verdict") for k, v in fr["extractors"].items()}
        lines.append(f"  {fid}: {parts}")

    txt_path = out_dir / "phase4_extractor_benchmark.txt"
    txt_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {json_path}")
    print(f"Wrote {txt_path}")


if __name__ == "__main__":
    main()

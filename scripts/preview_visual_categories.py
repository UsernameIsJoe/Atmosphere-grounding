#!/usr/bin/env python3
"""Build HTML + PNG previews of visual-category extractors on pilot images."""

from __future__ import annotations

import html
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from atmosphere_grounding.config import load_config, project_root, read_jsonl  # noqa: E402
from atmosphere_grounding.ground import TransformersVision  # noqa: E402
from atmosphere_grounding.ground.visual_categories import (  # noqa: E402
    SegmentationBackend,
    extract_image_features,
    load_visual_ontology,
)

OUT = project_root() / "visuals of steps" / "visual_categories"
N_IMAGES = 6

# Families to highlight in overlays / summary cards
SHOW_DINO = [
    "seating",
    "tree",
    "path_walkway",
    "people",
    "building_mass",
    "sign",
    "fence",
    "bicycle",
]
SHOW_SEG = [
    "sky_openness",
    "building_enclosure",
    "vegetation_enclosure",
    "ground_openness",
]
SHOW_METRIC = [
    "brightness_level",
    "luminance_contrast",
    "edge_complexity",
]
SHOW_SOFT = [
    "lit_area_soft",
    "gathering_cluster_soft",
    "sky_openness",
    "focal_dominance_soft",
]

SEG_COLORS = {
    "sky": (80, 160, 255),
    "building": (200, 80, 80),
    "house": (200, 80, 80),
    "skyscraper": (200, 80, 80),
    "tree": (40, 160, 70),
    "grass": (100, 200, 80),
    "plant": (60, 180, 90),
    "road": (140, 140, 140),
    "sidewalk": (170, 170, 150),
    "path": (160, 150, 120),
    "water": (50, 120, 220),
    "fence": (180, 140, 60),
    "wall": (160, 100, 80),
}


def sample_images(n: int) -> list[Path]:
    rows = read_jsonl(project_root() / "data" / "processed" / "images.jsonl")
    paths: list[Path] = []
    for r in rows:
        p = Path(r.get("path") or "")
        if not p.exists():
            alt = project_root() / (r.get("rel_path") or "")
            p = alt if alt.exists() else p
        if p.exists():
            paths.append(p)
    step = max(1, len(paths) // n)
    return [paths[i] for i in range(0, len(paths), step)][:n]


def draw_dino_overlay(img: Image.Image, families: dict) -> Image.Image:
    out = img.copy()
    draw = ImageDraw.Draw(out)
    w, h = out.size
    colors = [
        (255, 140, 0),
        (0, 200, 255),
        (255, 60, 120),
        (180, 255, 40),
        (255, 220, 0),
        (160, 100, 255),
    ]
    ci = 0
    for fid in SHOW_DINO:
        d = (families.get(fid) or {}).get("dino") or {}
        boxes = d.get("boxes") or []
        labels = d.get("labels") or []
        for box, lab in zip(boxes, labels):
            if not box or len(box) != 4:
                continue
            x0, y0, x1, y1 = box
            rect = [x0 * w, y0 * h, x1 * w, y1 * h]
            c = colors[ci % len(colors)]
            draw.rectangle(rect, outline=c, width=3)
            tag = f"{fid}:{lab}"[:40]
            draw.rectangle(
                [rect[0], max(0, rect[1] - 16), rect[0] + 7 * len(tag), rect[1]],
                fill=c,
            )
            draw.text((rect[0] + 2, max(0, rect[1] - 15)), tag, fill=(0, 0, 0))
            ci += 1
    return out


def draw_seg_overlay(img: Image.Image, seg_fracs: dict, seg_backend: SegmentationBackend) -> Image.Image:
    base = img.convert("RGBA")
    if not seg_backend.ok:
        return base.convert("RGB")
    fracs, masks = seg_backend.analyze(img)
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    arr = np.array(overlay)
    for label, mask in masks.items():
        color = SEG_COLORS.get(label)
        if color is None or not mask.any():
            continue
        alpha = 90
        arr[mask, 0] = color[0]
        arr[mask, 1] = color[1]
        arr[mask, 2] = color[2]
        arr[mask, 3] = alpha
    overlay = Image.fromarray(arr, "RGBA")
    return Image.alpha_composite(base, overlay).convert("RGB")


def family_card_html(fid: str, feats: dict) -> str:
    parts = [f"<b>{html.escape(fid)}</b>"]
    if "dino" in feats:
        d = feats["dino"]
        parts.append(
            f"dino: hits={d.get('n_hits')} best={d.get('best_score', 0):.2f} "
            f"labels={html.escape(str(d.get('labels') or [])[:60])}"
        )
    if "seg" in feats:
        s = feats["seg"]
        parts.append(f"seg: fraction={s.get('fraction', 0):.3f}")
    if "siglip" in feats:
        g = feats["siglip"]
        parts.append(
            f"siglip: {html.escape(str(g.get('top_phrase')))} "
            f"({g.get('best_score', 0):.3f})"
        )
    if "metric" in feats:
        m = feats["metric"]
        val = m.get("value")
        parts.append(
            f"metric[{html.escape(str(m.get('formula')))}]="
            f"{val if val is None else f'{val:.3f}'}"
        )
    return "<br/>".join(parts)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    cfg = load_config()
    onto = load_visual_ontology(cfg)
    images = sample_images(N_IMAGES)
    print(f"previewing {len(images)} images → {OUT}")

    vision = TransformersVision(cfg)
    seg_model = (cfg.get("models") or {}).get(
        "segmentation_model",
        (onto.get("extractor_settings") or {}).get(
            "segmentation_model", "facebook/mask2former-swin-small-ade-semantic"
        ),
    )
    seg = SegmentationBackend(seg_model)

    cards: list[str] = []
    summary_rows: list[dict] = []

    for i, path in enumerate(images):
        print(f"  {i+1}/{len(images)} {path}")
        img = Image.open(path).convert("RGB")
        # Downscale for gallery speed/size
        max_side = 900
        scale = min(1.0, max_side / max(img.size))
        if scale < 1:
            img_s = img.resize(
                (int(img.size[0] * scale), int(img.size[1] * scale)),
                Image.Resampling.LANCZOS,
            )
        else:
            img_s = img

        feats = extract_image_features(img_s, onto, vision=vision, seg=seg, cfg=cfg)
        families = feats["families"]

        dino_img = draw_dino_overlay(img_s, families)
        seg_img = draw_seg_overlay(img_s, feats.get("seg_label_fractions") or {}, seg)

        dino_path = OUT / f"{i:02d}_dino.jpg"
        seg_path = OUT / f"{i:02d}_seg.jpg"
        dino_img.save(dino_path, quality=85)
        seg_img.save(seg_path, quality=85)

        highlight_ids = list(
            dict.fromkeys(SHOW_DINO + SHOW_SEG + SHOW_METRIC + SHOW_SOFT)
        )
        card_bits = [
            family_card_html(fid, families[fid])
            for fid in highlight_ids
            if fid in families
        ]

        summary_rows.append(
            {
                "index": i,
                "path": str(path),
                "seg_ok": feats.get("seg_ok"),
                "metrics": feats.get("image_metrics"),
                "sky_fraction": (families.get("sky_openness") or {}).get("seg", {}).get(
                    "fraction"
                ),
                "tree_dino_hits": (families.get("tree") or {})
                .get("dino", {})
                .get("n_hits"),
                "people_dino_hits": (families.get("people") or {})
                .get("dino", {})
                .get("n_hits"),
            }
        )

        cards.append(
            f"""
            <section class="card">
              <h2>Image {i:02d} — {html.escape(path.parent.name)}/{html.escape(path.name)}</h2>
              <div class="pair">
                <figure>
                  <img src="{dino_path.name}" alt="dino"/>
                  <figcaption>DINO boxes (selected families)</figcaption>
                </figure>
                <figure>
                  <img src="{seg_path.name}" alt="seg"/>
                  <figcaption>Segmentation overlay (ADE20K colors)</figcaption>
                </figure>
              </div>
              <div class="feats">{"".join(f"<div class='feat'>{b}</div>" for b in card_bits)}</div>
            </section>
            """
        )

    (OUT / "preview_summary.json").write_text(
        json.dumps(summary_rows, indent=2), encoding="utf-8"
    )

    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>Visual category extractor preview</title>
<style>
  body {{ font-family: "IBM Plex Sans", "Source Sans 3", system-ui, sans-serif;
         margin: 0; background: #1a1d21; color: #e8eaed; }}
  header {{ padding: 1.5rem 2rem; border-bottom: 1px solid #333; }}
  header h1 {{ margin: 0 0 .4rem; font-size: 1.4rem; font-weight: 600; }}
  header p {{ margin: 0; color: #9aa0a6; max-width: 52rem; line-height: 1.45; }}
  .card {{ padding: 1.5rem 2rem; border-bottom: 1px solid #2a2e33; }}
  .pair {{ display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }}
  figure {{ margin: 0; }}
  img {{ width: 100%; height: auto; border-radius: 4px; background: #111; }}
  figcaption {{ color: #9aa0a6; font-size: .85rem; margin-top: .35rem; }}
  .feats {{ display: grid; grid-template-columns: 1fr 1fr; gap: .5rem .75rem;
            margin-top: 1rem; font-size: .82rem; }}
  .feat {{ background: #24282e; padding: .55rem .7rem; border-radius: 4px;
           line-height: 1.35; }}
  @media (max-width: 900px) {{
    .pair, .feats {{ grid-template-columns: 1fr; }}
  }}
</style>
</head>
<body>
<header>
  <h1>Visual category extractors — pilot preview</h1>
  <p>
    {len(images)} Cambridge pilot photos. Left: Grounding DINO boxes for key families.
    Right: Mask2Former ADE20K segmentation overlay. Below: per-family DINO / seg / SigLIP / metric
    scores from <code>configs/visual_categories_v1.yaml</code>.
  </p>
</header>
{"".join(cards)}
</body>
</html>
"""
    html_path = OUT / "index.html"
    html_path.write_text(page, encoding="utf-8")
    print(f"Wrote {html_path}")
    print(f"Open: file://{html_path}")


if __name__ == "__main__":
    main()

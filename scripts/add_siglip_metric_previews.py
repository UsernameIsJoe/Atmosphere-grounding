#!/usr/bin/env python3
"""Add SigLIP + metric visual panels to the category review gallery."""

from __future__ import annotations

import html
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from atmosphere_grounding.config import project_root  # noqa: E402
from atmosphere_grounding.ground.visual_categories import compute_image_metrics  # noqa: E402

OUT = project_root() / "visuals of steps" / "visual_categories"
SCORES = OUT / "full_category_scores.json"

# Soft / SigLIP-primary families to chart
SIGLIP_FAMILIES = [
    "sky_openness",
    "building_enclosure",
    "vegetation_enclosure",
    "ground_openness",
    "lit_area_soft",
    "gathering_cluster_soft",
    "focal_dominance_soft",
    "slope_grade",
    "landmark_object",
]


def _font(size: int = 14):
    for name in (
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def make_metric_panel(img: Image.Image, metrics: dict[str, float]) -> Image.Image:
    """Side-by-side: original | luminance | edge map | metric readout."""
    rgb = img.convert("RGB")
    arr = np.asarray(rgb, dtype=np.float32) / 255.0
    gray = arr.mean(axis=2)

    # Luminance map (grayscale)
    lum = (np.clip(gray, 0, 1) * 255).astype(np.uint8)
    lum_img = Image.fromarray(lum, mode="L").convert("RGB")

    # Edge magnitude map
    gx = np.zeros_like(gray)
    gy = np.zeros_like(gray)
    gx[:, 1:] = np.abs(np.diff(gray, axis=1))
    gy[1:, :] = np.abs(np.diff(gray, axis=0))
    edge = gx + gy
    if edge.max() > 1e-8:
        edge = edge / edge.max()
    edge_img = Image.fromarray((edge * 255).astype(np.uint8), mode="L").convert("RGB")

    # Contrast heat: local deviation from mean (abs)
    contrast = np.abs(gray - gray.mean())
    if contrast.max() > 1e-8:
        contrast = contrast / contrast.max()
    # Magma-ish: dark purple → yellow
    c = contrast
    heat = np.stack([c, c * 0.45, 1.0 - c * 0.7], axis=-1)
    heat = (np.clip(heat, 0, 1) * 255).astype(np.uint8)
    heat_img = Image.fromarray(heat, mode="RGB")

    # Resize tiles to common height
    h = 280
    tiles = []
    labels = ["original", "luminance", "edges", "contrast map"]
    for im in (rgb, lum_img, edge_img, heat_img):
        scale = h / im.size[1]
        tiles.append(
            im.resize((max(1, int(im.size[0] * scale)), h), Image.Resampling.LANCZOS)
        )

    gap = 8
    panel_w = sum(t.size[0] for t in tiles) + gap * (len(tiles) - 1)
    footer_h = 70
    canvas = Image.new("RGB", (panel_w, h + footer_h), (20, 22, 26))
    draw = ImageDraw.Draw(canvas)
    font = _font(13)
    font_sm = _font(11)
    x = 0
    for t, lab in zip(tiles, labels):
        canvas.paste(t, (x, 0))
        draw.rectangle([x, h - 18, x + t.size[0], h], fill=(0, 0, 0))
        draw.text((x + 4, h - 16), lab, fill=(230, 230, 230), font=font_sm)
        x += t.size[0] + gap

    # Metric readout strip
    m = metrics or compute_image_metrics(rgb)
    readout = (
        f"brightness={m.get('mean_luminance', 0):.3f}   "
        f"contrast(std)={m.get('luminance_std', 0):.3f}   "
        f"color_variety={m.get('channel_std_mean', 0):.3f}   "
        f"edge_complexity={m.get('gradient_edge_density', 0):.3f}"
    )
    draw.text((8, h + 18), "IMAGE METRICS", fill=(16, 172, 132), font=font)
    draw.text((8, h + 40), readout, fill=(220, 220, 220), font=font)
    return canvas


def make_siglip_panel(families: dict, width: int = 900) -> Image.Image:
    """Horizontal bar chart of SigLIP phrase scores for soft/spatial families."""
    rows: list[tuple[str, str, float, dict]] = []
    for fid in SIGLIP_FAMILIES:
        f = families.get(fid) or {}
        g = f.get("siglip")
        if not g:
            continue
        scores = g.get("scores") or {}
        if not scores:
            # single best only
            rows.append((fid, str(g.get("top_phrase") or ""), float(g.get("best_score") or 0), {}))
        else:
            # show all phrases for this family, sorted
            for phrase, sc in sorted(scores.items(), key=lambda x: -x[1]):
                rows.append((fid, phrase, float(sc), scores))

    # Deduplicate: keep best 2 phrases per family for readability
    kept: list[tuple[str, str, float]] = []
    count_by: dict[str, int] = {}
    for fid, phrase, sc, _ in rows:
        n = count_by.get(fid, 0)
        if n >= 2:
            continue
        count_by[fid] = n + 1
        kept.append((fid, phrase, sc))

    font = _font(13)
    font_sm = _font(11)
    row_h = 28
    header_h = 48
    pad = 12
    left_w = 200
    mid_w = 360
    bar_max = width - left_w - mid_w - pad * 3
    h = header_h + row_h * max(1, len(kept)) + pad
    canvas = Image.new("RGB", (width, h), (20, 22, 26))
    draw = ImageDraw.Draw(canvas)
    draw.text((pad, 14), "SIGLIP soft / spatial phrase scores", fill=(95, 39, 205), font=font)
    draw.text(
        (pad, 32),
        "Top 2 phrases per family (cosine similarity; higher = better match)",
        fill=(150, 150, 160),
        font=font_sm,
    )

    if not kept:
        draw.text((pad, header_h + 8), "No SigLIP scores available", fill=(200, 80, 80), font=font)
        return canvas

    scores_only = [s for _, _, s in kept]
    smin, smax = min(scores_only), max(scores_only)
    span = max(1e-6, smax - smin)

    y = header_h
    for fid, phrase, sc in kept:
        # normalize bar within panel range for visibility
        t = (sc - smin) / span
        bar_w = int(8 + t * (bar_max - 8))
        draw.text((pad, y + 6), fid[:28], fill=(180, 185, 195), font=font_sm)
        draw.text((pad + left_w, y + 6), phrase[:48], fill=(230, 230, 235), font=font_sm)
        x0 = pad + left_w + mid_w
        draw.rectangle([x0, y + 6, x0 + bar_max, y + 20], fill=(40, 44, 52))
        # purple bar
        draw.rectangle([x0, y + 6, x0 + bar_w, y + 20], fill=(120, 80, 220))
        draw.text((x0 + bar_max + 6, y + 5), f"{sc:.3f}", fill=(200, 200, 210), font=font_sm)
        y += row_h

    return canvas


def update_review_html() -> None:
    review = OUT / "review_all_categories.html"
    if not review.exists():
        print("review_all_categories.html missing; skip HTML patch")
        return
    text = review.read_text(encoding="utf-8")

    # Replace 2-col pair blocks with 2x2 quad including siglip/metric when present
    # Simpler: inject a note + replace pair class CSS and rewrite each image section's media via regenerate page stub.
    # We'll do a lightweight injection: after each existing .pair, if not already expanded, user regenerates full page.
    # Instead rewrite by injecting stylesheet + appending panels via string replace per image index.

    for i in range(6):
        dino = f"{i:02d}_dino.jpg"
        seg = f"{i:02d}_seg.jpg"
        sig = f"{i:02d}_siglip.jpg"
        met = f"{i:02d}_metric.jpg"
        old = f"""              <div class="pair">
                <figure>
                  <img src="{dino}" alt="dino"/>
                  <figcaption>DINO overlay (selected families)</figcaption>
                </figure>
                <figure>
                  <img src="{seg}" alt="seg"/>
                  <figcaption>Segmentation overlay</figcaption>
                </figure>
              </div>"""
        new = f"""              <div class="quad">
                <figure>
                  <img src="{dino}" alt="dino"/>
                  <figcaption>DINO — localized object boxes</figcaption>
                </figure>
                <figure>
                  <img src="{seg}" alt="seg"/>
                  <figcaption>SEG — semantic view fractions</figcaption>
                </figure>
                <figure>
                  <img src="{sig}" alt="siglip"/>
                  <figcaption>SigLIP — soft phrase score bars</figcaption>
                </figure>
                <figure>
                  <img src="{met}" alt="metric"/>
                  <figcaption>METRIC — luminance / edges / contrast</figcaption>
                </figure>
              </div>"""
        if old in text:
            text = text.replace(old, new)

    if ".quad" not in text:
        text = text.replace(
            ".pair { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin: 1rem 0; }",
            ".pair { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin: 1rem 0; }\n"
            "  .quad { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin: 1rem 0; }",
        )
        text = text.replace(
            "@media (max-width: 900px) {{ .pair {{ grid-template-columns: 1fr; }} }}",
            "@media (max-width: 900px) { .pair, .quad { grid-template-columns: 1fr; } }",
        )
        # fix if double braces already expanded wrong
        text = text.replace(
            "@media (max-width: 900px) { .pair { grid-template-columns: 1fr; } }",
            "@media (max-width: 900px) { .pair, .quad { grid-template-columns: 1fr; } }",
        )

    # Update header blurb
    text = text.replace(
        "Scores = DINO hits/confidence, SEG pixel fractions, SigLIP soft phrases, image metrics.",
        "Visuals for all four extractors: DINO boxes, SEG masks, SigLIP phrase bars, metric maps "
        "(luminance / edges / contrast).",
    )
    review.write_text(text, encoding="utf-8")
    print(f"Updated {review}")


def main() -> None:
    if not SCORES.exists():
        raise SystemExit(f"Missing {SCORES}; run build_category_review.py first")

    data = json.loads(SCORES.read_text(encoding="utf-8"))
    for row in data["images"]:
        i = int(row["index"])
        path = Path(row["path"])
        print(f"panels {i:02d} {path.name}")
        img = Image.open(path).convert("RGB")
        max_side = 900
        scale = min(1.0, max_side / max(img.size))
        if scale < 1:
            img = img.resize(
                (int(img.size[0] * scale), int(img.size[1] * scale)),
                Image.Resampling.LANCZOS,
            )

        # Flatten families from categories
        families: dict = {}
        for cat_fams in (row.get("categories") or {}).values():
            families.update(cat_fams)

        metrics = row.get("image_metrics") or compute_image_metrics(img)
        sig_panel = make_siglip_panel(families, width=max(900, img.size[0]))
        met_panel = make_metric_panel(img, metrics)

        sig_panel.save(OUT / f"{i:02d}_siglip.jpg", quality=90)
        met_panel.save(OUT / f"{i:02d}_metric.jpg", quality=90)

    update_review_html()

    # Also patch index.html gallery if present
    index = OUT / "index.html"
    if index.exists():
        t = index.read_text(encoding="utf-8")
        if "siglip.jpg" not in t:
            note = (
                "<p style='padding:0 2rem;color:#9aa0a6'>"
                "SigLIP + metric visual panels are on "
                "<a href='review_all_categories.html' style='color:#8ab4f8'>review_all_categories.html</a>."
                "</p>"
            )
            t = t.replace("</header>", "</header>\n" + note)
            index.write_text(t, encoding="utf-8")
            print(f"Updated {index}")

    print("Done — open review_all_categories.html")


if __name__ == "__main__":
    main()

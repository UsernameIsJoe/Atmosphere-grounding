#!/usr/bin/env python3
"""Full category review: 12 top-level categories + all family scores per preview image."""

from __future__ import annotations

import html
import json
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from atmosphere_grounding.config import load_config, project_root, read_jsonl  # noqa: E402
from atmosphere_grounding.ground import TransformersVision  # noqa: E402
from atmosphere_grounding.ground.visual_categories import (  # noqa: E402
    SegmentationBackend,
    extract_image_features,
    load_visual_ontology,
)

# Reuse the existing preview gallery folder / image set
OUT = project_root() / "visuals of steps" / "visual_categories"
N_IMAGES = 6


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


def score_cells(feats: dict) -> str:
    bits: list[str] = []
    if "dino" in feats:
        d = feats["dino"]
        bits.append(
            f"<span class='tag dino'>DINO</span> hits={d.get('n_hits', 0)} "
            f"best={float(d.get('best_score') or 0):.2f}"
        )
        labs = d.get("labels") or []
        if labs:
            bits.append(f"<span class='muted'>{html.escape(', '.join(str(x) for x in labs[:3]))}</span>")
    if "seg" in feats:
        s = feats["seg"]
        ok = s.get("backend_ok")
        bits.append(
            f"<span class='tag seg'>SEG</span> frac={float(s.get('fraction') or 0):.3f}"
            + ("" if ok else " <span class='warn'>(backend off)</span>")
        )
    if "siglip" in feats:
        g = feats["siglip"]
        bits.append(
            f"<span class='tag siglip'>SIGLIP</span> "
            f"{html.escape(str(g.get('top_phrase') or '—'))} "
            f"({float(g.get('best_score') or 0):.3f})"
        )
    if "metric" in feats:
        m = feats["metric"]
        val = m.get("value")
        val_s = "—" if val is None else f"{float(val):.3f}"
        bits.append(
            f"<span class='tag metric'>METRIC</span> "
            f"{html.escape(str(m.get('formula') or ''))}={val_s}"
        )
    return "<br/>".join(bits) if bits else "—"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    cfg = load_config()
    onto = load_visual_ontology(cfg)
    images = sample_images(N_IMAGES)
    print(f"scoring {len(images)} images for full category review → {OUT}")

    vision = TransformersVision(cfg)
    seg_model = (cfg.get("models") or {}).get(
        "segmentation_model",
        (onto.get("extractor_settings") or {}).get(
            "segmentation_model", "facebook/mask2former-swin-small-ade-semantic"
        ),
    )
    seg = SegmentationBackend(seg_model)

    # Taxonomy block
    tax_parts: list[str] = []
    for i, cat in enumerate(onto["categories"], 1):
        fams = "".join(
            f"<li><code>{html.escape(f['id'])}</code> "
            f"<span class='muted'>{html.escape(', '.join(f.get('extractors') or []))}</span></li>"
            for f in cat["families"]
        )
        tax_parts.append(
            f"""
            <div class="tax-card">
              <h3>{i}. {html.escape(cat.get('name') or cat['id'])}</h3>
              <p class="muted"><code>{html.escape(cat['id'])}</code> · {len(cat['families'])} families</p>
              <ul>{fams}</ul>
            </div>
            """
        )

    image_sections: list[str] = []
    all_scores: list[dict] = []

    for i, path in enumerate(images):
        print(f"  {i+1}/{len(images)} {path}")
        img = Image.open(path).convert("RGB")
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

        # Prefer existing overlay JPGs from preview script
        dino_name = f"{i:02d}_dino.jpg"
        seg_name = f"{i:02d}_seg.jpg"
        dino_exists = (OUT / dino_name).exists()
        seg_exists = (OUT / seg_name).exists()

        cat_tables: list[str] = []
        by_cat: dict[str, dict] = {}
        for cat in onto["categories"]:
            rows_html: list[str] = []
            cat_payload: dict[str, dict] = {}
            for fam in cat["families"]:
                fid = fam["id"]
                ffeats = families.get(fid) or {}
                cat_payload[fid] = ffeats
                rows_html.append(
                    f"<tr><td><code>{html.escape(fid)}</code></td>"
                    f"<td>{html.escape(', '.join(fam.get('extractors') or []))}</td>"
                    f"<td>{score_cells(ffeats)}</td></tr>"
                )
            by_cat[cat["id"]] = cat_payload
            cat_tables.append(
                f"""
                <details open class="cat-block">
                  <summary><strong>{html.escape(cat.get('name') or cat['id'])}</strong>
                    <span class="muted">({html.escape(cat['id'])})</span></summary>
                  <table>
                    <thead><tr><th>Family</th><th>Extractors</th><th>Scores</th></tr></thead>
                    <tbody>{''.join(rows_html)}</tbody>
                  </table>
                </details>
                """
            )

        all_scores.append(
            {
                "index": i,
                "path": str(path),
                "place_id": path.parent.name,
                "seg_ok": feats.get("seg_ok"),
                "image_metrics": feats.get("image_metrics"),
                "categories": by_cat,
            }
        )

        media = ""
        if dino_exists or seg_exists:
            media = f"""
              <div class="pair">
                <figure>
                  <img src="{dino_name if dino_exists else ''}" alt="dino"/>
                  <figcaption>DINO overlay (selected families)</figcaption>
                </figure>
                <figure>
                  <img src="{seg_name if seg_exists else ''}" alt="seg"/>
                  <figcaption>Segmentation overlay</figcaption>
                </figure>
              </div>
            """

        image_sections.append(
            f"""
            <section class="card" id="img-{i:02d}">
              <h2>Example image {i:02d} — {html.escape(path.parent.name)} / {html.escape(path.name)}</h2>
              <p class="muted">seg_ok={feats.get('seg_ok')} ·
                brightness={feats['image_metrics'].get('mean_luminance', 0):.3f} ·
                contrast={feats['image_metrics'].get('luminance_std', 0):.3f} ·
                edge={feats['image_metrics'].get('gradient_edge_density', 0):.3f}</p>
              {media}
              <h3>All category family scores</h3>
              {''.join(cat_tables)}
            </section>
            """
        )

    (OUT / "full_category_scores.json").write_text(
        json.dumps({"ontology_version": onto.get("version"), "images": all_scores}, indent=2),
        encoding="utf-8",
    )

    nav = " · ".join(
        f'<a href="#img-{i:02d}">Image {i:02d}</a>' for i in range(len(images))
    )

    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>Full visual-category review — 12 categories × example images</title>
<style>
  :root {{
    --bg: #14171b; --card: #1c2128; --text: #e8eaed; --muted: #9aa0a6;
    --line: #2a3038; --dino: #ff9f43; --seg: #54a0ff; --siglip: #5f27cd; --metric: #10ac84;
  }}
  body {{ margin:0; font-family: "IBM Plex Sans", "Source Sans 3", system-ui, sans-serif;
         background: var(--bg); color: var(--text); line-height: 1.4; }}
  header, .tax, .card {{ padding: 1.25rem 1.75rem; border-bottom: 1px solid var(--line); }}
  header h1 {{ margin: 0 0 .35rem; font-size: 1.35rem; }}
  .muted {{ color: var(--muted); }}
  .nav {{ margin-top: .75rem; font-size: .9rem; }}
  .nav a {{ color: #8ab4f8; margin-right: .25rem; }}
  .tax-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: .75rem; }}
  .tax-card {{ background: var(--card); border-radius: 6px; padding: .85rem 1rem; }}
  .tax-card h3 {{ margin: 0 0 .25rem; font-size: .98rem; }}
  .tax-card ul {{ margin: .4rem 0 0; padding-left: 1.1rem; font-size: .82rem; }}
  .pair {{ display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin: 1rem 0; }}
  img {{ width: 100%; border-radius: 4px; background: #0d0f12; }}
  figure {{ margin: 0; }}
  figcaption {{ color: var(--muted); font-size: .82rem; margin-top: .3rem; }}
  table {{ width: 100%; border-collapse: collapse; font-size: .82rem; margin: .5rem 0 1rem; }}
  th, td {{ text-align: left; vertical-align: top; padding: .4rem .5rem; border-bottom: 1px solid var(--line); }}
  th {{ color: var(--muted); font-weight: 600; }}
  code {{ font-size: .9em; }}
  details.cat-block {{ background: var(--card); border-radius: 6px; padding: .55rem .75rem; margin: .55rem 0; }}
  summary {{ cursor: pointer; }}
  .tag {{ display: inline-block; font-size: .68rem; font-weight: 700; padding: .05rem .35rem;
          border-radius: 3px; margin-right: .25rem; color: #111; }}
  .tag.dino {{ background: var(--dino); }}
  .tag.seg {{ background: var(--seg); }}
  .tag.siglip {{ background: var(--siglip); color: #fff; }}
  .tag.metric {{ background: var(--metric); }}
  .warn {{ color: #ff6b6b; }}
  @media (max-width: 900px) {{ .pair {{ grid-template-columns: 1fr; }} }}
</style>
</head>
<body>
<header>
  <h1>Full review — 12 visual categories × example images</h1>
  <p class="muted">
    Ontology from <code>configs/visual_categories_v1.yaml</code>.
    Scores = DINO hits/confidence, SEG pixel fractions, SigLIP soft phrases, image metrics.
    {len(images)} pilot example images.
  </p>
  <div class="nav">{nav} · <a href="index.html">Overlay gallery</a> ·
    <a href="full_category_scores.json">JSON scores</a></div>
</header>

<section class="tax">
  <h2>The 12 top-level categories</h2>
  <div class="tax-grid">{''.join(tax_parts)}</div>
</section>

{''.join(image_sections)}
</body>
</html>
"""
    out_html = OUT / "review_all_categories.html"
    out_html.write_text(page, encoding="utf-8")
    print(f"Wrote {out_html}")
    print(f"Wrote {OUT / 'full_category_scores.json'}")


if __name__ == "__main__":
    main()

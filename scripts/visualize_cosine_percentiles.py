#!/usr/bin/env python3
"""Show review↔image SigLIP pairs at each 5th percentile of cosine similarity.

Lets you eyeball where a mismatch threshold should sit.
Uses existing cached data + SigLIP; writes HTML under visuals of steps/.
"""

from __future__ import annotations

import base64
import io
import json
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "visuals of steps"
PROCESSED = ROOT / "data" / "processed"
CACHE = PROCESSED / "review_image_pair_scores.jsonl"


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def _img_b64(path: Path, max_side: int = 420) -> str:
    im = Image.open(path).convert("RGB")
    w, h = im.size
    scale = min(1.0, max_side / max(w, h))
    if scale < 1:
        im = im.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, format="JPEG", quality=82)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def score_pairs(force: bool = False) -> list[dict]:
    if CACHE.exists() and not force:
        rows = read_jsonl(CACHE)
        if rows and "cosine" in rows[0]:
            print(f"reusing {len(rows)} cached pair scores from {CACHE}")
            return rows

    import torch
    from transformers import AutoModel, AutoProcessor

    from atmosphere_grounding.config import load_config

    cfg = load_config(str(ROOT / "configs" / "cambridge_pilot.yaml"))
    places = pd.read_parquet(PROCESSED / "places.parquet")
    name_by = dict(zip(places["place_id"], places["name"]))
    reviews = read_jsonl(PROCESSED / "reviews.jsonl")
    images = read_jsonl(PROCESSED / "images.jsonl")

    imgs_by: dict[str, list[dict]] = {}
    for im in images:
        imgs_by.setdefault(im["place_id"], []).append(im)

    siglip_name = cfg["models"]["siglip_model"]
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"loading SigLIP only ({siglip_name}) on {device} …")
    proc = AutoProcessor.from_pretrained(siglip_name)
    model = AutoModel.from_pretrained(siglip_name).to(device).eval()

    def cosine(img: Image.Image, text: str) -> float:
        inputs = proc(text=[text], images=img, padding="max_length", return_tensors="pt")
        inputs = {k: v.to(device) for k, v in inputs.items()}
        with torch.no_grad():
            out = model(**inputs)
            img_e = out.image_embeds
            txt_e = out.text_embeds
            img_e = img_e / img_e.norm(dim=-1, keepdim=True)
            txt_e = txt_e / txt_e.norm(dim=-1, keepdim=True)
            return float((img_e @ txt_e.T).squeeze().detach().cpu())

    rows: list[dict] = []
    n_places = len(imgs_by)
    for pi, rev in enumerate(reviews):
        text = (rev.get("text") or "").strip()
        if not text:
            continue
        pid = rev["place_id"]
        place_imgs = imgs_by.get(pid) or []
        if not place_imgs:
            continue
        snippet = text[:120]
        for imeta in place_imgs:
            path = Path(imeta.get("path") or "")
            if not path.exists():
                alt = ROOT / (imeta.get("rel_path") or "")
                path = alt if alt.exists() else path
            if not path.exists():
                continue
            img = Image.open(path).convert("RGB")
            cos = cosine(img, snippet)
            rows.append(
                {
                    "place_id": pid,
                    "place_name": name_by.get(pid, pid),
                    "review_index": int(rev.get("review_index", 0)),
                    "image_index": imeta.get("image_index"),
                    "image_path": imeta.get("rel_path") or str(path),
                    "text": text,
                    "text_snippet": snippet,
                    "cosine": round(cos, 6),
                }
            )
        if (pi + 1) % 25 == 0:
            print(f"  … {pi + 1}/{len(reviews)} reviews, {len(rows)} pairs", flush=True)

    write_jsonl(CACHE, rows)
    print(f"wrote {len(rows)} pairs across ~{n_places} places → {CACHE}")
    return rows


def pick_percentile_examples(rows: list[dict], step: int = 5) -> list[dict]:
    scored = sorted(rows, key=lambda r: r["cosine"])
    n = len(scored)
    if n == 0:
        return []
    cos = np.array([r["cosine"] for r in scored], dtype=float)
    picks: list[dict] = []
    used: set[tuple] = set()
    for pct in range(0, 101, step):
        target = float(np.percentile(cos, pct))
        # nearest unused pair to this percentile value
        best_i = None
        best_d = 1e9
        for i, r in enumerate(scored):
            key = (r["place_id"], r["review_index"], r["image_index"])
            if key in used and pct not in (0, 100):
                continue
            d = abs(r["cosine"] - target)
            if d < best_d:
                best_d = d
                best_i = i
        assert best_i is not None
        r = dict(scored[best_i])
        key = (r["place_id"], r["review_index"], r["image_index"])
        used.add(key)
        r["percentile"] = pct
        r["percentile_target_cosine"] = round(target, 6)
        picks.append(r)
    return picks


def _esc(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _llm_by_review() -> tuple[dict[tuple[str, int], list[dict]], dict[tuple[str, int], list[dict]]]:
    passa: dict[tuple[str, int], list[dict]] = {}
    passb: dict[tuple[str, int], list[dict]] = {}
    for m in read_jsonl(PROCESSED / "mentions.jsonl"):
        key = (m["place_id"], int(m.get("review_index", 0)))
        passa.setdefault(key, []).append(m)
    for m in read_jsonl(PROCESSED / "mentions_fused.jsonl"):
        key = (m["place_id"], int(m.get("review_index", 0)))
        passb.setdefault(key, []).append(m)
    return passa, passb


def _format_llm_block(label: str, items: list[dict], *, fused: bool = False) -> str:
    if not items:
        return (
            f'<div class="llm"><div class="lab">{label}</div>'
            f'<p class="empty">(no LLM hit for this review)</p></div>'
        )
    bits = []
    for it in items:
        atm = _esc(str(it.get("atmosphere") or ""))
        phrase = _esc(str(it.get("phrase") or "").strip() or "—")
        nouns = ", ".join(_esc(str(n)) for n in (it.get("nouns") or [])) or "—"
        conf = it.get("visual_confidence", "—")
        line = (
            f"<div class='hit'>"
            f"<div><b>atmosphere:</b> {atm} &nbsp; <b>conf:</b> {conf}</div>"
            f"<div><b>phrase:</b> {phrase}</div>"
            f"<div><b>nouns:</b> {nouns}</div>"
        )
        if fused:
            supported = ", ".join(_esc(str(n)) for n in (it.get("supported_by_objects") or [])[:12]) or "—"
            note = _esc(str(it.get("conflict_note") or "").strip())
            line += f"<div><b>supported_by_objects:</b> {supported}</div>"
            if note:
                line += f"<div class='note'><b>conflict_note:</b> {note}</div>"
        line += "</div>"
        bits.append(line)
    return f'<div class="llm"><div class="lab">{label}</div>{"".join(bits)}</div>'


def write_html(picks: list[dict], all_rows: list[dict]) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    cos_all = np.array([r["cosine"] for r in all_rows], dtype=float)
    stats = {
        "n_pairs": len(all_rows),
        "mean": float(cos_all.mean()),
        "std": float(cos_all.std()),
        "p25": float(np.percentile(cos_all, 25)),
        "p50": float(np.percentile(cos_all, 50)),
        "p75": float(np.percentile(cos_all, 75)),
    }
    passa, passb = _llm_by_review()

    cards = []
    for r in picks:
        path = ROOT / r["image_path"]
        if not path.exists():
            path = Path(r["image_path"])
        b64 = _img_b64(path) if path.exists() else ""
        img_html = (
            f'<img src="data:image/jpeg;base64,{b64}" alt="pair"/>'
            if b64
            else "<em>missing image</em>"
        )
        text = _esc(r.get("text") or "")
        key = (r["place_id"], int(r["review_index"]))
        a_html = _format_llm_block("PASS A LLM (comment-only)", passa.get(key) or [])
        b_html = _format_llm_block(
            "PASS B LLM (fusion with image objects)", passb.get(key) or [], fused=True
        )
        cards.append(
            f"""
<section class="card">
  <div class="meta">
    <span class="pct">P{r['percentile']:02d}</span>
    <span class="cos">cosine = {r['cosine']:.4f}</span>
    <span class="tgt">(percentile target {r['percentile_target_cosine']:.4f})</span>
  </div>
  <div class="place">{_esc(str(r.get('place_name','')))}</div>
  <div class="row">
    <div class="img">{img_html}</div>
    <div class="txt">
      <div class="lab">RAW REVIEW</div>
      <p>{text}</p>
      {a_html}
      {b_html}
    </div>
  </div>
</section>
"""
        )

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"/>
<title>Step 8 — cosine percentiles (review ↔ image)</title>
<style>
  body {{ font-family: ui-sans-serif, system-ui, sans-serif; background:#0b0b0f; color:#e0f0f0;
         margin:0; padding:24px; line-height:1.4; }}
  h1 {{ font-size:1.35rem; margin:0 0 8px; }}
  .sub {{ color:#a0a8b0; max-width:900px; margin-bottom:20px; }}
  .stats {{ background:#12121a; border:1px solid #333348; padding:12px 16px; border-radius:8px;
            margin-bottom:22px; font-size:0.92rem; }}
  .card {{ background:#12121a; border:1px solid #333348; border-radius:10px; padding:14px 16px;
           margin-bottom:18px; }}
  .meta {{ display:flex; gap:14px; flex-wrap:wrap; align-items:baseline; margin-bottom:6px; }}
  .pct {{ font-weight:800; color:#f0f080; font-size:1.1rem; }}
  .cos {{ font-weight:700; color:#50f0a0; }}
  .tgt {{ color:#808890; font-size:0.85rem; }}
  .place {{ color:#90e0d0; margin-bottom:10px; font-weight:600; }}
  .row {{ display:grid; grid-template-columns: 0.9fr 1.3fr; gap:16px; }}
  @media (max-width: 900px) {{ .row {{ grid-template-columns: 1fr; }} }}
  img {{ width:100%; height:auto; border-radius:6px; display:block; }}
  .lab {{ font-size:0.75rem; letter-spacing:0.04em; color:#90e0d0; margin:10px 0 6px; font-weight:700; }}
  .txt > .lab:first-child {{ margin-top:0; }}
  .txt p {{ margin:0; color:#c8d0d8; white-space:pre-wrap; font-size:0.92rem; }}
  .llm {{ margin-top:10px; padding:10px 12px; background:#0b0b0f; border:1px solid #2a2a3a; border-radius:8px; }}
  .llm .lab {{ margin-top:0; color:#f0f080; }}
  .hit {{ margin-top:8px; font-size:0.88rem; color:#c8d0d8; border-top:1px solid #222232; padding-top:8px; }}
  .hit:first-of-type {{ border-top:none; padding-top:0; margin-top:0; }}
  .hit b {{ color:#e0f0f0; }}
  .note {{ color:#f0a0c0; margin-top:4px; }}
  .empty {{ color:#808890; font-style:italic; }}
  .guide {{ color:#f0a0c0; }}
</style></head>
<body>
<h1>Step 8 — review ↔ image pairs at each 5th percentile</h1>
<p class="sub">
  Each card is one Google review + one photo from the <em>same place</em>, with SigLIP cosine,
  plus the LLM outputs for that review (Pass A comment-only, Pass B fusion).
  Use this to pick a similarity threshold by eye.
</p>
<div class="stats">
  <div><b>{stats['n_pairs']}</b> same-place review–image pairs scored</div>
  <div>cosine mean={stats['mean']:.4f} · std={stats['std']:.4f} ·
       P25={stats['p25']:.4f} · P50={stats['p50']:.4f} · P75={stats['p75']:.4f}</div>
  <div class="guide">Current place-level rule (z&lt;−0.75) sat near cosine ≈ 0.04 on place means —
      compare that band to the cards below (pair scores are not identical to place means).</div>
</div>
{''.join(cards)}
</body></html>
"""
    out = OUT / "step8_cosine_percentiles.html"
    out.write_text(html, encoding="utf-8")
    return out


def write_summary_table(picks: list[dict], all_rows: list[dict]) -> Path:
    passa, passb = _llm_by_review()
    cos = np.array([r["cosine"] for r in all_rows], dtype=float)
    lines = [
        "percentile,target_cosine,example_cosine,place,review_index,image_index,"
        "passA_atmosphere,passA_phrase,passA_nouns,passB_atmosphere,passB_phrase,passB_nouns,text_snippet"
    ]
    for r in picks:
        key = (r["place_id"], int(r["review_index"]))
        a = (passa.get(key) or [None])[0]
        b = (passb.get(key) or [None])[0]
        snippet = (r.get("text_snippet") or "").replace('"', "'")[:80]
        a_atm = (a or {}).get("atmosphere", "")
        a_phrase = str((a or {}).get("phrase") or "").replace('"', "'")[:80]
        a_nouns = "|".join((a or {}).get("nouns") or [])
        b_atm = (b or {}).get("atmosphere", "")
        b_phrase = str((b or {}).get("phrase") or "").replace('"', "'")[:80]
        b_nouns = "|".join((b or {}).get("nouns") or [])
        lines.append(
            f"{r['percentile']},{r['percentile_target_cosine']},{r['cosine']},"
            f"\"{r.get('place_name','')}\",{r['review_index']},{r['image_index']},"
            f"\"{a_atm}\",\"{a_phrase}\",\"{a_nouns}\","
            f"\"{b_atm}\",\"{b_phrase}\",\"{b_nouns}\",\"{snippet}\""
        )
    dist = ["percentile,cosine"]
    for pct in range(0, 101, 5):
        dist.append(f"{pct},{float(np.percentile(cos, pct)):.6f}")
    out = OUT / "step8_cosine_percentiles.csv"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    (OUT / "step8_cosine_distribution_percentiles.csv").write_text(
        "\n".join(dist) + "\n", encoding="utf-8"
    )
    return out


def main() -> None:
    import sys

    force = "--force" in sys.argv
    rows = score_pairs(force=force)
    picks = pick_percentile_examples(rows, step=5)
    html = write_html(picks, rows)
    csv = write_summary_table(picks, rows)
    print("HTML:", html)
    print("CSV:", csv)
    print("Open the HTML in a browser to compare pairs by eye.")


if __name__ == "__main__":
    main()

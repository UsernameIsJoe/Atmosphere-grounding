#!/usr/bin/env python3
"""Independent preview visuals for pipeline steps 2, 4, 6, 7, 8.

Uses existing data under data/ only — does not re-run collect/LLM/vision.
Outputs PNGs (and HTML map) into visuals of steps/.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "visuals of steps"
PROCESSED = ROOT / "data" / "processed"


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def step2_map() -> Path:
    """Map of collected places with review/image counts."""
    places = pd.read_parquet(PROCESSED / "places.parquet")
    reviews = read_jsonl(PROCESSED / "reviews.jsonl")
    images = read_jsonl(PROCESSED / "images.jsonl")
    n_rev = Counter(r["place_id"] for r in reviews)
    n_img = Counter(i["place_id"] for i in images)
    places = places.copy()
    places["n_reviews_collected"] = places["place_id"].map(lambda p: n_rev.get(p, 0))
    places["n_images_collected"] = places["place_id"].map(lambda p: n_img.get(p, 0))
    places = places.sort_values(["lat", "lng"], ascending=[False, True]).reset_index(drop=True)
    places["idx"] = places.index + 1

    fig = plt.figure(figsize=(14, 8.2), facecolor="#0b0b0f")
    gs = fig.add_gridspec(1, 2, width_ratios=[1.35, 1.0], wspace=0.08)
    ax = fig.add_subplot(gs[0, 0])
    ax.set_facecolor("#0b0b0f")
    sizes = 90 + places["n_images_collected"] * 55
    sc = ax.scatter(
        places["lng"],
        places["lat"],
        s=sizes,
        c=places["n_reviews_collected"],
        cmap="cool",
        alpha=0.92,
        edgecolors="#e0f0f0",
        linewidths=0.7,
        zorder=3,
    )
    for _, row in places.iterrows():
        ax.text(
            row["lng"],
            row["lat"],
            str(int(row["idx"])),
            ha="center",
            va="center",
            fontsize=6.5,
            color="#0b0b0f",
            fontweight="bold",
            zorder=4,
        )
    cbar = fig.colorbar(sc, ax=ax, fraction=0.035, pad=0.02)
    cbar.set_label("Reviews collected", color="#e0f0f0")
    cbar.ax.yaxis.set_tick_params(color="#e0f0f0")
    plt.setp(plt.getp(cbar.ax.axes, "yticklabels"), color="#e0f0f0")
    ax.set_xlabel("Longitude", color="#e0f0f0")
    ax.set_ylabel("Latitude", color="#e0f0f0")
    ax.set_title(
        f"Step 2 — Harvard–MIT places collected\n"
        f"{len(places)} places · {len(reviews)} reviews · {len(images)} images\n"
        f"(marker size ∝ images; color ∝ reviews; numbers → key)",
        color="#e0f0f0",
        fontsize=11,
    )
    ax.tick_params(colors="#a0a8b0")
    for spine in ax.spines.values():
        spine.set_color("#333348")
    ax.grid(True, color="#1a1a28", linestyle="--", linewidth=0.5)
    for n_img, label in [(1, "1 image"), (3, "3 images")]:
        ax.scatter([], [], s=90 + n_img * 55, c="#90e0d0", edgecolors="#e0f0f0", label=label)
    ax.legend(facecolor="#12121a", edgecolor="#333348", labelcolor="#e0f0f0", fontsize=8)

    axk = fig.add_subplot(gs[0, 1])
    axk.set_facecolor("#0b0b0f")
    axk.axis("off")
    axk.set_title("Place key (R = reviews, I = images)", color="#e0f0f0", fontsize=10, loc="left")
    lines = [
        f"{int(r.idx):2d}. {str(r['name'])[:34]:<34}  R{int(r.n_reviews_collected)} I{int(r.n_images_collected)}"
        for _, r in places.iterrows()
    ]
    mid = (len(lines) + 1) // 2
    for col, chunk in enumerate([lines[:mid], lines[mid:]]):
        axk.text(
            0.02 + col * 0.52,
            0.97,
            "\n".join(chunk),
            transform=axk.transAxes,
            va="top",
            ha="left",
            fontsize=6.2,
            family="monospace",
            color="#c8d0d8",
            linespacing=1.35,
        )

    out = OUT / "step2_places_map.png"
    fig.subplots_adjust(left=0.06, right=0.98, top=0.90, bottom=0.08, wspace=0.06)
    fig.savefig(out, dpi=160, facecolor=fig.get_facecolor())
    plt.close(fig)

    table = places[
        ["idx", "name", "lat", "lng", "n_reviews_collected", "n_images_collected", "place_id"]
    ]
    table.to_csv(OUT / "step2_places_table.csv", index=False)

    # Lightweight offline HTML map (Leaflet CDN) for pan/zoom preview
    markers_js = []
    for _, r in places.iterrows():
        popup = (
            f"<b>{r['name']}</b><br/>"
            f"#{int(r['idx'])} · reviews={int(r.n_reviews_collected)} · images={int(r.n_images_collected)}"
        )
        markers_js.append(
            f"L.circleMarker([{r.lat},{r.lng}],{{radius:{4 + int(r.n_images_collected)*2},"
            f"color:'#e0f0f0',weight:1,fillColor:'#50f0a0',fillOpacity:0.85}})"
            f".bindPopup({json.dumps(popup)}).addTo(map);"
        )
    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"/>
<title>Step 2 places map</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>html,body,#map{{height:100%;margin:0;background:#0b0b0f}}</style></head>
<body><div id="map"></div>
<script>
const map=L.map('map').setView([42.365,-71.105],13);
L.tileLayer('https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png',{{
  attribution:'&copy; OSM &copy; CARTO', maxZoom:19
}}).addTo(map);
{chr(10).join(markers_js)}
</script></body></html>
"""
    (OUT / "step2_places_map.html").write_text(html, encoding="utf-8")
    return out


ATM_COLORS = {"inviting": "#7a8cff", "safe": "#50f0a0", "calm": "#90e0d0"}


def _wrap(text: str, width: int = 78) -> str:
    words = (text or "").replace("\n", " ").split()
    lines: list[str] = []
    cur: list[str] = []
    for w in words:
        trial = (" ".join(cur + [w])).strip()
        if len(trial) > width and cur:
            lines.append(" ".join(cur))
            cur = [w]
        else:
            cur.append(w)
    if cur:
        lines.append(" ".join(cur))
    return "\n".join(lines)


def _place_names() -> dict[str, str]:
    places = pd.read_parquet(PROCESSED / "places.parquet")
    return dict(zip(places["place_id"], places["name"]))


def _review_index(reviews: list[dict]) -> dict[tuple[str, int], dict]:
    return {(r["place_id"], int(r["review_index"])): r for r in reviews}


def _pick_pass_a_examples(n: int = 3) -> list[tuple[dict, dict]]:
    reviews = read_jsonl(PROCESSED / "reviews.jsonl")
    mentions = read_jsonl(PROCESSED / "mentions.jsonl")
    rev = _review_index(reviews)
    scored: list[tuple[float, int, dict, dict]] = []
    for i, m in enumerate(mentions):
        r = rev.get((m["place_id"], int(m["review_index"])))
        if not r or not (r.get("text") or "").strip():
            continue
        text = r["text"].strip()
        if len(text) < 40:
            continue
        phrase = (m.get("phrase") or "").strip()
        nouns = m.get("nouns") or []
        score = len(nouns) * 2 + (4 if phrase else 0) + min(len(text), 220) / 100
        scored.append((score, i, m, r))
    scored.sort(key=lambda t: t[0], reverse=True)
    picks: list[tuple[dict, dict]] = []
    seen: set[str] = set()
    for _, _, m, r in scored:
        atm = m["atmosphere"]
        if atm in seen:
            continue
        picks.append((m, r))
        seen.add(atm)
        if len(picks) >= n:
            break
    return picks


def _pick_pass_b_examples(n: int = 3) -> list[tuple[dict, dict, dict | None]]:
    reviews = read_jsonl(PROCESSED / "reviews.jsonl")
    mentions = read_jsonl(PROCESSED / "mentions.jsonl")
    fused = read_jsonl(PROCESSED / "mentions_fused.jsonl")
    rev = _review_index(reviews)
    a_idx = {(m["place_id"], int(m["review_index"]), m["atmosphere"]): m for m in mentions}
    scored: list[tuple[float, int, dict, dict, dict | None]] = []
    for i, f in enumerate(fused):
        r = rev.get((f["place_id"], int(f["review_index"])))
        if not r or not (r.get("text") or "").strip():
            continue
        a = a_idx.get((f["place_id"], int(f["review_index"]), f["atmosphere"]))
        objs = f.get("supported_by_objects") or []
        phrase = (f.get("phrase") or "").strip()
        nouns = f.get("nouns") or []
        a_nouns = set((a or {}).get("nouns") or [])
        changed = a is not None and a_nouns != set(nouns)
        # Prefer cases where fusion actually uses image objects / rewrites phrase
        score = (
            len(objs) * 4
            + (5 if phrase else 0)
            + (4 if changed else 0)
            + (2 if f.get("conflict_note") else 0)
            + min(len(r["text"]), 200) / 100
        )
        if not phrase and not objs and not changed:
            continue
        scored.append((score, i, f, r, a))
    scored.sort(key=lambda t: t[0], reverse=True)
    picks: list[tuple[dict, dict, dict | None]] = []
    seen: set[str] = set()
    for _, _, f, r, a in scored:
        if f["atmosphere"] in seen:
            continue
        picks.append((f, r, a))
        seen.add(f["atmosphere"])
        if len(picks) >= n:
            break
    return picks


def step4_pass_a() -> Path:
    """Show how Pass A LLM turns raw comments into atmosphere + nouns."""
    names = _place_names()
    examples = _pick_pass_a_examples(3)
    fig, axes = plt.subplots(len(examples), 1, figsize=(12, 3.4 * len(examples)), facecolor="#0b0b0f")
    if len(examples) == 1:
        axes = [axes]
    fig.suptitle(
        "Step 4 — Pass A LLM examples (comment-only)\n"
        "Input: review text  →  Output: atmosphere label, evidence phrase, visual nouns",
        color="#e0f0f0",
        fontsize=12,
        y=0.995,
    )
    for ax, (m, r) in zip(axes, examples):
        ax.set_facecolor("#12121a")
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis("off")
        place = names.get(m["place_id"], m["place_id"])
        atm = m["atmosphere"]
        color = ATM_COLORS.get(atm, "#e0f0f0")
        ax.add_patch(
            mpatches.FancyBboxPatch(
                (0.01, 0.06), 0.98, 0.88, boxstyle="round,pad=0.01", linewidth=1.2, edgecolor=color, facecolor="#0b0b0f"
            )
        )
        ax.text(0.03, 0.88, f"{place}", color="#e0f0f0", fontsize=10, fontweight="bold", va="top")
        ax.text(0.03, 0.76, "COMMENT (input)", color="#90e0d0", fontsize=8, fontweight="bold", va="top")
        # Keep comment short so it never overlaps the LLM output block
        comment = _wrap(r["text"], 92)
        comment_lines = comment.split("\n")
        if len(comment_lines) > 4:
            comment = "\n".join(comment_lines[:4]) + " …"
        ax.text(0.03, 0.71, comment, color="#c8d0d8", fontsize=8, va="top", family="sans-serif")
        phrase = (m.get("phrase") or "").strip() or "(no phrase extracted — nouns only)"
        nouns = ", ".join(m.get("nouns") or []) or "—"
        ax.text(0.03, 0.32, "LLM OUTPUT", color=color, fontsize=8, fontweight="bold", va="top")
        ax.text(
            0.03,
            0.26,
            f"atmosphere: {atm}\n"
            f"phrase: {phrase}\n"
            f"nouns: {nouns}\n"
            f"visual_confidence: {m.get('visual_confidence', '—')}",
            color=color,
            fontsize=8.5,
            va="top",
        )
    out = OUT / "step4_passA_llm_examples.png"
    old = OUT / "step4_passA_pool_to_pick.png"
    if old.exists():
        old.unlink()
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(out, dpi=160, facecolor=fig.get_facecolor())
    plt.close(fig)
    return out


def step6_pass_b() -> Path:
    """Show how Pass B fusion revises Pass A using detected image objects."""
    names = _place_names()
    examples = _pick_pass_b_examples(3)
    fig, axes = plt.subplots(len(examples), 1, figsize=(12.5, 3.6 * len(examples)), facecolor="#0b0b0f")
    if len(examples) == 1:
        axes = [axes]
    fig.suptitle(
        "Step 6 — Pass B fusion LLM examples (comment + image object list)\n"
        "Input: review + detected photo objects  →  Output: revised atmosphere phrase/nouns (+ which objects support it)",
        color="#e0f0f0",
        fontsize=12,
        y=0.995,
    )
    for ax, (f, r, a) in zip(axes, examples):
        ax.set_facecolor("#12121a")
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis("off")
        place = names.get(f["place_id"], f["place_id"])
        atm = f["atmosphere"]
        color = ATM_COLORS.get(atm, "#e0f0f0")
        ax.add_patch(
            mpatches.FancyBboxPatch(
                (0.01, 0.05), 0.98, 0.90, boxstyle="round,pad=0.01", linewidth=1.2, edgecolor=color, facecolor="#0b0b0f"
            )
        )
        ax.text(0.03, 0.88, f"{place}  ·  atmosphere: {atm}", color="#e0f0f0", fontsize=10, fontweight="bold", va="top")
        ax.text(0.03, 0.76, "COMMENT", color="#90e0d0", fontsize=8, fontweight="bold", va="top")
        ax.text(0.03, 0.72, _wrap(r["text"], 95), color="#c8d0d8", fontsize=7.8, va="top")

        img_objs = f.get("image_objects") or []
        ax.text(
            0.03,
            0.42,
            "IMAGE OBJECTS (from photos at this place):  " + _wrap(", ".join(img_objs[:14]) + (" …" if len(img_objs) > 14 else ""), 90),
            color="#f0f080",
            fontsize=7.8,
            va="top",
        )
        a_nouns = ", ".join((a or {}).get("nouns") or []) or "—"
        a_phrase = ((a or {}).get("phrase") or "").strip() or "—"
        b_nouns = ", ".join(f.get("nouns") or []) or "—"
        b_phrase = (f.get("phrase") or "").strip() or "—"
        supported = ", ".join(f.get("supported_by_objects") or []) or "(none marked)"
        ax.text(
            0.03,
            0.28,
            f"Pass A (comment-only):  nouns=[{a_nouns}]   phrase={a_phrase}\n"
            f"Pass B (after fusion):  nouns=[{b_nouns}]   phrase={b_phrase}\n"
            f"supported_by_objects:   {supported}",
            color=color,
            fontsize=8,
            va="top",
            fontweight="bold",
        )
        note = (f.get("conflict_note") or "").strip()
        if note:
            ax.text(0.03, 0.08, "note: " + _wrap(note, 100), color="#b01070", fontsize=7, va="top")

    out = OUT / "step6_passB_llm_examples.png"
    for stale in ("step6_passB_pool_to_pick.png", "step6_passB_noun_shift.png"):
        p = OUT / stale
        if p.exists():
            p.unlink()
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(out, dpi=160, facecolor=fig.get_facecolor())
    plt.close(fig)
    return out


def _draw_box(img: Image.Image, box: list[float], color=(240, 96, 32), width: int = 3) -> Image.Image:
    im = img.copy()
    draw = ImageDraw.Draw(im)
    w, h = im.size
    x0, y0, x1, y1 = box
    rect = [x0 * w, y0 * h, x1 * w, y1 * h]
    draw.rectangle(rect, outline=color, width=width)
    return im


def _crop_norm(img: Image.Image, box: list[float], pad: float = 0.0) -> Image.Image:
    w, h = img.size
    x0, y0, x1, y1 = box
    if pad:
        x0, y0 = max(0, x0 - pad), max(0, y0 - pad)
        x1, y1 = min(1, x1 + pad), min(1, y1 + pad)
    return img.crop((int(x0 * w), int(y0 * h), int(x1 * w), int(y1 * h)))


def _box_area(box: list[float]) -> float:
    return max(0.0, box[2] - box[0]) * max(0.0, box[3] - box[1])


def step7_examples() -> list[Path]:
    """Three evidence instances with box overlay + scene/object/context panels."""
    places = pd.read_parquet(PROCESSED / "places.parquet")
    name_by_id = dict(zip(places["place_id"], places["name"]))
    evidence = read_jsonl(PROCESSED / "evidence.jsonl")

    # Prefer readable physical nouns, mid-size boxes, one example per atmosphere.
    prefer = {
        "bench",
        "tree",
        "path",
        "walkway",
        "fence",
        "gate",
        "sign",
        "lamp",
        "building",
        "people",
        "grass",
        "lawn",
        "fountain",
        "stairs",
        "bicycle",
        "playground",
        "canopy",
    }
    skip_place_tokens = ("restroom", "loo", "toilet", "parking", "garage")
    prefer_place_tokens = ("park", "yard", "common", "square", "plaza", "court", "garden", "green")

    by_atm: dict[str, list[tuple[float, dict]]] = defaultdict(list)
    for e in evidence:
        if not e.get("box") or not e.get("noun") or not e.get("image_path"):
            continue
        path = ROOT / e["image_path"]
        if not path.exists():
            continue
        place_name = str(name_by_id.get(e["place_id"], "")).lower()
        if any(tok in place_name for tok in skip_place_tokens):
            continue
        noun = str(e["noun"]).lower()
        if not any(tok in noun for tok in prefer):
            continue
        # skip garbled multi-token duplicates like "building building facade"
        tokens = noun.split()
        if len(tokens) != len(set(tokens)):
            continue
        area = _box_area(e["box"])
        if area < 0.015 or area > 0.40:
            continue
        scores = [
            float(e.get("scene_score") or 0),
            float(e.get("object_score") or 0),
            float(e.get("context_score") or 0),
        ]
        mx = max(scores)
        # Prefer object/context wins and park-like places for clearer demos
        level_bonus = 0.012 if e.get("level") == "object" else 0.006 if e.get("level") == "context" else 0.0
        place_bonus = 0.01 if any(tok in place_name for tok in prefer_place_tokens) else 0.0
        rank = mx + level_bonus + place_bonus + min(area, 0.2) * 0.05
        by_atm[e["atmosphere"]].append((rank, e))

    picks: list[dict] = []
    used_images: set[str] = set()
    used_nouns: set[str] = set()
    for atm in ("inviting", "safe", "calm"):
        cands = sorted(by_atm.get(atm, []), key=lambda t: t[0], reverse=True)
        chosen = None
        for _, e in cands:
            noun_key = str(e["noun"]).lower()
            if e["image_path"] in used_images or noun_key in used_nouns:
                continue
            chosen = e
            break
        if chosen is None and cands:
            chosen = cands[0][1]
        if chosen is not None:
            picks.append(chosen)
            used_images.add(chosen["image_path"])
            used_nouns.add(str(chosen["noun"]).lower())

    # remove old example files so stale picks don't linger
    for old in OUT.glob("step7_example_*.png"):
        old.unlink()

    outs = []
    for i, e in enumerate(picks[:3], start=1):
        path = ROOT / e["image_path"]
        img = Image.open(path).convert("RGB")
        boxed = _draw_box(img, e["box"], color=(240, 96, 32), width=4)
        # label on boxed image
        draw = ImageDraw.Draw(boxed)
        w, h = boxed.size
        x0, y0, _, _ = e["box"]
        label = f"{e['noun']} ({e['level']})"
        draw.rectangle(
            [x0 * w, max(0, y0 * h - 22), x0 * w + 8 * len(label), y0 * h],
            fill=(240, 96, 32),
        )
        draw.text((x0 * w + 4, max(0, y0 * h - 20)), label, fill=(11, 11, 15))

        obj = _crop_norm(img, e["box"])
        ctx = _crop_norm(img, e["box"], pad=0.18)

        fig = plt.figure(figsize=(12, 7.4), facecolor="#0b0b0f")
        gs = fig.add_gridspec(3, 3, height_ratios=[3.0, 1.35, 1.0], hspace=0.45, wspace=0.25)
        ax0 = fig.add_subplot(gs[0, :])
        ax0.imshow(boxed)
        ax0.axis("off")
        place = name_by_id.get(e["place_id"], e["place_id"])
        ax0.set_title(
            f"Step 7 example {i} — {place}\n"
            f"Claim: atmosphere “{e['atmosphere']}” is visually linked to noun “{e['noun']}”\n"
            f"Orange box = detected region for that noun  ·  backend={e.get('backend')} (SigLIP via HuggingFace transformers)",
            color="#e0f0f0",
            fontsize=10,
        )

        panels = [
            ("scene = full photo", img, e.get("scene_score"), "scene"),
            ("object = tight box crop", obj, e.get("object_score"), "object"),
            ("context = box + padding", ctx, e.get("context_score"), "context"),
        ]
        for j, (label, crop, score, level_name) in enumerate(panels):
            ax = fig.add_subplot(gs[1, j])
            ax.imshow(crop)
            ax.axis("off")
            sc = f"{float(score):.4f}" if score is not None else "—"
            winner = "  ★ ablation winner" if e.get("level") == level_name else ""
            ax.set_title(f"{label}\nSigLIP score {sc}{winner}", color="#e0f0f0", fontsize=9)
            if e.get("level") == level_name:
                for spine in ax.spines.values():
                    spine.set_visible(True)
                    spine.set_color("#f06020")
                    spine.set_linewidth(2.5)

        axg = fig.add_subplot(gs[2, :])
        axg.set_facecolor("#0b0b0f")
        axg.axis("off")
        axg.text(
            0.0,
            0.95,
            "How to read this figure\n"
            "• Ablation = score the same noun–atmosphere claim three ways (full image / object crop / padded context) and keep the best.\n"
            f"• Ablation winner = “{e.get('level')}” here — that crop scored highest with SigLIP (cosine similarity of image vs text embedding).\n"
            "• transformers = Hugging Face model backend (not a heuristic). Higher score ⇒ stronger visual match for that crop.\n"
            "• Orange box comes from Grounding DINO object detection; Step 7 asks which scale of that detection best supports the atmosphere noun.",
            color="#c8d0d8",
            fontsize=8.5,
            va="top",
            ha="left",
            transform=axg.transAxes,
            linespacing=1.45,
        )

        safe_noun = str(e["noun"]).replace(" ", "_").replace("/", "-")
        out = OUT / f"step7_example_{i}_{e['atmosphere']}_{safe_noun}.png"
        fig.savefig(out, dpi=150, facecolor=fig.get_facecolor(), bbox_inches="tight")
        plt.close(fig)
        outs.append(out)

    # Companion: one clear winner from each ablation category on one page
    outs.append(step7_winner_categories(evidence, name_by_id, prefer, skip_place_tokens))
    return outs


def step7_winner_categories(
    evidence: list[dict],
    name_by_id: dict[str, str],
    prefer: set[str],
    skip_place_tokens: tuple[str, ...],
) -> Path:
    """One visual: best clear example of scene / object / context winners side by side."""
    by_level: dict[str, list[tuple[float, dict]]] = defaultdict(list)
    for e in evidence:
        if not e.get("box") or not e.get("noun") or not e.get("image_path"):
            continue
        path = ROOT / e["image_path"]
        if not path.exists():
            continue
        place_name = str(name_by_id.get(e["place_id"], "")).lower()
        if any(tok in place_name for tok in skip_place_tokens):
            continue
        noun = str(e["noun"]).lower()
        if not any(tok in noun for tok in prefer):
            continue
        tokens = noun.split()
        if len(tokens) != len(set(tokens)):
            continue
        area = _box_area(e["box"])
        if area < 0.02 or area > 0.40:
            continue
        scores = {
            "scene": float(e.get("scene_score") or 0),
            "object": float(e.get("object_score") or 0),
            "context": float(e.get("context_score") or 0),
        }
        winner = e.get("level")
        if winner not in scores:
            continue
        others = [s for lev, s in scores.items() if lev != winner]
        margin = scores[winner] - max(others)
        if margin < 0.01:
            continue
        place_bonus = 0.02 if any(
            tok in place_name for tok in ("park", "yard", "common", "square", "plaza", "garden", "green")
        ) else 0.0
        by_level[str(winner)].append((margin + place_bonus, e))

    picks: dict[str, dict] = {}
    used_imgs: set[str] = set()
    for lev in ("scene", "object", "context"):
        cands = sorted(by_level.get(lev, []), key=lambda t: t[0], reverse=True)
        # Prefer park-like places when available
        ordered = sorted(
            cands,
            key=lambda t: (
                any(
                    tok in str(name_by_id.get(t[1]["place_id"], "")).lower()
                    for tok in ("park", "yard", "common", "square", "plaza", "garden", "green")
                ),
                t[0],
            ),
            reverse=True,
        )
        for _, e in ordered:
            if e["image_path"] in used_imgs:
                continue
            picks[lev] = e
            used_imgs.add(e["image_path"])
            break

    fig, axes = plt.subplots(1, 3, figsize=(14, 5.6), facecolor="#0b0b0f")
    fig.suptitle(
        "Step 7 — Ablation winners by category\n"
        "Same idea three times: which crop best matches the atmosphere word? (★ = winner)",
        color="#e0f0f0",
        fontsize=12,
    )
    explain = {
        "scene": "SCENE winner\nFull photo beat the tight box\nand the surroundings crop.\n→ vibe is whole-place, not one object.",
        "object": "OBJECT winner\nTight box around the noun\nbeat the full photo & surroundings.\n→ the thing itself carries the signal.",
        "context": "CONTEXT winner\nSurroundings around the noun\nbeat the object alone & full photo.\n→ atmosphere is in what’s around it.",
    }
    for ax, lev in zip(axes, ("scene", "object", "context")):
        ax.set_facecolor("#0b0b0f")
        e = picks.get(lev)
        if e is None:
            ax.axis("off")
            ax.set_title(f"No clear {lev} example", color="#e0f0f0")
            continue
        img = Image.open(ROOT / e["image_path"]).convert("RGB")
        boxed = _draw_box(img, e["box"], color=(240, 96, 32), width=4)
        draw = ImageDraw.Draw(boxed)
        w, h = boxed.size
        x0, y0, _, _ = e["box"]
        tag = f"{e['noun']}"
        draw.rectangle([x0 * w, max(0, y0 * h - 22), x0 * w + 8 * len(tag) + 8, y0 * h], fill=(240, 96, 32))
        draw.text((x0 * w + 4, max(0, y0 * h - 20)), tag, fill=(11, 11, 15))
        ax.imshow(boxed)
        ax.axis("off")
        place = name_by_id.get(e["place_id"], e["place_id"])
        sc = (
            f"scene {float(e.get('scene_score') or 0):.3f}  |  "
            f"object {float(e.get('object_score') or 0):.3f}  |  "
            f"context {float(e.get('context_score') or 0):.3f}"
        )
        ax.set_title(
            f"★ {lev.upper()} winner\n{place}\n"
            f"“{e['atmosphere']}” ↔ {e['noun']}\n{sc}",
            color="#e0f0f0",
            fontsize=9,
        )
        # orange frame for the winning column
        for spine in ax.spines.values():
            spine.set_visible(True)
            spine.set_color("#f06020")
            spine.set_linewidth(2.5)

    # footer explanations under each column via fig text
    for i, lev in enumerate(("scene", "object", "context")):
        fig.text(
            0.14 + i * 0.31,
            0.04,
            explain[lev],
            color="#c8d0d8",
            fontsize=8,
            ha="center",
            va="bottom",
            linespacing=1.35,
        )

    out = OUT / "step7_ablation_winners_by_category.png"
    fig.subplots_adjust(left=0.03, right=0.97, top=0.82, bottom=0.22, wspace=0.12)
    fig.savefig(out, dpi=150, facecolor=fig.get_facecolor())
    plt.close(fig)
    return out


def step8_correlation() -> Path:
    places = pd.read_parquet(PROCESSED / "places.parquet")
    name_by_id = dict(zip(places["place_id"], places["name"]))
    corr = read_jsonl(PROCESSED / "place_correlation.jsonl")
    df = pd.DataFrame(corr)
    df["name"] = df["place_id"].map(name_by_id)
    df["align"] = df["review_image_align_mean"].fillna(0)
    df["jaccard"] = df["noun_jaccard"].fillna(0)
    df["z"] = df["review_image_align_z"].fillna(0) if "review_image_align_z" in df.columns else 0.0
    mode = (corr[0].get("mismatch_mode") if corr else None) or "cosine_percentile"
    cut = None
    for r in corr:
        if r.get("mismatch_cosine_threshold") is not None:
            cut = float(r["mismatch_cosine_threshold"])
            break

    fig = plt.figure(figsize=(13.5, 7.4), facecolor="#0b0b0f")
    gs = fig.add_gridspec(2, 2, height_ratios=[3.6, 1.7], hspace=0.38, wspace=0.28)
    ax = fig.add_subplot(gs[0, 0])
    ax2 = fig.add_subplot(gs[0, 1])
    axg = fig.add_subplot(gs[1, :])

    ax.set_facecolor("#0b0b0f")
    colors = df["likely_mismatch"].map(lambda m: "#b01070" if m else "#50f0a0")
    ax.scatter(df["align"], df["z"], c=colors, s=70, edgecolors="#e0f0f0", linewidths=0.5, alpha=0.9)
    if cut is not None:
        ax.axvline(cut, color="#f0f080", linestyle="--", linewidth=1.2, alpha=0.9, label=f"P10 cut ({cut:.4f})")
    ax.set_xlabel("Review↔photo cosine (SigLIP)  — higher = comments & photos agree more", color="#e0f0f0")
    ax.set_ylabel("Cosine z-score vs other places", color="#e0f0f0")
    ax.set_title(f"Step 8 — mismatch by cosine ({mode})", color="#e0f0f0")
    ax.tick_params(colors="#a0a8b0")
    for spine in ax.spines.values():
        spine.set_color("#333348")
    ax.grid(True, color="#1a1a28", linestyle="--", linewidth=0.5)
    handles = [
        mpatches.Patch(color="#50f0a0", label="match (above P10)"),
        mpatches.Patch(color="#b01070", label="mismatch (≤ P10)"),
    ]
    if cut is not None:
        handles.append(mpatches.Patch(color="#f0f080", label="P10 threshold"))
    ax.legend(handles=handles, facecolor="#12121a", labelcolor="#e0f0f0", fontsize=8)
    for _, row in df.nsmallest(3, "align").iterrows():
        ax.annotate(str(row["name"])[:18], (row["align"], row["z"]), fontsize=6, color="#c8d0d8")

    ax2.set_facecolor("#0b0b0f")
    df2 = df.sort_values("align", ascending=True)
    cols = df2["likely_mismatch"].map(lambda m: "#b01070" if m else "#3020e0")
    ax2.barh(df2["name"].str[:28], df2["align"], color=cols, edgecolor="#0b0b0f")
    if cut is not None:
        ax2.axvline(cut, color="#f0f080", linestyle="--", linewidth=1.2, alpha=0.9)
    ax2.set_xlabel("Review↔photo cosine (SigLIP)", color="#e0f0f0")
    ax2.set_title("Places ranked by comment–photo cosine", color="#e0f0f0")
    ax2.tick_params(colors="#a0a8b0", labelsize=7)
    for spine in ax2.spines.values():
        spine.set_color("#333348")
    ax2.legend(
        handles=[
            mpatches.Patch(color="#3020e0", label="match"),
            mpatches.Patch(color="#b01070", label="mismatch ≤ P10"),
        ],
        facecolor="#12121a",
        labelcolor="#e0f0f0",
        fontsize=8,
        loc="lower right",
    )

    n_mis = int(df["likely_mismatch"].sum())
    rate = float(df["likely_mismatch"].mean()) if len(df) else 0.0
    cut_txt = f"{cut:.4f}" if cut is not None else "—"
    axg.set_facecolor("#0b0b0f")
    axg.axis("off")
    axg.text(
        0.0,
        0.95,
        "Plain-language read\n"
        "• Score = SigLIP cosine between reviews and photos at each place.\n"
        f"• Match threshold = P10 (human-chosen): cosine ≤ {cut_txt} → mismatch.\n"
        f"• Current run: {n_mis}/{len(df)} places flagged ({rate:.0%}).",
        color="#c8d0d8",
        fontsize=9,
        va="top",
        ha="left",
        transform=axg.transAxes,
        linespacing=1.45,
    )

    out = OUT / "step8_place_correlation.png"
    fig.savefig(out, dpi=160, facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)

    summary = {
        "n_places": len(df),
        "mismatch_rate": float(df["likely_mismatch"].mean()) if len(df) else 0.0,
        "mismatch_mode": mode,
        "mismatch_cosine_threshold": cut,
        "mean_noun_jaccard": float(df["jaccard"].mean()) if len(df) else 0.0,
        "mean_review_image_align": float(df["align"].mean()) if len(df) else 0.0,
    }
    (OUT / "step8_correlation_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    return out


def write_index(paths: dict[str, list[Path] | Path]) -> Path:
    lines = [
        "# Visuals of pipeline steps",
        "",
        "Generated from existing `data/` artifacts (no full pipeline re-run).",
        "",
        "| Step | File | What it shows |",
        "|------|------|----------------|",
        "| 2 Collect | `step2_places_map.png` / `.html` / `step2_places_table.csv` | Map of places; reviews & images per place |",
        "| 4 Pass A | `step4_passA_llm_examples.png` | Real comments → LLM atmosphere / phrase / nouns |",
        "| 6 Pass B | `step6_passB_llm_examples.png` | Same comments + photo objects → fused LLM output |",
        "| 7 Grounding | `step7_example_*.png`, `step7_ablation_winners_by_category.png` | Per-example ablations + scene/object/context winners |",
        "| 8 Correlation | `step8_place_correlation.png` | Place-level text↔image alignment (+ plain-language note) |",
        "",
        "## How to read Steps 7–8",
        "",
        "### Step 7",
        "- **Orange box**: detected region for the noun.",
        "- **scene / object / context**: three crops; highest score = ablation winner.",
        "- **`step7_ablation_winners_by_category.png`**: one clear winner from each category side by side.",
        "",
        "### Step 8 (plain language)",
        "- **Mismatch flag** now uses **SigLIP review↔photo cosine** (relative z-score), not noun-string overlap.",
        "- Magenta = this place’s comment–photo cosine is unusually low vs other places (z < −0.75).",
        "- Noun Jaccard is still stored for diagnostics only.",
        "",
        "Regenerate:",
        "",
        "```bash",
        ".venv/bin/python scripts/visualize_pipeline_steps.py",
        "```",
        "",
    ]
    out = OUT / "README.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    print("Writing into", OUT)
    p2 = step2_map()
    print(" step2", p2.name)
    p4 = step4_pass_a()
    print(" step4", p4.name)
    p6 = step6_pass_b()
    print(" step6", p6.name)
    p7 = step7_examples()
    for p in p7:
        print(" step7", p.name)
    p8 = step8_correlation()
    print(" step8", p8.name)
    write_index({"2": p2, "4": p4, "6": p6, "7": p7, "8": p8})
    print("Done.")


if __name__ == "__main__":
    main()

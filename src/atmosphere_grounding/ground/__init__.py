"""Visual grounding: image–phrase match, noun boxes, scene/object/context ablation."""

from __future__ import annotations

import logging
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw

from atmosphere_grounding.config import (
    active_atmospheres,
    ensure_dirs,
    read_jsonl,
    resolve_path,
    write_json,
    write_jsonl,
)

log = logging.getLogger(__name__)


def _load_rgb(path: Path) -> Image.Image:
    return Image.open(path).convert("RGB")


def _crop_box(img: Image.Image, box: tuple[float, float, float, float]) -> Image.Image:
    w, h = img.size
    x0, y0, x1, y1 = box
    return img.crop(
        (
            max(0, int(x0 * w)),
            max(0, int(y0 * h)),
            min(w, int(x1 * w)),
            min(h, int(y1 * h)),
        )
    )


def _context_ring(
    img: Image.Image, box: tuple[float, float, float, float], pad: float = 0.15
) -> Image.Image:
    """Crop expanded context around box, then mask out the object interior."""
    w, h = img.size
    x0, y0, x1, y1 = box
    cx0 = max(0.0, x0 - pad)
    cy0 = max(0.0, y0 - pad)
    cx1 = min(1.0, x1 + pad)
    cy1 = min(1.0, y1 + pad)
    context = _crop_box(img, (cx0, cy0, cx1, cy1))
    # Gray out object region relative to context crop
    rw = max(1, context.size[0])
    rh = max(1, context.size[1])
    # object coords in context crop
    ox0 = int((x0 - cx0) / max(1e-6, (cx1 - cx0)) * rw)
    oy0 = int((y0 - cy0) / max(1e-6, (cy1 - cy0)) * rh)
    ox1 = int((x1 - cx0) / max(1e-6, (cx1 - cx0)) * rw)
    oy1 = int((y1 - cy0) / max(1e-6, (cy1 - cy0)) * rh)
    masked = context.copy()
    draw = ImageDraw.Draw(masked)
    draw.rectangle([ox0, oy0, ox1, oy1], fill=(128, 128, 128))
    return masked


def _mean_color_vec(img: Image.Image) -> np.ndarray:
    arr = np.asarray(img.resize((64, 64)), dtype=np.float32) / 255.0
    return arr.reshape(-1)


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    na = np.linalg.norm(a) + 1e-8
    nb = np.linalg.norm(b) + 1e-8
    return float(np.dot(a, b) / (na * nb))


# --- Heuristic backend (no GPU weights) ---

ATMOSPHERE_COLOR_PRIORS = {
    # Very rough RGB mood priors for smoke tests / fixtures
    "calm": np.array([0.45, 0.55, 0.50], dtype=np.float32),
    "safe": np.array([0.55, 0.55, 0.40], dtype=np.float32),
    "inviting": np.array([0.60, 0.50, 0.35], dtype=np.float32),
}


def heuristic_phrase_scores(img: Image.Image, phrases: list[str]) -> list[float]:
    arr = np.asarray(img.resize((32, 32)), dtype=np.float32) / 255.0
    mean = arr.mean(axis=(0, 1))
    scores = []
    for phrase in phrases:
        prior = None
        for atm, vec in ATMOSPHERE_COLOR_PRIORS.items():
            if atm in phrase.lower():
                prior = vec
                break
        if prior is None:
            prior = np.array([0.5, 0.5, 0.5], dtype=np.float32)
        scores.append(float(1.0 - np.linalg.norm(mean - prior) / np.sqrt(3)))
    return scores


def heuristic_ground_nouns(
    img: Image.Image, nouns: list[str]
) -> list[dict[str, Any]]:
    """Place synthetic boxes by hashing noun → grid cell (deterministic for fixtures)."""
    w, h = img.size
    boxes: list[dict[str, Any]] = []
    for i, noun in enumerate(nouns):
        hsh = abs(hash(noun)) % 1000
        gx = (hsh % 3) / 3.0
        gy = ((hsh // 3) % 3) / 3.0
        size = 0.22
        x0 = min(0.75, gx + 0.05)
        y0 = min(0.75, gy + 0.05)
        boxes.append(
            {
                "noun": noun,
                "box": [x0, y0, min(1.0, x0 + size), min(1.0, y0 + size)],
                "score": 0.4 + (i % 5) * 0.05,
                "backend": "heuristic",
            }
        )
    return boxes


# --- Transformers backend (optional) ---

class TransformersVision:
    def __init__(self, cfg: dict[str, Any]) -> None:
        import torch
        from transformers import AutoModel, AutoProcessor, AutoImageProcessor

        self.cfg = cfg
        self.torch = torch
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        log.info("loading vision models on %s …", self.device)
        siglip_name = cfg["models"]["siglip_model"]
        self.siglip_proc = AutoProcessor.from_pretrained(siglip_name)
        self.siglip = AutoModel.from_pretrained(siglip_name).to(self.device).eval()

        dino_name = cfg["models"]["dinov2_model"]
        self.dino_proc = AutoImageProcessor.from_pretrained(dino_name)
        self.dino = AutoModel.from_pretrained(dino_name).to(self.device).eval()

        gd_name = cfg["models"]["grounding_dino_model"]
        try:
            from transformers import AutoModelForZeroShotObjectDetection

            self.gd_proc = AutoProcessor.from_pretrained(gd_name)
            self.gd = AutoModelForZeroShotObjectDetection.from_pretrained(gd_name).to(
                self.device
            ).eval()
            self.has_gd = True
            log.info("Grounding DINO ready: %s", gd_name)
        except Exception as e:
            log.warning("Grounding DINO unavailable (%s); using SigLIP vocab detect", e)
            self.has_gd = False

    def embed_image(self, img: Image.Image) -> np.ndarray:
        import torch

        inputs = self.dino_proc(images=img, return_tensors="pt")
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        with torch.no_grad():
            out = self.dino(**inputs)
            feat = out.last_hidden_state.mean(dim=1).squeeze(0).cpu().numpy()
        return feat.astype(np.float32)

    def phrase_scores(self, img: Image.Image, phrases: list[str]) -> list[float]:
        if not phrases:
            return []
        inputs = self.siglip_proc(
            text=phrases, images=img, padding="max_length", return_tensors="pt"
        )
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        with self.torch.no_grad():
            out = self.siglip(**inputs)
            # Cosine similarity of L2-normalized embeds (comparable across calls)
            if getattr(out, "image_embeds", None) is not None and getattr(
                out, "text_embeds", None
            ) is not None:
                img_e = out.image_embeds
                txt_e = out.text_embeds
                img_e = img_e / img_e.norm(dim=-1, keepdim=True)
                txt_e = txt_e / txt_e.norm(dim=-1, keepdim=True)
                sims = (img_e @ txt_e.T).squeeze(0)
                vals = sims.detach().cpu().flatten().tolist()
                return [float(v) for v in vals]
            logits = out.logits_per_image.squeeze(0)
            if logits.ndim == 0:
                return [float(logits.detach().cpu())]
            # Relative ranking among candidate phrases
            probs = self.torch.softmax(logits.float(), dim=-1)
            return [float(v) for v in probs.detach().cpu().tolist()]

    def ground_nouns(self, img: Image.Image, nouns: list[str]) -> list[dict[str, Any]]:
        if not nouns:
            return []
        box_thr = float(self.cfg["models"].get("grounding_box_threshold", 0.25))
        text_thr = float(self.cfg["models"].get("grounding_text_threshold", 0.25))
        if not self.has_gd:
            # SigLIP soft detection over candidate nouns
            scores = self.phrase_scores(img, nouns)
            out = []
            for noun, score in sorted(zip(nouns, scores), key=lambda x: -x[1])[:8]:
                if score < 0.08:
                    continue
                out.append(
                    {
                        "noun": noun.lower(),
                        "box": [0.1, 0.1, 0.9, 0.9],
                        "score": float(score),
                        "backend": "siglip_vocab",
                    }
                )
            return out or heuristic_ground_nouns(img, nouns[:4])

        text = " . ".join(nouns) + " ."
        inputs = self.gd_proc(images=img, text=text, return_tensors="pt")
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        with self.torch.no_grad():
            outputs = self.gd(**inputs)
        try:
            results = self.gd_proc.post_process_grounded_object_detection(
                outputs,
                inputs.get("input_ids"),
                box_threshold=box_thr,
                text_threshold=text_thr,
                target_sizes=[img.size[::-1]],
            )[0]
        except TypeError:
            results = self.gd_proc.post_process_grounded_object_detection(
                outputs,
                inputs["input_ids"],
                threshold=box_thr,
                text_threshold=text_thr,
                target_sizes=[img.size[::-1]],
            )[0]
        w, h = img.size
        boxes_out: list[dict[str, Any]] = []
        labels = results.get("text_labels") or results.get("labels") or []
        for box, score, label in zip(
            results.get("boxes", []), results.get("scores", []), labels
        ):
            x0, y0, x1, y1 = [float(v) for v in box.tolist()]
            boxes_out.append(
                {
                    "noun": str(label).lower().strip(),
                    "box": [x0 / w, y0 / h, x1 / w, y1 / h],
                    "score": float(score),
                    "backend": "grounding_dino",
                }
            )
        if not boxes_out:
            scores = self.phrase_scores(img, nouns)
            for noun, score in sorted(zip(nouns, scores), key=lambda x: -x[1])[:6]:
                if score < 0.08:
                    continue
                boxes_out.append(
                    {
                        "noun": noun.lower(),
                        "box": [0.1, 0.1, 0.9, 0.9],
                        "score": float(score),
                        "backend": "siglip_vocab",
                    }
                )
        return boxes_out



def _decide_level(scene_s: float, obj_s: float, ctx_s: float) -> str:
    scores = {"scene": scene_s, "object": obj_s, "context": ctx_s}
    return max(scores, key=scores.get)


def _resolve_image_path(imeta: dict[str, Any]) -> Path | None:
    path = Path(imeta.get("path") or "")
    if path.exists():
        return path
    from atmosphere_grounding.config import project_root

    alt = project_root() / (imeta.get("rel_path") or "")
    return alt if alt.exists() else None


def detect_objects(
    cfg: dict[str, Any],
    vision: Any | None = None,
    *,
    force: bool = False,
) -> list[dict[str, Any]]:
    """Image-first object list (independent of reviews). Writes objects.jsonl."""
    ensure_dirs(cfg)
    processed = resolve_path(cfg, "processed_dir")
    out_path = processed / "objects.jsonl"
    if out_path.exists() and not force:
        existing = read_jsonl(out_path)
        if existing and existing[0].get("backend") in {
            "grounding_dino",
            "siglip_vocab",
            "transformers",
        }:
            log.info("reusing %d cached object detections (%s)", len(existing), out_path)
            return existing
    images = read_jsonl(processed / "images.jsonl")
    vocab = list(cfg["models"].get("detection_vocabulary") or [])
    backend_name = cfg["models"].get("vision_backend", "heuristic")

    if vision is None and backend_name == "transformers":
        try:
            vision = TransformersVision(cfg)
            log.info("detect_objects: transformers ready")
        except Exception as e:
            log.warning("detect_objects: transformers failed (%s); heuristic", e)
            backend_name = "heuristic"
            vision = None

    rows: list[dict[str, Any]] = []
    for imeta in images:
        path = _resolve_image_path(imeta)
        if not path:
            continue
        img = _load_rgb(path)
        if vision is not None:
            dets = vision.ground_nouns(img, vocab)
        else:
            dets = heuristic_ground_nouns(img, vocab[:8])
        for det in dets:
            rows.append(
                {
                    "place_id": imeta["place_id"],
                    "image_index": imeta.get("image_index"),
                    "image_path": imeta.get("rel_path") or str(path),
                    "noun": det.get("noun"),
                    "box": det.get("box"),
                    "score": det.get("score"),
                    "backend": det.get("backend") or backend_name,
                }
            )

    write_jsonl(processed / "objects.jsonl", rows)
    # Per-place aggregate list for fusion LLM
    by_place: dict[str, Counter[str]] = defaultdict(Counter)
    for r in rows:
        if r.get("noun"):
            by_place[r["place_id"]][str(r["noun"]).lower()] += 1
    place_objects = [
        {
            "place_id": pid,
            "objects": [{"noun": n, "count": c} for n, c in counter.most_common(20)],
            "object_list": [n for n, _ in counter.most_common(20)],
        }
        for pid, counter in sorted(by_place.items())
    ]
    write_json(processed / "place_objects.json", place_objects)
    write_json(
        processed / "objects_summary.json",
        {
            "n_detections": len(rows),
            "n_places": len(place_objects),
            "backend": backend_name,
            "vocab_size": len(vocab),
        },
    )
    log.info(
        "detected %d object instances across %d places",
        len(rows),
        len(place_objects),
    )
    return rows


def run_ground(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    ensure_dirs(cfg)
    processed = resolve_path(cfg, "processed_dir")
    mentions = read_jsonl(processed / "mentions.jsonl")
    # Prefer fused mentions when present
    fused_path = processed / "mentions_fused.jsonl"
    if fused_path.exists():
        fused = read_jsonl(fused_path)
        if fused:
            mentions = fused
            log.info("using mentions_fused.jsonl (%d rows)", len(mentions))
    images = read_jsonl(processed / "images.jsonl")
    atmospheres = active_atmospheres(cfg)
    backend_name = cfg["models"].get("vision_backend", "heuristic")

    vision = None
    if backend_name == "transformers":
        try:
            vision = TransformersVision(cfg)
            log.info("using transformers vision backend")
        except Exception as e:
            log.warning("transformers backend failed (%s); using heuristic", e)
            backend_name = "heuristic"

    # Image-first detections (always refresh when grounding)
    detect_objects(cfg, vision=vision)
    objects = read_jsonl(processed / "objects.jsonl")
    objects_by_place: dict[str, list[str]] = defaultdict(list)
    for o in objects:
        if o.get("noun"):
            objects_by_place[o["place_id"]].append(str(o["noun"]).lower())

    images_by_place: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for im in images:
        images_by_place[im["place_id"]].append(im)

    # Group mentions by place+atmosphere
    by_place_atm: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for m in mentions:
        if m["atmosphere"] in atmospheres:
            by_place_atm[(m["place_id"], m["atmosphere"])].append(m)

    evidence: list[dict[str, Any]] = []
    top_k = int(cfg["models"].get("match_top_k_images", 3))

    for (place_id, atm), ms in by_place_atm.items():
        phrases = []
        nouns: list[str] = []
        for m in ms:
            if m.get("phrase"):
                phrases.append(f"{atm}: {m['phrase'][:120]}")
            nouns.extend(m.get("nouns") or [])
        # Merge image-detected nouns for grounding targets
        nouns.extend(objects_by_place.get(place_id) or [])
        phrases = [atm] + phrases
        phrases = phrases[:8]
        noun_counts = Counter(n.lower() for n in nouns if n)
        top_nouns = [n for n, _ in noun_counts.most_common(8)]

        place_images = images_by_place.get(place_id) or []
        if not place_images:
            continue

        scored_imgs: list[tuple[float, dict[str, Any], Image.Image]] = []
        for imeta in place_images:
            path = _resolve_image_path(imeta)
            if not path:
                log.warning("missing image %s", imeta.get("path"))
                continue
            img = _load_rgb(path)
            if vision is not None:
                scores = vision.phrase_scores(img, phrases)
            else:
                scores = heuristic_phrase_scores(img, phrases)
            score = float(np.mean(scores)) if scores else 0.0
            scored_imgs.append((score, imeta, img))

        scored_imgs.sort(key=lambda x: x[0], reverse=True)
        for match_score, imeta, img in scored_imgs[:top_k]:
            if vision is not None:
                dets = vision.ground_nouns(img, top_nouns) if top_nouns else []
                scene_feat = vision.embed_image(img)
            else:
                dets = heuristic_ground_nouns(img, top_nouns) if top_nouns else []
                scene_feat = _mean_color_vec(img)

            if not dets:
                evidence.append(
                    {
                        "place_id": place_id,
                        "atmosphere": atm,
                        "image_path": imeta.get("rel_path") or imeta["path"],
                        "image_index": imeta.get("image_index"),
                        "noun": None,
                        "box": None,
                        "match_score": match_score,
                        "scene_score": match_score,
                        "object_score": None,
                        "context_score": None,
                        "level": "scene",
                        "backend": backend_name,
                    }
                )
                continue

            for det in dets:
                box = tuple(det["box"])
                obj = _crop_box(img, box)
                ctx = _context_ring(img, box)
                if vision is not None:
                    obj_s = float(np.mean(vision.phrase_scores(obj, [atm])))
                    ctx_s = float(np.mean(vision.phrase_scores(ctx, [atm])))
                    scene_s = match_score
                else:
                    obj_feat = _mean_color_vec(obj)
                    ctx_feat = _mean_color_vec(ctx)
                    prior = ATMOSPHERE_COLOR_PRIORS.get(
                        atm, np.array([0.5, 0.5, 0.5], dtype=np.float32)
                    )
                    scene_s = match_score
                    obj_mean = np.asarray(obj.resize((32, 32)), dtype=np.float32).mean(
                        axis=(0, 1)
                    ) / 255.0
                    ctx_mean = np.asarray(ctx.resize((32, 32)), dtype=np.float32).mean(
                        axis=(0, 1)
                    ) / 255.0
                    obj_s = float(
                        0.5 * _cosine(obj_feat, scene_feat)
                        + 0.5 * (1.0 - np.linalg.norm(obj_mean - prior) / np.sqrt(3))
                    )
                    ctx_s = float(
                        0.5 * _cosine(ctx_feat, scene_feat)
                        + 0.5 * (1.0 - np.linalg.norm(ctx_mean - prior) / np.sqrt(3))
                    )

                level = _decide_level(scene_s, obj_s, ctx_s)
                evidence.append(
                    {
                        "place_id": place_id,
                        "atmosphere": atm,
                        "image_path": imeta.get("rel_path") or imeta["path"],
                        "image_index": imeta.get("image_index"),
                        "noun": det["noun"],
                        "box": list(box),
                        "det_score": det.get("score"),
                        "match_score": match_score,
                        "scene_score": scene_s,
                        "object_score": obj_s,
                        "context_score": ctx_s,
                        "level": level,
                        "backend": backend_name,
                    }
                )

    write_jsonl(processed / "evidence.jsonl", evidence)

    profiles = build_profiles(evidence, mentions, atmospheres)
    prof_dir = processed / "atmosphere_profiles"
    for atm, profile in profiles.items():
        write_json(prof_dir / f"{atm}.json", profile)
    write_json(
        processed / "ground_summary.json",
        {
            "n_evidence": len(evidence),
            "backend": backend_name,
            "atmospheres": atmospheres,
        },
    )
    return evidence


def build_profiles(
    evidence: list[dict[str, Any]],
    mentions: list[dict[str, Any]],
    atmospheres: list[str],
) -> dict[str, Any]:
    places_with: dict[str, set[str]] = defaultdict(set)
    for m in mentions:
        places_with[m["atmosphere"]].add(m["place_id"])

    all_places = {m["place_id"] for m in mentions}
    profiles: dict[str, Any] = {}
    for atm in atmospheres:
        pos_places = places_with.get(atm, set())
        counter_places = all_places - pos_places
        noun_support: Counter[str] = Counter()
        noun_places: dict[str, set[str]] = defaultdict(set)
        level_counts: Counter[str] = Counter()
        for e in evidence:
            if e["atmosphere"] != atm:
                continue
            level_counts[e.get("level") or "scene"] += 1
            noun = e.get("noun")
            if noun:
                noun_support[noun] += 1
                noun_places[noun].add(e["place_id"])

        nouns = []
        for noun, count in noun_support.most_common(20):
            support_places = noun_places[noun]
            # crude precision: fraction of noun's places that mention atm
            prec = len(support_places & pos_places) / max(1, len(support_places))
            nouns.append(
                {
                    "noun": noun,
                    "count": count,
                    "n_places": len(support_places),
                    "precision_vs_mentions": round(prec, 3),
                    "counterexample_places": sorted(list(support_places & counter_places))[:10],
                }
            )
        profiles[atm] = {
            "atmosphere": atm,
            "n_mention_places": len(pos_places),
            "n_counterexample_places": len(counter_places),
            "level_counts": dict(level_counts),
            "recurring_nouns": nouns,
        }
    return profiles

"""Collect Cambridge public places + photos under quota caps."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Any

import pandas as pd

from atmosphere_grounding.collect.client import PlacesClient
from atmosphere_grounding.collect.quota import QuotaLedger
from atmosphere_grounding.config import (
    ensure_dirs,
    read_json,
    resolve_path,
    write_json,
    write_jsonl,
)

log = logging.getLogger(__name__)


def _bare_id(place_resource: str) -> str:
    return place_resource.replace("places/", "")


def _in_bbox(lat: float, lng: float, bbox: dict[str, float]) -> bool:
    return bbox["south"] <= lat <= bbox["north"] and bbox["west"] <= lng <= bbox["east"]


def _excluded_name(name: str, substrings: list[str]) -> bool:
    lower = name.lower()
    return any(s.lower() in lower for s in substrings)


def _normalize_place(raw: dict[str, Any]) -> dict[str, Any] | None:
    loc = raw.get("location") or {}
    lat = loc.get("latitude")
    lng = loc.get("longitude")
    if lat is None or lng is None:
        return None
    display = raw.get("displayName") or {}
    name = display.get("text") if isinstance(display, dict) else str(display)
    rid = raw.get("id") or ""
    return {
        "place_id": _bare_id(rid),
        "resource_name": rid if rid.startswith("places/") else f"places/{rid}",
        "name": name or "",
        "lat": float(lat),
        "lng": float(lng),
        "types": list(raw.get("types") or []),
        "formatted_address": raw.get("formattedAddress") or "",
        "rating": raw.get("rating"),
        "user_rating_count": raw.get("userRatingCount") or 0,
        "n_photos": len(raw.get("photos") or []),
        "n_reviews": len(raw.get("reviews") or []),
    }


def discover_place_ids(client: PlacesClient, cfg: dict[str, Any]) -> list[str]:
    queries = cfg["places"]["search_queries"]
    hard_search = int(cfg["quota"]["hard_caps"]["text_search"])
    seen: dict[str, dict[str, Any]] = {}
    searches = 0

    for query in queries:
        if searches >= hard_search:
            log.warning("search cap reached (%s)", hard_search)
            break
        try:
            data = client.text_search(query)
        except RuntimeError as e:
            log.warning("stopping discovery: %s", e)
            break
        searches += 1
        for p in data.get("places") or []:
            pid = _bare_id(p.get("id") or "")
            if not pid:
                continue
            loc = p.get("location") or {}
            lat, lng = loc.get("latitude"), loc.get("longitude")
            if lat is None or lng is None:
                continue
            if not _in_bbox(float(lat), float(lng), cfg["region"]["bbox"]):
                continue
            name = ((p.get("displayName") or {}).get("text")) or ""
            if _excluded_name(name, cfg["places"]["exclude_name_substrings"]):
                continue
            types = set(p.get("types") or [])
            include = set(cfg["places"]["include_types"])
            # Keep if any include type matches, or if types empty (defer to details)
            if include and types and not (types & include):
                # still keep parks discovered by query text even if type missing
                if "park" not in query.lower() and "plaza" not in query.lower():
                    continue
            seen[pid] = p

    log.info("discovered %d unique place ids after filters", len(seen))
    return list(seen.keys())


def collect_from_api(cfg: dict[str, Any], *, dry_run: bool | None = None) -> dict[str, Any]:
    ensure_dirs(cfg)
    raw_dir = resolve_path(cfg, "raw_dir")
    processed = resolve_path(cfg, "processed_dir")
    ledger = QuotaLedger(resolve_path(cfg, "quota_ledger"), cfg)
    dry = cfg["collect"]["dry_run"] if dry_run is None else dry_run
    client = PlacesClient(cfg, ledger, raw_dir, dry_run=dry)

    place_ids = discover_place_ids(client, cfg)
    max_places = int(cfg["places"]["max_places"])
    max_photos = int(cfg["places"]["max_photos_per_place"])
    max_reviews = int(cfg["places"]["max_reviews_per_place"])

    rows: list[dict[str, Any]] = []
    review_rows: list[dict[str, Any]] = []
    image_rows: list[dict[str, Any]] = []

    for pid in place_ids:
        if len(rows) >= max_places:
            break
        try:
            details = client.place_details(pid)
        except RuntimeError as e:
            log.warning("stopping details: %s", e)
            break
        if details.get("dry_run"):
            continue
        norm = _normalize_place(details)
        if not norm:
            continue
        if not _in_bbox(norm["lat"], norm["lng"], cfg["region"]["bbox"]):
            continue
        if _excluded_name(norm["name"], cfg["places"]["exclude_name_substrings"]):
            continue
        include = set(cfg["places"]["include_types"])
        types = set(norm["types"])
        if include and types and not (types & include | {"park", "tourist_attraction"}):
            # Prefer public-space-ish types; allow tourist_attraction parks
            if "park" not in types and "tourist_attraction" not in types:
                continue

        rows.append(norm)

        for i, rev in enumerate((details.get("reviews") or [])[:max_reviews]):
            text = (rev.get("text") or {}).get("text") or rev.get("originalText", {}).get(
                "text"
            )
            if not text:
                continue
            review_rows.append(
                {
                    "place_id": pid,
                    "review_index": i,
                    "rating": rev.get("rating"),
                    "language": (rev.get("text") or {}).get("languageCode")
                    or cfg["region"]["language"],
                    "text": text,
                    "publish_time": rev.get("publishTime"),
                }
            )

        img_dir = raw_dir / "images" / pid
        for j, photo in enumerate((details.get("photos") or [])[:max_photos]):
            name = photo.get("name")
            if not name:
                continue
            dest = img_dir / f"{j:02d}.jpg"
            try:
                path = client.download_photo(name, dest)
            except RuntimeError as e:
                log.warning("stopping photos: %s", e)
                break
            if path:
                image_rows.append(
                    {
                        "place_id": pid,
                        "image_index": j,
                        "path": str(path),
                        "rel_path": f"data/raw/images/{pid}/{dest.name}",
                        "photo_name": name,
                    }
                )

    # Rank by review/photo richness if we somehow overshot earlier
    rows = sorted(
        rows,
        key=lambda r: (r.get("n_reviews") or 0, r.get("user_rating_count") or 0),
        reverse=True,
    )[:max_places]

    places_path = processed / "places.parquet"
    pd.DataFrame(rows).to_parquet(places_path, index=False)
    write_jsonl(processed / "reviews.jsonl", review_rows)
    write_jsonl(processed / "images.jsonl", image_rows)
    write_json(
        processed / "collect_summary.json",
        {
            "n_places": len(rows),
            "n_reviews": len(review_rows),
            "n_images": len(image_rows),
            "quota": ledger.summary(),
            "dry_run": dry,
        },
    )
    return {
        "places": rows,
        "reviews": review_rows,
        "images": image_rows,
        "quota": ledger.summary(),
    }


def collect_from_fixtures(cfg: dict[str, Any]) -> dict[str, Any]:
    """Copy fixture places/reviews/images into raw+processed for offline runs."""
    ensure_dirs(cfg)
    fixtures = resolve_path(cfg, "fixtures_dir")
    raw_dir = resolve_path(cfg, "raw_dir")
    processed = resolve_path(cfg, "processed_dir")

    places_src = fixtures / "places"
    if places_src.exists():
        for src in places_src.glob("*.json"):
            dest = raw_dir / "places" / src.name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)

    images_src = fixtures / "images"
    if images_src.exists():
        for place_dir in images_src.iterdir():
            if not place_dir.is_dir():
                continue
            dest_dir = raw_dir / "images" / place_dir.name
            dest_dir.mkdir(parents=True, exist_ok=True)
            for img in place_dir.glob("*"):
                shutil.copy2(img, dest_dir / img.name)

    places_meta = read_json(fixtures / "places_table.json")
    reviews = read_json(fixtures / "reviews.json")
    images_meta = []
    for row in places_meta:
        pid = row["place_id"]
        img_dir = raw_dir / "images" / pid
        if img_dir.exists():
            for j, img in enumerate(sorted(img_dir.glob("*"))):
                images_meta.append(
                    {
                        "place_id": pid,
                        "image_index": j,
                        "path": str(img),
                        "rel_path": f"data/raw/images/{pid}/{img.name}",
                        "photo_name": f"fixture/{pid}/{img.name}",
                    }
                )

    pd.DataFrame(places_meta).to_parquet(processed / "places.parquet", index=False)
    write_jsonl(processed / "reviews.jsonl", reviews)
    write_jsonl(processed / "images.jsonl", images_meta)
    write_json(
        processed / "collect_summary.json",
        {
            "n_places": len(places_meta),
            "n_reviews": len(reviews),
            "n_images": len(images_meta),
            "source": "fixtures",
        },
    )
    return {
        "places": places_meta,
        "reviews": reviews,
        "images": images_meta,
        "quota": {},
    }


def run_collect(
    cfg: dict[str, Any],
    *,
    dry_run: bool = False,
    use_fixtures: bool | None = None,
) -> dict[str, Any]:
    use_fx = (
        cfg["collect"]["use_fixtures"] if use_fixtures is None else use_fixtures
    )
    if use_fx:
        log.info("collecting from fixtures")
        result = collect_from_fixtures(cfg)
        label = "fixtures"
    else:
        result = collect_from_api(cfg, dry_run=dry_run)
        label = "dry_run" if dry_run else "collect"

    if cfg.get("collect", {}).get("backup_on_collect", True) and not dry_run:
        if result.get("places"):
            from atmosphere_grounding.collect.backup import backup_google_raw

            dest = backup_google_raw(cfg, label=label)
            result["backup"] = str(dest)
    return result

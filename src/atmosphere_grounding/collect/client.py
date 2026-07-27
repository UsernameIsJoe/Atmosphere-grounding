"""Google Places API (New) client with disk cache and quota guards."""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests

from atmosphere_grounding.collect.quota import (
    SKU_PLACE_DETAILS,
    SKU_PLACE_PHOTOS,
    SKU_TEXT_SEARCH,
    QuotaLedger,
)
from atmosphere_grounding.config import api_key

log = logging.getLogger(__name__)

PLACES_BASE = "https://places.googleapis.com/v1"
FIELD_MASK_SEARCH = (
    "places.id,places.displayName,places.location,places.types,"
    "places.formattedAddress,nextPageToken"
)
FIELD_MASK_DETAILS = (
    "id,displayName,location,types,formattedAddress,"
    "reviews,photos,userRatingCount,rating"
)


class PlacesClient:
    def __init__(
        self,
        cfg: dict[str, Any],
        ledger: QuotaLedger,
        raw_dir: Path,
        *,
        dry_run: bool = False,
    ) -> None:
        self.cfg = cfg
        self.ledger = ledger
        self.raw_dir = raw_dir
        self.dry_run = dry_run
        self.session = requests.Session()
        self.key = api_key()

    def _headers(self, field_mask: str) -> dict[str, str]:
        if not self.key and not self.dry_run:
            raise RuntimeError(
                "GOOGLE_MAPS_API_KEY missing. Copy .env.example → .env or use --use-fixtures."
            )
        return {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.key or "DRY_RUN",
            "X-Goog-FieldMask": field_mask,
        }

    def text_search(self, query: str, page_token: str | None = None) -> dict[str, Any]:
        cache_key = hashlib.sha1(f"{query}|{page_token or ''}".encode()).hexdigest()[:16]
        cache_path = self.raw_dir / "search" / f"{cache_key}.json"
        if cache_path.exists():
            log.info("cache hit text_search %s", cache_path.name)
            return json.loads(cache_path.read_text(encoding="utf-8"))

        decision = self.ledger.check(SKU_TEXT_SEARCH, 1)
        if not decision.allowed:
            raise RuntimeError(decision.reason)

        body: dict[str, Any] = {
            "textQuery": query,
            "languageCode": self.cfg["region"]["language"],
            "maxResultCount": 20,
            "locationBias": {
                "circle": {
                    "center": {
                        "latitude": self.cfg["region"]["center"]["lat"],
                        "longitude": self.cfg["region"]["center"]["lng"],
                    },
                    "radius": float(self.cfg["places"].get("search_radius_m", 2500)),
                }
            },
        }
        if page_token:
            body["pageToken"] = page_token

        if self.dry_run:
            log.info("[dry-run] text_search would call for query=%r", query)
            return {"places": [], "dry_run": True, "query": query}

        resp = self.session.post(
            f"{PLACES_BASE}/places:searchText",
            headers=self._headers(FIELD_MASK_SEARCH),
            json=body,
            timeout=60,
        )
        if not resp.ok:
            raise RuntimeError(
                f"text_search HTTP {resp.status_code}: {_safe_error(resp)}"
            )
        self.ledger.record(SKU_TEXT_SEARCH, 1, {"query": query})
        data = resp.json()
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        return data

    def place_details(self, place_id: str) -> dict[str, Any]:
        # Accept resource name "places/xxx" or bare id
        pid = place_id.replace("places/", "")
        cache_path = self.raw_dir / "places" / f"{pid}.json"
        if cache_path.exists():
            log.info("cache hit place_details %s", pid)
            return json.loads(cache_path.read_text(encoding="utf-8"))

        decision = self.ledger.check(SKU_PLACE_DETAILS, 1)
        if not decision.allowed:
            raise RuntimeError(decision.reason)

        if self.dry_run:
            log.info("[dry-run] place_details would call for %s", pid)
            return {"id": f"places/{pid}", "dry_run": True}

        resp = self.session.get(
            f"{PLACES_BASE}/places/{quote(pid, safe='')}",
            headers=self._headers(FIELD_MASK_DETAILS),
            timeout=60,
        )
        if not resp.ok:
            raise RuntimeError(
                f"place_details HTTP {resp.status_code}: {_safe_error(resp)}"
            )
        self.ledger.record(SKU_PLACE_DETAILS, 1, {"place_id": pid})
        data = resp.json()
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        return data

    def download_photo(
        self,
        photo_name: str,
        dest: Path,
        *,
        max_width_px: int = 1200,
    ) -> Path | None:
        if dest.exists():
            log.info("cache hit photo %s", dest.name)
            return dest

        decision = self.ledger.check(SKU_PLACE_PHOTOS, 1)
        if not decision.allowed:
            raise RuntimeError(decision.reason)

        if self.dry_run:
            log.info("[dry-run] photo download would call for %s → %s", photo_name, dest)
            return None

        # photo_name is like "places/PLACE_ID/photos/PHOTO_REF"
        url = f"{PLACES_BASE}/{photo_name}/media"
        resp = self.session.get(
            url,
            params={
                "maxWidthPx": max_width_px,
                "skipHttpRedirect": "false",
                "key": self.key,
            },
            headers={"X-Goog-Api-Key": self.key or ""},
            timeout=60,
            stream=True,
        )
        if not resp.ok:
            raise RuntimeError(
                f"photo HTTP {resp.status_code}: {_safe_error(resp)}"
            )
        self.ledger.record(SKU_PLACE_PHOTOS, 1, {"photo": photo_name})
        dest.parent.mkdir(parents=True, exist_ok=True)
        with dest.open("wb") as f:
            for chunk in resp.iter_content(chunk_size=65536):
                if chunk:
                    f.write(chunk)
        return dest


def _safe_error(resp: requests.Response) -> str:
    """Return API error text with any api-key-looking tokens redacted."""
    text = resp.text or ""
    key = resp.request.headers.get("X-Goog-Api-Key") if resp.request else None
    if key:
        text = text.replace(key, "[REDACTED]")
    return text[:800]

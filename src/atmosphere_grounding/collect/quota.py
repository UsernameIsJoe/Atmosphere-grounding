"""Quota ledger: soft/hard caps for Places API SKUs."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SKU_TEXT_SEARCH = "text_search"
SKU_PLACE_DETAILS = "place_details_enterprise"
SKU_PLACE_PHOTOS = "place_photos"


@dataclass
class QuotaDecision:
    allowed: bool
    reason: str
    projected: int
    soft_cap: int
    hard_cap: int


class QuotaLedger:
    """Tracks billable Places API events and refuses calls past soft/hard caps."""

    def __init__(self, path: Path, cfg: dict[str, Any]) -> None:
        self.path = path
        self.cfg = cfg
        self.data = self._load()

    def _load(self) -> dict[str, Any]:
        if self.path.exists():
            return json.loads(self.path.read_text(encoding="utf-8"))
        return {
            "created_at": _now(),
            "updated_at": _now(),
            "counts": {
                SKU_TEXT_SEARCH: 0,
                SKU_PLACE_DETAILS: 0,
                SKU_PLACE_PHOTOS: 0,
            },
            "events": [],
        }

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.data["updated_at"] = _now()
        self.path.write_text(json.dumps(self.data, indent=2) + "\n", encoding="utf-8")

    def count(self, sku: str) -> int:
        return int(self.data["counts"].get(sku, 0))

    def soft_cap(self, sku: str) -> int:
        free = int(self.cfg["quota"]["free_monthly_caps"][sku])
        frac = float(self.cfg["quota"]["soft_fraction"])
        hard = int(self.cfg["quota"]["hard_caps"][sku])
        return min(int(free * frac), hard)

    def hard_cap(self, sku: str) -> int:
        return int(self.cfg["quota"]["hard_caps"][sku])

    def check(self, sku: str, n: int = 1) -> QuotaDecision:
        projected = self.count(sku) + n
        soft = self.soft_cap(sku)
        hard = self.hard_cap(sku)
        if projected > hard:
            return QuotaDecision(
                False,
                f"{sku}: projected {projected} exceeds hard cap {hard}",
                projected,
                soft,
                hard,
            )
        if projected > soft:
            return QuotaDecision(
                False,
                f"{sku}: projected {projected} exceeds soft budget {soft}",
                projected,
                soft,
                hard,
            )
        return QuotaDecision(True, "ok", projected, soft, hard)

    def record(self, sku: str, n: int = 1, meta: dict[str, Any] | None = None) -> None:
        decision = self.check(sku, n)
        if not decision.allowed:
            raise RuntimeError(f"Quota refused before record: {decision.reason}")
        self.data["counts"][sku] = self.count(sku) + n
        self.data["events"].append(
            {
                "ts": _now(),
                "sku": sku,
                "n": n,
                "meta": meta or {},
                "count_after": self.data["counts"][sku],
            }
        )
        self.save()

    def summary(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for sku in (SKU_TEXT_SEARCH, SKU_PLACE_DETAILS, SKU_PLACE_PHOTOS):
            out[sku] = {
                "used": self.count(sku),
                "soft_cap": self.soft_cap(sku),
                "hard_cap": self.hard_cap(sku),
                "remaining_soft": max(0, self.soft_cap(sku) - self.count(sku)),
            }
        return out


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

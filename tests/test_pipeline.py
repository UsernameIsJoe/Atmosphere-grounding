"""Unit tests using fixtures only (no live API)."""

from __future__ import annotations

from pathlib import Path

import pytest

from atmosphere_grounding.collect.pipeline import run_collect
from atmosphere_grounding.collect.quota import (
    SKU_PLACE_DETAILS,
    QuotaLedger,
)
from atmosphere_grounding.config import load_config, resolve_path
from atmosphere_grounding.extract import heuristic_extract, run_extract
from atmosphere_grounding.graph import build_graph, inspect_atmosphere
from atmosphere_grounding.ground import run_ground


@pytest.fixture()
def cfg(tmp_path, monkeypatch):
    # Load real config but redirect data dirs into tmp via monkeypatch of paths
    c = load_config()
    # Use project fixtures; write outputs under tmp
    c["paths"]["raw_dir"] = str(tmp_path / "raw")
    c["paths"]["processed_dir"] = str(tmp_path / "processed")
    c["paths"]["graph_dir"] = str(tmp_path / "graph")
    c["paths"]["quota_ledger"] = str(tmp_path / "quota_ledger.json")
    c["collect"]["use_fixtures"] = True
    c["models"]["vision_backend"] = "heuristic"
    return c


def test_quota_soft_stop(tmp_path):
    cfg = load_config()
    cfg["quota"]["hard_caps"]["place_details_enterprise"] = 2
    cfg["quota"]["soft_fraction"] = 0.5  # soft = min(500, 2) wait free*0.5 vs hard
    cfg["quota"]["free_monthly_caps"]["place_details_enterprise"] = 1000
    # soft = min(500, 2) = 2
    ledger = QuotaLedger(tmp_path / "q.json", cfg)
    ledger.record(SKU_PLACE_DETAILS, 1)
    ledger.record(SKU_PLACE_DETAILS, 1)
    d = ledger.check(SKU_PLACE_DETAILS, 1)
    assert d.allowed is False


def test_heuristic_extract_lexicon_only():
    rows = heuristic_extract(
        "A calm lawn with trees; also the coffee was expensive.",
        ["inviting", "safe", "calm"],
        "p1",
        0,
    )
    atms = {r["atmosphere"] for r in rows}
    assert "calm" in atms
    assert all(a in {"inviting", "safe", "calm"} for a in atms)


def test_pipeline_fixtures(cfg):
    collect = run_collect(cfg, use_fixtures=True)
    assert collect["places"]
    assert collect["reviews"]
    assert collect["images"]

    mentions = run_extract(cfg, use_heuristic=True)
    assert any(m["atmosphere"] == "calm" for m in mentions)
    assert any(m["atmosphere"] == "safe" for m in mentions)
    assert any(m["atmosphere"] == "inviting" for m in mentions)

    evidence = run_ground(cfg)
    assert evidence
    levels = {e["level"] for e in evidence}
    assert levels & {"scene", "object", "context"}

    G = build_graph(cfg)
    assert G.number_of_nodes() > 0
    chains = inspect_atmosphere(G, "calm")
    # May be empty if nouns missing, but ASSOCIATED_WITH should exist for some atm
    any_chains = (
        inspect_atmosphere(G, "calm")
        or inspect_atmosphere(G, "safe")
        or inspect_atmosphere(G, "inviting")
    )
    assert any_chains
    graphml = Path(resolve_path(cfg, "graph_dir") / "cambridge_pilot.graphml")
    assert graphml.exists()

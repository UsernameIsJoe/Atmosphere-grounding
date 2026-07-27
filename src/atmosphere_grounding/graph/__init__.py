"""Build and inspect the multimodal atmosphere knowledge graph."""

from __future__ import annotations

import json
import logging
from collections import Counter, defaultdict
from typing import Any

import networkx as nx
import pandas as pd

from atmosphere_grounding.config import (
    ensure_dirs,
    read_jsonl,
    resolve_path,
    write_json,
)

log = logging.getLogger(__name__)


def _as_types_str(types_val: Any) -> str:
    if types_val is None:
        return ""
    if isinstance(types_val, str):
        return types_val
    if isinstance(types_val, (list, tuple)):
        return ",".join(str(t) for t in types_val)
    # numpy array / pandas list from parquet
    try:
        return ",".join(str(t) for t in list(types_val))
    except TypeError:
        return str(types_val)


def build_graph(cfg: dict[str, Any]) -> nx.MultiDiGraph:
    ensure_dirs(cfg)
    processed = resolve_path(cfg, "processed_dir")
    graph_dir = resolve_path(cfg, "graph_dir")

    places_path = processed / "places.parquet"
    places = (
        pd.read_parquet(places_path).to_dict(orient="records")
        if places_path.exists()
        else []
    )
    images = read_jsonl(processed / "images.jsonl")
    mentions = read_jsonl(processed / "mentions.jsonl")
    fused = read_jsonl(processed / "mentions_fused.jsonl")
    if fused:
        mentions = fused
    evidence = read_jsonl(processed / "evidence.jsonl")
    objects = read_jsonl(processed / "objects.jsonl")
    correlations = read_jsonl(processed / "place_correlation.jsonl")

    G = nx.MultiDiGraph(name="cambridge_atmosphere_pilot")
    region_id = cfg["region"]["id"]
    G.add_node(
        f"region:{region_id}",
        kind="Region",
        label=cfg["region"]["name"],
        region_id=region_id,
    )

    for p in places:
        pid = p["place_id"]
        nid = f"place:{pid}"
        G.add_node(
            nid,
            kind="Place",
            label=p.get("name") or pid,
            place_id=pid,
            lat=p.get("lat"),
            lng=p.get("lng"),
            types=_as_types_str(p.get("types")),
        )
        G.add_edge(nid, f"region:{region_id}", kind="IN_REGION")

    for im in images:
        iid = f"image:{im['place_id']}:{im.get('image_index', 0)}"
        G.add_node(
            iid,
            kind="Image",
            label=im.get("rel_path") or im.get("path"),
            path=im.get("rel_path") or im.get("path"),
            place_id=im["place_id"],
        )
        G.add_edge(f"place:{im['place_id']}", iid, kind="HAS_IMAGE")

    for atm in cfg["atmospheres"]["active"]:
        G.add_node(f"atmosphere:{atm}", kind="Atmosphere", label=atm, atmosphere=atm)

    # Semantic mentions
    for i, m in enumerate(mentions):
        atm = m["atmosphere"]
        phrase = (m.get("phrase") or "")[:200]
        phrase_id = f"phrase:{m['place_id']}:{m.get('review_index', 0)}:{i}"
        G.add_node(
            phrase_id,
            kind="Phrase",
            label=phrase[:80],
            phrase=phrase,
            visual_confidence=m.get("visual_confidence"),
        )
        G.add_edge(
            f"place:{m['place_id']}",
            f"atmosphere:{atm}",
            kind="MENTIONS",
            phrase_id=phrase_id,
            confidence=m.get("visual_confidence"),
        )
        G.add_edge(phrase_id, f"atmosphere:{atm}", kind="MENTIONS")
        for noun in m.get("nouns") or []:
            nn = f"noun:{noun.lower()}"
            if nn not in G:
                G.add_node(nn, kind="Noun", label=noun.lower(), noun=noun.lower())
            G.add_edge(phrase_id, nn, kind="CONTAINS_NOUN")

    # Visual evidence
    assoc_agg: dict[tuple[str, str], dict[str, Any]] = {}
    for i, e in enumerate(evidence):
        vid = f"evidence:{i}"
        G.add_node(
            vid,
            kind="VisualEvidence",
            label=f"{e.get('atmosphere')}:{e.get('noun') or 'scene'}",
            atmosphere=e.get("atmosphere"),
            noun=e.get("noun"),
            level=e.get("level"),
            match_score=e.get("match_score"),
            scene_score=e.get("scene_score"),
            object_score=e.get("object_score"),
            context_score=e.get("context_score"),
            image_path=e.get("image_path"),
            box=str(e.get("box")),
        )
        atm_n = f"atmosphere:{e['atmosphere']}"
        G.add_edge(atm_n, vid, kind="SUPPORTED_BY", confidence=e.get("match_score"))
        img_n = f"image:{e['place_id']}:{e.get('image_index', 0)}"
        if img_n in G:
            G.add_edge(vid, img_n, kind="FROM_IMAGE")
        if e.get("noun"):
            nn = f"noun:{e['noun'].lower()}"
            if nn not in G:
                G.add_node(nn, kind="Noun", label=e["noun"].lower(), noun=e["noun"].lower())
            G.add_edge(vid, nn, kind="CONTAINS_NOUN")
            key = (e["atmosphere"], e["noun"].lower())
            agg = assoc_agg.setdefault(
                key, {"count": 0, "levels": defaultdict(int), "scores": []}
            )
            agg["count"] += 1
            agg["levels"][e.get("level") or "scene"] += 1
            if e.get("match_score") is not None:
                agg["scores"].append(float(e["match_score"]))

    # Image-first detections
    for o in objects:
        noun = (o.get("noun") or "").lower()
        if not noun:
            continue
        nn = f"noun:{noun}"
        if nn not in G:
            G.add_node(nn, kind="Noun", label=noun, noun=noun)
        img_n = f"image:{o['place_id']}:{o.get('image_index', 0)}"
        if img_n in G:
            G.add_edge(
                img_n,
                nn,
                kind="DETECTS",
                score=o.get("score"),
                backend=o.get("backend"),
            )
        place_n = f"place:{o['place_id']}"
        if place_n in G:
            G.add_edge(place_n, nn, kind="DETECTS", score=o.get("score"))

    # Place-level comment↔image alignment
    for c in correlations:
        place_n = f"place:{c['place_id']}"
        if place_n not in G:
            continue
        G.nodes[place_n]["noun_jaccard"] = c.get("noun_jaccard")
        G.nodes[place_n]["review_image_align"] = c.get("review_image_align_mean")
        G.nodes[place_n]["likely_mismatch"] = c.get("likely_mismatch")
        align = c.get("review_image_align_mean")
        if align is not None:
            # Link place to region with alignment attribute already; add self-doc edge via atmosphere if mentioned
            for atm in c.get("mentioned_atmospheres") or []:
                G.add_edge(
                    place_n,
                    f"atmosphere:{atm}",
                    kind="ALIGNED_TO",
                    score=align,
                    noun_jaccard=c.get("noun_jaccard"),
                    mismatch=c.get("likely_mismatch"),
                )

    for (atm, noun), agg in assoc_agg.items():
        level = max(agg["levels"], key=agg["levels"].get) if agg["levels"] else "scene"
        conf = sum(agg["scores"]) / len(agg["scores"]) if agg["scores"] else 0.0
        G.add_edge(
            f"atmosphere:{atm}",
            f"noun:{noun}",
            kind="ASSOCIATED_WITH",
            count=agg["count"],
            confidence=round(conf, 4),
            level=level,
        )

    out_graphml = graph_dir / "cambridge_pilot.graphml"
    # GraphML needs string attributes
    H = nx.MultiDiGraph()
    for n, attrs in G.nodes(data=True):
        H.add_node(n, **{k: "" if v is None else str(v) for k, v in attrs.items()})
    for u, v, k, attrs in G.edges(keys=True, data=True):
        H.add_edge(
            u,
            v,
            key=str(k),
            **{ak: "" if av is None else str(av) for ak, av in attrs.items()},
        )
    nx.write_graphml(H, out_graphml)

    write_json(
        graph_dir / "graph_summary.json",
        {
            "n_nodes": G.number_of_nodes(),
            "n_edges": G.number_of_edges(),
            "node_kinds": _count_kinds(G, "node"),
            "edge_kinds": _count_kinds(G, "edge"),
            "graphml": str(out_graphml),
        },
    )
    export_browser_view(cfg, G)
    # Keep in-memory rich graph for inspect
    G.graph["summary_path"] = str(graph_dir / "graph_summary.json")
    return G


def export_browser_view(cfg: dict[str, Any], G: nx.MultiDiGraph | None = None) -> dict[str, Any]:
    """Write readable JSON + self-contained HTML (open in any browser)."""
    ensure_dirs(cfg)
    graph_dir = resolve_path(cfg, "graph_dir")
    processed = resolve_path(cfg, "processed_dir")
    if G is None:
        path = graph_dir / "cambridge_pilot.graphml"
        G = nx.read_graphml(path) if path.exists() else build_graph(cfg)

    atmospheres = list(cfg["atmospheres"]["active"])
    mentions = read_jsonl(processed / "mentions.jsonl")
    fused = read_jsonl(processed / "mentions_fused.jsonl")
    mention_rows = fused or mentions

    # Readable logic chains
    view: dict[str, Any] = {
        "region": cfg["region"]["name"],
        "atmospheres": {},
    }
    for atm in atmospheres:
        chains = inspect_atmosphere(G, atm, top_n=25)
        phrases = [
            {
                "place_id": m.get("place_id"),
                "phrase": m.get("phrase"),
                "nouns": m.get("nouns"),
                "visual_confidence": m.get("visual_confidence"),
            }
            for m in mention_rows
            if m.get("atmosphere") == atm
        ][:40]
        view["atmospheres"][atm] = {
            "associated_nouns": chains,
            "sample_phrases": phrases,
        }
    write_json(graph_dir / "logic_view.json", view)

    # Palette (from user reference swatches on black)
    EDGE_ASSOCIATED = "#3020e0"  # blue — atmosphere → image/visual noun
    EDGE_ATM_COMMENT = "#50f0a0"  # mint — atmosphere → comment noun
    EDGE_MENTIONS = "#f0f080"  # pale yellow — place → atmosphere
    EDGE_DETECTS = "#f06020"  # orange — place → image noun
    EDGE_COMMENT_NOUN = "#f0b0e0"  # pink — place → comment noun

    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    node_meta: dict[str, dict[str, Any]] = {}

    def add_node(nid: str, label: str, group: str, title: str = "") -> None:
        if nid in node_meta:
            prev = node_meta[nid]["group"]
            if {prev, group} == {"NounComment", "NounImage"}:
                node_meta[nid]["group"] = "NounBoth"
                for n in nodes:
                    if n["id"] == nid:
                        n["group"] = "NounBoth"
            return
        node_meta[nid] = {"group": group}
        nodes.append(
            {
                "id": nid,
                "label": label[:48],
                "group": group,
                "title": title or label,
            }
        )

    def add_edge(
        frm: str,
        to: str,
        *,
        label: str,
        color: str,
        title: str = "",
        width: float = 1.5,
    ) -> None:
        edges.append(
            {
                "from": frm,
                "to": to,
                # Keep label text out of default rendering; JS shows on hover only
                "label": "",
                "hoverLabel": label,
                "title": title or label,
                "color": color,
                "width": 0.55,
            }
        )

    # --- Collect noun sources ---
    comment_nouns: set[str] = set()
    place_comment_nouns: dict[str, set[str]] = defaultdict(set)
    place_atmospheres: dict[str, set[str]] = defaultdict(set)
    atm_comment_nouns: dict[str, Counter[str]] = defaultdict(Counter)
    for m in mention_rows:
        pid = m.get("place_id")
        atm = str(m.get("atmosphere") or "").lower().strip()
        if pid and atm:
            place_atmospheres[pid].add(atm)
        for noun in m.get("nouns") or []:
            noun = str(noun).lower().strip()
            if not noun:
                continue
            comment_nouns.add(noun)
            if pid:
                place_comment_nouns[pid].add(noun)
            if atm:
                atm_comment_nouns[atm][noun] += 1

    image_nouns: Counter[str] = Counter()
    place_image_nouns: dict[str, Counter[str]] = defaultdict(Counter)
    for u, v, a in G.edges(data=True):
        if str(a.get("kind")) != "DETECTS":
            continue
        if str(G.nodes[u].get("kind")) != "Place":
            continue
        if str(G.nodes[v].get("kind")) != "Noun":
            continue
        noun = str(G.nodes[v].get("noun") or v.replace("noun:", "")).lower()
        pid = str(G.nodes[u].get("place_id") or u.split("place:")[-1])
        image_nouns[noun] += 1
        place_image_nouns[pid][noun] += 1

    def noun_group(noun: str) -> str:
        in_c = noun in comment_nouns
        in_i = noun in image_nouns
        if in_c and in_i:
            return "NounBoth"
        if in_i:
            return "NounImage"
        return "NounComment"

    # Places that have any signal
    place_nodes = [
        (n, a) for n, a in G.nodes(data=True) if str(a.get("kind")) == "Place"
    ]
    active_place_ids = set(place_atmospheres) | set(place_image_nouns) | set(
        place_comment_nouns
    )

    for n, a in place_nodes:
        pid = str(a.get("place_id") or n.split("place:")[-1])
        if pid not in active_place_ids:
            continue
        mismatch = str(a.get("likely_mismatch")).lower() in {"true", "1"}
        # Browser view: hide mismatch places (keep them in GraphML only)
        if mismatch:
            continue
        label = str(a.get("label") or n)
        title = str(a.get("label") or "")
        if a.get("noun_jaccard") not in (None, ""):
            title += f" | jaccard={a.get('noun_jaccard')} align={a.get('review_image_align')}"
        add_node(n, label, "Place", title)

    for atm in atmospheres:
        add_node(f"atmosphere:{atm}", atm, "Atmosphere")

    # Atmosphere → comment nouns (from LLM extract)
    for atm in atmospheres:
        for noun, cnt in atm_comment_nouns.get(atm, Counter()).most_common(20):
            nn = f"noun:{noun}"
            add_node(nn, noun, noun_group(noun))
            add_edge(
                f"atmosphere:{atm}",
                nn,
                label=f"comment×{cnt}",
                color=EDGE_ATM_COMMENT,
                title=f"atmosphere→comment noun (count={cnt})",
                width=2,
            )

    # Atmosphere → visual/image nouns (ASSOCIATED_WITH profile)
    for atm in atmospheres:
        for chain in inspect_atmosphere(G, atm, top_n=15):
            noun = str(chain.get("noun") or "").lower()
            if not noun:
                continue
            nn = f"noun:{noun}"
            add_node(nn, noun, noun_group(noun))
            add_edge(
                f"atmosphere:{atm}",
                nn,
                label=f"visual×{chain.get('count')}",
                color=EDGE_ASSOCIATED,
                title=f"ASSOCIATED_WITH (visual) {chain}",
                width=2,
            )

    # Place → atmosphere (MENTIONS) + place → nouns (kept)
    for pid, atms in place_atmospheres.items():
        place_n = f"place:{pid}"
        if place_n not in node_meta:
            continue
        for atm in atms:
            add_edge(
                place_n,
                f"atmosphere:{atm}",
                label="MENTIONS",
                color=EDGE_MENTIONS,
                title="place → atmosphere (comment corpus)",
            )
        for noun in sorted(place_comment_nouns.get(pid, []))[:8]:
            nn = f"noun:{noun}"
            add_node(nn, noun, noun_group(noun))
            add_edge(
                place_n,
                nn,
                label="comment",
                color=EDGE_COMMENT_NOUN,
                title="place → comment noun",
                width=1.2,
            )

    # Image: place → top detected nouns (DETECTS)
    for pid, counts in place_image_nouns.items():
        place_n = f"place:{pid}"
        if place_n not in node_meta:
            continue
        for noun, cnt in counts.most_common(6):
            nn = f"noun:{noun}"
            add_node(nn, noun, noun_group(noun))
            add_edge(
                place_n,
                nn,
                label=f"DETECTS×{cnt}",
                color=EDGE_DETECTS,
                title=f"DETECTS count={cnt}",
                width=1.5,
            )

    # Drop isolates (nodes with no edges)
    degree: Counter[str] = Counter()
    for e in edges:
        degree[e["from"]] += 1
        degree[e["to"]] += 1
    nodes = [n for n in nodes if degree[n["id"]] > 0]
    keep = {n["id"] for n in nodes}
    edges = [e for e in edges if e["from"] in keep and e["to"] in keep]

    payload = {"nodes": nodes, "edges": edges}
    write_json(graph_dir / "browser_graph.json", payload)

    html = _HTML_TEMPLATE.replace("__GRAPH_JSON__", json.dumps(payload))
    html_path = graph_dir / "view.html"
    html_path.write_text(html, encoding="utf-8")
    log.info(
        "browser view written to %s (%d nodes, %d edges, 0 isolates)",
        html_path,
        len(nodes),
        len(edges),
    )
    return {"html": str(html_path), "logic_view": str(graph_dir / "logic_view.json")}


def _count_kinds(G: nx.MultiDiGraph, which: str) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    if which == "node":
        for _, attrs in G.nodes(data=True):
            counts[str(attrs.get("kind", "?"))] += 1
    else:
        for _, _, attrs in G.edges(data=True):
            counts[str(attrs.get("kind", "?"))] += 1
    return dict(counts)


def inspect_atmosphere(G: nx.MultiDiGraph, atmosphere: str, top_n: int = 15) -> list[dict[str, Any]]:
    atm_n = f"atmosphere:{atmosphere}"
    if atm_n not in G:
        return []
    chains: list[dict[str, Any]] = []
    for _, v, attrs in G.out_edges(atm_n, data=True):
        if attrs.get("kind") == "ASSOCIATED_WITH":
            chains.append(
                {
                    "atmosphere": atmosphere,
                    "noun": G.nodes[v].get("noun") or v,
                    "count": attrs.get("count"),
                    "confidence": attrs.get("confidence"),
                    "level": attrs.get("level"),
                }
            )
    chains.sort(key=lambda x: float(x.get("count") or 0), reverse=True)
    return chains[:top_n]


def load_graphml(cfg: dict[str, Any]) -> nx.MultiDiGraph:
    path = resolve_path(cfg, "graph_dir") / "cambridge_pilot.graphml"
    return nx.read_graphml(path)


_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Cambridge atmosphere logic graph</title>
  <script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
  <style>
    html, body { margin: 0; height: 100%; font-family: "Avenir Next", "Segoe UI", sans-serif; background: #000; color: #e0f0f0; }
    header { padding: 14px 18px 10px; border-bottom: 1px solid #1a1a28; background: #050508; }
    header h1 { margin: 0; font-size: 1.05rem; font-weight: 600; letter-spacing: 0.02em; color: #e0f0f0; }
    .legend { display: flex; flex-wrap: wrap; gap: 10px 16px; margin-top: 10px; font-size: 0.78rem; color: #c8d0d8; }
    .legend span { display: inline-flex; align-items: center; gap: 6px; }
    .legend .leg-link {
      cursor: pointer; padding: 3px 8px; border-radius: 6px;
      border: 1px solid transparent; user-select: none;
    }
    .legend .leg-link:hover { border-color: #333348; background: #12121a; }
    .legend .leg-link.active { border-color: #e0f0f0; background: #1a1a28; }
    .swatch { width: 11px; height: 11px; border-radius: 3px; display: inline-block; }
    .line { width: 18px; height: 3px; border-radius: 2px; display: inline-block; }
    #network { height: calc(100% - 88px); width: 100%; background: #000; }
  </style>
</head>
<body>
  <header>
    <h1>Harvard–MIT atmosphere logic graph</h1>
    <div class="legend">
      <span><i class="swatch" style="background:#3020e0"></i>Atmosphere</span>
      <span><i class="swatch" style="background:#f0f080"></i>Place</span>
      <span><i class="swatch" style="background:#50f0a0"></i>Noun (comment)</span>
      <span><i class="swatch" style="background:#f06020"></i>Noun (image)</span>
      <span><i class="swatch" style="background:#90e0d0"></i>Noun (both)</span>
      <span class="leg-link" data-edge-color="#f0f080"><i class="line" style="background:#f0f080"></i>place→atmosphere</span>
      <span class="leg-link" data-edge-color="#50f0a0"><i class="line" style="background:#50f0a0"></i>atmosphere→comment noun</span>
      <span class="leg-link" data-edge-color="#3020e0"><i class="line" style="background:#3020e0"></i>atmosphere→visual noun</span>
      <span class="leg-link" data-edge-color="#f0b0e0"><i class="line" style="background:#f0b0e0"></i>place→comment noun</span>
      <span class="leg-link" data-edge-color="#f06020"><i class="line" style="background:#f06020"></i>place→image noun</span>
    </div>
  </header>
  <div id="network"></div>
  <script>
    const data = __GRAPH_JSON__;
    // Seed atmosphere hubs in a tight triangle; other nodes settle around them
    const atmIds = data.nodes.filter(n => n.group === 'Atmosphere').map(n => n.id);
    const hubPos = [
      { x: 0, y: -80 },
      { x: -120, y: 90 },
      { x: 120, y: 90 }
    ];
    atmIds.forEach((id, i) => {
      const p = hubPos[i % hubPos.length];
      const node = data.nodes.find(n => n.id === id);
      if (node) { node.x = p.x; node.y = p.y; node.fixed = { x: true, y: true }; }
    });

    const nodes = new vis.DataSet(data.nodes.map(n => {
      if (n.group === 'Atmosphere') {
        return { ...n, font: { size: 28, color: '#e0f0f0', face: 'Avenir Next, Segoe UI, sans-serif', bold: true }, mass: 8, margin: 14 };
      }
      return { ...n, mass: n.group && n.group.startsWith('Noun') ? 1 : 2 };
    }));

    const BASE_W = 0.55;
    const DIM_W = 0.25;
    const HOT_W = 3.0;
    const edges = new vis.DataSet(data.edges.map((e, i) => {
      const col = e.color || '#90e0d0';
      // Prefer hoverLabel; ignore any leftover label strings in data
      const hoverLabel = e.hoverLabel || '';
      return {
        id: e.id || ('e' + i),
        from: e.from,
        to: e.to,
        _label: hoverLabel,
        label: undefined,
        title: e.title || hoverLabel || '',
        width: BASE_W,
        color: { color: col, highlight: col, hover: col, opacity: 0.5 },
        font: { color: '#e0f0f0', strokeWidth: 0, size: 0 }
      };
    }));

    function edgeBaseColor(e) {
      if (!e) return '#90e0d0';
      return (typeof e.color === 'object' && e.color.color) ? e.color.color : (e.color || '#90e0d0');
    }

    function resetEdgeStyles() {
      edges.update(edges.getIds().map(id => {
        const e = edges.get(id);
        const col = edgeBaseColor(e);
        return {
          id,
          width: BASE_W,
          label: undefined,
          font: { color: '#e0f0f0', strokeWidth: 0, size: 0 },
          color: { color: col, highlight: col, hover: col, opacity: 0.5 }
        };
      }));
    }

    function emphasizeEdges(edgeIds) {
      const hot = new Set(edgeIds);
      edges.update(edges.getIds().map(id => {
        const e = edges.get(id);
        const col = edgeBaseColor(e);
        const on = hot.has(id);
        return {
          id,
          width: on ? HOT_W : DIM_W,
          label: on && e._label ? e._label : undefined,
          font: {
            color: '#e0f0f0',
            strokeWidth: 0,
            size: on && e._label ? 12 : 0,
            background: on && e._label ? 'rgba(0,0,0,0.75)' : undefined
          },
          color: { color: col, highlight: col, hover: col, opacity: on ? 1 : 0.18 }
        };
      }));
    }

    const container = document.getElementById('network');
    const network = new vis.Network(container, { nodes, edges }, {
      physics: {
        enabled: true,
        solver: 'barnesHut',
        barnesHut: {
          gravitationalConstant: -12000,
          centralGravity: 0.55,
          springLength: 110,
          springConstant: 0.05,
          damping: 0.5,
          avoidOverlap: 0.6
        },
        stabilization: { enabled: true, iterations: 400, fit: true }
      },
      nodes: {
        borderWidth: 0,
        shape: 'box',
        margin: 8,
        font: { face: 'Avenir Next, Segoe UI, sans-serif', size: 12 }
      },
      groups: {
        Atmosphere: { color: { background: '#3020e0', border: '#3020e0' }, font: { color: '#e0f0f0', size: 28 } },
        Place: { color: { background: '#f0f080', border: '#f0f080' }, font: { color: '#102050', size: 12 } },
        NounComment: { color: { background: '#50f0a0', border: '#50f0a0' }, font: { color: '#102050', size: 12 } },
        NounImage: { color: { background: '#f06020', border: '#f06020' }, font: { color: '#e0f0f0', size: 12 } },
        NounBoth: { color: { background: '#90e0d0', border: '#90e0d0' }, font: { color: '#102050', size: 12 } }
      },
      edges: {
        arrows: { to: { enabled: true, scaleFactor: 0.45 } },
        smooth: { type: 'continuous', roundness: 0.4 },
        selectionWidth: 1,
        hoverWidth: 0.5,
        font: { size: 0, strokeWidth: 0 }
      },
      interaction: {
        hover: true,
        hoverConnectedEdges: false,
        tooltipDelay: 60,
        multiselect: true,
        dragNodes: true
      }
    });

    network.on('hoverNode', function (params) {
      if (lockedEdgeColor) return;
      emphasizeEdges(network.getConnectedEdges(params.node));
    });
    network.on('blurNode', function () {
      if (lockedEdgeColor) return;
      resetEdgeStyles();
    });

    network.on('hoverEdge', function (params) {
      if (lockedEdgeColor) return;
      emphasizeEdges([params.edge]);
    });
    network.on('blurEdge', function () {
      if (lockedEdgeColor) return;
      resetEdgeStyles();
    });

    // Legend click: thicken all edges of that link color (toggle)
    let lockedEdgeColor = null;
    function edgesMatchingColor(hex) {
      const want = (hex || '').toLowerCase();
      return edges.getIds().filter(id => {
        const e = edges.get(id);
        return edgeBaseColor(e).toLowerCase() === want;
      });
    }
    function setLegendActive(hex) {
      document.querySelectorAll('.leg-link').forEach(el => {
        el.classList.toggle('active', el.getAttribute('data-edge-color') === hex);
      });
    }
    document.querySelectorAll('.leg-link').forEach(el => {
      el.addEventListener('click', function () {
        const hex = el.getAttribute('data-edge-color');
        if (lockedEdgeColor === hex) {
          lockedEdgeColor = null;
          setLegendActive(null);
          resetEdgeStyles();
          return;
        }
        lockedEdgeColor = hex;
        setLegendActive(hex);
        emphasizeEdges(edgesMatchingColor(hex));
      });
    });

    network.once('stabilizationIterationsDone', function () {
      network.setOptions({ physics: false });
      atmIds.forEach(id => nodes.update({ id, fixed: false }));
      resetEdgeStyles();
      network.fit({ animation: false, padding: 40 });
    });
  </script>
</body>
</html>
"""

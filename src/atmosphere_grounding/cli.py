"""CLI entrypoints for the Cambridge atmosphere grounding pilot."""

from __future__ import annotations

import logging
from typing import Optional

import typer
from rich import print as rprint
from rich.table import Table

from atmosphere_grounding.collect.pipeline import run_collect
from atmosphere_grounding.collect.quota import QuotaLedger
from atmosphere_grounding.config import load_config, resolve_path, set_seed
from atmosphere_grounding.correlate import run_correlation
from atmosphere_grounding.extract import run_extract, run_fusion_pass
from atmosphere_grounding.graph import (
    build_graph,
    export_browser_view,
    inspect_atmosphere,
    load_graphml,
)
from atmosphere_grounding.ground import detect_objects, run_ground

app = typer.Typer(
    name="atmosphere",
    help="Cambridge pilot: atmosphere → visual grounding → knowledge graph",
    add_completion=False,
)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)


def _cfg(config: Optional[str]) -> dict:
    cfg = load_config(config)
    set_seed(int(cfg.get("seed", 42)))
    return cfg


@app.command("quota")
def quota_cmd(
    config: Optional[str] = typer.Option(None, help="Path to YAML config"),
) -> None:
    """Show quota ledger vs soft/hard caps."""
    cfg = _cfg(config)
    ledger = QuotaLedger(resolve_path(cfg, "quota_ledger"), cfg)
    table = Table(title="Places API quota ledger")
    table.add_column("SKU")
    table.add_column("Used")
    table.add_column("Soft")
    table.add_column("Hard")
    table.add_column("Remaining soft")
    for sku, row in ledger.summary().items():
        table.add_row(
            sku,
            str(row["used"]),
            str(row["soft_cap"]),
            str(row["hard_cap"]),
            str(row["remaining_soft"]),
        )
    rprint(table)


@app.command("collect")
def collect_cmd(
    config: Optional[str] = typer.Option(None, help="Path to YAML config"),
    dry_run: bool = typer.Option(False, help="Plan API calls without spending quota"),
    use_fixtures: bool = typer.Option(
        False, help="Use data/fixtures instead of live Places API"
    ),
) -> None:
    """Discover Cambridge public places, cache details + photos under quota caps."""
    cfg = _cfg(config)
    result = run_collect(cfg, dry_run=dry_run, use_fixtures=use_fixtures)
    rprint(
        {
            "n_places": len(result["places"]),
            "n_reviews": len(result["reviews"]),
            "n_images": len(result["images"]),
            "quota": result.get("quota"),
        }
    )


@app.command("extract")
def extract_cmd(
    config: Optional[str] = typer.Option(None),
    heuristic: bool = typer.Option(
        False, help="Force heuristic extractor (skip Ollama)"
    ),
) -> None:
    """Extract lexicon atmospheres + nouns from reviews via Ollama (or heuristic)."""
    cfg = _cfg(config)
    mentions = run_extract(cfg, use_heuristic=heuristic)
    rprint({"n_mentions": len(mentions)})


@app.command("ground")
def ground_cmd(config: Optional[str] = typer.Option(None)) -> None:
    """Match images, ground nouns, run scene/object/context ablation + profiles."""
    cfg = _cfg(config)
    evidence = run_ground(cfg)
    rprint({"n_evidence": len(evidence)})


@app.command("graph")
def graph_cmd(config: Optional[str] = typer.Option(None)) -> None:
    """Build NetworkX multimodal graph and write GraphML."""
    cfg = _cfg(config)
    G = build_graph(cfg)
    rprint(
        {
            "n_nodes": G.number_of_nodes(),
            "n_edges": G.number_of_edges(),
        }
    )


@app.command("detect")
def detect_cmd(config: Optional[str] = typer.Option(None)) -> None:
    """Image-first object detection (Grounding DINO / SigLIP vocab)."""
    cfg = _cfg(config)
    rows = detect_objects(cfg)
    rprint({"n_detections": len(rows)})


@app.command("fuse")
def fuse_cmd(
    config: Optional[str] = typer.Option(None),
    heuristic: bool = typer.Option(False),
) -> None:
    """Pass-B fusion: comment mentions + image object lists → mentions_fused.jsonl."""
    cfg = _cfg(config)
    fused = run_fusion_pass(cfg, use_heuristic=heuristic)
    rprint({"n_fused": len(fused)})


@app.command("correlate")
def correlate_cmd(config: Optional[str] = typer.Option(None)) -> None:
    """Place-level comment↔image correlation report."""
    cfg = _cfg(config)
    rows = run_correlation(cfg)
    rprint({"n_places": len(rows)})


@app.command("backup")
def backup_cmd(config: Optional[str] = typer.Option(None)) -> None:
    """Snapshot current Google raw cache into data/backup/google/."""
    from atmosphere_grounding.collect.backup import backup_google_raw

    cfg = _cfg(config)
    dest = backup_google_raw(cfg, label="manual")
    rprint({"backup": str(dest)})


@app.command("view")
def view_cmd(
    config: Optional[str] = typer.Option(None),
    no_open: bool = typer.Option(False, help="Write HTML but do not open browser"),
) -> None:
    """Build a browser HTML view of the logic graph and open it."""
    import webbrowser
    from pathlib import Path

    cfg = _cfg(config)
    paths = export_browser_view(cfg)
    html = Path(paths["html"])
    rprint(f"Wrote {html}")
    rprint(f"Readable chains: {paths['logic_view']}")
    if not no_open:
        webbrowser.open(html.resolve().as_uri())


@app.command("inspect")
def inspect_cmd(
    atmosphere: str = typer.Argument(..., help="e.g. inviting | safe | calm"),
    config: Optional[str] = typer.Option(None),
    top: int = typer.Option(15, help="Max noun associations to show"),
) -> None:
    """Print atmosphere → noun association chains for human review."""
    cfg = _cfg(config)
    path = resolve_path(cfg, "graph_dir") / "cambridge_pilot.graphml"
    if not path.exists():
        rprint("[yellow]Graph missing; building…[/yellow]")
        G = build_graph(cfg)
    else:
        G = load_graphml(cfg)
    chains = inspect_atmosphere(G, atmosphere.lower(), top_n=top)
    table = Table(title=f"Atmosphere → noun: {atmosphere}")
    table.add_column("noun")
    table.add_column("count")
    table.add_column("confidence")
    table.add_column("level")
    for c in chains:
        table.add_row(
            str(c.get("noun")),
            str(c.get("count")),
            str(c.get("confidence")),
            str(c.get("level")),
        )
    if not chains:
        rprint(f"[red]No ASSOCIATED_WITH edges for {atmosphere}[/red]")
    else:
        rprint(table)


@app.command("run-all")
def run_all_cmd(
    config: Optional[str] = typer.Option(None),
    use_fixtures: bool = typer.Option(
        True, help="Default True for safe offline e2e; set --no-use-fixtures for live API"
    ),
    dry_run: bool = typer.Option(False),
    heuristic: bool = typer.Option(False, help="Force heuristic LLM extract"),
) -> None:
    """Run collect → extract → ground → graph (fixtures by default)."""
    cfg = _cfg(config)
    rprint("[bold]1/4 collect[/bold]")
    run_collect(cfg, dry_run=dry_run, use_fixtures=use_fixtures)
    rprint("[bold]2/4 extract[/bold]")
    run_extract(cfg, use_heuristic=heuristic)
    rprint("[bold]3/4 ground[/bold]")
    run_ground(cfg)
    rprint("[bold]4/4 graph[/bold]")
    G = build_graph(cfg)
    for atm in cfg["atmospheres"]["active"]:
        chains = inspect_atmosphere(G, atm, top_n=8)
        rprint(f"\n[cyan]{atm}[/cyan]: {chains}")


if __name__ == "__main__":
    app()

# Discussions

Research brief materials and design-session outputs for **Atmosphere Grounding**.

This folder is **standalone documentation** for presentations and design history. The canonical technical architecture lives in [`Docs/ARCHITECTURE.txt`](../Docs/ARCHITECTURE.txt).

## Contents

| File | Description |
|------|-------------|
| [`presentation-slides.md`](presentation-slides.md) | All slide text + embedded images (Markdown) |
| [`text/`](text/) | **Exact plain-text** slide copy (`.txt`, one file per slide) |
| [`flowcharts.md`](flowcharts.md) | Mermaid source diagrams |
| [`design-decisions-summary.md`](design-decisions-summary.md) | Condensed design decisions |
| [`images/`](images/) | **PNG flowcharts** for PowerPoint/Keynote + `.mmd` sources |

## Slide images (PNG — exact files for upload to slides)

| File | Use |
|------|-----|
| [`images/architecture-full.png`](images/architecture-full.png) | Detailed pipeline (Steps 0–6) |
| [`images/architecture-compact.png`](images/architecture-compact.png) | One-slide overview |
| [`images/two-layers.png`](images/two-layers.png) | Layer A + Layer B conceptual |
| [`images/research-stages.png`](images/research-stages.png) | Stage 0 → 1 → 2 (LoRA) |
| [`images/lora-final-goal.png`](images/lora-final-goal.png) | Final goal: distillation → LoRA |

## Related repo docs

- [`Docs/ARCHITECTURE.txt`](../Docs/ARCHITECTURE.txt) — full pipeline guide
- [`Docs/DESIGN_LOCK.txt`](../Docs/DESIGN_LOCK.txt) — compact decision summary
- [`Docs/PROJECT.txt`](../Docs/PROJECT.txt) — goals and research stages

## Viewing flowcharts

GitHub renders Mermaid diagrams inside `.md` files. Open [`flowcharts.md`](flowcharts.md) in the browser on github.com for automatic diagrams.

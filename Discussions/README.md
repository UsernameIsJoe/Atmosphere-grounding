# Discussions

Research brief materials and design-session outputs for **Atmosphere Grounding**.

This folder is **standalone documentation** for presentations and design history. The existing implemented/earlier technical architecture is described in [`Docs/ARCHITECTURE.txt`](../Docs/ARCHITECTURE.txt). **The latest research direction, not yet implemented or locked, is recorded in [`current-research-baseline-2026-11.md`](current-research-baseline-2026-11.md).**

## Contents

| File | Description |
|------|-------------|
| [`presentation-slides.md`](presentation-slides.md) | All slide text + embedded images (Markdown) |
| [`text/`](text/) | **Exact plain-text** slide copy (`.txt`, one file per slide) |
| [`flowcharts.md`](flowcharts.md) | Mermaid source diagrams |
| [`design-decisions-summary.md`](design-decisions-summary.md) | Condensed design decisions | 
| [`current-research-baseline-2026-11.md`](current-research-baseline-2026-11.md) | **Current research baseline**: two parallel branches, shared-location learning, visual predictor and open methods |
| [`project-research-map-and-workstreams-2026-11-03.md`](project-research-map-and-workstreams-2026-11-03.md) | **Project-wide research map**: NLI, ABSA, evidence integration, visual features, cross-modal learning, prediction and evaluation guardrails |
| [`location-sentiment-five-research-questions.md`](location-sentiment-five-research-questions.md) | Five conceptual research topics (exploratory learning agenda) |
| [`stage1a-three-approach-comparison-2026-11-03.md`](stage1a-three-approach-comparison-2026-11-03.md) | **Current three-way text experiment**: direct NLI, multi-hypothesis NLI, pretrained ABSA → NLI |
| [`stage1a-executed-results-evaluation-audit-2026-11-03.md`](stage1a-executed-results-evaluation-audit-2026-11-03.md) | **Executed results**: both successful A/B/C runs, full confusion counts, metrics, artifacts and provisional-label limitations |
| [`stage1a-next-research-sequence-2026-11-03.md`](stage1a-next-research-sequence-2026-11-03.md) | **Agreed next steps**: label-free hypothesis robustness, NLI model comparison, ABSA model comparison, then integration |
| [`stage1a-hypothesis-robustness-results-2026-11-03.md`](stage1a-hypothesis-robustness-results-2026-11-03.md) | **214-review hypothesis robustness results**: consistency, full run provenance, probability variation and illustrative failures |
| [`stage1a-hypothesis-vocabulary-literature-and-plan-2026-11-03.md`](stage1a-hypothesis-vocabulary-literature-and-plan-2026-11-03.md) | **Literature review & implemented next test**: synonyms vs facets, 60-candidate vocabulary, label-free ensemble checks and experimental limitations |
| [`stage1a-expanded-vocabulary-results-2026-11-03.md`](stage1a-expanded-vocabulary-results-2026-11-03.md) | **Executed 60-candidate, 214-review experiment**: ensemble stability, variation, outliers, run artifacts, and limitations |
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

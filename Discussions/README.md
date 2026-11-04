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
| [`stage1a-nli-checkpoint-screening-plan-2026-11-03.md`](stage1a-nli-checkpoint-screening-plan-2026-11-03.md) | **NLI model screening**: 50 reviews across 43 locations, DeBERTa vs ModernBERT, binary/three-way output safeguards and model-comparison protocol |
| [`stage1a-nli-checkpoint-screening-results-2026-11-03.md`](stage1a-nli-checkpoint-screening-results-2026-11-03.md) | **Executed matched-model screening**: BART, DeBERTa, ModernBERT; 50 reviews, consistency, speed, agreements, and binary-output caveats |
| [`stage1a-absa-next-experiment-plan-2026-11-03.md`](stage1a-absa-next-experiment-plan-2026-11-03.md) | **Next ABSA research**: compare location evidence extraction independently, controlled cases, then context-preserving NLI integration |
| [`stage1a-absa-extraction-screening-results-2026-11-03.md`](stage1a-absa-extraction-screening-results-2026-11-03.md) | **Completed ABSA extraction screening**: three models/baselines, 50 reviews, evidence coverage, controlled probes and tomorrow's integration handoff |
| [`stage1a-absa-nli-integration-literature-and-design-2026-11-04.md`](stage1a-absa-nli-integration-literature-and-design-2026-11-04.md) | **Next-phase research**: ASTE aspect–opinion relations, aspect-conditioned inference, evidence-set fusion, experimental controls and staged implementation plan |
| [`stage1a-relation-pilot-results-2026-11-04.md`](stage1a-relation-pilot-results-2026-11-04.md) | **Executed M1 relation pilot**: two run audits, AOS-versus-dependency results, controlled failures and next integration gate |
| [`stage1a-m2-structured-evidence-experiment-2026-11-04.md`](stage1a-m2-structured-evidence-experiment-2026-11-04.md) | **M2 experiment configured**: four ABSA/extraction sources, BART evidence-augmentation controls, matched 20-review pilot |
| [`stage1a-m2-structured-evidence-results-2026-11-04.md`](stage1a-m2-structured-evidence-results-2026-11-04.md) | **Executed M2 study**: 480 NLI predictions, all extractor annotations, repeated-text control, structure-ablation limits and M2b recommendation |
| [`stage1a-m2b-claim-level-nli-plan-2026-11-04.md`](stage1a-m2b-claim-level-nli-plan-2026-11-04.md) | **M2b controlled NLI experiment**: 18 logical cases, effective swaps, independent claim evidence, aggregation and repetition controls |
| [`stage1a-m2b-claim-level-nli-results-2026-11-04.md`](stage1a-m2b-claim-level-nli-results-2026-11-04.md) | **Completed M2b**: 345 NLI evaluations, logical contrasts, operative relation swaps, misleading evidence flags and next relevance tests |
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

| [`stage1a-m2c-relevance-direction-check-2026-11-04.md`](stage1a-m2c-relevance-direction-check-2026-11-04.md) | **Bounded M2c direction check**: 20 fixed claims, relevance vs direct NLI, prespecified stop gate, return to Stage 1B |

| [`stage1a-m2c-relevance-results-and-closeout-2026-11-04.md`](stage1a-m2c-relevance-results-and-closeout-2026-11-04.md) | **M2c executed and closed**: passes overall predefined relevance screen (13/16 retained, 8/44 false positives); proceed only to bounded real-review check and refocus on Stage 1B |

| [`stage1a-integrated-absa-nli-baseline-2026-11-04.md`](stage1a-integrated-absa-nli-baseline-2026-11-04.md) | **Consolidated Stage 1A baseline**: one source-preserving ABSA→NLI implementation, fixed integration architecture, tests and CI |

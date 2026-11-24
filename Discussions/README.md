# Discussions

**PPLX-Decider executed test (November 24):** [Native BF16 probability, repeatability and option-order results](../research_audit/stage1a_pplx_decider_12_2026-11-24/README.md) — same twelve calm targets; 480 main readouts plus reload/API checks. Identical logits and probabilities across ten repeats of each input; median order gap 1.07 points, maximum 6.90; no verdict flips. All twelve verdicts match Gemma, including the personal-stress attribution error. Includes native raw logits, two figures and an assistant plausibility audit; no emotion-calibration or accuracy claim.

**November 24 consolidated discussion:** [Gemma audit, temperature, stability figures and mean/median clarification](gemma-probability-audit-temperature-and-stability-2026-11-24.md) — includes the researcher's agreement on the reviewed cases, all five charts and exact values, reference-audit limitations, the A/B definitions, and the distinction between averaging predictions and summarizing sensitivity. No new model inference.

**Gemma assistant plausibility audit (November 24):** [Text/codebook review and four cases for researcher adjudication](../research_audit/stage1a_probability_formats_12_2026-11-23/GEMMA_QUALITATIVE_AUDIT_2026-11-24.md) — the researcher clarified that the requested audit is a current advanced-LLM reading of whether the probabilities make semantic sense. Seven cases appear reasonable, one has a clear attribution mismatch, and four were presented for human review; subsequent general agreement is recorded in the consolidated follow-up. This is a qualitative assistant assessment, with full contexts and saved temperature vectors, rather than an inherited-reference accuracy claim.

**Gemma usefulness check (November 23):** [Soft probabilities versus fixed smoothing](../research_audit/stage1a_probability_formats_12_2026-11-23/GEMMA_SIGNAL_EVALUATION.md) — no new inference. Some coarse case distinctions are visible, but error ranking is weak against provisional references and the small loss advantage depends heavily on K01. Only two calm judgments are explicitly in the current audit; validated confidence or training utility is not established.

**Executed alternatives and softening evaluation (November 23):** [Qwen numbers/semantic answers and offline Gemma evaluation](../research_audit/stage1a_probability_formats_12_2026-11-23/README.md) — existing cold letter observations reused, missing baselines and new orders added; 615 new Qwen readouts plus nine expanded top-k calls, zero new Gemma calls. Numbers and semantic answers improve typical sensitivity, with large remaining order effects. Gemma softening exposes previously compressed letter sensitivity.

**Executed repeatability and logits test (November 23):** [Report, charts, code and raw results](../research_audit/stage1a_probability_repeatability_12_2026-11-23/README.md) — 1,248 native readouts on the same 12 reviews, 240 cache-control calls and 64 direct Gemma passes. Qwen's letter effect survives deterministic full recomputation; disabling cache reuse stabilized the tested prompts. Undoing Gemma's soft-cap did not soften its probabilities.

Research brief materials and design-session outputs for **Atmosphere Grounding**.

**November 23 probability stability follow-up:** [Discussion, literature and four answers](model-probability-stability-and-logits-2026-11-23.md) — identical-run repeatability versus code/wording sensitivity, stabilization methods, proposed tolerance and logits access. Includes the correction that the first pilot did not measure identical-request probability variability.

**Executed probability pilot (November 23):** [Calm, same 12 reviews, Qwen and Gemma](../research_audit/stage1a_calm_probability_12_2026-11-23/README.md) — 72 main calls, native probability readouts, code-mapping control, raw results and cleanup record. Development experiment; no calibration or training-benefit claim.

**November 23 follow-up:** [Three-point discussion remark](research-discussion-2026-11-19.md#9-november-23-follow-up) — probability signals in the emotion representation, embedding-based segment weights, and NLI hypothesis families aligned with image definitions. Embedding and NLI directions are provisionally agreed; probability utility remains to be tested.

**November 19 session:** [Full discussion record](research-discussion-2026-11-19.md) · [Shared-catalogue methodology](shared-catalogue-cross-modal-methodology-2026-11-19.md) · [Matching walkthrough](cross-modal-matching-research-walkthrough-2026-11-19.md).

This folder is **standalone documentation** for presentations and design history. The existing implemented/earlier technical architecture is described in [`Docs/ARCHITECTURE.txt`](../Docs/ARCHITECTURE.txt). **The latest conceptual discussion (2026-11-19) is [shared-catalogue cross-modal emotion grounding](shared-catalogue-cross-modal-methodology-2026-11-19.md), including evidence vectors, target eligibility and four unresolved methodological issues. Its learning methods remain proposals.** The [earlier research baseline](current-research-baseline-2026-11.md) provides historical context.

## Contents

| File | Description |
|------|-------------|
| [Model probability stability, stabilization and logits](model-probability-stability-and-logits-2026-11-23.md) | **November 23 follow-up discussion**: four research answers, repeat-control caveat, comparison chart, primary sources and proposed diagnostics |
| [November 19 research discussion](research-discussion-2026-11-19.md) | **Start here for the full day's discussion**: development of the idea, clarifications, decisions, open issues and links to both detailed records |
| [Cross-modal matching research walkthrough](cross-modal-matching-research-walkthrough-2026-11-19.md) | **Full November 19 answer, preserved as written**: processing location collections, whole-image and region matching, no-match handling, partial transport, sources and A–D comparison |
| [Shared-catalogue cross-modal methodology](shared-catalogue-cross-modal-methodology-2026-11-19.md) | **November 19 discussion record**: text emotion/evidence vectors, image attributes, eligibility, primary research references, experiment proposal and four unresolved issues |
| [`presentation-slides.md`](presentation-slides.md) | All slide text + embedded images (Markdown) |
| [`text/`](text/) | **Exact plain-text** slide copy (`.txt`, one file per slide) |
| [`flowcharts.md`](flowcharts.md) | Mermaid source diagrams |
| [`design-decisions-summary.md`](design-decisions-summary.md) | Condensed design decisions | 
| [`current-research-baseline-2026-11.md`](current-research-baseline-2026-11.md) | **Earlier research baseline**: two parallel branches, shared-location learning, visual predictor and open methods |
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

| [`stage1a-integrated-absa-nli-executed-audit-2026-11-04.md`](stage1a-integrated-absa-nli-executed-audit-2026-11-04.md) | **Integrated run verified**: 20 reviews, 408 NLI calls, source evidence retention and key remaining ABSA→NLI mechanism gap |

| [`stage1a-absa-guided-source-nli-2026-11-04.md`](stage1a-absa-guided-source-nli-2026-11-04.md) | **ABSA-indexed source-clause NLI**: original offsets, contrastive decomposition, unmatched evidence fallback and whole-sentence comparison |

| [`stage1a-absa-guided-nli-executed-results-2026-11-04.md`](stage1a-absa-guided-nli-executed-results-2026-11-04.md) | **Executed ABSA-indexed NLI audit**: 62 evidence units/emotion, only two label changes (one formatting artifact), and segmentation regression fix |

| [`stage1a-absa-relevance-nli-ledger-2026-11-04.md`](stage1a-absa-relevance-nli-ledger-2026-11-04.md) | **Operational ABSA→relevance→NLI evidence ledger**: real-review source provenance, component comparison, non-destructive safeguards and execution caveats |

| [`stage1a-real-review-evidence-audit-2026-11-04.md`](stage1a-real-review-evidence-audit-2026-11-04.md) | **First semantic audit**: 30 real passage–emotion judgments, relevance vs NLI error analysis, and review of all 11 grounded AOS relations |

| [`stage1a-absa-relation-benchmark-v1-2026-11-04.md`](stage1a-absa-relation-benchmark-v1-2026-11-04.md) | **ABSA-focused model selection**: existing DeBERTa/SetFit vs AOS/dependency roles, 11 annotated controlled relation references, strict relation/negation benchmark and CI workflow |

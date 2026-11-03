# Atmosphere Grounding — Whole-Project Research Map and Stage 1A Workstream Tracker

**Updated:** November 3, 2026. **Status:** Living project map; the authoritative research objective remains [current-research-baseline-2026-11.md](current-research-baseline-2026-11.md). This tracker preserves scope while individual experiments proceed; it is not a design lock.

## End-to-end objective

Use textual evidence of emotional atmosphere and measurable visual qualities from **sets of reviews and images associated through shared physical location IDs**. Learn associations across locations and eventually predict nine theory-supported atmospheric/emotional categories from images and visual qualities. The pilot tests only calm, inviting, safe; the final nine-category taxonomy remains to be confirmed. No one-to-one review/photo pairing.

## Research stages and status

| Stage | Research problem | Current status | Guardrail |
|---|---|---|---|
| **1A — Text to location-attributed emotion evidence** | Detect support, contradiction, insufficient evidence, cited passages and uncertainty | **Active**. Initial 30-review NLI/ABSA comparison, 214-review hypothesis sensitivity test complete; 60-hypothesis vocabulary experiment implemented (successful results not yet verified) | Do not equate reviewer emotion with atmospheric evidence; no independently human-rated ground truth |
| **1B — Image to visual feature library** | Consistent theory-grounded visual descriptors: objects, densities, contrast, composition, spatial enclosure, etc. | **Concept/design task open**; existing code and ontology require audit | Fixed library across locations and not hard-coded to nine emotions |
| **2 — Location-level cross-modal learning** | Learn which feature vectors associate with review-derived emotion evidence when texts and images are *unpaired* | **Not yet tested** | Use location as unit of association and train/test split; associations are not causal explanations |
| **3 — Visual atmosphere prediction** | Primary: image + explicit visual-quality vector → nine predictions; stretch: image-only → nine predictions | **Goal defined; model undecided** | Reviews are weak training evidence, not mandatory inference inputs. Do not prematurely commit to VLM/CLIP/LoRA |
| **Validation / infrastructure (cross-cutting)** | Data rights, annotation, uncertain evidence, place-level holdout and generalization | **Partly identified, mostly unresolved** | Existing assistant-authored provisional labels are not external ground truth |

## Stage 1A: preserve ALL workstreams

### A. NLI: formulation / vocabulary

**Current focus.** Three-class `facebook/bart-large-mnli` has been tested on real reviews. Full-corpus run [41673219260](https://github.com/UsernameIsJoe/Atmosphere-grounding/actions/runs/41673219260) used 214 reviews and seven hypotheses per pilot emotion; inviting showed greater wording sensitivity than calm or safe. See [robustness results](stage1a-hypothesis-robustness-results-2026-11-03.md). Expanded **60-candidate** registry with separate core paraphrases, related facets and opposing controls: [vocabulary study](stage1a-hypothesis-vocabulary-literature-and-plan-2026-11-03.md) and [draft JSON](../configs/stage1a_hypothesis_vocabulary_draft.json). Corresponding Actions workflow is configured but results not verified when this map was updated.

**Next:** inspect paraphrase families, outlier passages, confidence distributions, ensemble instability and semantic drift; compare genuine synonyms, not all merely related concepts. Keep facets separately labeled. Do not treat consistency as predictive accuracy or probabilities as calibrated emotional intensity.

### B. NLI: checkpoint comparison (NOT superseded by vocabulary work)

**Pending:** run the SAME review/hypothesis dataset on current BART-MNLI, DeBERTa-v3-large-zeroshot-v2.0, and ModernBERT-large-zeroshot-v2.0 (subject to verified model compatibility). Preserve model label-space differences: binary entailment/not-entailment is **not** interchangeable with three-way support/contradiction/neutral. Also test negation, irrelevant reviewer emotions, multi-claim/mixed reviews and premises whose conclusions are unsupported.

### C. ABSA: alternative extractors (NOT dropped)

**Completed initial test:** [A/B/C experiment audit](stage1a-executed-results-evaluation-audit-2026-11-03.md) compared direct NLI, multi-hypothesis NLI, and **one** pretrained `yangheng/deberta-v3-base-end2end-absa` extraction pass followed by NLI. The tested ABSA sentence filter sometimes discarded relevant context (e.g. disruptive sirens), so no improvement was demonstrated on 30 provisional, assistant-labeled reviews. **This does not show ABSA is inherently ineffective.**

**Pending:**
- Compare several *distinct* ABSA/aspect-identification methods, not just checkpoint sizes: end-to-end ABSA, Arctic-ABSA, instruction-guided aspect extraction, SetFitABSA where suitable; aspect-conditioned `yangheng/deberta-v3-large-absa-v1.1` serves a **different task** (sentiment for supplied aspect) and should not be treated as a drop-in extractor.
- Measure independently: which location-grounded descriptions/spans were found, evidence lost vs original reviews, aspect precision versus usefulness, extraction from long/negated/mixed texts, domain suitability and computational cost.
- Preserve source sentences/spans and polarity as separate metadata; **positive/negative aspect sentiment is not automatically an atmosphere emotion label.**
- Test ABSA as **context-preserving annotations or supplementary evidence**, not only a hard filter. Assess whether the model captures observations missed by direct NLI.

### D. Stage 1A integration and other baselines

**Pending:** compare direct NLI, strong hypothesis-ensemble NLI, ABSA-augmented NLI, and embeddings for retrieval/similarity; surface lexical co-occurrence as a modest baseline only. Keep all changes controlled so effects can be attributed to component choices. Evaluate competing support/contradiction/neutral signals rather than averaging away disagreement. Develop passage- and review-to-location aggregation, evidence coverage, sparse-review handling, review reliability and uncertainty before generating any definitive per-location scores.

## Stage 1B and Stage 2: active scientific dependencies

**Image features:** decide theory-grounded fixed feature library, feature extraction models/measurements, per-image outputs and extraction quality audit. Keep features emotion-agnostic at extraction, even if later associated with emotions.

**Location association:** align aggregated textual evidence with collections of visual measurements by `place_id`. Compare simple interpretable models first; test multi-instance/set learning only if warranted. Split held-out **locations**, not individual reviews/images. Test predictors against place type confounds, missing signals and limitations of visually unobservable atmosphere (noise, odors, social treatment, safety).

## Evaluation guardrails and unresolved questions

- Current repo corpus: **214 reviews / 43 locations**; test samples include clusters of reviews per place. Current results describe internal consistency, not validity.
- Human-rated atmosphere ground truth **does not exist**. The earlier 30-review S/C/U labels were assistant-authored diagnostic references, not human-annotated truth. Label-free tests (hypothesis variation, controlled logical cases, model disagreement, evidence retention) can advance methods but cannot prove correctness.
- Final nine emotions, semantic definitions, aspects, location aggregation scheme and score interpretation **remain open**.
- Confirm permissions for training/storage/reuse of Google Maps-derived text and images before downstream learning.
- **No feature drift:** do not let hypotheses choose the image feature library, or let visual data define textual emotion labels by circular logic.
- Historical `Docs/PROJECT.txt`, `Docs/ARCHITECTURE.txt` and `Docs/DESIGN_LOCK.txt` describe older architecture and do not supersede the current baseline.

## Agreed research order (within Stage 1A)

1. Hypothesis formulation/vocabulary (active; 60-candidate experiment configured).
2. NLI checkpoint comparison on frozen inputs.
3. **ABSA model and aspect-extraction comparison** (explicitly retained).
4. Integration of text evidence methods, then review-to-location aggregation.

The other project stages remain part of the same research program and can be developed alongside Stage 1A, but should not be prematurely fixed by text-only results.

**Next project-level checkpoint:** after the expanded vocabulary experiment, evaluate results and continue to NLI-model variation; preserve ABSA comparison as a separate required workstream, then integrate with Stage 1B and cross-modal research.

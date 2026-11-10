# Atmosphere Grounding — Reviewed research design (Sections 3–7)

**Date:** 2026-11-10  
**Status:** Agreed project-level research structure; **methods remain proposals, not validated implementations**.  
**Scope:** This memo records the review of the supplied *Atmosphere Grounding: Project Design (v2)*, specifically its Sections 3–7. It is a research-design update, **not** an assertion that the LLM-panel, fine-tuned student, visual pipeline, association models, or predictor have been trained or validated.

## Decision and interpretation

Retain the four-stage research flow in the proposed architecture:

- **Stage 1A: text grounding.** Convert place-linked human descriptions into *source-evidenced, location-attributed reports* about atmosphere, including direction, strength/coverage, attribution, disagreement and uncertainty. A diverse local-LLM annotation panel followed by a trained scoring model is the **current candidate approach**, not a locked architecture.
- **Stage 1B: visual grounding.** Independently measure a fixed, interpretable, atmosphere-agnostic library of physical, spatial and photographic image features. Report per-photo measurements and their variability; aggregate at the place level for the primary cross-modal analysis. Learned semantic features (e.g., SigLIP) must remain distinguishable from named/measured features.
- **Stage 2: cross-modal association learning.** Use *shared place identity* as weak text–image correspondence. Test which visual features, alone or in combinations, are associated with variation in *reported* atmosphere. Prioritize interpretable, place-level analyses, geographical/place-type controls and uncertainty; avoid describing observational associations as causal effects.
- **Stage 3: validation and application.** Test robustness and generalization on unseen, geographically separated places, with null/shuffle baselines and external checks where licensable. **If** justified by results, produce a visual predictor that does not require new reviews at inference. The practical endpoint remains image plus measurable visual features; image-only prediction is a stretch goal.

These stages specify **research questions, input/output contracts and guardrails**. Implementation choices and numerical acceptance thresholds should be refined through controlled research, rather than fixed prematurely.

## Section 3 — Architecture (retain)

Two separately evaluated evidence-production branches, 1A text and 1B images, converge through the **place** as the unit of analysis. Reviews/photos have no known one-to-one pairing. Training/evaluation must split whole places, with spatially separated holdouts for claims of geographical generalization.

**Boundary:** Do not pass image-derived atmosphere suggestions to the text labeling branch, and do not assign atmosphere labels to visual features during extraction.

## Section 4 — Stage 1A: text grounding (refined design, 2026-11-10)

**Current detailed decision record:** [STAGE1A_REFINED_DESIGN_2026-11-10.md](STAGE1A_REFINED_DESIGN_2026-11-10.md). This replaces the earlier provisional Section 4 discussion below; the historical archived audits remain unchanged.

- **No human labeling in Stage 1A.** Model disagreement, prompt sensitivity, reproducibility, source checks and student-to-panel fidelity are measurable; none establishes independent accuracy or correspondence to human perception.
- **Clause-first deterministic segmentation**, shared by the three independent annotating LLMs, with full-review context retained. Allow arrays of evidence records only when necessary within an already segmented clause.
- Two prompts per model: A supplies candidate labels; B tests wording sensitivity. Keep every individual vote; use majority as a baseline and full categorical vote distributions as soft targets, not probabilities of correctness.
- Trust checks include pairwise agreement and 3–0/2–1/three-way split diagnostics, literal source provenance, per-type and hard-case breakdowns; no spurious two-model leave-one-out majority.
- **NLI-first adaptation:** prioritize fine-tuning an NLI-pretrained DeBERTa model and compare with separate evidence heads initialized from the **same NLI checkpoint**. A base classifier from scratch is not mandatory. Direct/indirect indicators are not automatically logical entailments.
- Aggregate place profiles as **coverage, direction and uncertainty**, rather than a single unsupported emotion score. Missing evidence is not negative evidence.
- **Mandatory Stage 2 sensitivity:** rerun associations using majority and each individual panel model; compare sign, magnitude and spatial/statistical stability. In addition, contrast **explicit-only** atmosphere evidence against tracks adding direct indicators and indirect evidence to expose possible shared-LLM-prior effects. These are robustness diagnostics, not proof of semantic correctness.
- All methods, gates and actual performance remain to be tested; no Stage 1A implementation is claimed here.

## Section 5 — Stage 1B: visual grounding (retain purpose, revise weighting)

- Filter images for usable depictions of space, tracking exclusion rates and selection bias. Audit filter error on independently inspected photographs.
- Maintain separate interpretable feature groups: objects/segmentation/spatial descriptors, photographic properties and optionally semantic embeddings. Validate detectors/segmenters against human-audited image measurements; their outputs are *model-derived measurements*, not intrinsically objective truth.
- Avoid photo selection or importance weighting **conditioned on selected atmosphere evidence** in the confirmatory association test. Referent matching on emotion-bearing review spans, even if the exact matched referent is excluded later, can still favor correlated image features and produce selection bias.
- **Primary Stage-2 profile:** an emotion-blind, filtered, unweighted place profile, including per-feature spread and missingness. Investigate review/photo referent weighting only as a clearly labeled secondary sensitivity analysis; findings supported only by weighted analyses remain exploratory.
- The existing `configs/visual_categories_v1.yaml` is a starting feature library, **not yet certified for the revised objective**.

## Section 6 — Stage 2: association learning (retain, distinguish two outcomes)

- The **place** is the sample unit (photos and reviews within it are repeated measurements, not new independent places).
- Model **(1) whether an atmosphere is mentioned/reported** separately from **(2) support versus opposition conditional on evidence**. A simple two-part or hierarchical model is a candidate, not yet selected.
- Begin with transparent descriptive associations and regularized regression/GAM or comparable interpretable models; extend to interactions and richer architectures only if sample size and held-out gains justify them. Named visual-feature inputs already provide an interpretable bottleneck; a separate concept-bottleneck network is not a required stage.
- Pre-specify feature testing families and multiple-comparison handling (e.g., FDR). Consider geographic structure, place types, sampling/review counts, imagery conditions and residual spatial autocorrelation; stratify or control where data permit.
- Predefine primary unweighted vs secondary weighted, named-feature-only vs semantic-embedding sensitivity analyses.
- **Do not claim sub-place associations** until text is actually tied to specific photos/sub-areas; only shared place IDs are currently grounded.

**Scientific result:** empirical association between visually measured features and *review-reported* perception, potentially transferable across place types/areas; not causality or an objective, universal emotion score.

## Section 7 — Stage 3: validation and application (retain with explicit gates)

- Evaluate each upstream measurement instrument independently (LLM-panel consistency and source integrity, image feature quality). End-to-end success against silver review targets alone is **not** independent perceptual validation.
- Use spatial/neighborhood blocks for held-out testing; avoid geography leakage through tuning. Compare shuffled/place-level null models and appropriately simple baselines; report uncertainty and when models should abstain.
- Separate three outcomes: **association stability**, **prediction of LLM-derived review labels**, and **external human correspondence if ever independently assessed**. These are not equivalent claims.
- If the evidence supports it, develop a visual-input predictor with uncertain, feature-grounded outputs and an interpretation layer limited to structured measured results. Review text is training evidence, not mandatory at prediction time.

## Repo reconciliation / sources of truth

- `Discussions/current-research-baseline-2026-11.md` establishes the contemporary research goal (nine categories, text evidence + independent visual library, eventual visual prediction). Preserve its distinction from older co-occurrence-first documents.
- `research_audit/stage1a_final_2026-11-10/README.md` records **unvalidated** component tests and the need for independent semantic evaluation. Keep this archive intact.
- `Docs/PROJECT.txt`, `Docs/ARCHITECTURE.txt`, `Docs/DESIGN_LOCK.txt` and the root README describe the earlier pilot implementation; they are **historical / operational documentation**, not evidence that the present proposal has been implemented.
- `configs/lexicon.yaml` currently lists **11** atmosphere terms; the modern research goal specifies **nine** but has not frozen the exact taxonomy. The pilot evaluates **calm, inviting, safe**. Do not silently select nine of the eleven. Resolve into one future versioned taxonomy before labeling.
- Current corpus reported by the archived audit: **214 reviews across 43 places**. These numbers are development provenance, not a validation claim.
- The attached Project Design v2 proposed Stage 1A panel annotation and NLI adaptation. The [2026-11-10 Stage 1A refinement](STAGE1A_REFINED_DESIGN_2026-11-10.md) records the current **agreed research-design decisions**, not completed experiments.

## Research precedents / evidence boundaries

- **Snorkel / weak supervision:** programmatic/noisy labels and downstream learning are established approaches, but correlated label sources and independent evaluation matter: Ratner et al., *Snorkel: Rapid Training Data Creation with Weak Supervision* (VLDB 2017), https://arxiv.org/abs/1711.10160 .
- **NLI transfer and hypothesis artifacts:** entailment-based label formulations can be sensitive to lexical choices; NLI does not automatically implement domain inference: Ma et al., *Issues with Entailment-based Zero-shot Text Classification* (ACL 2021), https://aclanthology.org/2021.acl-short.99/ .
- **Visual street perception precedent:** Place Pulse 2.0 studies visually perceived city qualities from crowd judgments of street views; not equivalent to review-reported atmosphere: Dubey et al. (2016), https://arxiv.org/abs/1608.01769 .
- **SigLIP 2** provides language-trained visual representations that can be useful but also import semantic priors: https://huggingface.co/blog/siglip2 .
- **Spatial CV:** Roberts et al., *Cross-validation strategies for data with temporal, spatial, hierarchical, or phylogenetic structure* (Ecography 2017), https://doi.org/10.1111/ecog.02881 .

These references support the *plausibility of components*, not the empirical validity of this particular pipeline.

## Next design questions (not yet decided)

1. Final nine category names and rubric; whether any axes are genuinely bipolar.
2. Clause segmentation edge cases and multi-evidence alignment across models.
3. Panel prompt stability, silver-label construction and NLI-specific supervision masks.
4. Evidence-type separation (explicit versus direct indicators versus indirect) and Stage 2 shared-bias diagnostics.
5. Stage 1B feature-quality gates and treatment of uneven photo coverage.
6. Stage 2 estimand, spatial controls, and target sample sizes after pilot prevalence checks.
7. Stage 3 criteria for transitioning from association research to visual prediction.

**Record of decision:** Keep Sections **3–7** as the project backbone. Use the agreed Stage 1A NLI-first candidate comparison without assuming a winner; do **not** prematurely lock other model choices or interpret prior pilot counts/LLM agreement as accuracy. This is a design update only; no pipeline implementation or new experiments were performed in this change.

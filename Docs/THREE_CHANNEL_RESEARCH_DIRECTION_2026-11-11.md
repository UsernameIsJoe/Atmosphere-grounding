# Three Channels — Research Direction (2026-11-11)

**Date:** November 11, 2026  
**Status:** Agreed conceptual research direction; **not** an implemented, empirically validated, or method-locked architecture.  
**Scope:** Project-wide reframing of Atmosphere Grounding. This document records the idea so it can be developed and challenged without forcing an immediate redesign of the existing code.

## Why three channels?

The original design had two branches: review-based atmosphere measurements (Stage 1A) and atmosphere-agnostic image qualities (Stage 1B), connected through location identity (Stage 2). Exploratory Stage 1A tests of ABSA, NLI, relevance filtering, and smaller local LLMs have not established stable, trustworthy atmosphere interpretation. This raises concern that model capacity, local hardware limits, and the requirement to finish text understanding before examining visual associations could dominate the project.

The new direction is **not** to make model-capacity competition the subject of the project. The project is an exploratory, rigorous research concept—not a commercial system requiring a polished universal emotion model. Instead of betting on a single successful text measurement pipeline, separate three meaningfully different views of a place and study their relationships.

## Three channels (kept distinct)

| Channel | What it measures | Typical input/output | Scientific boundary |
|---|---|---|---|
| **T-E: Text evidence** | Place-attributed atmosphere **explicitly reported** by people | Review source spans -> evidence for/against a category, attribution, review coverage and uncertainty -> place profile | Explicit does not mean error-free; extraction and selective reviewing still bias the measure. |
| **T-I: Text inference** | Atmosphere **inferred** from broader descriptions and contextual cues in review text | Reviews -> category-specific inferred atmosphere estimates with uncertainty/provenance | An inference is not a reported feeling or ground truth; language-model priors and physical-feature stereotypes may dominate. |
| **I-Q: Image quality** | Fixed, interpretable, **atmosphere-agnostic** visual properties | Photos -> objects, spatial/compositional measurements, visual density/contrast and other measured features -> place profile | Image quality is not an emotion rating; feature extractors require their own validation. |

The existing 11-category ontology remains a **starting taxonomy**, subject to construct review; initial pilots may use calm, inviting, safe. Not every quality is necessarily a psychological emotion (e.g., open or compressed). Preserve category definitions and measurement versions.

**All three channels attach to `place_id`.** Reviews and photos from the same place are weakly associated; there is no assumed one-to-one photo/review match. Keep individual evidence, missingness, denominators, and provenance; aggregate appropriately at the place level.

## Three parallel scientific relationships

1. **T-E ↔ I-Q:** Which measured physical/visual characteristics vary with *explicitly reported* atmosphere? This is the clearest empirically grounded text/visual comparison, but not a causal test.
2. **T-E ↔ T-I:** When does inferred atmosphere agree with, extend, or contradict explicit reports? This tests behavior and potential blind spots of inference; agreement between two readings of the same text is **not independent validation**.
3. **T-I ↔ I-Q:** Which visual properties correlate with model-inferred atmosphere, including associations absent from explicit reports? Compare these patterns with T-E ↔ I-Q to detect potentially imported language/visual priors.

The third channel does **not** create a majority-vote truth metric or automatically make an emotion score more trustworthy. Disagreements are **research outputs**, not failures to be smoothed over. For example, if inferred calmness correlates with greenery but explicitly reported calmness does not, this can indicate a model prior, differences in coverage, or sampling effects; it is a question for investigation, not proof of any one explanation.

## Research posture and achievable first outputs

- **Independence in development:** Build and test T-E, T-I and I-Q in parallel. No channel must be perfect for exploratory pairwise comparisons to begin.
- **Separate instruments:** Keep raw channel outputs and model/source versions separate. Do not train/evaluate a channel on its own supposed independent corroboration or leak image-derived emotion hints into text evidence.
- **Evidence isn't infallible:** T-E is expected to be more defensible, but explicitly reported experiences can be misinterpreted, negated, attributed to something other than the place, or absent because reviewers did not mention them. Milestone-level human scientific audits remain useful.
- **Inference is worth studying even if imperfect:** Whether inferred scores align with reported experience is part of the research question, not an assumption of success.
- **Stage 2 is comparative:** Compare channel relationships on matched places and geography/place-type held-outs where feasible; measure missingness, category prevalence, feature quality, reliability, and disagreement. Do not mistake observational association for cause, or the same underlying text for independent views.
- **Small, valuable first deliverables:** (a) independent place-level channel profiles, (b) three pairwise association/discordance analyses, and (c) concrete cases showing agreement, disagreement, and uncertainty.
- **Long-term aspiration only:** A model that can predict atmospheric qualities from either text or images (perhaps with measurable visual features). Cross-modal prediction is **not** an immediate milestone, a guaranteed outcome, or the success criterion for early research.

## Relationship to prior Stage 1A plans

The November 11 [explicit-evidence/recall plan](STAGE1A_RESEARCH_PLAN_2026-11-11.md) remains a **candidate implementation strategy for T-E** (cue + LLM confirmation, optional recall student, M0–M3 audits). It does not define T-I, and its previously deferred environmental-condition track `3B` must **not** be silently equated with the new T-I channel. T-I's scope and methods are open research questions.

Prior project-wide two-branch [design](PROJECT_DESIGN_V2_REVIEWED_2026-11-10.md), archived tests and code remain intact for provenance. The project now considers **three measurements with three pairwise comparisons** at the *conceptual research* level. We have not agreed on inference algorithms, metrics/score formulas, confidence-combination rules, or implementation sequencing beyond avoiding unnecessary dependencies.

## Open questions for next discussion

1. Operational definitions and outputs of **T-I**: what may be inferred from reviews, and how to distinguish textual inference from invented emotional claims.
2. Comparability: how T-E coverage/support measures, T-I predictions, and I-Q vectors can be associated **without forcing them into the same numeric scale**.
3. Which categories and place types offer an informative, modest proof-of-concept for each pair.
4. Scientific evaluation of each instrument and whether any association survives place/geographical separation and shared-bias checks.
5. What counts as a useful intermediate result if text-to-image or image-to-text atmosphere prediction never succeeds.

**Decision record:** Preserve the three-channel idea as the current project-level research hypothesis. Do not merge channel scores or claim validation; refine the design through discussion and targeted experiments.

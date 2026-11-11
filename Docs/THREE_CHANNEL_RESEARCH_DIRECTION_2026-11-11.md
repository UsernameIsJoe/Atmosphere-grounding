# Three Channels — Triangle Research Direction (2026-11-11)

**Date:** November 11, 2026  
**Status:** Current **project-level research hypothesis**, still exploratory. No chosen estimation method, validated results, or new implementation.  
**Intent:** Preserve the idea and its evolution so future work can challenge and build on it without prematurely locking the pipeline.

## 1. Motivation and shift in thinking

The earlier project arranged two channels—review emotion and measured image qualities—into a sequence: text grounding first, visual grounding second, association third. Pilot attempts using ABSA, NLI, relevance gates and small local LLMs exposed unstable judgments and conceptual ambiguities. The project should **not** become a benchmark of LLM capacity or local hardware, nor depend on a commercial-grade emotion classifier before its central idea can be tested.

The November 11 first three-channel sketch separated **text evidence**, **text inference** and **image quality**, initially as three pairwise comparisons. The later refinement is stronger: they form a **triangle, not a chain**. Direct E–I is the target; T may offer an indirect route through two relationships that could be easier to observe.

## 2. Three channels, kept separate

| Symbol | Channel | What it contributes | Boundaries |
|---|---|---|---|
| **E** | **Text evidence** | Explicit, place-attributed reports of atmosphere from reviews, with source spans, support/opposition, attribution, review coverage and uncertainty | Primary *reported-perception* reference, not objective truth. Extraction errors, selection bias and missing reviews remain. |
| **T** | **Text inference / descriptive bridge** | Place-related descriptions from reviews: activities, uses, social context, environmental conditions, spatial experiences and potentially their inferred relevance | Its **provisional primary role is descriptive**, rather than producing another unqualified emotion score. Distinguish directly stated descriptions from inferred associations; how far inference is allowed remains an open question. |
| **I** | **Image quality** | Fixed, interpretable, atmosphere-agnostic visual measurements (objects, canopy, seating, enclosure, density, color/contrast, etc.) | Measured visual properties, not emotion labels; some text-described conditions are not visible in photographs. |

All channels are joined through **place identity**. Reviews and photos share a place, not known one-to-one correspondence. Preserve raw evidence, source IDs, denominators, missingness and versions; aggregate repeated observations without pretending each sentence/photo is an independent place.

### Triangle / three distinct research questions

```text
                    E — explicit reported atmosphere
                   / \
   E–T: reported   /   \   E–I: DIRECT TARGET
  experience and  /     \  observed atmosphere–visual relationship
  description    /       \
                T ——————— I
                   T–I: text description ↔ measured image qualities
```

- **E–I (direct, target):** Which image qualities are associated with explicitly *reported* atmosphere? Valuable but likely sparse and noisy because people mention only selected experiences.
- **E–T (interpretive):** Which reported activities, circumstances, spatial experiences and environmental descriptions accompany explicit atmosphere reports?
- **T–I (grounding):** Which *visually observable* textual concepts correspond to image measurements? These may have richer coverage than E.

**Hypothesis:** If some T features are both empirically associated with E and visibly measurable in I, an **E–T–I indirect route** might help estimate or investigate E–I where explicit evidence is scarce. Both the **direct E–I route** and the **indirect E–T–I route** should be compared; combining them is a *future, testable option*, not assumed to strengthen truth.

This makes T a possible **semantic bridge between perception reports and observable physical qualities**, rather than a second emotion-judging authority. T and I are similar in their descriptive proximity to environments, but must **remain different channels**: one is language about a place; the other is measured imagery.

### Concrete example

- **E:** "I feel relaxed here" (explicit calm experience).
- **T:** "People read beneath the shaded trees" (an activity/environment description in a review).
- **I:** Measured canopy cover, shaded area (if measurable), seating and spatial enclosure.

We can ask whether reading/shade descriptions are associated with explicit relaxation reports (**E–T**), whether shade/seating descriptions match image measurements (**T–I**), and whether those image features independently associate with relaxation reports (**E–I**). This example illustrates a *hypothesis*, **not** a proven link or causal mechanism.

## 3. Scientific safeguards — the indirect route is conditional

1. **No guaranteed transitivity.** Two strong associations (E–T and T–I) do **not** entail a valid E–I estimate. Confounding by location type, geography, photography conditions, selective reviewing, and shared model biases can create spurious paths. The indirect route needs explicit assumptions and held-out checks.
2. **Visual reachability matters.** T concepts about visible shade, paths or seating are candidates for the T–I bridge. Noise, smell, subjective interactions and crowd behavior may relate to E but not be inferable from static imagery; retain them in T and E–T analysis but don't force them into visual predictions.
3. **Shared reviews aren't independent corroboration.** E and T can originate from the same writing and model family. Use source-separated/split-review or cross-fitted checks where feasible, independent source audits, and report dependence rather than treating triangle agreement as three votes for truth.
4. **Disagreement is informative.** If T and I agree on greenery but the E–I relationship is weak, investigate label coverage, model priors, sample selection and context. Do not mechanically override E with an indirect estimate.
5. **Separate observational association from causality.** E–I is not a causal claim, and E–T–I is not automatically a valid mediation model.
6. **Relevant precedents are analogies, not ready-made estimators.** Network meta-analysis compares direct and indirect relationships under transitivity/consistency assumptions, but our data are observational and not exchangeable randomized treatments. Pivot-based multimodal alignment (e.g., ImageBind) illustrates bridging sparsely paired modalities; its success does not establish emotion grounding here.

## 4. Realistic initial research outputs

- **Three independently inspectable place-level channel datasets**, with missingness and provenance.
- **Three pairwise association/discordance studies** with uncertainty and appropriate place-level/spatial holdouts.
- **A direct-versus-indirect E–I comparison**, testing whether T adds stable, held-out information *beyond* direct E–I and simpler baselines; report cases of consistency and inconsistency.
- **A map of identifiable vs unidentifiable conditions** (which T concepts imagery can and cannot support).

Success does **not** require a fully integrated model. Longer term, a model predicting reported atmospheric qualities from text or images is an aspiration, not an immediate milestone or commitment.

## 5. Relationship to previous plans and open decisions

- The existing [Stage 1A explicit-evidence / recall design](STAGE1A_RESEARCH_PLAN_2026-11-11.md) is a **candidate way to build E**, not the mandatory implementation for the whole triangle.
- **T remains a distinct research problem**; do not silently relabel Stage 1A's deferred nonvisual-conditions track `3B` as T. Its precise extractive vs inferential tasks, outputs and human audit needs still require research.
- The earlier [two-branch design](PROJECT_DESIGN_V2_REVIEWED_2026-11-10.md), scripts and failed/unfinished audits are retained as historical implementation evidence; do not mistake them for validation of the triangle.
- The **11-category taxonomy** from `configs/lexicon.yaml` remains a starting point; a focused pilot can test only a few categories. Some (e.g., `open`, `compressed`) may be spatial perception constructs rather than psychological emotions.

**Open choices:** how to operationalize T (descriptions vs inferred affect), which visual subset of T is testable, whether and how indirect associations should be estimated, how to handle review sparsity and dependency, what comparison baselines/metrics are appropriate, and how to calibrate a modest proof-of-concept.

**Decision record (2026-11-11):** Keep **E, T and I as three separate channels**. Treat **E–I as the target**, **E–T and T–I as potential support**, compare direct and indirect routes **before** combining anything, and let disagreement remain an interpretable research outcome. No methods, scores, or outputs are claimed to work yet.

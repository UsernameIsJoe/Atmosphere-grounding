# Research discussion — November 19, 2026

This is a structured record of today's concept and methodology discussion for Atmosphere Grounding. It preserves the development of the proposal, the researcher's clarifications, agreed direction, open issues and candidate methods. The detailed methodology and the later answer are linked below.

| Record | What it preserves |
|---|---|
| [Probability stability, stabilization and logits — November 23](model-probability-stability-and-logits-2026-11-23.md) | Follow-up discussion and four research answers: repeatability, practical stabilization, proposed fluctuation tolerance, pre-softmax access and primary sources. |
| [November 23 follow-up remark](#9-november-23-follow-up) | Native probability signals, segment representativeness weights, and NLI hypothesis families aligned with image categories; provisional decisions and open validation. |
| [Shared-catalogue cross-modal methodology](shared-catalogue-cross-modal-methodology-2026-11-19.md) | Full methodological proposal, representation and eligibility rules, aggregation, model comparisons, four issues and primary references. |
| [Cross-modal matching research walkthrough](cross-modal-matching-research-walkthrough-2026-11-19.md) | The later research answer preserved as written, with clickable citations: how to process each location's images and segments, match at several scales, allow no match and compare methods. |

## 1. Why we stepped back from the LLM experiments

The recent LLM work concerns extracting and interpreting emotional evidence from reviews. The researcher clarified that the **214 reviews and calm/inviting/safe experiments are a pilot**, not the complete project scope or final emotion catalogue.

The long-term goal is to use weakly tied text and image data about locations to train or adapt a model that predicts emotional or atmospheric qualities from images. Reviews provide emotional evidence. A parallel image pipeline measures descriptive visual attributes. The research question is how those measured attributes relate to the reported experience, and how this can support an image-based predictor.

The discussion therefore concerns the concept and contribution of the full project, rather than another model-capacity experiment.

## 2. How the shared-catalogue idea developed

| Step in the discussion | Researcher's proposal or clarification | Resulting interpretation |
|---|---|---|
| Initial proposal | Emotional interpretation remains uncertain even for people. Preserve different kinds of evidence rather than mixing all judgments together. Organize text evidence using categories also used by the image pipeline. | Keep the source and character of emotional evidence available for later analysis and grounding. |
| More precise clarification | Each review contains segments; each segment has an emotion vector. Evidence can concern activity, people, objects, nature, buildings or open-space design. Images contain several of these simultaneously. The initial description assigned one evidence type to a text segment. | A shared catalogue can organize category-conditioned emotional supervision, while images retain multiple descriptive attributes. |
| Subsequent revision | The researcher explicitly agreed that text evidence should also be a vector rather than one categorical value. | **The current direction is an evidence-category vector and an emotion vector for each text segment, with a multi-category descriptive vector for each image.** The earlier single-type formulation is superseded. |
| Scope clarification | Categories need not contribute equally. A nice-waitress comment should not contribute to the place-emotion target, but its category should be retained. | Category membership, eligibility for the target and numerical weighting are separate decisions. Retaining metadata does not require using it as emotional supervision. |

Within-text correlations between category-conditioned emotion profiles may help describe the data or guide model sharing. Such correlations would not independently establish an image–emotion relationship.

## 3. Current representation and eligibility direction

| Unit or field | Intended role |
|---|---|
| Text segment | Emotion vector, evidence-category vector, original text/context, validity and eligibility metadata. |
| Review | Preserves the relationship among its segments; segmentation should not give verbose reviewers extra independent weight. |
| Image | Measured descriptive attributes spanning several categories; no emotion score assigned during feature extraction. |
| Location | A collection of review segments and photographs linked by the same place ID. |
| E/T provenance | Describes how an emotional judgment is supported; distinct from what category the evidence concerns. |
| Visual predictor | Learns from eligible text-derived supervision and must have an image-only prediction route. |

For the researcher's nice-waitress example, retain the people category and original record, but give that staff-service appraisal **zero eligibility for the defined place-emotion target**. This does not exclude all people-related evidence: crowding, access and public use may concern the place.

Category membership does not itself express confidence, emotional contribution or visual observability. An unmentioned emotion is missing evidence, not a negative score. Overlapping categories also do not turn one emotional proposition into several independent observations.

The category names are examples, not an adopted final taxonomy. The catalogue, score scales, observation masks and any numerical weights still require definition and evaluation.

## 4. The four issues identified in the discussion

| Issue | Why it matters | Proposed response |
|---|---|---|
| **Categories need attributes and relationships underneath them.** | People presence does not distinguish a dense crowd from scattered visitors. Trees and benches do not establish that the seating is shaded. | Preserve specific conditions, relationships, qualifiers and scene context alongside broad categories. |
| **Allow genuinely unmatched evidence.** | Reviews and photos can concern different areas, times, seasons or situations. Eligible experiences may lack visible evidence. | Same place and category create candidate links; permit several matches, uncertainty or no match. Keep out-of-scope eligibility decisions separate from missing visual correspondence. |
| **Multi-category evidence does not isolate each category's emotional effect.** | A calm report about trees, seating and people concerns that described situation; it does not establish a separate calming effect for each component. | Preserve the proposition, segment identity, review hierarchy and overlapping memberships. Interpret category profiles as observational summaries. |
| **Place-level supervision and image-level prediction need different validation.** | Predicting a place's review profile does not prove that each photograph receives a valid emotion score. | Distinguish review-grounded place atmosphere from an individual image's perceived emotion. Evaluate the intended claim using held-out places and independent judgments; add image-level evaluation for a single-image claim. |

These are unresolved methodological issues, not reasons to abandon the proposal. The [detailed treatment](shared-catalogue-cross-modal-methodology-2026-11-19.md#12-four-issues-to-resolve) is preserved in the methodology record.

## 5. How the literature discussion expanded

The first comparison covered four established families: **CLIP** for global image–text alignment, **FILIP** for word–patch correspondence, **ALBEF** for alignment followed by joint processing, and **MIL-NCE** for learning from weak candidate correspondences. Their roles and references are in [the methodology comparison](shared-catalogue-cross-modal-methodology-2026-11-19.md#11-how-imagetext-relationships-are-commonly-learned).

The later research found more specific precedents:

| Precedent | Ingredient relevant to the discussion | Limit on what it establishes here |
|---|---|---|
| [Hessel, Lee and Mimno, EMNLP 2019](https://aclanthology.org/D19-1210/) | Learn links inside multi-image, multi-sentence documents using collection-level membership rather than individual training pairs. | Replacing a document with a location is a proposed adaptation; it does not validate the added emotion-supervision task. |
| RegionCLIP and FILIP | Region- or patch-level image–text representations and correspondence. | Ordinary whole-image CLIP representations should not automatically be assumed to provide equally reliable local matching. |
| DenseCLIP | Pixel–text matching for dense prediction. | Pixel-level descriptive measurements do not establish pixel-level emotional attribution. |
| [MASK, ICLR 2026](https://proceedings.iclr.cc/paper_files/paper/2026/hash/e48fa1c4f08fd1ae35d5df8352c3106d-Abstract-Conference.html) | Externally grounded semantic concepts connect words and visual-region prototypes for unpaired matching. | Supports the concept-bridge principle, not the sufficiency of our proposed broad categories. |
| [OMIT: optimal partial transport](https://arxiv.org/html/2603.14349v1) | Partial correspondence between visual and textual fragments, reducing irrelevant alignments. | Extending it from image–caption retrieval to location-wide collections requires new design choices and validation. |
| [Attention-based MIL, ICML 2018](https://proceedings.mlr.press/v80/ilse18a.html) | Learn weighted aggregation when labels belong to collections rather than every instance. | Our emotion vectors need a suitable regression or distributional objective rather than an unchanged classification formulation. |

The [preserved walkthrough](cross-modal-matching-research-walkthrough-2026-11-19.md) contains the explanations and complete linked sources.

## 6. Candidate workflow for a location

The researcher asked whether to filter segment–image similarity first, whether to inspect an entire image at once, whether pixels should be the starting unit, and how to handle collections on both sides.

The proposed response was:

1. **Preserve both roles of each segment:** descriptive conditions for possible correspondence, and eligible emotional evidence for supervision. A generic emotional report can inform the place profile without a fabricated local match.
2. **Keep multiple visual scales:** whole scenes for layout and context, regions for identifiable elements, and masks for relevant descriptive measurements. Keep regions attached to their image and position.
3. **Use evidence vectors as guidance:** combine category membership with entities, attributes and relationships. Category overlap alone is insufficient.
4. **Score possible correspondences before hard filtering:** construct a segment-by-image compatibility matrix, refine it with local evidence and retain multiple plausible links or no match.
5. **Compare selective similarity links with partial transport:** start with the more transparent formulation and assess whether joint allocation improves correspondence.
6. **Train from weighted visual collections:** do not copy each segment's emotional label onto every candidate photograph. Establish descriptive matching separately first, then evaluate emotion learning.

CLIP can supply pretrained descriptive representations even when our own data lack exact pairs. Using it as an encoder does not require treating every same-place combination as a correct caption–image pair.

Matching should concern described conditions, rather than selecting an image because a model already calls it calm or safe. Material from different places can also depict the same conditions, so automatically treating every different-place combination as a negative needs scrutiny.

## 7. Proposed comparisons and what remains open

Two related experimental proposals were discussed. Their similarly named variants should not be conflated.

| Proposal | Comparisons | Main question |
|---|---|---|
| Earlier shared-catalogue comparison | Pooled emotion target; additional category-conditioned targets; strict category inputs versus category plus scene context; category-shuffle control. | Does preserving the evidence category improve supervision or interpretation? |
| Later matching comparison | A: category/place profiles without segment–photo links; B: add whole-image descriptive links; C: add regions while retaining scenes; D: replace simple selection with partial transport. | Does explicit matching help, does local evidence add value, and is joint allocation worthwhile? |

The recommendation to begin with **A–C in the later matching comparison** is a proposal, not a claim that those methods have already been run or adopted as a final architecture.

Still open:

- The shared catalogue and crosswalk to existing visual features.
- Emotion score meaning, validity and aggregation.
- The correspondence scorer, acceptance rules, no-match handling and numerical weights.
- How much pretrained representation learning to retain or adapt.
- The pooling and emotion-prediction objective.
- Independent evaluation of both descriptive links and emotional predictions.
- The scope of a place-level versus single-image prediction claim.

**No new inference or training experiment was run as part of this conceptual discussion.** Published components support the candidate methods; they do not empirically validate their exact combination for this project.

## 8. Where to resume

Use this record as the entry point, the [shared-catalogue methodology](shared-catalogue-cross-modal-methodology-2026-11-19.md) for the broader contribution and statistical formulation, and the [preserved walkthrough](cross-modal-matching-research-walkthrough-2026-11-19.md) for the detailed matching discussion. The next conceptual task is to choose and specify a candidate method while retaining the unresolved decisions above.

---

## 9. November 23 follow-up

**Status: discussion remark only.** The embedding and NLI directions below are provisionally agreed. Probability is accepted as a candidate soft signal under the stated trust premise; its empirical benefit remains open. This remark records the discussion and does not change prompts, code, model choices or the implemented pipeline.

### 1. Native probabilities in the text emotion representation

The intended use is to retain native model probabilities as part of the segment's emotion representation or soft supervision. The model is not being asked to generate numerical confidence scores or score its own verdict.

**Agreed interpretation:** if we trust the model's interpretation and its relative preferences among defined semantic alternatives, properly extracted probabilities over those alternatives are mathematically legitimate signals of how strongly the model favors an interpretation. Here, "strength" means model confidence/preference about the interpretation, not the intensity of the experienced emotion. Trusting the winning label alone does not establish calibration of the probability values.

The existing [v0.5 extraction prompt](../Docs/STAGE1A_PILOT_PROMPT_V0_5_2026-11-16.md) already makes a controlled `supports`/`opposes` decision for each accepted claim. This is not a newly proposed prompt principle. Keep its ability to return no claims or retain separate supporting and opposing claims, with quotes and E/T provenance.

Distinguish:

- Native likelihoods of actual direction choices can supply a decision-preference signal.
- Likelihoods of mandatory emotion names or formatting tokens do not measure emotional evidence.
- Free emotion generation is not inherently invalid, but a word's probability at one generated position is not automatically a comparable probability that a segment supports that emotion.

**Usefulness is still to be established.** There are two separate questions: whether probabilities help identify reliable claims, and whether retaining them as soft targets improves later training beyond hard decisions. Poor calibration alone does not settle the second question. Compare against hard labels, constant label smoothing and probabilities shuffled among comparable claims. A probability assigned to an alternative direction is model uncertainty; it is not an independently observed opposing claim. Missing emotional evidence remains missing supervision.

The inspected [v0.5 benchmark runner](../scripts/stage1a_codebook_v05_directional_benchmark_20261116.py) does not request or save native log probabilities. Extraction of full alternative-label likelihoods, tokenization, aggregation into segment vectors and downstream use remain implementation/research decisions. No replacement prompt or new probability experiment is adopted or reported by this remark.

**Executed follow-up (November 23):** the [calm-only probability pilot](../research_audit/stage1a_calm_probability_12_2026-11-23/README.md) now records 72 main calls on the same 12 source reviews and prior model digests. Single-token readouts captured native probabilities; code swapping preserved chosen states but changed Qwen scores, while Gemma was highly saturated and retained the known K01 attribution failure. See the report for exact comparisons, raw outputs, missing-alternative bounds and limitations. This adds experimental evidence to the remark; it does not change the provisional embedding/NLI decisions or adopt probabilities as calibrated evidence-quality weights.

### 2. Embeddings for segment representativeness

**Provisionally agreed:** use embedding similarity between the original segment and its original full review to estimate how much that segment represents the review. This is intended to contribute to segment weighting during aggregation/training. It is a salience/representativeness measure, not a check of whether an LLM-generated interpretation is correct.

Use the same suitable embedding model for both texts. A shared embedding space makes similarity calculations consistent; it does not guarantee correct relative rankings. Run a rudimentary task-specific comparison of a small number of credible models on real reviews, select an adequate model and freeze it. Do not become fixated on finding an optimal model.

Validate against representativeness judgments. A less central segment can still carry important emotional evidence. The precise score-to-weight transformation, normalization and placement in the learning objective remain open.

### 3. NLI evidence-type vectors and shared image definitions

**Provisionally agreed:** pursue NLI category-membership vectors using a small hypothesis family for each evidence category. In this role the families concern categories such as vegetation, people, objects, buildings or spatial layout; they are not automatically an additional emotion-scoring system.

Build the hypotheses from the same category definitions used by the image pipeline. The wording and measurement procedures may differ by modality, but the category meanings must align. These examples are not a frozen final taxonomy.

Allow multiple categories per segment. Keep category membership separate from eligibility: a nice-waitress comment can retain people metadata while contributing zero eligibility under the agreed place-emotion scope.

Check sensitivity using equivalent hypothesis paraphrases on fixed real segments: compare score spread, membership flips, and accuracy against independent category annotations. Distinguish equivalent wording from different category facets; different facets need not receive identical scores. Averaging a family can improve robustness, but stable outputs can still be wrong. Keep the variation visible, select on development cases and check separate cases and unused paraphrases before freezing the family. No NLI checkpoint, thresholds or final catalogue are selected here.

### Research precedents discussed

These support the component methods, not the untested combination for our project:

- [Zhao et al., 2021 — Calibrate Before Use](https://proceedings.mlr.press/v139/zhao21c.html): label-probability classification and prompt/label bias.
- [Hinton et al., 2015 — Distilling the Knowledge in a Neural Network](https://arxiv.org/abs/1503.02531): class distributions as soft training targets.
- [Rossiello et al., 2017 — Centroid-based Text Summarization](https://aclanthology.org/W17-1003/): sentence-to-document representativeness through embedding similarity.
- [Muennighoff et al., 2023 — MTEB](https://aclanthology.org/2023.eacl-main.148/): embedding suitability varies across tasks.
- [Plaza-del-Arco et al., 2022 — NLI Prompts for Zero-shot Emotion Classification](https://aclanthology.org/2022.coling-1.592/): sensitivity to hypothesis formulation and prompt-ensemble robustness; transferring this to our evidence categories requires validation.


---

## 10. Probability stability, stabilization and logits — November 23

The researcher asked whether the observed code-mapping probability changes could instead reflect variation across identical requests, then requested a literature-based assessment of reproducibility, stabilization, acceptable fluctuation and pre-softmax access. The [full follow-up discussion](model-probability-stability-and-logits-2026-11-23.md) preserves the four answers, exact original/rotated mappings, comparison chart, primary papers and implementation references.

**Interpretation correction:** the probability pilot ran each mapping once per case/model. Its 23.26-point Qwen difference is an observed between-mapping gap; there is no identical-request probability-repeat baseline to isolate a letter effect. Gemma's saturation can also suppress visible percentage movement. Neither result establishes which model has intrinsically more stable probabilities.

The record distinguishes computation controls and batch-invariant kernels from label/wording robustness methods. Four balanced mappings with semantic probability averaging and a 50-repeat diagnostic are proposed. The **1 percentage point peak-to-peak tolerance is an assistant-proposed project criterion, not a literature standard or adopted rule**. Native logits can be captured through direct llama.cpp/Transformers access; returned log probabilities already preserve relative logit differences for available candidates. These are discussion findings and proposals; no additional inference, backend migration, calibration or training was executed for this follow-up.


---

## 11. Executed probability repeatability test — November 23

The researcher authorized testing whether Qwen's letter sensitivity exceeds identical-request variation and whether Gemma's extreme probabilities can be explained or reversed through its internal transformations. The [executed report](../research_audit/stage1a_probability_repeatability_12_2026-11-23/README.md) preserves the protocol, exact checkpoints, twelve inputs/targets, figures, analysis, scripts and raw archive.

**Design actually run:** same reviews and target segments, calm only; ABCD, BCDA, CDAB and DABC with fixed semantic option order and wording. Ten shuffled repeat blocks per model, followed by three after reload: **1,248 native readouts**. The earlier 50-repeat proposal was not executed.

| Main-phase comparison | Qwen | Gemma |
|---|---:|---:|
| Largest identical-request probability range | 3.66 percentage points | 1.55 percentage points |
| Largest spread between mapping means | 22.93 percentage points | 1.21 percentage points |
| Cases with different winners across four mappings | 1/12 | 0/12 |

The native phases had no verdict flips within an identical payload. Smaller percentage movement in Gemma can be masked by saturation and does not establish intrinsically steadier internal preferences.

**Practical stabilizer:** observed Qwen noise motivated a separately logged control: three reviews under four mappings, ten repeats per cache condition, **240 additional calls**. Same GGUF, same Ollama-bundled binary and rendered prompts; only `cache_prompt` changes within the direct endpoint. Reuse produced a maximum 4.81-point repeat range and verdict flips in two of twelve prompt groups. Full recomputation produced identical four-code log probabilities in all twelve groups, at median 0.89 s rather than 0.50 s per call. This does not remove letter sensitivity: the cold-cache mapping spread reached **24.78 points**, and U06 changed from support to neither under CDAB. The normal Ollama completion implementation hardcodes cache reuse, so adopting this stabilizer requires the tested backend route or an adapter; production code was not changed.

**Gemma math test:** a separate llama-cpp-python backend loaded the identical BF16 GGUF for **64 direct passes**. Chosen states and input token counts matched native results in 64/64 comparisons; the largest probability gap against a native mean was 0.399 points. Metadata verifies final soft-capping with c=30. All four code logits were inside the cap in every pass, permitting an analytic inverse. Removing the cap did not reduce any winning probability; it sharpened choices or left them numerically saturated. For example, K01's original-map probability was 98.7994%, and its uncapped counterpart was effectively 100%. This remains the earlier attribution-error case. The inverse reconstructs values from actual finite-precision capped logits; it is not a directly hooked internal pre-cap tensor.

**Current direction:** retain log probabilities/logit margins; control full recomputation for further measurements; compare balanced semantic-mapping averages and retain their spread. Temperature scaling remains a sensitivity calculation until fitted on separate annotations. No calibrated-confidence or image-training benefit is established by this test. The provisionally agreed embedding and NLI directions are unchanged.

All results were downloaded and hashes verified before terminating the owned pod. Lease approximately 33 minutes; estimated compute $1.48 at $2.69/hour. The post-termination pod list was empty. See the report's cleanup record.


---

## 12. Qwen alternatives and Gemma softened scores — November 23

The researcher asked whether numbers or unmarked option text could improve Qwen, whether letter sensitivity had already ruled those alternatives out, and whether Gemma's saturated probabilities could become usable through softening. The subsequent clarification was to reuse the existing letter experiment and evaluate saved Gemma outputs, avoiding an unnecessary new Gemma stability run. The researcher authorized starting the tests and evaluation.

The [executed report](../research_audit/stage1a_probability_formats_12_2026-11-23/README.md) now preserves the exact protocol, prompts, inputs, tokenization, model/runtime records, raw outputs, evaluation scripts and charts. Qwen uses the original twelve reviews, calm-only v0.5 codebook and checkpoint, with full prompt recomputation. Label assignment changes and definition-order changes are separate factors. Four balanced cyclic variants per factor were tested; all 24 permutations and assignment/order interactions were not tested.

Three cross-runtime letter anchors reproduced the old cold scores exactly, allowing reuse of 120 existing readouts on three reviews × four mappings. New calls fill nine reviews' missing cold letter baselines, test previously unmeasured definition orders, and evaluate numbers and semantic answers. Three repetitions per new input, plus the three anchors, give **615 new readout records**; nine required an additional top-200 readout to obtain all candidates. Shared native scores did not change on expansion. All **216 unique conditions** had identical returned state probabilities across repeats.

| Qwen comparison | Letters | Numbers | Unmarked semantic answers |
|---|---:|---:|---:|
| Median assignment spread (percentage points) | 14.34 | 7.70 | Not applicable |
| Largest assignment spread | 24.78 | 23.61 | Not applicable |
| Cases changing verdict under assignments | 1/12 | 0/12 | Not applicable |
| Median definition-order spread | 16.36 | 17.67 | 6.29 |
| Largest definition-order spread | 40.53 | 48.14 | 39.94 |
| Cases changing verdict under order | 2/12 | 1/12 | 1/12 |

Numbers reduce assignment sensitivity on ten of twelve cases, while definition order remains a problem. Semantic answers improve typical order sensitivity and share the same canonical verdicts as the two coded formats on all twelve cases, but retain a large worst case and one order-induced verdict change. Median logit-margin variation also supports these typical improvements, so the analysis does not rely only on visually flatter percentages. This is evidence of partial robustness gains, not an independently validated accuracy or calibration improvement.

The semantic response vocabulary is `none/support/opposition/both`, with meaningful state names embedded in otherwise unmarked definition sentences. The initially proposed `neither` was two tokens. Before any scored review, it was changed to the equivalent one-token `none`; the first preflight failure is retained. All response strings then passed tokenization, and all scored responses complied exactly. No grammar or logit bias forced the choices.

**Gemma required no new inference.** The existing 64 direct readouts (48 unique inputs, sixteen repeat pairs), 624 native readouts and T=1,2,4,6,8 grid were evaluated offline. Every direct repeat pair remains identical at every temperature and winners do not change. At T=4, mean winning probability is **93.57%**, compared with **99.90%** at T=1; maximum letter-mapping spread rises from **1.16 to 14.20 percentage points**. K01's opposition probability ranges from 68.20% to 82.40% across mappings at T=4, retaining the earlier attribution-error verdict.

This sharpens the earlier interpretation: Gemma's raw percentages and verdicts looked less sensitive, while saturation compressed changes in its underlying preferences. Softening reveals those changes; it does not provide calibrated certainty or resolve mapping bias. The distributions contain case-specific information beyond fixed label smoothing, but its training value is untested. Four-mapping averages are exported as comparison artifacts rather than adopted targets.

The evaluation also finds that omitted top-20 alternatives become consequential when softened: native state-probability bounds can be 3.02 points wide at T=4, and wider at larger temperatures. Use the full four captured logits, not rounded percentages or zero-filled omissions. Native cached repeat variation and deterministic direct-backend results remain separate conditions.

The owned Qwen pod was terminated after about fourteen minutes; estimated compute **$0.63** at the observed $2.69/hour. All downloaded archive/file hashes were verified before deletion, and the post-termination pod list was empty. No production pipeline or final probability-supervision scheme was changed.


---

## 13. Does Gemma's softened distribution add useful information? — November 23

The researcher identified a gap: the previous evaluation described distribution shape, repeatability and sensitivity without evaluating whether the probabilities help identify dependable judgments. The [offline usefulness addendum](../research_audit/stage1a_probability_formats_12_2026-11-23/GEMMA_SIGNAL_EVALUATION.md) addresses this with saved logits and recorded references; no additional model calls were made.

Reference provenance limits this check. The current v0.5 runner's explicit calm audit contains only K01 = none and U06 = supports. The twelve-case reference fields also include inherited, partly disputed labels; K03 and U01 differ from the older conservative reference. These wider labels are retained as provisional sensitivity checks, not promoted to current independent ground truth.

Four mapping distributions are averaged per review, preserving twelve cases rather than counting mappings or repeats as independent observations. The control is fixed uniform label smoothing around the same hard verdicts, matched to the mean winning probability without using reference labels. At T=4, the model vectors have NLL **1.012 versus 1.011** for the control, Brier sum **0.432 versus 0.463**, and error-ranking AUROC **0.556**, all against the merged provisional reference. Removing K01 reverses the Brier advantage (**0.363 versus 0.344**); the modest advantage is case-sensitive rather than robust.

Some coarse preferences are visible. At T=4 the known K01 attribution failure receives about **74%** winning probability, versus about **99%** on explicit intrusive traffic noise (U03, aligned with its archived reference). U06, the other explicit current calm audit, receives about **92%** on support. K04 remains about **95%** despite its earlier low-crowding grounding concern; that concern is not assigned a new error label. Fine confidence ordering also changes with mappings in six of twenty-five pairs sharing a winner; those reversals are below one percentage point among high-confidence neither cases.

**Current assessment:** there are reproducible model preferences and promising coarse distinctions, but no robust evidence yet that the case-specific softened vectors outperform simple smoothing or provide dependable confidence weights. They remain research artifacts. This is not proof that soft targets cannot help downstream training; that comparison was not run. The addendum preserves case-level vectors, reference variants, all leave-one-case-out comparisons and a reproducible evaluation script.

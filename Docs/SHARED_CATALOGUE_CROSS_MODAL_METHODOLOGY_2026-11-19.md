# Shared-catalogue cross-modal emotion grounding

Research discussion record · November 19, 2026

**Scope:** Each text segment has an evidence-category vector and a vector of emotion scores. Each image has a vector of descriptive attributes covering multiple categories from that same catalogue. Reviews and images correspond by location. The aim is to use this structure to learn an image-based emotion predictor.

**Status:** Focused literature review and proposed method, updated to reflect the researcher's agreement that text evidence may belong to multiple categories. Category membership is separate from eligibility for the place-emotion target. A comment about a nice waitress retains its people metadata but is excluded from that target under the researcher's stated scope. No new inference or training experiments were run. The pilot size and pilot emotions do not define the full research scope.

## Reading guide and discussion status

The long-term goal is to learn or adapt a model that predicts emotional or atmospheric qualities from images using weakly tied Google place reviews and photographs. The 214-review dataset and calm/inviting/safe experiments are a pilot, not the full project scope.

The agreed conceptual direction is to retain an emotion vector and an evidence-category vector for each text segment, and a descriptive multi-category attribute vector for each image. Shared categories are intended to organize the supervision and support correspondence; they do not establish a verified segment–photo pair.

The exact catalogue, score scales, aggregation, numerical weights, matching objective and model architecture remain research choices. This document records the discussion and candidate methods; it does not report a new implemented pipeline or change the existing review gate or extraction configuration.

- Representation and eligibility: [Sections 1–5](#1-the-proposal-precisely).
- Visual representation and proposed learning comparison: [Sections 6–10](#6-construct-the-image-representation).
- Established image–text methods: [Section 11](#11-how-imagetext-relationships-are-commonly-learned).
- The four unresolved issues from the discussion: [Section 12](#12-four-issues-to-resolve).
- Primary research references: [References](#references).
- Follow-up answer, preserved as written: [Cross-modal matching research walkthrough](CROSS_MODAL_MATCHING_RESEARCH_WALKTHROUGH_2026-11-19.md).

## 1. The proposal, precisely

“Gene” is used here to mean a vector.

| Unit | Representation |
|---|---|
| Text segment | An evidence-category vector, an emotion vector and explicit target-eligibility metadata. |
| Review | A collection of these segments, retaining the original review and context. |
| Image | A descriptive attribute vector spanning several categories; no emotion score is assigned during feature extraction. |
| Location | A collection of reviews and images, joined through the same location ID. |
| Trained visual model | Uses image-derived information to predict emotions, with the category structure providing additional training supervision. |

Let a_s be the category-membership vector assigned to segment s, and e_s its emotion vector. The candidate categories include activity, people, objects, nature, buildings and open-space design. They are examples to define and evaluate, not an adopted final taxonomy. A multi-hot vector is a transparent first representation: several categories may be present, and the entries need not sum to one. If continuous values are introduced, their meaning must distinguish confidence, prominence and emotional relevance rather than treating these as interchangeable.

For an image i, x_i is the visual attribute vector. It can contain several category entries simultaneously. Detailed measurements such as amount, density, contrast and spatial arrangement can be retained under relevant category groups or as shared scene measurements.

Both modalities can now span several categories, but their values still have different meanings. Text records what is mentioned and appraised; images record visible content and measured properties. Matching category names does not make these vectors directly comparable numerical measurements.

The important change is in supervision. The earlier approach assigned a location one overall emotion vector. The new approach can preserve a separate emotion vector for every evidence category represented in its reviews.

## 2. What changes statistically

A location can now provide targets of the form:

| Evidence category | Emotional target obtained from text |
|---|---|
| Nature | Emotions expressed in segments categorized as nature. |
| People | Emotions expressed in segments categorized as people. |
| Objects | Emotions expressed in segments categorized as objects. |
| Activity | Emotions expressed in segments categorized as activity. |
| Buildings / open-space design | Corresponding category-conditioned emotional profiles. |

Each row contains the same set of emotion dimensions. Across locations, the model can investigate how visual measurements relate to these different rows.

This preserves source information that disappears when all text emotions are pooled. A positive reaction to people and a positive reaction to natural surroundings can produce the same pooled emotion score, yet offer different supervision for a visual model.

However, a row means “emotion reported in eligible segments that include evidence category c.” It does not establish that category c caused the emotion or isolate its contribution from other categories in the same segment. Overlapping membership creates correlated targets, not independent evidence for several separate effects.

The shared category is a key organizing the supervision. The visual attribute vector and emotion vector are different quantities; their relationship must be learned rather than calculated through direct vector similarity.

## 3. Closest methodological precedents

| Research | Ingredient relevant to this proposal | What should not be transferred automatically |
|---|---|---|
| Wang, Lu and Zhai, KDD 2010: Latent Aspect Rating Analysis [1] | Segment reviews by aspect and retain ratings at the aspect level instead of one undifferentiated rating. | Its hotel-rating model assumes an overall weighted combination and infers latent ratings. We already aim to extract segment-level emotional evidence and should test our own aggregation. |
| Nguyen et al., AAAI 2014: Multi-view multi-instance multi-label learning [2] | Represent an object through sets of instances from different views, including cases with a missing view. | Its task uses discrete labels; our emotional scores require an appropriate multi-output or distributional objective. |
| Xing et al., IJCAI 2020: Weakly-supervised multi-view multi-instance multi-label learning [3] | Addresses incomplete annotations and imperfect correspondence between groups across views. | Neighborhood label completion and inferred instance labels are assumptions, not verified ground truth for our missing emotion evidence. |
| Ma et al., KDD 2018: Multi-gate Mixture-of-Experts [4] | Share model components while learning different prediction functions and relationships between tasks. | Its learned experts are not automatically named evidence categories. We would define category outputs and, where useful, category feature groups explicitly. |
| Lopez-Paz et al., ICLR 2016: Distillation and privileged information [5] | Additional information can supervise training even when it is absent at prediction time. | A separate teacher model is not mandatory for our first implementation. The text-derived targets can directly supervise a visual predictor. |

These precedents support an implementable formulation. They do not demonstrate that this particular catalogue improves emotion prediction.

A related multimodal model, M3DN [6], uses multiple text and image instances and a consistency objective over bag-level label predictions. Its optimal transport concerns predictions and a learned label metric; it should not be described as automatically finding a physical match for each text segment.

## 4. Separate membership, target eligibility and visual correspondence

The evidence vector answers which categories are involved. It does not decide whether the segment belongs in the research target or whether an image can substantiate it.

| Decision | Meaning | Example under the researcher's scope |
|---|---|---|
| Category membership | What content or evidence sources are present? | A comment about a nice waitress can have people membership. |
| Place-emotion eligibility | Does the emotional proposition concern the defined place-experience target? | That staff-service appraisal is excluded from the place-emotion target. |
| Visual correspondence | Is there matching visible evidence in the available photographs? | Seeing a person does not establish that the waitress was nice. |

Do not give excluded service comments merely a small weight: their target-eligibility mask is zero. Retain their labels and original text for auditing and possible future changes in scope. Do not exclude the entire people category; density, access and social use can concern the place. Write the scope rubric before inspecting its predictive effect.

For eligible material, keep emotional extraction confidence, observation coverage and visual correspondence separate from category membership. A category is not intrinsically more reliable because it is nature rather than people. Any later numerical weights require an explicit meaning and development-set evaluation.

Split independent emotional propositions where this preserves meaning. Retain inseparable relations, qualifiers and context. The real U06 passage about sitting in a chair under fairy lights while a busker plays illustrates why multi-category evidence does not identify a separate causal emotion effect for each mentioned element. If different emotion dimensions concern different propositions, preserve that linkage rather than applying every emotion to every category indiscriminately.

E/T can remain separate provenance metadata. The category vector identifies what the evidence concerns; E/T identifies how the emotional judgment is grounded. Neither is a calibrated confidence score.

## 5. Construct category targets while preserving the review hierarchy

For location l and category c, collect eligible, observed segment emotion vectors whose membership includes c. In the simple binary-membership baseline:

$$
\mathbf y_{l,c}=\mathrm{Aggregate}\{\mathbf e_s:s\text{ belongs to }l,\ a_{s,c}=1,\ g_s=1\}.
$$

Here g_s is the target-eligibility indicator. Use emotion-specific or proposition-specific masks when a segment contains several claims with different eligibility. A defensible first baseline aggregates within each review and category, then across reviews. This prevents a verbose reviewer from receiving more weight simply by producing more segments. Preserve segment identity across categories so overlapping memberships do not become additional independent observations or inflate a pooled overall target.

For every category and emotion, preserve coverage, the contributing reviews, disagreement and missingness. If a segment does not provide evidence for safe, that entry should not silently become a low safety score. Use a validity mask alongside the fixed-length emotion vector. Preserve supporting and opposing evidence in the underlying records even if the chosen summary is numerical.

The result is a category-by-emotion target matrix for each location, with a corresponding observation mask. It is not necessary to collapse this matrix into one vector before learning.

The meaning and scale of each score still need definition. The representation itself does not turn model probabilities into calibrated emotion intensity.

## 6. Construct the image representation

Each image retains the multi-category attribute vector proposed by the researcher. An optional implementation organizes the detailed features into groups:

- Nature: visible vegetation, canopy, amount and distribution.
- Buildings: mass, facades, openings, enclosure-related measurements.
- Objects: seating, fixtures and amenities.
- People/activity: visible people and depicted activities.
- Open-space design: routes, boundaries, spatial organization and other defined measurements.
- Shared scene properties: contrast, density and composition where a single category assignment would be artificial.

A shared catalogue does not require exactly one scalar per image category. If the vector contains only category presence or proportions, test whether it is too coarse to explain emotional differences. Preserve the original descriptive attributes rather than discard them to create matching names.

Pool the images of a location into visual profiles while retaining variability and coverage. Mean and spread of measured features provide an interpretable first baseline. A learned set-pooling model is a later comparison.

A missing category in one photograph is not proof that the entire place lacks it. Static images of people also do not directly establish the friendliness reported in a people segment. These limitations can differ by category and should be measured.

## 7. Train category outputs and an overall output

A simple first formulation predicts one emotion vector for each category:

$$
\widehat{\mathbf y}_{l,c}=f_c(\mathbf X_l),
$$

where X_l summarizes the location's images. The category functions can share parameters; this need not be a collection of unrelated models.

Compare two input policies:

| Policy | Input to category c's prediction | Meaning |
|---|---|---|
| Strict matching | Only image measurements assigned to c | Tests the strongest same-category assumption. |
| Category plus context | Category c's measurements plus shared scene information | Allows the surrounding scene and other categories to matter. |

The second policy is the more plausible candidate, but the comparison should decide. An activity experience can depend on spatial layout; feelings about people can depend on visibility or crowding. Matching category names alone does not justify excluding these relationships.

For the final overall emotion prediction, retain an overall output trained against a consistently defined overall text target. Apply the same approved eligibility rules to this target in every comparison, including the pooled baseline; otherwise a gain could reflect changed scope rather than category supervision. Add the category targets as additional supervision:

$$
\mathcal L=
\mathcal L_{\mathrm{overall}}+
\lambda\mathcal L_{\mathrm{categories}}.
$$

The category loss is evaluated only where the relevant category–emotion target is observed. Select lambda on development data and report how the choice affects both overall and category predictions.

This architecture gives the proposed categorization a concrete role: it teaches the visual model several more specific emotional targets while preserving the original overall task. If category labels are merely stored and then discarded during pooling, their benefit to learning has not been tested.

An alternative is to build the overall prediction from the category representations. Compare this with the additional-supervision approach. Do not assume image area fractions or category counts are valid weights for combining emotions. The proportion of pixels showing people is not the proportion of a visitor's emotion attributable to people.

At prediction time, the model receives the new image or image set, derives its visual attributes, and outputs emotions. It does not require a new review or a user-supplied text category.

## 8. What this can and cannot improve

The proposal may reduce the mixing of emotionally different sources, provide more informative supervision per location, expose which kinds of experience are visually predictable, and improve interpretation of failures.

It does not create additional independent locations, establish segment-to-photo pairs, resolve incorrect emotion extraction, or prove causation. Its conceptual advantage is more specific supervision, not a guaranteed increase in accuracy.

Categorization can also make labels sparser. Rare categories require careful sharing of parameters or partial pooling; they should not receive invented targets. Category imbalance, category errors and inconsistent segmentation can remove the expected benefit.

Within-text correlations between the category emotion profiles can inform model sharing. Estimate those relationships on training places only. Such correlations describe relationships among reports and may reflect common reviewers, activities or place types; they do not independently validate an image relationship.

## 9. A focused experiment

Use the current chosen text extraction and visual measurement methods. The initial experiment should change the representation and use of supervision, not reopen the LLM-capacity search.

| Condition | Training targets and structure | Question |
|---|---|---|
| A: pooled baseline | Overall emotion target only | What does the earlier structure achieve? |
| B: category supervision | Same overall target plus the category emotion matrix | Does retaining evidence type improve learning? |
| C: strict matching | Category outputs restricted to matching visual groups | Is direct category restriction helpful? |
| D: category plus context | Matching visual groups plus shared scene context | Does context improve on strict matching? |
| Control | Shuffle existing segment category assignments within locations while preserving counts and the overall target | Does the genuine category assignment contribute beyond extra outputs or regularization? |

Keep the image inputs, global targets and whole-location splits comparable. Account for differences in model capacity. Report error separately for the overall and category outputs, and inspect categories whose apparent gain is driven by reduced coverage. No synthetic review content is needed.

Include independent audits of segment categories and emotion evidence. For the final predictive claim, use independent human judgments in addition to agreement with the text-processing pipeline. Use geographically separated holdouts when claiming geographical transfer.

Training on place image sets does not automatically establish valid scores for each individual photograph. An eventual single-image claim needs image-level evaluation. This does not prevent developing the category structure or testing it at the place level first.

A useful result could be improved overall prediction, improved category prediction, or more faithful interpretation at comparable overall performance. If the true category labels behave like shuffled labels, the proposed mechanism lacks empirical support under that test.

## 10. Recommended next step

Define a compact evidence catalogue and image-feature crosswalk, audit multi-category membership and target eligibility on real segments, and construct category-by-emotion profiles with missingness masks. Then run the pooled-versus-category comparison before adopting a complex alignment model.

The central hypothesis is:

**Retaining the evidence-category vector of each eligible emotional segment supplies useful category-conditioned supervision for learning emotions from image attributes of the same location.**

This is the proposal to test. Both text and images can cover several evidence categories. Whether their shared catalogue helps the final model depends on annotation consistency, target eligibility, visual predictability and how the category targets are used in training.

## 11. How image–text relationships are commonly learned

These are established methodological families, not a ranking of current models or a recommendation to test every named model.

| Family and primary example | Relationship learned | Relevance to this project |
|---|---|---|
| Global contrastive alignment: CLIP [7] | Encodes an image and its associated text into a shared embedding space, learning to distinguish original pairs from alternatives. | Useful pretrained representations for descriptive similarity. A same-place review and photo are not automatically a genuine caption–image pair. |
| Fine-grained alignment: FILIP [8] | Uses word-token and image-patch interactions to train more local correspondence. | Helps connect descriptions of visible entities to image content; it does not itself supply emotional attribution. |
| Cross-modal fusion: ALBEF [9] | Aligns representations and then uses cross-attention for joint image–text processing. | Useful when the task needs both modalities together. A final image-only emotion model needs a suitable image-only prediction route. |
| Weak candidate-set alignment: MIL-NCE [10] | Learns from groups of plausible video–narration correspondences rather than requiring an exact temporal pair. | An analogy for sets of reviews and photos at a place. Its video results do not validate a place-level adaptation. |

The proposed project can reasonably be described as weakly paired cross-modal learning with shared, interpretable evidence categories. Stronger claims of grounding need evidence that the learned correspondence tracks relevant visible content.

The closest starting point is a place-level collection of candidate text and image correspondences. This is a methodological recommendation, not evidence that MIL-NCE already solves the place-emotion task. Some places may contain no valid visual match for a particular emotional proposition.

Keep descriptive correspondence separate from emotional supervision: match descriptions of visible conditions to photographs, then use eligible emotional evidence to learn their association. Selecting a photograph because a pretrained model already calls it calm and using that selection as independent proof of the calm relation would build the conclusion into the matching step.

Shared categories need not replace learned semantic features. Keep the catalogue for interpretation and supervision; compare measured attributes alone with additional pretrained descriptive features and, if warranted, learned correspondence. Neither similarity nor attention is a calibrated emotion score or proof of causal influence.

## 12. Four issues to resolve

These are the four issues identified in the November 19 discussion. They remain open methodological questions, with proposed responses below.

### 12.1 Categories need attributes and relationships

People does not distinguish a dense crowd from scattered visitors. Nature does not distinguish trees shading seating from vegetation obstructing a path. Category presence alone can therefore join situations with very different emotional implications.

**Proposed response:** retain measurable conditions, qualifiers, negation and relationships under or alongside the shared categories. Audit whether text descriptions and visual measurements mean the same thing. Winoground [11] provides a precedent for testing compositional understanding beyond object-word overlap; its results concern the models evaluated in that paper.

### 12.2 Allow genuinely unmatched evidence

A review can describe nighttime conditions while all available photographs show daytime. The same place can contain different areas, seasons, activities and situations. An emotional proposition can also be eligible for the place target while lacking visible evidence in the available photos.

**Proposed response:** treat same-place and same-category membership as candidate links. Permit no match and retain reasons and coverage information. Do not force every eligible segment onto an image, or treat every same-place review–photo combination as an established positive pair. Audit content correspondence separately from emotional prediction.

The staff-service example is a different decision: a nice-waitress segment retains people metadata but contributes zero to the defined place-emotion target. It is out of scope for that target, rather than merely a low-confidence visual match.

### 12.3 Multi-category evidence does not isolate each category's emotional effect

When one segment mentions trees, seating and people while expressing calm, the emotion concerns the described situation. The multi-category vector does not independently establish that each component produces calm, and multiplying the record across categories does not create independent observations.

**Proposed response:** preserve segment identity, the full emotional proposition and the review hierarchy. Keep inseparable relationships together; split only independent propositions where meaning is preserved. Interpret category-conditioned emotion profiles as observational summaries, not causal effects. Preserve overlapping membership when evaluating uncertainty and use the same eligibility rules in all baseline comparisons.

### 12.4 Place-level supervision and image-level prediction need different validation

A model can predict a place's review-derived emotion profile without identifying which photograph contains the relevant evidence. Success with a photo collection does not automatically validate emotion scores for each individual photograph.

**Proposed response:** define the prediction claim explicitly. Predicting review-grounded place atmosphere from images is related to, but different from, predicting what a particular picture makes an observer feel. Use held-out places and independent judgments for the first claim; add independent image-level judgments and a defined observer/task protocol for a single-image claim. Use geographically separated holdouts when claiming geographical transfer.

### What the first comparison should establish

Start with the pooled-target versus category-supervision comparison in Section 9, holding eligibility, visual inputs and evaluation splits comparable. Add descriptive matching as a separate experimental condition. Audit a small sample of segment–photo correspondences, including unmatched cases. Evaluate both the bridge and the emotion predictions rather than treating success at one as proof of the other.

## 13. Relationship to existing project records

- [Earlier E/T/I research framing](THREE_CHANNEL_RESEARCH_DIRECTION_2026-11-11.md): evidence provenance remains distinct from the new content-category vector.
- [Current visual-category configuration](../configs/visual_categories_v1.yaml): existing feature groups are a starting point for a crosswalk, not an already validated shared catalogue.
- [Stage 1A review-gate decision record](STAGE1A_REVIEW_ELIGIBILITY_GATE_LOCK_2026-11-16.md): operational pilot decisions remain separately documented.
- [Earlier project research baseline](../Discussions/current-research-baseline-2026-11.md): historical context for the parallel text and image branches.

## References

1. Wang, H., Lu, Y., and Zhai, C. (2010). [Latent Aspect Rating Analysis on Review Text Data: A Rating Regression Approach](https://timan.cs.illinois.edu/czhai/pub/kdd2010-lara.pdf). KDD 2010. Aspect segmentation and rating regression inspected; its aggregation assumptions are not adopted here.
2. Nguyen, C.-T., Wang, X., Liu, J., and Zhou, Z.-H. (2014). [Labeling Complicated Objects: Multi-View Multi-Instance Multi-Label Learning](https://cdn.aaai.org/ojs/8999/8999-13-12527-1-2-20201228.pdf). AAAI 2014. Relevant to sets of instances and incomplete views.
3. Xing, Y., Yu, G., Wang, J., Domeniconi, C., and Zhang, X. (2020). [Weakly-Supervised Multi-view Multi-instance Multi-label Learning](https://www.ijcai.org/proceedings/2020/432). IJCAI 2020. Relevant to missing annotations and imperfect correspondence; its discrete-label completion procedure is not adopted.
4. Ma, J., Zhao, Z., Yi, X., Chen, J., Hong, L., and Chi, E. H. (2018). [Modeling Task Relationships in Multi-task Learning with Multi-gate Mixture-of-Experts](https://research.google/pubs/modeling-task-relationships-in-multi-task-learning-with-multi-gate-mixture-of-experts/). KDD 2018. Relevant to sharing information while retaining task-specific prediction.
5. Lopez-Paz, D., Bottou, L., Schölkopf, B., and Vapnik, V. (2016). [Unifying Distillation and Privileged Information](https://leon.bottou.org/publications/pdf/iclr-2016.pdf). ICLR 2016. Relevant to using additional representations during training without requiring them at prediction.
6. Yang, Y., Wu, Y.-F., Zhan, D.-C., Liu, Z.-B., and Jiang, Y. (2018). [Complex Object Classification: A Multi-Modal Multi-Instance Multi-Label Deep Network with Optimal Transport](https://www.kdd.org/kdd2018/accepted-papers/view/complex-object-classification-a-multi-modal-multi-instance-multi-label-deep). KDD 2018. Conference abstract inspected; its complete implementation was not audited.

7. Radford, A., et al. (2021). [Learning Transferable Visual Models From Natural Language Supervision](https://proceedings.mlr.press/v139/radford21a.html). ICML 2021. Global contrastive image–text representation learning.
8. Yao, L., et al. (2022). [FILIP: Fine-grained Interactive Language-Image Pre-Training](https://arxiv.org/abs/2111.07783). ICLR 2022. Word–patch late interaction for contrastive alignment.
9. Li, J., et al. (2021). [Align before Fuse: Vision and Language Representation Learning with Momentum Distillation](https://proceedings.neurips.cc/paper_files/paper/2021/hash/505259756244493872b7709a8a01b536-Abstract.html). NeurIPS 2021. Contrastive alignment followed by cross-modal fusion.
10. Miech, A., et al. (2020). [End-to-End Learning of Visual Representations from Uncurated Instructional Videos](https://openaccess.thecvf.com/content_CVPR_2020/papers/Miech_End-to-End_Learning_of_Visual_Representations_From_Uncurated_Instructional_Videos_CVPR_2020_paper.pdf). CVPR 2020. MIL-NCE for noisy, temporally misaligned video–narration supervision; an analogy for candidate-set matching, not an established place-emotion method.
11. Thrush, T., et al. (2022). [Winoground: Probing Vision and Language Models for Visio-Linguistic Compositionality](https://openaccess.thecvf.com/content/CVPR2022/papers/Thrush_Winoground_Probing_Vision_and_Language_Models_for_Visio-Linguistic_Compositionality_CVPR_2022_paper.pdf). CVPR 2022. Tests relationships and composition beyond matching word inventories.

These sources support the ingredients of the proposed design. None supplies empirical validation of the researcher's exact combination of segment emotion vectors, evidence-category vectors, scope masks and category-organized image attributes.
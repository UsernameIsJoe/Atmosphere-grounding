# Full-review eligibility gate v0.5 — contextual relevance draft

Status: proposed, untested, not adopted. This replaces neither the accepted v0.4 files nor its configuration. The relevance-ratio experiment is set aside; retain its historical outputs. This draft returns to one whole-review binary decision with no text-share threshold. It is distinct from the archived v0.5 ratio experiment and the downstream emotion-codebook versions.

## Purpose and scope

KEEP a review only when it supplies an identifiable, text-grounded characteristic of the reviewed place as a place to visit, use, enter, stay, navigate or experience. REJECT when it supplies only accounts or evaluations of events, people, objects, transactions or outcomes occurring there, without an independently informative place characteristic.

The gate assesses relevance, not whether any emotion is present. Spatial, sensory, access, functional or visitor-experience information may qualify without emotion words. Do not apply the E/T taxonomy here or require direct emotional evidence. Keep the original full review for downstream segmentation when it passes; retain rejected reviews for audit.

## Main change: distinguish a described quality from a successful outcome

An event being enjoyable, a service being excellent, or a reviewer recommending a venue does not by itself identify a quality of that venue. Attributing an outcome to the venue or its team does not convert the outcome into place-level evidence. The same distinction applies to negative outcomes.

Determine what the description actually evaluates in the context of the full review:

| Content | Eligibility role |
|---|---|
| Identifiable spatial, sensory, atmospheric, access, facility or use condition of the reviewed place | Can qualify |
| Direct description of how being in, moving through, or using the place feels or works | Can qualify; first-person and subjective reports are valid |
| Textually identified establishment-level visitor practice or access rule | Can qualify; do not infer a practice from one employee's behavior |
| Success, failure, enjoyment or convenience of a private event, appointment, meal or transaction | Insufficient on its own |
| Praise/criticism of staff performance, planning, food, drinks or individual exhibits | Insufficient on its own |
| Generic appraisal of atmosphere or experience as perfect, special, excellent or disappointing, without describing its character | Insufficient on its own |
| A feature named solely to support an argument about an unrelated policy, person or transaction | Insufficient on its own |

A meaningful atmosphere or feeling description need not explain its physical cause. Do not demand objective measurements, architectural details or a literal emotion adjective. Conversely, the words place, atmosphere, experience, comfortable or welcoming are not automatic KEEP triggers: resolve their meaning and role in context.

## Whole-review decision procedure

1. Read the complete review to resolve the subject, referents and role of its claims. Do not choose a seemingly relevant phrase before understanding the account.
2. Identify a candidate place characteristic actually stated in the review. Say internally what the reader learns about being in or using that location.
3. Check that this is a distinct, informative place assertion, not a rewording of an event/meal/transaction outcome or an inference from staff competence, satisfaction or gratitude. Do not add a venue capability, service culture, atmosphere or access entitlement that the reviewer has not stated.
4. Check that the candidate is substantive: does it identify the character of the place or experience, rather than only say that it was good/bad or suitable for that occasion?
5. KEEP if a candidate survives those checks; otherwise REJECT. After deciding, select a short contiguous source-exact anchor that demonstrates the qualifying characteristic. The reason must name that characteristic, not merely say that the review concerns the venue.

## Mixed reviews and protection against over-rejection

One short, genuinely qualifying observation may suffice even in a long personal story. No minimum length, proportion, majority-topic rule or repeat-visit requirement applies. An event mention does not disqualify a review. A condition observed during a celebration or appointment can qualify if the text actually describes the place's noise, space, ambience, accessibility, comfort, use or other visitor experience.

Here “independent” means the place description conveys information beyond whether the event or service went well. It does not mean removing the surrounding story, ignoring pronouns, requiring a second visit, or proving that the condition would persist without the event. Context is necessary both to recognize valid observations and to reject incidental place language.

Retain v0.4 boundaries for individual food/service outcomes, incidental institutional features, other locations, exhibit-only/history-only text, and meaningful restroom/facility conditions. A single hazard, an access restriction or a directly experienced condition can qualify. People or event language is never an automatic rejection rule.

## Output contract

Use the unchanged binary schema: keep, anchor_quote, reason. KEEP requires a nonempty exact substring; REJECT requires an empty anchor. Do not output ratios, unit labels, emotions, E/T, confidence, inferred general practices or extra fields. A valid substring does not establish semantic eligibility by itself.

## Evaluation before adoption

Freeze this draft separately from v0.4 and use the same gate model/settings for a controlled comparison. Review old false keeps and previously accepted mixed/first-person reviews together; do not judge success solely on one wedding case. Add fresh authentic reviews spanning celebrations, appointments, meals and transactions, including reviews with genuine place observations. Keep evaluator labels, previous model verdicts and known test quotations out of model input. No literal cohort examples or case-specific exceptions are included in the executable prompt below.

Check both false keeps and new false rejections, inspect exact anchors/reasons, and report comparison to v0.4. Development-set improvements are not independent accuracy. Do not change the current gate configuration or run inference merely because this draft exists.

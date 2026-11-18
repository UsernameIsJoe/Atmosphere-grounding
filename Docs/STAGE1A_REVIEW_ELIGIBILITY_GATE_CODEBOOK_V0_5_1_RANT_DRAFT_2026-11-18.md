# Review eligibility gate — v5.1 hostile-rant exclusion codebook draft

**Status:** Untested, not adopted. New amendment to the tested v5 scenario candidate, following the researcher's request to exclude hostile, accusatory rants even if they contain place information. Preserve v0.4, tested v5 and their results unchanged. Do not apply the earlier proposed N05-specific facility tuning.

## New review-level exclusion: dominant hostile denunciation

**REJECT when personal hostility, sweeping accusation or denunciation drives the review, even when it contains concrete or relevant place details.** This is a separate corpus-eligibility rule, not an attempt to redefine every hostile review as irrelevant. Evaluate the complete review before selecting any place anchor.

Use observable rhetorical patterns. A clear dominant pattern can include:
- Extended personal/degrading attacks or abusive character judgments.
- Repeated or sweeping claims about bad motives, corruption or wrongdoing that function primarily as denunciation rather than a bounded account of what happened.
- A grievance escalating into broad condemnation and pressure to shame, punish or mobilize others against the target, instead of remaining a specific account of place conditions.

Slurs or profanity are not required. An accusatory grievance-and-mobilization narrative may qualify without either. These are contextual indicators, not a keyword list, a text ratio or an allegation-verification procedure. Do not require every indicator, but require a clear dominant hostile-denunciation pattern; one critical expression is insufficient.

### Safeguards for legitimate negative experience

Do not exclude a review solely because it is angry, negative, emphatic, profane, low-rated, policy-critical, alleges misconduct or asks for accountability/investigation. A request for action or an accusation alone is not a rant. Strongly worded but specific, proportionate descriptions of unsafe access, severe noise, dirt, broken fixtures, exclusionary access practices or other experienced conditions remain eligible for the ordinary relevance check.

An isolated angry phrase does not automatically invalidate an otherwise informative review. If the dominant hostile-denunciation pattern is unclear, do not apply this exclusion; continue with the existing relevance rules. Do not infer irrationality, dishonesty, mental state, actual motives or the truth/falsity of disputed allegations. A reviewer can be distressed and factually accurate; the rule concerns the communicative character and eligibility of the review for this corpus.

### Priority and consequences

The review-level exclusion overrides the ordinary mixed-review rescue rule. If the review clearly qualifies as a hostile rant, one genuine facility or atmosphere observation does not make it KEEP. Otherwise, v5's original mixed-review policy remains: a substantive place observation may suffice even when brief or surrounded by other material. This is not the rejected v0.6 general main-place-focus requirement.

For a hostile-rant rejection, the reason must identify that rule and its observable rhetorical basis. Do not say there is no location information if relevant details are actually present. Keep the original review and exclusion reason in the reject/audit ledger. No new output field or additional LLM call is introduced.

This amendment targets hostile denunciation as requested in the latest clarification. It does not impose a new blanket ban on intense positive emotion; unsupported praise is already assessed by the relevance rules. Excluding hostile rhetoric is an explicit sampling decision: retained emotion distributions will not represent all submitted reviews. Preserve rejection counts and source texts so this selection can be audited.

## Retained relevance rule, subject to the new exclusion

Read the complete original review before segmentation. For a review that passes the hostile-rant screen, KEEP if at least one substantive, contextually relevant observation characterizes the reviewed place as a place to enter, visit, use, navigate, stay in or experience. Otherwise REJECT. The qualifying observation can be short and need not dominate the review. Neither a text ratio nor a main-topic requirement applies.

Place evidence can concern spatial layout/design, light/sound/crowding, atmosphere, comfort, facilities, cleanliness, accessibility, use, visitor experience or an explicitly reported establishment-level visitor practice. Subjective and first-person observations qualify; a single visit can establish an observed condition or access rule. Permanent conditions, repeat visits, physical measurements and emotion adjectives are not required.

Evidence must be about the reviewed location, substantive enough to identify an interpretable quality, and relevant in the whole review's context. A physical noun, favorable adjective, location name or short exact quote is not sufficient by itself. Do not substitute a different site, a particular individual's merits or a private outcome for the place being reviewed.

## New aid: common insufficient-evidence scenarios

These exclusions describe what cannot independently justify KEEP. They are not hard rejection categories or keyword bans. Apply the exceptions below before deciding the full review.

### 1. Private celebrations, ceremonies and organized events

Includes weddings, receptions, birthdays, parties and similar occasions. Event success/failure, memorable experiences, stress-free planning, gratitude, coordination, catering and one event's bartending performance are insufficient by themselves. Do not promote them into venue capability, sensory environment, hospitality or operational efficiency merely because the venue hosted the event. Generic praise of an atmosphere as suitable or ideal for an occasion does not identify the atmosphere's character.

**Preserve:** independently described room layout, actual sound/light conditions, space, seating, comfort, accessibility, facilities or other meaningful place experience. The event context does not invalidate genuine observations. Do not infer that a reported condition is permanent or caused by architecture unless the text supports that inference.

### 2. Individual staff encounters and private transactions

Includes a waitress, waiter, cashier, coordinator, agent, manager or another individual. A person's kindness, competence, mistake, special assistance, one-off service speed or refusal is insufficient on its own. Appreciation or frustration does not establish the place's general hospitality or atmosphere. Transaction, booking and appointment outcomes alone also fail.

**Preserve:** a directly stated visitor-facing rule, access restriction or explicitly reported recurring establishment practice. An employee enforcing or explaining an access rule does not make the rule irrelevant. Do not generalize a particular person's behavior into a practice the review does not state.

### 3. Food, drink and catering evaluations

Taste, portions, menu/dish selections, presentation, individual meal quality, catering praise and serving speed in one meal or event do not independently establish place-level environmental or visitor qualities. Do not turn attractive food into a spatial or atmospheric observation.

**Preserve:** separately reported ambience, dining-space conditions, comfort, accessibility, facilities, use or establishment-level visitor practices. A review may discuss food extensively and still KEEP for one genuine place observation.

### 4. Incidental facilities or objects within an unrelated dispute

A room, kitchen, piece of equipment or physical feature named only to argue about institutional policy, food administration, a private transaction or another unrelated outcome is insufficient. The review must teach an interpretable characteristic of being in or using the place, rather than merely name a physical object supporting that dispute.

**Preserve:** firsthand facility conditions, usability, hazards, cleanliness, sensory conditions and access information. A restroom can itself be the reviewed location; its design, darkness, dirt or broken handwashing facility is place evidence. Station cleanliness or a closed visitor facility can qualify even when the reviewer describes a personal inconvenience. A museum's visitor experience, accessibility and suitability for different visitors can qualify without a detailed architectural description.

## Mixed-review and ambiguity safeguards

- A wedding, reception, waitress, meal, appointment or institutional dispute is never an automatic REJECT trigger.
- If the review-level hostile-rant exclusion does not apply, a single substantive place observation can qualify a mixed review. The place does not have to be the main subject, a co-main subject or a specified fraction of the text.
- Generic positive/negative verdicts and scenario outcomes do not become place evidence merely because an adjective or venue name appears beside them.
- A description of atmosphere or a place-directed feeling need not explain its physical cause. Resolve what the feeling describes: being in/using the place, or only the success of an occasion/interaction.
- A particular service incident is insufficient on its own, but a disclosed physical hazard, access rule or actual facility condition can qualify from one visit. People and first-person narrative do not negate place evidence.
- Artwork/history-only content remains insufficient without meaningful observations about the reviewed venue or visitor experience. Recommendations about other locations are not evidence about the reviewed site.
- If no plausible substantive place observation survives the checks, REJECT. Do not invent missing qualities, infer a venue-wide capability or select another equally weak quote to avoid rejection.

## One-call decision procedure and output

1. Read the entire original review and resolve its referents. Apply the review-level hostile-denunciation exclusion first; if it clearly applies, REJECT for that reason even if place details exist.
2. Check candidate evidence against the four common insufficient-evidence scenarios.
3. Search the same full review for independent, substantive place evidence, applying the preservation rules. Do not reject merely because an excluded scenario appears.
4. Make the whole-review KEEP/REJECT decision.
5. For a review-level exclusion, REJECT with an empty anchor and a reason naming the observable hostile-denunciation pattern; do not claim the text necessarily lacks place details. Otherwise, for KEEP, choose one short contiguous source-exact anchor that demonstrates the actual qualifying place observation. The reason names that quality; it must not disguise an excluded event/service outcome as place evidence. For REJECT, use an empty anchor and briefly identify why no qualifying place observation remains.

Output remains exactly **keep, anchor_quote, reason**, using the existing three-field schema. No focus labels, text-unit labels, ratios, emotion judgments, E/T tags or additional LLM calls are proposed. Exact substring checking validates quotation form, not semantic relevance.

## Difference from tested v5 and evaluation boundary

For reviews not excluded by the new hostile-rant rule, the base relevance and mixed-review recall protection remain v5/v0.4's. The new change is the higher-priority whole-review hostile-denunciation exclusion. The general scenario list, prohibitions on relabeling scenario outcomes as site qualities, and matched protections for legitimate place evidence are inherited unchanged from tested v5. It does not adopt the failed focus-first eligibility policy.

No actual test-review quotations, case IDs or expected case verdicts are included as examples. Tested v5 had already removed legacy literal illustration blocks and case-level calibration from v0.4; that example inventory is unchanged in this amendment. A comparison against v0.4 must disclose both that inherited change and the scenario additions. The scenarios were motivated by development errors, so the existing 36 reviews are still a regression set, not an independent holdout. Add fresh authentic examples of both scenario-only reviews and genuine mixed/place reviews before making generalization claims.

Do not change the accepted v0.4 prompt, codebook, runner, schema or current-version pointer. New inference requires a separately prepared/versioned runner, its own manifest and output directory. This draft has not been run, has no accuracy estimate and is not adopted. The primary downstream emotion model remains Gemma; retained Qwen comparison output and the no-emotion/no-E/T policy are unchanged.

## Required evaluation for this amendment

No test has been run. Evaluate both hostile rants that contain plausible place details and strong but legitimate negative reviews, including specific allegations, policy criticism, requests for accountability, facilities failures, hazards and emphatic first-person reports. Inspect false exclusions of grounded negative evidence as carefully as missed rants. Use fresh authentic reviews as well as existing regression cases; the motivating case is development material, not independent validation. Keep actual test quotations and case IDs out of model instructions. Report exclusion reasons separately from no-place-evidence reasons using the existing reason field.

The earlier three-case human audit remains U01 REJECT, U02 KEEP, N05 REJECT. That evaluator reference is not an instruction to add case-ID overrides. No new gate adoption, extraction run or change to the Gemma-primary policy follows from creating this draft.

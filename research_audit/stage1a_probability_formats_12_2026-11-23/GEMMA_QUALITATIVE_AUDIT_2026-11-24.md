# Gemma probability plausibility: assistant audit, November 24, 2026

**Researcher follow-up:** The researcher subsequently said “i actually agree with those cases,” referring to K04, K05, K06 and U06. This records general agreement with the presented assessments; no separate replacement percentages or new blinded labels were supplied. See the [full November 24 discussion](../../Discussions/gemma-probability-audit-temperature-and-stability-2026-11-24.md).

The researcher requested a current advanced-LLM review of whether Gemma's probabilities make semantic sense, with controversial cases deferred to the researcher. This replaces using inherited reference labels as the basis for the requested qualitative judgment; earlier numeric audits remain archived.

**Models tested:** `qwen3.8:27b`, 27B Q4_K_M, and `gemma4:31b-it-bf16`, 31B BF16. This review adds zero calls to either model. The current ChatGPT/Codex assistant performed the reading; its exact backend model identifier is not exposed.

## What was reviewed

All twelve original targets and complete reviews, the frozen v0.5 calm definition and target-only evidence instructions, and all four state probabilities at T=1,2,4,6,8. The display below uses arithmetic mapping means at T=4 for consistency with the existing report. T=4 is not claimed to be optimal or calibrated. Full reviews resolve attribution and scope; other sentences cannot become additional target evidence. Prior labels and scores were already visible, so this is an openly qualitative audit, not a blinded independent benchmark. No replacement confidence percentages, NLL/Brier scores or accuracy claims are invented.

## Assessment

**Seven distributions are qualitatively reasonable, one has a clear attribution mismatch, and four were referred for researcher review.** These categories are the assistant's judgments, not human adjudications or measured accuracy.

| Case | Target | T=4 winning state / probability | Assessment |
|---|---|---|---|
| K01 | It was so stressful but her humanity made everything so much better! | opposition_only: 74.0% | clear_mismatch |
| K02 | Lights in the small box were years away- it was completely dark. | neither: 97.0% | reasonable |
| K03 | I wouldn't go here if your looking for walk. | neither: 97.9% | reasonable |
| K04 | What made this visit extra special was how surprisingly uncrowded it was. | support_only: 94.9% | human_review |
| K05 | If the owner of the chickens sees it, he yells from his home and asks if you are feeding poison to them. | opposition_only: 94.3% | human_review |
| K06 | It’s not closed to the street though so you have to keep an eye on your kids. | neither: 79.6% | human_review |
| U01 | 1/2 of the space was empty to become a dance floor later in the night. | neither: 98.6% | reasonable |
| U02 | The three exhibits on display were quite underwhelming… | neither: 98.6% | reasonable |
| U03 | It is hard to get the sound of the Memorial Drive cars out of your head as they are only a few yards from this park with no real barriers blocking the sound. | opposition_only: 98.7% | reasonable |
| U04 | This museum is fun for all ages. | neither: 98.7% | reasonable |
| U05 | This station is epic and famous, but not the cleanest. | neither: 98.5% | reasonable |
| U06 | Lovely sitting under the fairy lights in a comfy Adirondack chair, while a busker played songs from the 70s. | support_only: 92.2% | human_review |

## Clear cases and the main failure

**K01: neither.** The full review attributes stress to a late photographer and elopement logistics. Empathetic service improves that situation; the target does not establish site-induced disturbance. Opposition remains the dominant state after softening, so the principal interpretation error persists. Its lower certainty than the direct traffic-noise case is informative but does not repair attribution.

**K02: neither.** The target reports darkness in a restroom without reporting calm, agitation, intrusive noise or place-induced tension. Darkness may relate to other constructs; neither is a reasonable calm-specific preference.

**K03: neither.** A warning that the park is unsuitable for walking is about activity suitability. No calm-related experience or specific disturbance appears in this target. Positive descriptions elsewhere cannot supply another target claim.

**U01: neither.** The target describes a future dance-floor use, not experienced dancing, noise or agitation. Empty space and a future activity are insufficient calm evidence. Neither is reasonable despite the inherited conflicting reference.

**U02: neither.** Disappointment with exhibit quality does not establish a calm or agitating atmosphere. Neither is a reasonable construct-specific preference.

**U03: opposition_only.** The target explicitly describes intrusive traffic sound that the visitor cannot get out of their head, attributable to the park surroundings. Strong opposition is supported by the calm codebook; no supporting calm claim is supplied.

**U04: neither.** Fun for all ages reports enjoyment and accessibility, without calm or disturbance. Neither is a reasonable calm-specific preference.

**U05: neither.** Fame, positive place appraisal and poor cleanliness do not themselves supply tranquility or agitation in this target. The model correctly avoids transferring general sentiment or inviting-related evidence into calm.

## Four cases discussed with the researcher

The quoted targets and full contexts below were presented for calm review under v0.5. The researcher expressed general agreement with these four case assessments. That response is recorded as group agreement, rather than manufacturing separately supplied labels or probability vectors.

### K04

> What made this visit extra special was how surprisingly uncrowded it was.

**T=4 distribution:** neither: 2.9%, support_only: 94.9%, opposition_only: 1.3%, both: 0.9%.

**My reading:** support_only (T) is plausible; neither remains defensible. The target positively appraises an uncrowded visit, which plausibly reduces bustle. It does not itself describe ease or tranquility. The following sentences about comfortable strolling are outside the target. I lean toward support by inference, but support at 94.9% versus neither at 2.9% looks more decisive than this boundary warrants.

**Full review for scope/attribution:** Harvard Square never disappoints! I recently took my aunt for a visit, and we had such a lovely time soaking in the atmosphere. One of our favorite stops was the The Harvard Coop—and of course, we couldn’t leave without picking up some merchandise!

What made this visit extra special was how surprisingly uncrowded it was. We were able to stroll comfortably, browse at our own pace, and truly enjoy the charm of the Square without the usual hustle and bustle.

It’s always such a classic Boston experience—great shopping, beautiful surroundings, and that unmistakable Harvard vibe. A must-visit every time!

**Researcher response:** General agreement with the presented assessment, recorded in the follow-up above.

### K05

> If the owner of the chickens sees it, he yells from his home and asks if you are feeding poison to them.

**T=4 distribution:** neither: 2.2%, support_only: 1.8%, opposition_only: 94.3%, both: 1.6%.

**My reading:** opposition_only (T). Visitor-directed yelling and accusation plausibly constitute an agitating encounter at the park. I lean opposition. Whether this is sufficient calm evidence, rather than solely hostility relevant to inviting/safe, remains a construct-boundary judgment. The 94.3% preference is plausible directionally but cannot itself settle that boundary.

**Full review for scope/attribution:** Park is good. The chickens will chase you if you have any food. If the owner of the chickens sees it, he yells from his home and asks if you are feeding poison to them. Also he has a security camera pointing at the park.

**Researcher response:** General agreement with the presented assessment, recorded in the follow-up above.

### K06

> It’s not closed to the street though so you have to keep an eye on your kids.

**T=4 distribution:** neither: 79.6%, support_only: 1.8%, opposition_only: 17.1%, both: 1.5%.

**My reading:** neither, with opposition as a plausible alternative. The target explicitly requires parental vigilance because of access to the street. This directly concerns safety and can plausibly imply reduced ease, although no stress or agitation is stated. The split of 79.6% neither and 17.1% opposition acknowledges a relevant alternative and is qualitatively sensible.

**Full review for scope/attribution:** It’s a cute small park good for little ones. It’s not closed to the street though so you have to keep an eye on your kids. But it’s really a great place to bring little as

**Researcher response:** General agreement with the presented assessment, recorded in the follow-up above.

### U06

> Lovely sitting under the fairy lights in a comfy Adirondack chair, while a busker played songs from the 70s.

**T=4 distribution:** neither: 5.7%, support_only: 92.2%, opposition_only: 1.0%, both: 1.2%.

**My reading:** support_only (T). Lovely sitting in a comfortable chair with music plausibly depicts ease. I lean support. Comfort, pleasantness and music do not necessarily establish tranquility, and music presence alone is insufficient. The 92.2% versus 5.7% neither preference may be too decisive for an unsettled calm boundary.

**Full review for scope/attribution:** Lovely sitting under the fairy lights in a comfy Adirondack chair, while a busker played songs from the 70s.  I was right next to, and under, the giant tree.  I’d like to know the age of that tree if anyone knows.

**Researcher response:** General agreement with the presented assessment, recorded in the follow-up above.

## What the probabilities appear to add

- At T=4, K01's erroneous opposition preference is 74.0%, versus 98.7% on explicit intrusive traffic noise. That is a useful-looking coarse distinction. K01 still assigns only 19.9% to neither; softening does not repair its attribution.
- K06 gives meaningful probability to a relevant opposing interpretation: neither 79.6%, opposition 17.1%, with little mass on support/both. This is qualitatively more informative than a hard neither verdict.
- K03 and U01 look semantically compatible with neither. They should not be called errors merely because an inherited reference version says opposition. Therefore the earlier three-disagreement error-ranking calculation is not a verdict from this reading.
- K04 and U06 remain strongly concentrated on support even though the boundary is debatable. K05 strongly prefers opposition; the calm-versus-hostility boundary deserves an explicit researcher decision.
- At T=8, the explicit traffic-noise case falls to 84.5% opposition and assigns 5.6% support and 4.3% both, despite no calm-supporting target evidence. Higher temperature spreads mass mechanically and does not consistently make semantic alternatives more plausible. It cannot be selected solely because the values look less extreme.
- Mapping variation remains relevant: K01's T=4 opposition probability spans 68.2–82.4%, and K06's neither spans 72.3–85.0%. Retain the full mapping vectors/ranges; fine percentage differences are not automatically meaningful.

**Present interpretation:** the distributions contain potentially useful case distinctions and alternative-state information, alongside a clear attribution error and unresolved construct boundaries. This assistant review judges qualitative plausibility; an exact claim such as “94% means 94% correct” is not established. The researcher response stays separate from the initial assistant reading. Temperature scaling preserves each individual distribution's winning state and does not create new evidence.

[Machine-readable audit, full contexts and temperature vectors](GEMMA_QUALITATIVE_AUDIT_2026-11-24.json) · [Original experimental report](README.md) · [Earlier provisional-reference check](GEMMA_SIGNAL_EVALUATION.md)

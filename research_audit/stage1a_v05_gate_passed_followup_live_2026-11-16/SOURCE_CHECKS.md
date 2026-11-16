# Initial source checks — latest v0.5 follow-up only

These are assistant source inspections after seeing model output, not independent human gold. No additional model was called for grading, no output was rewritten, and no original extraction was retried. This is a selective diagnostic check, not a completed claim-by-claim precision/recall audit.

## Clear issues in structurally valid outputs
| Target | Qwen3.8 | Gemma4 | Source check |
|---|---|---|---|
| N07__03: “Food punches well above its weight for a place like this.” | Inviting supports, E | Inviting supports, E | Food-quality praise promoted to place-level inviting evidence without a reported visiting/staying relationship. |
| N04__04: “great taxidermy animals (mammals and fish and birds)!!” | Inviting supports, E | Inviting supports, E | Exhibit quality promoted to inviting despite the explicit exhibit-quality boundary in the frozen codebook. |
| N09__02: “Delicious food, good coffee!” | Inviting supports, E | No claims | Qwen substitutes product satisfaction for atmosphere; Gemma abstains on this target. |
| N06__02: “Tried their root beer float, and loved it.” | Inviting supports, E | No claims | Same product-to-atmosphere overreach in Qwen; Gemma abstains. |
| N06__04: “Their patio is nice, although we did get into a predicament with the staff.” | “Their patio is nice” supports calm, E | Case invalid | “Nice” does not establish calm. Other staff-conflict claims need separate direction/provenance review; they are not automatically wrong merely because this calm claim is unsupported. |
| N04__10: children doing a scavenger hunt | Calm opposes, T, from “potential noise” | Not attempted | Qwen invents noisy/disruptive consequences from an activity alone; no disturbance is reported. |

These examples show residual false emotion readings among reviews that passed the gate. They do not measure errors prevented by the gate, because rejected reviews were not included in this run.

## Context and scope issues
- Both models call **T06__04** (“She made the entire process feel easy and stress-free.”) calm support, E, referent place. Full context identifies wedding planning/coordination, so this is an event/process-to-atmosphere attribution concern. Keep it for researcher review rather than converting all wedding-review claims automatically into errors.
- **T06** is a known eligibility false positive, separately from claim correctness. Some statements genuinely describe a private-event experience; eligibility and correct scoped extraction are distinct.
- Qwen's T12__06 inviting claim from architectural uniqueness and T10__03 calm inference from AC/seating need boundary review. They are not silently counted as confirmed errors here.
- E/T and referent problems should be scored separately from emotion-direction errors. A correct direction does not validate the provenance label.

## Invalid outputs: excluded from valid-output comparison
- **Qwen T02__01:** cold-start request timeout; raw response unavailable. Not an empty judgment or a semantic miss.
- **Gemma T02__01:** category-order validation failure; parsed claims also wrongly use the referent “animals.” Preserve the raw response; do not salvage it as a valid result.
- **Gemma N07__01:** borrows “warm atmosphere” from another sentence in full-review context. Exact-target validator catches the quote leak.
- **Gemma N06__04:** borrows “didn’t enjoy the tension” and the later patio-refusal wording from other sentences. Exact-target validator catches both quote leaks.

## Validity and coverage limits
Only **38** targets have valid outputs from both models. Qwen completed 10/12 reviews with all sentences valid; Gemma completed 5/12. Neither model has a valid T02 result. Missing and invalid segments remain explicit.
The gate does not certify that every sentence in a retained mixed review is emotion-relevant. This test reveals why the extractor must still reject food/exhibit-only sentences.

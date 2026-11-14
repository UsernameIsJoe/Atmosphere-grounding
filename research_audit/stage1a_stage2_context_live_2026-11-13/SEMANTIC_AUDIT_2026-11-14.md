# Stage 2 semantic audit (2026-11-14)

## Status and scope
72/72 model calls completed, zero JSON/schema execution failures. This is a *researcher semantic audit*, not an independently blinded measured accuracy score. The test used a single manually selected target sentence/phrase from each of 12 genuine review texts, not full segmentation of all reviews. Models: Qwen3.6 27B BF16 and Gemma4 31B BF16. Inputs: isolated target, target + whole-review reference context, and whole review without privileged target.

## Main finding
Full context is **not** universally better. In segment+context mode, Qwen3.6 returned quotes not in the target in K04 (stroll comfortably; browse at our own pace; without the usual hustle and bustle), K05 (security camera), and U04 (good time, pricing, commute). These are outside-target evidence leaks, even if genuinely in the overall source review. The source_exact false flag is correct and must not be dismissed as quote-copying failure in those cases. Qwen3.6 also produced abbreviated, nonexact quotations in full-review mode. Gemma4 largely respected target bounds but sometimes labeled humans or environmental objects as "animals" (K01, K02, U06, and K05 full review).

## Counts (descriptive, not accuracy)
- Qwen segment: 21 claims, 0 unverified source quotes; segment+context: 29 claims, 7 unverified (some are context leakage); full: 57 claims, 3 unverified.
- Gemma segment: 15 claims, 0 unverified; segment+context: 16 claims, 0 unverified; full: 39 claims, 1 unverified.
- Qwen changed >=1 of three atmosphere verdicts on 5/12 reviews for target+context vs target; 8/12 for full review vs target.
- Gemma changed >=1 verdict on 3/12 for target+context; 7/12 for full review.
- Full-review outputs answer a *different target scope*, so changes are not automatically errors or improvements.

## Case adjudication: conservative atmosphere-scope rules
K01: target-segment calm NONE (personal wedding/logistics stress, not site calm); target inviting NONE or weak person-centered inference. Full review inviting SUPPORTS from friendly people, scoped socially, not architecture. Both models incorrectly map 'so stressful' to site calm opposition.
K02: target segment reports absence of lighting in a restroom; calm NONE, inviting OPPOSES/INFERENCE, safe OPPOSES/INFERENCE under user's approved prior adjudication. Not a direct subjective feeling of threat. Full review reinforces discomfort/neglect. Qwen's full-review safe NONE and Gemma's UNCERTAIN miss user's adopted safety rule.
K03: target 'wouldn't go here if looking for a walk' is activity suitability, *not* evidence place is uninviting; calm/safe NONE. Both models incorrectly call target inviting OPPOSES. Full review can support inviting from 'nice little place to hang out' and calm inference from uncrowded; full vs target are distinct judgments.
K04: target 'surprisingly uncrowded': calm SUPPORTS/INFERENCE; inviting/safe NONE. Extra full-review praise/comfort is not allowable to score this target. Qwen segment+context contaminated target with 'stroll comfortably' and 'without usual hustle and bustle'. Full review can have direct calm and comfort basis.
K05: negative calm from yelling, inviting from hostility, safe OPPOSES/INFERENCE under user's prior adjudication. Security camera presence alone is NOT an affirmative felt-safe cue; both models' MIXED/UNCERTAIN safety is overcautious or wrongly counterbalanced.
K06: target 'not closed to street; watch kids': safe OPPOSES/INFERENCE, calm/inviting NONE. Full review inviting SUPPORTS from 'cute ... great place for little ones', distinct scope. Qwen target 'mixed safe' underweights danger; Gemma target gets direction but sometimes calls basis BOTH unnecessarily.
U01: empty area that will later be a dance floor is a spatial scheduling description; no calm/inviting/safe evidence in target.
U02: underwhelming *exhibits* is about quality, not welcome, calm or safety; all NONE. Qwen target+context inviting OPPOSES is a category spillover.
U03: traffic sound is intrusive; calm OPPOSES/DIRECT; inviting and safe NONE. Proximity to roadway is mentioned in sound context, not an automatic safety claim.
U04: 'fun for all ages' means age-accessible enjoyment; whether it counts as invitedness depends on adopted inclusivity vs atmosphere threshold. Conservative target inviting NONE, at most inferred welcomingness. Qwen off-target quotes in context arm were invalid. Full review broadly positive but not necessarily felt welcomed.
U05: USER ADJUDICATED inviting OPPOSES/INFERENCE. Poor cleanliness and closed/inaccessible toilets count as evidence of an uninviting visitor experience, without automatically implying calmness or safety. Distinguish the target segment (cleanliness) from the full review (closed toilets), so scope boundaries remain explicit.
U06: USER ADJUDICATED calm UNCERTAIN (inference). Lovely comfortable seating under lights and music directly supports inviting but does not establish calm; both relaxing and lively readings remain plausible. Safe NONE.

## User adjudication lock (2026-11-14)
- U05 inviting: OPPOSES / INFERENCE (negative experiential contribution of cleanliness and unavailable amenities; ensure evidence stays within the evaluated scope).
- U06 calm: UNCERTAIN / INFERENCE (relaxation possible, but not sufficiently established).
- Prior user locks: K01 calm NONE, K02 safe OPPOSES/INFERENCE, K05 safe OPPOSES/INFERENCE.
- These are category judgments, not a full independently annotated gold dataset.

## Next experiment proposal
1. Freeze 12 existing reviews and create full-span sentence/clause inventory for each, with source offsets and the original review context.
2. Evaluate 2 selected models in two segment modes: target only vs target + entire review for referent disambiguation. Omit full-review-only arm from the paired accuracy test because it has a different target scope.
3. Use explicit evidence, inferred condition, emotion verdict and basis, attribution, and quote/span validity as independently audited dimensions; enforce target-only quotation and forbid context-only rationales.
4. Run a **small, stratified 24-segment diagnostic** first (2 models × 2 modes × 24 segments = 96 calls). Include known pitfalls K01/K02/K03/K04/K05/K06/U05/U06 and positive/negative/null cases. Assess against the locked human judgments where available and request human adjudication only on unresolved ambiguous cases.
5. If leakage persists, compare prompt-only versus hard source-bound structured claim extraction, keeping prompts, data, and models fixed. Do not escalate model capacity yet.


## Method recommendations
- Keep the entire source review for referent resolution, but hard constrain each output claim's quotation and corresponding emotion rationale to the target span. A mechanically exact target check is *necessary but not sufficient*; review-context words in reasons and category verdicts can leak without being quoted.
- Report explicit cue vs description vs inference separately. Label emotion direction at target-level and report full-review judgments in their own scope, not as paired accuracy.
- Audit source/entity attribution separately from emotion verdict; cardinal failures of Gemma4's referent field mean 'conservative' is not equivalent to reliable.
- Perform broader segment coverage and independent human gold before choosing a final extraction model or architecture.
- User approved K01 calm none, K02 safe opposes, K05 safe opposes. Preserve them as research-specific adjudications, not population-wide truths.

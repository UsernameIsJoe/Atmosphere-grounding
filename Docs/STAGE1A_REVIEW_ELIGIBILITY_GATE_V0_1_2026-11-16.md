# Stage 1A review-eligibility gate v0.1 (draft, 2026-11-16)

**Placement:** Original complete review → **binary eligibility filter** → segmentation → v0.5 directional extraction. This **supersedes the placement** of the earlier [segment-level routing proposal](STAGE1A_EVIDENCE_ROUTING_GATE_DRAFT_2026-11-16.md); it does **not** implement that earlier proposal or the deferred cascade.

**Research question:** Does the **whole review** contain at least one useful observation about the **place as encountered/experienced by a visitor**, sufficient to justify passing it to the segmenter? The gate is **not** an emotion detector, topic classifier, E/T labeler, or extraction model.

## Binary rule

- **KEEP** when **any specific, relevant passage** reports or appraises spatial/environmental/sensory qualities; the atmosphere, accessibility, comfort, safety, desirability, or experience of visiting/staying; or a **visitor-facing interaction** that materially shapes the experience of the place.
- **REJECT** only when the **entire review** lacks such passages—for example, it exclusively recounts historical background, describes the subject/content/quality of artwork or exhibits without relating that to the experience of the place, or narrates an unrelated private occurrence (e.g., a personal appointment running late) without place-facing observations.
- **Mixed reviews: KEEP** if any passage qualifies. The subsequent segmenter can remove irrelevant portions; **never require a majority** of the review to be place-related.
- **Unclear cases: KEEP.** Conservative rejection protects recall; false exclusions are more damaging than extra material downstream.

**Non-general incident boundary:** A private, accidental, isolated occurrence **without a defensible connection to the location or visitor experience** does not qualify by itself. An actual visitor-facing staff interaction, a safety encounter on the site, or a description of using the space **can** qualify even if experienced once. “Non-general” should **not** mechanically mean “mentioned once,” because the v0.5 codebook recognizes situated visitor-facing experiences as evidence.

**Do not** count generic praise such as “Great!” alone, or trivial venue names, as qualifying evidence. But a direct and meaningful appraisal of the **place as a destination** (e.g., enjoyable to visit) counts; don't reject it merely because no architecture vocabulary occurs.

## Exact system message

Insert the text below without adding emotion-analysis instructions.

```text
You are a HIGH-RECALL eligibility filter for full visitor reviews of real places.

Decide ONLY whether this COMPLETE review deserves to proceed to segmentation
for a study of place qualities and visitors' experience of being there.
Do not classify its topic. Do not score calm, inviting, safe, or any emotion.
Do not extract segments. Return exactly one binary keep decision.

KEEP if the review contains at least ONE specific claim about the place
as encountered: physical/spatial/sensory conditions, ambience, accessibility,
use or comfort, appeal or desirability of visiting/staying, visitor-facing
hospitality, or an experienced social/safety condition of the place.
An emotion adjective is not necessary. Interactions with staff or other
people can qualify when they affect the experience of being at the place.

REJECT only if the ENTIRE review provides no such place-experience material:
e.g., history alone, artistic subject/content/quality alone with no effect
on the visit, or an unrelated personal incident/appointment without
place-related observations.

If some passages qualify and others do not, KEEP the entire review for
the segmenter. A one-off incident is irrelevant only when unrelated to
the place or visitor experience; a one-time staff interaction can qualify.
If the distinction is genuinely unclear, KEEP. Do NOT require most of the
review to qualify. Do not use a rating or generic praise alone as evidence.

Output exactly:
{"keep": boolean, "anchor_quote": string, "reason": string}
For KEEP, anchor_quote must be a short, contiguous, exact substring
of review_text that demonstrates what qualifies. No invented quotation.
For REJECT, anchor_quote must be "" and reason must briefly explain
why no qualifying material exists. No category names or emotion labels.
Return JSON only, no additional text.
```

## User message

```json
{"review_text":"<original complete review text>"}
```

Use JSON serialization for the actual text; do not substitute literal prose into JSON without escaping.

## Schema

See [v0.1 output JSON schema](../configs/stage1a_review_eligibility_gate_v01.json). Output is solely `keep` (boolean), `anchor_quote` (exact source excerpt when kept, otherwise empty), and `reason` (brief evidence-grounded explanation). The quote is a provenance check, **not a segmentation boundary**.

## Known boundary from previous audit

The original elopement review (K01) includes an unrelated photographer delay **but also** reports people being nice, staff warmth, and using the space for photos. Under this conservative whole-review rule it **should pass**; the later segmenter/interpreter must not mistake the private stress for a place atmosphere claim. Rejecting the entire review would erase previously researcher-approved positive Inviting evidence.

Conversely, a review containing **only** a private delay and no observations about the venue should be rejected.

## Validation plan (not yet an experiment)

1. Assemble a **review-level** human audit on authentic source reviews, deliberately including pure non-place material, mixed reviews, and clear spatial-experience reviews. The old 12-case segment-level judgments are **not** a review-eligibility gold standard.
2. First metric: **false-negative rate on human-KEEP reviews**; separately measure reject precision, review retention rate and skipped review counts. Keep failed/filtered originals for audit.
3. Run **gate → segmentation → v0.5** only after independently checking review-level false exclusions. Do not silently merge this gate into a segment-level experiment.
4. No model has been run and no Runpod compute is requested by this design document. The [Python runner](../scripts/stage1a_review_eligibility_gate_v01_20261116.py) is an optional implementation to prepare and execute the gate later.

**Principle:** This filter protects **review eligibility**, not the validity of every sentence inside a kept review. Later stages must still handle attribution and irrelevant passages.

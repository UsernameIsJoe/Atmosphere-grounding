# Stage 1A — full-review eligibility gate codebook v0.2 (draft, 2026-11-16)

**Role:** Binary full-review eligibility **before segmentation**. The question is whether the review contains meaningful **place-level evidence**, not whether anything noteworthy happened at the place. This codebook supersedes the acceptance rationale in review gate v0.1 but does not alter the Stage 1A emotion codebook v0.5.

## Core test: place-level versus individual encounter

**Place-level evidence** reports a spatial, environmental, sensory, functional, atmospheric, access, or visitor-experience **characteristic of the location being reviewed**. It need not be objectively permanent or universal; a specific visitor's experience can qualify if it meaningfully reveals the character, conditions, use, accessibility, atmosphere or establishment-level service of the place.

**Isolated personal encounter** concerns a particular person, transaction, gratitude, unique private mishap or private occasion without a defensible place-level characterization. Its occurrence *at* a place does not make it evidence *about* the place.

The distinction is about **what the review tells us**, not whether it uses "I", concerns people, or describes a single visit.

## Binary outputs

- **KEEP** when at least one **meaningful, text-grounded passage** characterizes the **reviewed location** as a place to enter, use, experience, visit, stay, navigate or avoid. Place qualities include design/layout, ambience, sound/light/crowds, access and facilities, visitor-facing conditions, attractiveness, and discernible establishment-level hospitality/service practices.
- **REJECT** when the entire review has **no** meaningful place-level evidence. Examples: thanks to a named waitress for personal help; one particular server's friendliness absent any broader characterization; a private appointment delay; history-only narration; descriptions/ratings of individual art pieces/exhibits without appraising the visit or environment; impressions of *another* location rather than the one reviewed.
- **MIXED:** KEEP the full review when it also contains qualifying place-level evidence, even if most sentences are about private events. The segmenter will remove irrelevant material later. But incidental mentions such as "we took photos there", "I was here", or "the staff did not complain" do **not** automatically elevate a purely personal story to place-level evidence.
- **AMBIGUOUS:** Prefer KEEP only when the review offers a **plausible substantive** observation about the reviewed place; otherwise REJECT. Do not manufacture a place-level generalization to avoid a false negative.
- **Scope:** The "place" is the **venue/site actually being reviewed**. The venue may be a park, station, square, store, gallery, museum, restaurant or restroom. Avoid substituting a reviewer's comments about another venue.

## Visitor-facing people: precise boundary

| Evidence | Gate | Reason |
|---|---|---|
| "This store feels welcoming; staff generally make visitors feel at ease" | KEEP | General establishment-level experience |
| "The servers here are routinely attentive even when the place is busy" | KEEP | Repeated/establishment-level service practice |
| "Thank you to waitress Anna for helping with my birthday surprise" | REJECT | Praise of one named person/private event only |
| "One cashier was very kind when my card failed" | REJECT | Isolated transaction |
| "The posted entry policy prevented visitors from using the entrance" | KEEP | Repeatable access rule of place |
| "People here are regularly confronted by a neighboring resident" | KEEP | Reported recurring place-facing condition; do not claim universality beyond text |

One observed incident **can** qualify if it discloses a physical hazard, posted rule, systemic access condition or directly experienced place characteristic; count neither singularity nor interpersonal language as an automatic reject or keep.

## Artwork and history

- **REJECT:** An explanation of a monument's history; reviews solely rating art pieces or exhibitions, without comments on the experience of the reviewed place.
- **KEEP:** "The gallery lighting made it difficult to see the works"; "the museum is enjoyable to explore with children"; a site/history discussion also containing substantive reports about how the place feels or works.
- Praise for a **different** location is not evidence about the reviewed site.

## Calibration using existing 12 reviews (development hypotheses; not independent gold)

- **K01 — REJECT:** Wedding-specific gratitude and the photographer's delay dominate; the references to taking photos and not being stopped do not meaningfully characterize the venue. This explicitly overrides v0.1's KEEP and is the user's stated boundary.
- **K02 — KEEP:** Here the reviewed location is a restroom; its actual darkness, cleanliness and broken washing facility are conditions of that place, not incidental "black box" trivia.
- **K03 — KEEP:** A park's crowding, benches and usefulness for staying/visiting.
- **K04 — KEEP:** The square's comfortable strolling and low crowds form a place-directed visitor experience.
- **K05 — KEEP (provisional):** Conditional chicken-chasing behavior and encounters facing park users describe site-associated conditions, not just a standalone compliment to an individual.
- **K06 — KEEP:** The park's proximity/exposure to the street.
- **U01 — KEEP (provisional):** Spatial layout and dance-floor use describe the venue, even though review includes party details.
- **U02 — REJECT (provisional):** A judgment of the exhibits and advice to visit *other* campus locations; no meaningful assessment of the reviewed venue's space/visitor experience.
- **U03 — KEEP:** Courts and road noise.
- **U04 — KEEP:** Describes the museum as a visitor experience for all ages, independent of the named exhibits.
- **U05 — KEEP:** Station cleanliness, visit impression and restroom closure.
- **U06 — KEEP:** Site furniture, lighting and the experience of sitting under the tree.

These are **expected gate interpretations**, to check through a human review-level audit; not claims that the 12-item dataset independently establishes accuracy.

## Evaluation controls

Use only the full source review; no selected segment or prior emotion label. Output **binary** keep and short source-exact anchor for KEEP, otherwise empty anchor; no topic tags, emotion verdicts, E/T, or segment boundaries. Check exact quote substring mechanically. A short anchor demonstrates eligibility but is not a substitute for reading full context.

**Success:** Very high recall on genuinely eligible reviews **without** automatically keeping every review that mentions a venue, employee, history or exhibit. Specifically evaluate false-kept personal encounters and false-rejected first-person place experiences. Run a balanced, independently adjudicated set with authentic negative reviews before reporting meaningful precision/recall.

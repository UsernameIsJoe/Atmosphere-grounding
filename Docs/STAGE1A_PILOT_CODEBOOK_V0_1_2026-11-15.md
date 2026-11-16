# Stage 1A pilot codebook v0.1 — Calm, Inviting, Safe

**Status:** DRAFT for researcher M0 review; not validated or approved for production.  
**Scope:** one immutable target segment within its original full review.  
**Date:** 2026-11-15.  
**Decision output:** one of `supports | opposes | none | uncertain` for EACH of calm, inviting, safe. No `mixed` verdict; no numerical confidence score.

## Purpose and boundaries

Measure whether the **target segment** conveys a place-attributed claim about an experienced atmosphere. The review is **context for reference resolution only** (e.g., what "it" refers to, whether stress concerns the event rather than the place). It must NOT supply additional evidence, quotes, or independent reasons for the target's verdict. Exact evidence quotes must be substrings of the target.

Do **not** equate atmosphere with overall review sentiment, popularity, aesthetic merit, event success, accessibility, or object presence. A positive review can oppose an emotion; a negative review can support an emotion.

Each emotion is independent. A segment may support calm and safe, oppose inviting, or any other justified combination. Do not classify a *mix of different emotions* as mixed.

### Provenance tracks (experimental — not a confidence ladder)

- **E — explicitly reported atmosphere or experienced condition:** The segment directly reports how the site felt or a clearly experienced environmental/social condition relevant to the emotion (e.g. "It felt safe"; "The constant noise made the park stressful"). Source is an experienced claim, **not** merely the model's interpretation of a physical object.
- **T — descriptive / inference-bearing condition:** The segment reports a place-related observation that could plausibly affect atmosphere but does **not** explicitly establish that felt relationship (e.g. "There was no fence between the playground and the road"). An inferred emotional judgment from T is **a hypothesis**, not an E observation.
- **E and T are not confidence grades.** A very clear T observation can support only a tentative atmospheric inference; an explicit E statement can still be irrelevant if about the wrong referent. Record the source track for each evidence item. The pilot can generate an overall verdict, but downstream E-only and E+T profiles must remain separately inspectable. Production Stage 1A's E-first architecture is **not** superseded by this experimental pilot.

### Attribution gate

For each possible claim ask:
1. What is described, and who/what does it refer to? (site itself, its surrounding environment, people at the site, animals, an unrelated event, or unclear)
2. Is the condition relevant to visitors' experience of **this place**, rather than solely to the reviewer's private life, schedule, expectations, or the quality of an exhibit/product?
3. Is the evidence in the TARGET, not merely the full review?
4. Does it support/oppose one of our narrowly defined atmospheric dimensions, rather than general enjoyment/disappointment?
5. Would the direction still be defensible without stereotypical assumptions about darkness, density, trees, prices, fame, or cleanliness?

People and services may contribute to **inviting** or **safe** if the text describes interactions a visitor encounters at the place. Do not extrapolate one person's behavior into an absolute property of all people or the whole site. Nearby traffic can influence **calm** when the reviewer describes its actual impact on the experience; merely mentioning a road is insufficient.

## Four verdicts — apply per emotion

| Verdict | Operational meaning | Evidence behavior |
|---|---|---|
| `supports` | The model can defend a positive relationship for this target and emotion under the codebook. | Cite exact target evidence; preserve E/T provenance. |
| `opposes` | The model can defend a negative relationship for this target and emotion. | Cite exact target evidence; preserve E/T provenance. |
| `none` | The model can confidently determine that the target supplies **no sufficiently defensible directional evidence** for this emotion. Includes irrelevant facts, unsupported associations, or text too indeterminate to establish direction. | May explain rejected cues, but do not invent positive/negative evidence. |
| `uncertain` | Even after applying the codebook and available context, the model **cannot reliably choose among supports, opposes, and none**. This is a decision-level abstention, not a category for slight/weak mood or a synonym for mixed. | Explain exactly which alternatives cannot be resolved; cite only target evidence if any. |

**Decision threshold:** Ask whether there is a defensible, relevant, target-grounded reason for supports or opposes. If neither is defensible and that conclusion is clear, assign **none**. Reserve **uncertain** for genuine failure to determine which verdict is warranted; do not use it automatically for weak evidence, generic descriptive language, or absence of emotion words. Do NOT ask the LLM to invent a numeric confidence percentage.

**Same-emotion contradictions:** Retain each positive and negative source item separately. If one direction is clearly supported at the target level after qualifications/negation are respected, choose that direction and mention the counterevidence. If neither direction can be selected reliably, choose **uncertain**. Do not silently average opposite claims into **none**.

**Negation/scope:** "Not unsafe" is not automatically "safe"; "not calm" opposes calm only when it characterizes the place/experience. Hypotheticals, other people's reports, comparisons, temporally qualified remarks, and negation must be kept in scope.

## Emotion definitions and boundaries

### CALM

**Construct:** A visitor-experienced atmosphere of tranquility, low agitation, ease, quiet, or relaxation. **Opposition:** Reported disturbance, intrusive noise, chaotic activity, or place-induced stress/tension.

- **Direct E support:** "The courtyard felt peaceful"; "It was quiet and relaxing there."
- **Direct E opposition:** "The traffic noise made it impossible to relax"; "The square was loud and overwhelming."
- **T examples (inference only):** "The garden was nearly empty"; "The road runs directly alongside the playground." These do not automatically determine calm.
- **Exclude:** Personal deadline/wedding/travel stress not attributed to the place; pleasant music without a stated relaxing or disruptive impact; "fun", "beautiful", and uncrowded as automatic synonyms for calm.
- **Boundary:** The presence of music/noise is not itself necessarily opposition; its characterized experience and scope matter.

### INVITING

**Construct:** A visitor-experienced sense of welcome, ease of approach/entry, inclusion, hospitality, or comfort in entering or staying. **Opposition:** Reported hostility, exclusion, discouragement, or barriers that actually make the place feel inaccessible or unwelcoming.

- **Direct E support:** "The staff made us feel welcome"; "I felt comfortable staying there."
- **Direct E opposition:** "We were made to feel unwelcome"; "Visitors were shouted at and told to leave."
- **T examples (inference only):** "There were comfortable chairs"; "The entrance has several steps"; "The restroom was closed." Relevance may exist without establishing welcome as a felt judgment.
- **Exclude:** General excitement, exhibit quality, fame, fun, beauty, low price, or a reviewer's preference for a different activity as *automatic* evidence of welcomingness.
- **Boundary:** Friendly service can be local evidence about that experience; it must not be generalized to every visitor or the entire neighborhood.

### SAFE

**Construct:** A visitor-experienced sense of security/protection from physical harm or credible personal threat, including clearly reported exposure to danger. **Opposition:** Reported unsafe conditions, threats, hazards, or credible anxiety about personal safety tied to the place.

- **Direct E support:** "I felt safe walking through the park"; "The crossing felt secure."
- **Direct E opposition:** "The broken railing made the walkway dangerous"; "I was threatened while visiting."
- **T examples (inference only):** "There was no gate between the play area and the street"; "The restroom was completely dark"; "A security camera overlooked the park." These do not automatically establish feeling safe or unsafe.
- **Exclude:** Generic discomfort, bad maintenance, dirt, darkness, unattractiveness, high prices, or loudness **without a defensible safety relationship**.
- **Boundary:** A hostile exchange may matter for safety when there is a credible threat or fear; hostility alone more clearly bears on inviting. Distinguish felt safety from objectively verified crime risk.

## Stable calibration anchors (authored examples; NOT evaluation data)

These are *illustrative anchors*, not human-adjudicated corpus labels. Do not score new cases merely by word overlap; check referent, scope, negation, and category definition.

| Target segment | Emotion | Expected verdict | Track | Why |
|---|---|---|---|---|
| "The park was quiet and I could finally relax." | calm | supports | E | Explicit peaceful experience at site |
| "The noise from the road made this park exhausting." | calm | opposes | E | Experienced environmental disruption |
| "The park has three picnic tables." | calm | none | — | No defensible calm direction |
| "I was stressed because my train was late, but the courtyard was peaceful." | calm | supports | E | Explicitly separates external stress from place atmosphere |
| "We felt welcomed as soon as we entered." | inviting | supports | E | Direct place-attributed welcome |
| "The visitors were shouted at and told to leave." | inviting | opposes | E | Explicit exclusion in place interaction |
| "The exhibition had three rooms." | inviting | none | — | Exhibition layout does not establish welcome |
| "The staff were polite, but we were refused entry." | inviting | uncertain | E | Contradictory inviting signals: abstain if neither dominates |
| "I felt safe walking here after dark." | safe | supports | E | Explicit felt security |
| "The broken bridge railing made the walkway dangerous." | safe | opposes | E | Explicit reported physical hazard |
| "The area had a security camera." | safe | none | T candidate | Camera existence does not establish the site's felt safety |
| "Some visitors felt protected; others reported feeling threatened in the same space." | safe | uncertain | E | Contradictory reported perceptions cannot support one direction without qualifications |

**Important:** `uncertain` cannot be guaranteed by textual pattern. If contextual evidence resolves the ambiguity, use the resolved direction; if a vague segment clearly does not support any direction, use `none`.

## Known disputed cases are NOT codebook anchors

The pilot's K01/K02/K03/K04/K05/K06/U01/U02/U04/U05/U06 disputes must remain **development/audit cases**, not unquestioned gold. In particular, repeated user blind ratings conflict on K01 calm, K02 safe, U05 inviting, and U06 calm. Any future benchmark must use separate, unseen place-disjoint segments and independent human adjudication. Do not tune rules to match one blind round.

## Reproducibility and acceptance

1. Freeze this exact version and hash; inject the entire text (or a fixed semantically identical machine-readable excerpt) into **every** model call, in the same order.
2. Freeze target text, full-review text, segmentation, category order, schema, prompt, model digest, decoding settings and run IDs; record hashes.
3. Mechanical checks: every quote must match the target exactly; every evidence ID must exist; distinct category verdict for each of three emotions; no `mixed` verdict; no context-only quote; per-emotion rationale explains direction or abstention.
4. Audit semantically: correct referent, emotion relevance, E/T provenance, direct-vs-inferred direction, appropriate `none` and `uncertain`, and context leakage in rationales.
5. Report repeat-run *verdict agreement* and human agreement separately; a fixed codebook is **a design hypothesis**, not evidence of achieved consistency. Note same-model run instability has been documented in Haldar & Hockenmaier, "Rating Roulette" (Findings of EMNLP 2025).

**Pending researcher approval:** Fine boundaries of inviting (comfort vs inclusion) and safe (physical threat vs perceived social safety); role of T-derived verdicts in the overall pilot score; and how to resolve same-emotion contradictions when no direction dominates.

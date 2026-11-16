# Stage 1A pilot codebook v0.2 — Calm, Inviting, Safe

**Status:** REVISED DRAFT for researcher M0 review and controlled testing; not validated or approved for production.  
**Scope:** one immutable target segment within its original full review.  
**Date:** 2026-11-16.  
**Version policy:** v0.1 is preserved unchanged. This revision changes judgment procedure and calibration, **not** the three emotion definitions.  
**Decision output:** one of `supports | opposes | none | uncertain` for EACH of calm, inviting, safe. No `mixed` verdict; no numerical confidence score.

## Purpose and boundaries

Judge whether the **target segment** supplies defensible evidence about the place-attributed atmosphere, whether expressed through a reported experience (E) or a place condition whose atmospheric bearing is supported by context (T). A text need not contain the emotion's name or an explicit adjective to count. Judge what the statement actually conveys, not whether a keyword is present. The review is **context for reference resolution only** (e.g., what "it" refers to, whether stress concerns the event rather than the place). It must NOT supply additional evidence, quotes, or independent reasons for the target's verdict. Exact evidence quotes must be substrings of the target.

Do **not** equate atmosphere with overall review sentiment, popularity, aesthetic merit, event success, accessibility, or object presence. A positive review can oppose an emotion; a negative review can support an emotion.

Each emotion is independent. A segment may support calm and safe, oppose inviting, or any other justified combination. Do not classify a *mix of different emotions* as mixed.

### Provenance tracks (experimental — not a confidence ladder)

- **E — explicitly reported atmosphere or experienced condition:** The segment directly reports how the site felt or a clearly experienced environmental/social condition relevant to the emotion (e.g. "It felt safe"; "The constant noise made the park stressful"). Source is an experienced claim, **not** merely the model's interpretation of a physical object.
- **T — descriptive / inference-bearing condition:** The segment reports a place-related observation that could plausibly affect atmosphere but does **not** explicitly establish that felt relationship (e.g. "There was no fence between the playground and the road"). An inferred emotional judgment from T is **a hypothesis**, not an E observation.
- **E and T are not confidence grades.** A clear T observation may justify a directional atmospheric inference when its implications are grounded in the particular statement, not merely a generic association; it must still be labeled **T**. An explicit E statement can still be irrelevant if about the wrong referent. Record the source track for each evidence item. The pilot can generate an overall verdict, but downstream E-only and E+T profiles must remain separately inspectable. Production Stage 1A's E-first architecture is **not** superseded by this experimental pilot.

### Attribution and relevance checks (reasoning aids, NOT automatic rejection gates)

For each possible claim ask:
1. What is described, and who/what does it refer to? (site itself, its surrounding environment, people at the site, animals, an unrelated event, or unclear)
2. Is the condition relevant to visitors' experience of **this place**, rather than solely to the reviewer's private life, schedule, expectations, or the quality of an exhibit/product?
3. Is the evidence in the TARGET, not merely the full review?
4. Is there a defensible direction for one of our narrowly defined atmospheric dimensions, rather than just general enjoyment/disappointment? A directional implication need not be expressed as an emotion adjective.
5. Does the particular segment support the direction through an experienced impact, situational relationship, or explanation—not merely a stereotype about darkness, density, trees, prices, fame, or cleanliness?

People and services may contribute to **inviting** or **safe** if the text describes interactions a visitor encounters at the place. Do not extrapolate one person's behavior into an absolute property of all people or the whole site. Nearby traffic can influence **calm** when the reviewer describes its actual impact on the experience; merely mentioning a road is insufficient.

## Four verdicts — apply per emotion

| Verdict | Operational meaning | Evidence behavior |
|---|---|---|
| `supports` | The model can defend a positive relationship for this target and emotion under the codebook. | Cite exact target evidence; preserve E/T provenance. |
| `opposes` | The model can defend a negative relationship for this target and emotion. | Cite exact target evidence; preserve E/T provenance. |
| `none` | After considering plausible cues in both directions, the model can confidently determine that **neither direction has a defensible connection to the atmosphere**. General sentiment, off-target facts, and truly non-directional description belong here. | Briefly explain the missing relationship, not just the absence of an emotion word. |
| `uncertain` | Even after applying the codebook and available context, the model **cannot reliably choose among supports, opposes, and none**. This is a decision-level abstention, not a category for slight/weak mood or a synonym for mixed. | Explain exactly which alternatives cannot be resolved; cite only target evidence if any. |

**Decision threshold — evaluate direction BEFORE defaulting to none:** Review the target for explicit and implicit cues of support AND opposition for each emotion. Decide whether any cue supplies a specific, defensible relationship to this place. A relationship can be reported (E) or reasonably inferred from a described condition (T), but must be traceable to this segment. If a direction is defensible, use `supports` or `opposes` and retain provenance. Only choose `none` after checking both directions and determining that neither is defensible. Reserve `uncertain` for genuine inability to choose among the three verdicts—not merely because evidence is indirect or lacks an adjective. Do NOT request a numeric confidence score.

**A directional test for T:** Ask: (a) Does the segment report a real, place-relevant condition? (b) Does it communicate enough about the condition's *relationship* to visitors' atmospheric experience to justify this particular emotion and direction, rather than a generic stereotype? If yes, a T-based directional verdict can be defensible, clearly tagged `T`. If not, `none` is appropriate. Example: "The cars beside the park are so loud I can't hear myself think" opposes **calm** through an experienced impact (E); "There is a road near the park" does **not** establish opposition to calm (T candidate, `none`). A T-only judgment must not be reported downstream as an E observation.

**Same-emotion contradictions:** Consider positive and negative signals separately. If one direction is better supported once attribution, negation and qualifications are considered, choose that direction and describe the counterevidence. If both are relevant and cannot be resolved into a defensible verdict, choose **uncertain**. Do not silently average genuine opposing evidence into **none**. A mixed sentiment about a visit is not necessarily two directions of the *same emotion*.

**Negation/scope:** "Not unsafe" is not automatically "safe"; "not calm" opposes calm only when it characterizes the place/experience. Hypotheticals, other people's reports, comparisons, temporally qualified remarks, and negation must be kept in scope.

## Required decision sequence (per emotion)

1. **Read the target as a statement, not a bag of cues.** Use the full review *only* to resolve what the target refers to.
2. **Consider both directions.** Could some target-grounded phrase support the emotion? Could some phrase oppose it? Include experienced effects, social interactions, access-related experiences, and place-related conditions—not only emotion words.
3. **Evaluate relevance and referent.** Does the particular statement connect to the visitor's experience at this place? Reject a direction when it requires an unsupported stereotype or changes who/what the statement describes.
4. **Commit to one verdict:** `supports` or `opposes` when that interpretation is defensible; `none` only when neither is; `uncertain` only when the choice genuinely cannot be resolved.
5. **Document, don't revise, the decision.** Once the verdict is selected, record exact source phrases and their E/T provenance. If documentation reveals a contradiction, reconsider the verdict rather than producing inconsistent labels. Mechanical JSON/quote constraints are *validation*, not the basis for semantic judgment.

**Important distinction:** "Potentially relevant to an emotion" is *not by itself* enough to assign a direction. Conversely, a clear account of an adverse or welcoming place experience need not use the words "unsafe", "unwelcoming", "stressful", or "calm". Avoid both over-interpretation and reflexive `none`.

**Output simplification for v0.2:** Evidence belongs *inside each emotion's assessment*, with exact `quote`, `track` (`E`/`T`), `direction`, and `referent`. No global evidence IDs, cross-category links, or numeric confidence. `none` has an empty evidence array, with any considered-but-rejected cues mentioned in its short reason. `supports`/`opposes` include at least one target-grounded evidence phrase in the chosen direction. An `uncertain` assessment can preserve unresolved directional items or have an empty evidence array. These formatting rules **must not** restrict semantic consideration during the verdict step.

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
| "The staff were polite, but I was made to feel unwelcome when they refused us entry." | inviting | opposes | E | Directly reported exclusion overrides incidental politeness |
| "I felt safe walking here after dark." | safe | supports | E | Explicit felt security |
| "The broken bridge railing made the walkway dangerous." | safe | opposes | E | Explicit reported physical hazard |
| "The area had a security camera." | safe | none | T candidate | Camera existence does not establish the site's felt safety |
| "Some visitors felt protected; others reported feeling threatened in the same space." | safe | uncertain | E | Unresolved conflicting reports about the same place; the model cannot defend one direction |

**Important:** These synthetic examples are calibration aids only; they do not establish empirical accuracy. `uncertain` cannot be guaranteed by textual pattern. If contextual evidence resolves the ambiguity, use the resolved direction; if a vague segment clearly does not support any direction, use `none`.

### Boundary counterexamples (illustrative, NOT corpus labels)

| Target segment | Emotion | Verdict | Why |
|---|---|---|---|
| "The museum was fun for children and grandparents." | inviting | none | Enjoyment across ages does not necessarily establish welcome or ease of approach |
| "The guide personally greeted us and made us feel at home." | inviting | supports | Felt hospitality, even without the word "inviting" |
| "The tight entrance and confusing signs made us hesitate to go inside." | inviting | opposes | Described barriers have an actual discouraging effect, not just physical presence |
| "I was worried about a personal deadline while sitting there." | calm | none | Stress is not attributed to the place |
| "I couldn't relax because of the nearby construction noise." | calm | opposes | Place-related disturbance is reported without the word "calm" |
| "There's no barrier between the play area and fast-moving traffic, so parents need to keep children from running into the road." | safe | opposes | A specific exposure pathway justifies danger, even if no one says "unsafe"; classify the source as E only when directly experienced/reported, otherwise T |
| "There was a street near the park." | safe | none | No stated hazard or place-specific justification of danger |

## Known disputed cases are NOT codebook anchors

The pilot's K01/K02/K03/K04/K05/K06/U01/U02/U04/U05/U06 disputes must remain **development/audit cases**, not unquestioned gold. In particular, repeated user blind ratings conflict on K01 calm, K02 safe, U05 inviting, and U06 calm. Any future benchmark must use separate, unseen place-disjoint segments and independent human adjudication. Do not tune rules to match one blind round.

## Reproducibility and acceptance

1. Freeze this exact v0.2 version and hash; inject the complete text into **every** v0.2 model call, in the same order. Keep v0.1 and original prompts untouched.
2. Freeze target text, full-review text, segmentation, category order, schema, prompt, model digest, decoding settings and run IDs; record hashes.
3. Mechanical checks: every quote must match the target exactly; each emotion's embedded evidence has a valid track, direction and referent; exactly one verdict per category; no `mixed` verdict; no context-only quote; for `none`, evidence array empty; rationale explains direction or abstention.
4. Audit semantically: correct referent, emotion relevance, E/T provenance, direct-vs-inferred direction, appropriate `none` and `uncertain`, and context leakage in rationales.
5. Report repeat-run verdict agreement, reference agreement on **the same comparable cases**, mechanical validity, E/T provenance and recall of defensible directional cases separately. Frozen decoding can make three repetitions identical without establishing semantic correctness. A fixed codebook is a design hypothesis, not evidence of achieved accuracy.

**Controlled comparison:** Use the existing original-prompt and v0.1 results as **two frozen historical conditions**; run **only v0.2** with the same 12 targets, two models, segment+review context, and three repeats. The v0.2 prompt/schema form part of this third condition, so any difference is attributable to the **v0.2 package**, not uniquely to this codebook wording. Do not treat historically disputed human labels as unquestioned ground truth.

**Pending researcher approval:** Fine boundaries of inviting (comfort vs inclusion) and safe (physical threat vs perceived social safety); role of T-derived verdicts in the overall pilot score; and how to resolve same-emotion contradictions when no direction dominates.

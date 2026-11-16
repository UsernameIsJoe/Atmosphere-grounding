# Stage 1A pilot codebook v0.3 — Calm, Inviting, Safe

**Status:** Concise experimental revision for researcher review; not validated.  
**Scope:** Place-attributed atmosphere in a target review segment. The full review is background for resolving references, not additional segment evidence.  
**Versioning:** v0.1 and the untested longer v0.2 remain archived unchanged.

## What counts as evidence

An emotion word is **not required**. A statement counts when its described experience, interaction, or environmental condition provides a **specific, defensible connection** to the atmosphere of that place. Neither broad sentiment ("great," "awful") nor an object alone establishes an emotion. Preserve the subject, place, negation, cause, and time of any claim. A visitor's interaction with people at the place can be evidence; it is not automatically a general property of everyone there. Surroundings count when the statement links them to the experience of the place.

**E — reported experience:** The segment directly characterizes the visitor's felt atmosphere, or reports an experienced place-related condition/impact (e.g., "The traffic noise made the courtyard stressful"). This does not require a category adjective.

**T — descriptive inference:** The segment describes a place-related condition from which an atmospheric direction is inferred, without reporting that experience (e.g., "The play area opens directly onto fast-moving traffic"). A T inference needs a defensible, *specific* connection, not a generic stereotype; retain it as T, never relabel it E. E and T are different evidence origins, **not confidence levels**. Overall pilot verdicts may consider either; downstream E-only views must exclude T-only claims.

## Verdict definitions (independent for each emotion)

| Verdict | Meaning |
|---|---|
| `supports` | There is a defensible target-grounded positive relationship to this emotion. |
| `opposes` | There is a defensible target-grounded negative relationship to this emotion. |
| `none` | Neither direction is defensible **after considering both**, including indirect evidence. This is absent *evidence*, not an assertion that the place lacks the emotion. |
| `uncertain` | Available wording/context does not allow a reliable choice among supports, opposes, and none. Explain the unresolved ambiguity; do not use as a synonym for weak evidence. |

There is **no mixed** verdict and no numerical confidence. For conflicting claims about the *same emotion*, choose a direction if defensible after qualification; otherwise `uncertain`. Distinct emotions can receive distinct directions. Do not convert negated negatives automatically into positives (e.g., "not unsafe" is not necessarily "safe").

## Three emotion definitions

### CALM

**Construct:** A visitor-experienced atmosphere of tranquility, low agitation, ease, quiet, or relaxation. **Opposition:** Reported disturbance, intrusive noise, chaotic activity, or place-induced stress/tension.

**Includes:** Peaceful experience or intrusive noise that actually affects the visit, even without saying "calm."  
**Boundary:** Being empty, busy, green, musical, or near a road does not *by itself* establish calm or its opposition. Stress from an unrelated personal event does not describe the place.

### INVITING

**Construct:** A visitor-experienced sense of welcome, ease of approach/entry, inclusion, hospitality, or comfort in entering or staying. **Opposition:** Reported hostility, exclusion, discouragement, or barriers that actually make the place feel inaccessible or unwelcoming.

**Includes:** Visitor-facing hospitality, exclusion, or an entrance/barrier described as encouraging or discouraging use.  
**Boundary:** Fun, fame, good exhibits, beauty, and a single physical feature do not *by themselves* establish welcome. A staff interaction may describe that visit without proving a universal site character.

### SAFE

**Construct:** A visitor-experienced sense of security/protection from physical harm or credible personal threat, including clearly reported exposure to danger. **Opposition:** Reported unsafe conditions, threats, hazards, or credible anxiety about personal safety tied to the place.

**Includes:** Reported reassurance, credible threats, or a described exposure pathway to danger (e.g., children could enter fast traffic directly from an unfenced play area).  
**Boundary:** Darkness, dirt, security cameras, noise, or maintenance concerns do not *by themselves* prove safety or danger. Hostility alone more directly bears on inviting unless it conveys threat.

## Small calibration set (illustrative, not test labels)

| Target phrase | Emotion → verdict | Track / reason |
|---|---|---|
| "I could finally relax in the quiet garden." | Calm → supports | E; explicitly experienced ease |
| "The construction noise made it impossible to relax." | Calm → opposes | E; described disruption |
| "The garden was almost empty." | Calm → none | Descriptive cue alone; no established effect |
| "We felt welcome when the host greeted us." | Inviting → supports | E; situated hospitality |
| "They turned us away and made us feel unwelcome." | Inviting → opposes | E; direct exclusion |
| "The museum had five exhibits." | Inviting → none | No welcome/exclusion relation |
| "The path felt secure even after dark." | Safe → supports | E; reported security |
| "The unfenced play area leads straight into moving traffic." | Safe → opposes | T; specific physical danger path |
| "There were cameras near the entrance." | Safe → none | T candidate; no defensible direction alone |
| "One section felt protected, but another was threatening; I cannot tell which experience characterized the place overall." | Safe → uncertain | E; unresolved opposing reports |

**Calibration principle:** Do not treat examples as keyword rules. The decisive distinction is a defensible *place–emotion relationship*, not presence of the exact emotion word.

---
*Research protocol and output formatting belong in the accompanying prompt, not this codebook. The earlier twelve contested segments remain development/audit cases, not independent ground truth.*

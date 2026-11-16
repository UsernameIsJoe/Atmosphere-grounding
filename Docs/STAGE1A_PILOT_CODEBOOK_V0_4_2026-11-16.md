# Stage 1A pilot codebook v0.4 — Calm, Inviting, Safe

**Status:** Researcher-directed boundary revision; DRAFT, not tested or production-approved.  
**Scope:** Place-attributed experience/atmosphere in original visitor reviews. The target segment supplies evidence; surrounding text may clarify referents but cannot silently supply additional target evidence.  
**Changes from v0.3:** Broader **Inviting** (including place appeal/desirability), broader **Safe** (including credible social intimidation), and operational distinction between `none` and `uncertain`. The emotional dimensions remain independent. Do not use the nine recent audit cases as model prompt examples for a future independent benchmark.

## Evidence basis

An emotion adjective is **not required**. Count a reported experience, site-directed assessment, interpersonal interaction during the visit, or spatial/sensory/social condition when it has a **defensible relationship to the particular atmospheric dimension**. A mention of an object or unrelated life event alone is insufficient.

- **E — reported experience or site assessment:** The review directly says how the visitor experienced or appraised the place, an encountered interaction, or a condition that affected the visit. It need not use an explicit emotion word. A direct appraisal of the *place* can be E for inviting.
- **T — inference from a reported condition:** A place-related condition supports a plausible atmospheric relationship **not explicitly experienced or appraised** in the text. Record the specific connection and retain `T` provenance; never silently promote T to E.
- E and T indicate **how a claim is grounded**, not model confidence. A T-only claim is not an E observation. Keep the streams inspectable separately.

**Attribution:** Place/surroundings and visitor-facing people or services may be relevant; unrelated event stress, an exhibit's standalone quality, and a visitor's unrelated personal circumstances do not automatically characterize the place. Preserve spatial and temporal scope. Context may resolve references but not become unquoted target evidence.

## Emotion constructs and boundaries

### CALM

**Construct:** A visitor-experienced atmosphere of tranquility, low agitation, ease, quiet, or relaxation. **Opposition:** Reported disturbance, intrusive noise, chaotic activity, or place-induced stress/tension.

- Support: quiet/relaxing experience or a specifically reported sense of ease.
- Oppose: intrusive sound, disruption, agitation, or tension attributable to the site or its surroundings.
- **Boundary:** An empty garden, music, a busy event, or a nearby street is not inherently calm or stressful. A delay in someone's personal plans is not necessarily evidence about the atmosphere.

### INVITING

**Construct:** A visitor-experienced **appeal or desirability of approaching, entering, visiting, or staying at a place**, including welcome, inclusion, hospitality, comfort, and the perceived attractiveness of the place itself. **Opposition:** Site-directed deterrence or aversion, hostility, exclusion, discomfort, or a barrier that discourages visiting or staying.

- Support: direct positive appraisal of the place as attractive, appealing, engaging, or worth visiting; comfort in staying; welcoming interactions.
- Oppose: a site-directed recommendation against visiting **for a stated visitor purpose**, discouraging entry/use, interpersonal rejection, or an experienced barrier.
- **Boundary:** Place-level desirability can count even when hospitality is not described. **Fame alone** does not prove desirability; explicitly positive appraisal of the place may. An exhibit's quality, ticket price, or private activity outcome does not automatically characterize the place's inviting atmosphere unless the statement links it to visiting/staying. A staff interaction is evidence for that encounter, not proof of universal treatment.

### SAFE

**Construct:** A visitor-experienced sense of security and protection from harm **or credible interpersonal threat/intimidation**, plus directly reported exposure to a specific danger. **Opposition:** Reported hazards, threats, intimidation, or place-related fear that reasonably undermines a visitor's sense of security.

- Support: reported sense of safety, protective experience, or place-specific reassurance.
- Oppose: credible physical hazards, direct threats, or intimidating encounters such as aggressive confrontation directed toward visitors—even if no physical attack is reported.
- **Boundary:** Minor rudeness does not automatically imply unsafe; distinguish social unwelcomeness from intimidation or fear. Darkness, grime, nearby roads, security cameras and noise alone do not establish safety direction without a specific, relevant consequence or credible concern. Felt safety is not an independently verified crime-risk estimate.

## Directional verdicts (for each emotion separately)

| Verdict | Operational definition |
|---|---|
| `supports` | Target contains defensible positive directional evidence, directly reported (E) or specifically inferred (T). |
| `opposes` | Target contains defensible negative directional evidence, directly reported (E) or specifically inferred (T). |
| `none` | **No materially relevant atmospheric relationship** remains after scope, context and both directions are considered. Includes clearly unrelated statements and ordinary features without a specific atmospheric connection. `None` says nothing about the actual place. |
| `uncertain` | A **materially relevant** claim or condition exists, but referent, direction, or whether its consequence warrants a directional verdict cannot reliably be resolved even with legitimate context. Identify the competing readings; do not use for merely missing an emotion adjective. |

**Clarification:** Do not turn every potentially relevant descriptive word into `uncertain`. The unresolved cue must be particular and consequential enough that competing atmospheric readings are credible. An ordinary neutral feature without a specific relationship is `none`. A concrete condition that plausibly changes how a person can enter/use a place, but whose visitor-facing consequence remains genuinely undecidable, can be `uncertain`. Distinguish this from a specific danger pathway, which can justify directional T evidence. Do not invent a confidence percentage.

**Contradictions:** When there is evidence in both directions for the **same** emotion, preserve both and select a dominant defensible direction only if supported; otherwise `uncertain`. No `mixed` output. Negating a negative phrase is not automatically evidence of a positive condition.

## Calibration illustrations — authored, not evaluation labels

| Target statement | Emotion | Verdict | Basis |
|---|---|---|---|
| “I relaxed under the trees while the courtyard stayed quiet.” | Calm | Supports | E: lived tranquility |
| “The nearby machinery drowned out conversations and made us tense.” | Calm | Opposes | E: experienced disruption |
| “The plaza contains twelve benches.” | Calm | None | Feature only; no calm relationship |
| “The building itself is spectacular and worth visiting.” | Inviting | Supports | E: direct positive site desirability |
| “The gallery entrance was so frustrating that we decided to leave.” | Inviting | Opposes | E: experienced deterrence |
| “The sculpture has three floors.” | Inviting | None | Structure alone |
| “I felt protected crossing the pedestrian bridge.” | Safe | Supports | E: felt protection |
| “The exposed path drops into fast traffic with no separation.” | Safe | Opposes | T: specified exposure pathway |
| “The guard loudly threatened to throw visitors out.” | Safe | Opposes | E: reported intimidation |
| “A surveillance camera stood by the entrance.” | Safe | None | Object presence alone |
| “The only restroom was unlit; the reviewer says nothing about whether anyone could use it or felt threatened.” | Safe | Uncertain | Specific use-related cue, but plausible danger/insufficiency remains unresolved; adjudicate in context |

**Examples are calibration illustrations, not gold labels.** The existing K/U dispute cases are development material and must not be used to manufacture an independent evaluation set.

**Workflow note:** Pre-interpretation segmentation/context routing and JSON formatting are defined **outside** this codebook. See the proposed [Stage 1A evidence-routing gate](STAGE1A_EVIDENCE_ROUTING_GATE_DRAFT_2026-11-16.md). The previous original, v0.1 and v0.3 experimental outputs remain frozen; v0.4 has not been tested.

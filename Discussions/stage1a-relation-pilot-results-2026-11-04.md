# Stage 1A — M1 Aspect–Opinion Relation Pilot: Executed Results (2026-11-04)

## Run audit

- [Run #1, 41861381724](https://github.com/UsernameIsJoe/Atmosphere-grounding/actions/runs/41861381724), commit `6d2c576fefd05c7663a0aedd6663ecb0b64207fe`: GitHub marks both jobs **success**, BUT generative `aos_t5` output was **zero parsed relationships on all 20 reviews and all eight controls** because the code expected JSON and the model actually emitted colon-delimited text. Dependency extractor completed normally. **This is a successful CI run but an invalid generative extraction comparison.**
- [Corrected run #5, 41861834607](https://github.com/UsernameIsJoe/Atmosphere-grounding/actions/runs/41861834607), commit `c28e32dc6327b2616748870fa52b62ace6fe339f`: overall GitHub conclusion **success**; valid artifacts for both methods. Generator prompt and parser adjusted for colon-delimited output. Artifact `13341405142` = generative AOS; artifact `13339209138` = dependency baseline. Both contain `manifest.json`, `summary.json`, `review_cases.jsonl`, and `controlled_cases.json`.
- Both runs used 20 selected real reviews from 19 locations and 8 prespecified controlled sentences. No NLI and no independent human reference labels were used. Do **not** refer to CI success as scientific validation.

## Corrected run: observed output

| Metric | Dependency-rule baseline | Generative AOS |
|---|---:|---:|
| Relations emitted on 20 real reviews | 67 | 15 |
| Source-exact grounded relations | 67 | 12 |
| Flagged ungrounded (source phrase absent/repeated) | 0 | 3 |
| Reviews with no emitted relation | 1 | 5 |
| Parse statuses | 20 `dependency_rules` | 15 `parsed_colon_triplets`, 5 `unparsed_generation` |
| Timed extraction | ~0.30 seconds | ~17.36 seconds |

These are measures of quantity, literal phrase matchability, and runtime **not** precision or recall. The baseline's token spans are always literally source-exact by construction; the AOS model can normalize, invent, or misattach opinion words.

## Concrete interpretation (from corrected artifacts)

**More promising relation links:**
- Controlled **“The gardens are beautiful, but the traffic is deafening.”** The dependency method extracts `gardens → beautiful` and `traffic → deafening`; AOS extracts only `traffic → deafening`. Both can find at least some evidence, but AOS misses one obvious positive relation.
- Controlled **“The benches are comfortable but the lighting is harsh.”** Dependency extracts both `benches → comfortable` and `lighting → harsh`; AOS extracts only `lighting → harsh`.
- Real row 53: Dependency links `staff → friendly` and `staff → helpful`; AOS generates the same relations but **both are rejected by strict exact-match grounding** because `staff` occurs multiple times, illustrating false negatives from repeated-string ambiguity.
- Real row 26: AOS links `bike parking → adequate` with **negative** polarity, but the original review is “cool park, 0 adequate bike parking. absurd for hsq”. This reveals need to inspect how negation/quantity is represented, not trust a single bare `adequate` opinion.
- Real row 139: AOS extracts `colage → gooooooooood`; dependency outputs no pairs. This is general praise, not established emotion-attributed evidence.

**Semantically problematic examples:**
- Controlled **“The park is not quiet; sirens make the atmosphere stressful.”** Dependency produces `park → quiet` (negation scope is lost) and `sirens → make` (non-opinion verb). AOS produces `sirens → stressful`, but misses the explicit `not quiet` relation.
- Controlled **“Broken glass covers the sidewalk and makes the path dangerous.”** Dependency emits `glass → Broken` and `glass → covers`, missing `path → dangerous`. AOS emits no relation.
- Controlled **“I felt happy because I found my lost phone.”** Both extract target `phone` with positive/negative descriptors, though the happy emotion is reviewer-specific and does **not** establish an inviting/happy place. AOS emits `phone → happy`, illustrating *misattribution*.
- Real row 55: AOS generates `park:darker:positive, park:cosy:positive`, but no relations pass parsing/source checks; `cosy` paraphrases the source's `cozy`. Literal source grounding can reject plausible normalized tokens without deciding if relation was valid.
- Controlled **“Relaxing, quiet, and serene.”** Neither method returns a relation. Nominal relation extraction is insufficient for adjective-only atmosphere observations.

## Methodological findings

1. **No winner has been established.** Dependency extraction is broad and cheap but includes irrelevant grammatical attachments; AOS is selective and does not cover many obvious pairs. AOS may produce semantically reasonable normalized tokens whose source spans are not exact. All 67 dependency links have source offsets by construction, which is not evidence of valid opinion relations.
2. **The generative model is functioning on corrected run #5** (15 relations, 12 exact-span verified), unlike run #1 where the output parser discarded every generation.
3. **Existing relation representation remains inadequate** for negation, implicit adjective-only atmosphere, speaker-vs-location attribution, and multiple simultaneous contrasting claims. These are exactly the difficulties relevant to downstream emotional reasoning.
4. **Do not feed extracted triples directly to emotion NLI as established facts.** Both methods need source-grounded context and separate provenance of raw text versus model inference. Keep full review accessible; do not discard unextracted sentences.
5. Prior 50-review ABSA extraction findings remain valid; this M1 test is an additional *relation extraction* probe, not an ABSA+NLI integration or a human-rated accuracy experiment.

## Recommended next methodological step

Rather than expanding the number of reviews or optimizing span count, test a **relation record with negation, target attribution, and explicit opinion/source offsets**, retaining unmatched adjective/sensory statements. Use the eight existing controlled sentences for regression, but add contrastive minimal pairs such as `The park is quiet` / `The park is not quiet`, `The staff are friendly` / `I was happy after finding my phone`, `trees beautiful` and `traffic deafening` in isolation and together.

Only then pilot **M2 aspect-conditioned NLI** on a small fixed review set and hypotheses, comparing direct whole-review NLI, source-grounded clause evidence, and structured relation-augmented evidence. Include **swapped target–opinion controls**, source-only controls, and polarity removed to test whether relationship structure genuinely contributes signal.

**No quantitative claim of atmosphere validity is supported at this stage.**

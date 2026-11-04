# Stage 1A ABSA — original real-review sentence-input experiment, executed results

**Date:** 2026-11-04. [Successful GitHub Actions run 41908682135](https://github.com/UsernameIsJoe/Atmosphere-grounding/actions/runs/41908682135); commit `a0d070999f2fbdf4206dfc068dd84cc081f8590a`. All three model jobs and paired-comparison job passed. Artifact `13361622882` contains `comparison.json` and `review_comparison.jsonl`; three additional model artifacts contain full sentence-level predictions.

## Research question

Does applying the existing AOS T5 and GTS-BERT joint aspect–opinion extractors to **verbatim original review sentences**, rather than entire reviews, improve recovery of previously listed target relations? This is a correction of model-input protocol, **not a new model search, not an independently validated evaluation, and not a test of relevance/NLI**.

20 original source reviews, **56 source-aligned sentences**, and **29 partial, assistant-authored real-review target pairs**. No generated or synthetic test review content. Source offsets were checked in CI. Models were fed verbatim segmented sentences and outputs reassembled to original reviews.

## Measured results

| Method | Whole-review reference targets recovered | Sentence-level | Change |
|---|---:|---:|---:|
| AOS T5 | 5/29 (17.2%) | 8/29 (27.6%) | +3 |
| GTS-BERT joint ASTE | 9/29 (31.0%) | 14/29 (48.3%) | +5 |
| spaCy dependency rules | 22/29 (75.9%) | 22/29 (75.9%) | 0 |

Additional sentence-run diagnostics:

| Method | Source-grounded relations emitted | Sentences with at least one relation | Input truncations/skips | Unparsed generation |
|---|---:|---:|---:|---:|
| AOS T5 | 31 | 36/56 | 0 | **20/56** |
| GTS-BERT | 27 | 22/56 | 0 | 0 |
| Dependency rules | 67 | 38/56 | 0 | 0 |

**Important interpretation:** GTS improved with sentence-level input under otherwise analogous checkpoint/decoder/128 maximum length. For AOS the experimental settings also changed maximum generated output length (previous full review max 180, sentence experiment 250), so its +3 cannot be attributed uniquely to segmentation. We checked only 29 **incomplete** target pairs, not exhaustive relation correctness: neither reported fractions nor emitted relation counts are independent precision, recall or F1. AOS's 20 unparsed outputs signal additional prompt/output-parsing or model-format fragility; these require source and raw-generation inspection before treating them as genuine no-relationship cases.

## Review examples from output

- Row 53: dependency recovers `staff→friendly` and `staff→helpful`; GTS `staff→friendly`; AOS none credited.
- Row 55: GTS recovers `park→cozy`, dependency `park→charming`, illustrating complementary evidence rather than universal winners.
- Row 113: GTS `place→Inspiring`, dependency `location→great`.
- Row 26: AOS and GTS recover lexical `bike parking→adequate`, but review says **`0 adequate bike parking`**. Lexical recovery alone **does not validate quantity/negation interpretation**.
- Row 57: strict target spans can overlook semantically equivalent longer targets; keep the original phrase when adjudicating.

## Conclusion and bounded next check

**Our earlier whole-review input protocol understated recoverable target relationships for both pretrained joint extractors.** This establishes a preprocessing-sensitive result, not that the models now achieve acceptable semantic reliability. The dependency rule baseline's recovery is broader, but its many emitted links still lack exhaustive correctness judgments.

Before further model comparisons, inspect AOS's **20 unparsed sentence generations** and score *source-level correct/incorrect opinion attachment*, quantity/negation, and polarity on the real reviews. Do not introduce synthetic content, change the three-stage architecture, or call these published checkpoint accuracy numbers.

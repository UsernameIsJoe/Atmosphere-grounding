# Stage 1A — M2 structured ABSA evidence + NLI: executed results and validity audit

**Date:** November 4, 2026  
**Status:** Completed 20-review/3-emotion/8-condition experiment; descriptive findings only. **No independent reference labels, so no measured accuracy or superiority.**

## Provenance

- [Successful GitHub Actions run 41869251112](https://github.com/UsernameIsJoe/Atmosphere-grounding/actions/runs/41869251112); head commit `4c5ea483489b8a1eb0a89dd6f1b5d8045543c6f0`; completed all test, artifact retrieval, NLI inference, and integrity checks.
- Artifact `13344501532`, name `stage1a-m2-structured-nli`; contains `summary.json` and `review_cases.jsonl`.
- 20 exactly matched real reviews from the prior M1 AOS/dependency and 50-review DeBERTa/SetFit artifacts; three hypotheses (`calm`, `inviting`, `safe`), 8 conditions, **480 three-way BART-large-MNLI inferences**, inference elapsed **417.24 seconds** (not CI setup).
- NLI hypothesis strings are in the artifact. Original text is included for all conditions. No NLI model or vocabulary selection or human-rated emotion ground truth.

## Changed NLI predicted class vs original full-review input (number of 20 reviews)

| Condition | Calm | Inviting | Safe |
|---|---:|---:|---:|
| Duplicate original text (control) | 5 | 5 | 3 |
| AOS triplet relations | 4 | **7** | 1 |
| Dependency grammar relations | 4 | 3 | 1 |
| DeBERTa aspect names | 5 | 5 | 1 |
| SetFit aspect names | 3 | 1 | 3 |
| AOS swapped | 4 | 7 | 1 |
| Dependency swapped | 4 | 2 | 1 |

The duplicate condition is highly influential even though it adds no new facts; **class-changing rates are not evidence of improvement**. The original and annotation-augmented premises are not length matched. This is a coarse intervention in an NLI model trained on ordinary sentence pairs rather than structured metadata.

## Internal signal magnitudes (mean absolute change in entailment softmax vs full input)

| Condition | Calm | Inviting | Safe |
|---|---:|---:|---:|
| Duplicate | 0.1781 | 0.2688 | 0.1160 |
| AOS relations | 0.1072 | 0.1824 | 0.0497 |
| Dependency relations | 0.1077 | 0.1380 | 0.0699 |
| DeBERTa names | 0.1332 | 0.2015 | 0.0713 |
| SetFit names | 0.0517 | 0.1082 | 0.0855 |

These are descriptive probability perturbations, **not confidence calibration or emotional intensity**.

## Critical structural-ablation audit

- AOS produced **at most one uniquely source-grounded relation on every one of the 20 reviews**: **0/20** eligible for an aspect–opinion swap. Consequently AOS versus `aos_t5_swapped` has **identical input and identical output throughout**. **No AOS structure-dependence test actually occurred.** In eight reviews AOS condition was also exactly identical to original full review because no relations passed the grounding filter.
- Dependency relations: **14/20 reviews**, or 42 review–emotion decisions, were eligible for swapping. The swapped relation text differed in all 42, yet the predicted NLI class changed for just **3/42** review–emotion decisions (2 calm, 1 inviting, 0 safe). Mean absolute entailment difference **0.0315** on eligible pairs. This is weak evidence that the *formatting intervention* is sensitive to the correct target–opinion pairing, not evidence that structure is useless: the dependency pairs themselves contain grammatical and semantic errors.
- The no-swap/unmodified AOS controls **must not** be counted as evidence for robustness to incorrect pairing. Need synthetic multi-relation contrastive examples to test this mechanism.

## Grounded case examples from review_cases.jsonl

- **Row 2**: “This is a very nice park ... [busy weekends] ... Not too many trees for shade ...”. Full inviting prediction neutral, AOS/dependency/DeBERTa annotations switch to entailment; AOS contains `park → nice`. Dependency includes malformed `trees → remember`. A change could be greater focus on `nice`, not a validated atmospheric judgment.
- **Row 21**: “Great place for a walk or run along the river. Or simply to sit down and enjoy the sun.” Full inviting neutral; AOS, dependency and DeBERTa switch to entailment; AOS oddly links `river → Great`. This might represent implicit attraction or a source relation error; unresolved.
- **Row 26**: “cool park, **0 adequate bike parking. absurd for hsq**”. Full inviting neutral; AOS switches to entailment via `bike parking → adequate`, which omits the critical negation/quantity **0** and carries obvious meaning-distortion risk. This is the clearest reason NOT to interpret added support as improvement.
- **Row 38**: “I Love this park, they have sprinklers ... Great place to bring your little kid's”. Full inviting neutral; AOS and DeBERTa switch to entailment; AOS links `sprinklers → Love` (questionable attachment).
- **Row 74**: report of secluded parks and police patrol; AOS `parks → best` makes inviting neutral → entailment, but no validated atmospheric judgment.
- **Row 113**: “Inspiring place with great location. We could get a chance to walk in the buildings ... Hope to see again.” Full inviting entailment; AOS addition changes it to neutral, whereas dependency and prior ABSA annotations retain entailment. The integration can suppress possibly relevant evidence.
- **Row 181**: “Best happening place ... Harvard ... everyone wanted to be”. Full inviting neutral; AOS switches to entailment based on `Harvard business school → Best`. Could reflect generic enthusiasm instead of inviting atmosphere.
- **Row 53**: “beautiful and memorable exhibit ... staff ... friendly and helpful.” No AOS grounded pairs; full inviting entailment, duplicated review and dependency both neutral; evidence of formatting/pairing fragility.

All examples are real review data, not evidence of correctness. Source-verifiable aspect/opinion strings are **not** verified aspect–opinion semantic relationships.

## What was and was not learned

1. All four existing ABSA/extraction sources were compared **as annotation representations**, avoiding accidental AOS default selection. But DeBERTa/SetFit supply aspect names, while AOS/dependency supply opinion links; **not an apples-to-apples extractor quality comparison**.
2. Both annotation and simple repetition perturb NLI substantially; no incremental benefit of actual structure has been identified.
3. Inviting remains particularly sensitive. Most AOS changes on inviting are neutral → support (six), but row 113 moves support → neutral; no inference of higher accuracy.
4. The **AOS swapped control was non-operative** on this sample, and dependency swap produced only 3/42 classification changes. This does not support claiming model use of correct relation binding.
5. **Missing crucial information:** negation, scope, attribution, contrast, adjective-only claims and actual perceived emotion evidence. The prompt labels extracted relations as “unverified interpretations”, but the NLI checkpoint may nevertheless treat them as premise evidence.
6. End-to-end effect on location-level aggregation, visual features and prediction has NOT been tested; the project structure is unchanged.

## Next experimental decision

**Do not scale M2 unchanged.** First design a smaller, source-grounded and logically controlled M2b study targeting the mechanism:

- **(i) fixed minimal pairs:** `park quiet / park not quiet`, `0 adequate parking / adequate parking`, environmental noise vs reviewer happiness, gardens beautiful and traffic deafening alone/together;
- **(ii) two+ independently valid aspect-opinion pairs per sample** to make swapping operative, explicitly report eligible counts and preserve source tokens;
- **(iii) separate genuine semantic relation changes from duplicate input, formatting/length and shuffled/irrelevant candidate controls**;
- **(iv) hold NLI checkpoint + target hypothesis unchanged** within each comparison, and measure directional logic consistency in synthetic examples rather than human-like interpretation of real unlabeled reviews;
- **(v) audit raw relation fidelity, especially negation and entity attribution, before treating extraction output as supporting evidence**.

More generally, reconsider whether pretrained generic NLI of *long augmented premises* is the right integration mechanism: true evidence decomposition might require separate per-claim entailment followed by conflict-preserving aggregation, not merely appending annotations to the review. Test that explicit design against the original full-review baseline.

**No ABSA model, vocabulary, output-class regime, or final 9-emotion model is locked.**

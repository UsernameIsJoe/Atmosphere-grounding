# Stage 1A — Expanded 60-Hypothesis Vocabulary Experiment Results (2026-11-03)

## Provenance and completion

- [Successful GitHub Actions run 41696683666](https://github.com/UsernameIsJoe/Atmosphere-grounding/actions/runs/41696683666), job 126128961712.
- Original run artifact: `stage1a-expanded-vocabulary-ensemble`, artifact ID **13269858363**, contains `summary.json`, `review_cases.jsonl`, `registry_snapshot.json`.
- Run commit: `14b78b30b2c0a7395172e366f81005df77646651`.
- BART-large-MNLI, all **214 reviews from 43 location IDs**, 60 exploratory hypotheses (20 per emotion), **12,840 premise–hypothesis evaluations**.
- **NO independent human-rated ground truth** and no accuracy/precision/recall claims. Prior assistant-authored pilot labels were not used to score this experiment.
- Registry snapshot SHA-256: `bb70add500f25ce7415416b31cbbdf1910c95306bacb7b4c8ae70b84306d6da1`.

## Experiment design

Six preliminary near-paraphrase **core** formulations per emotion, ten **related but non-equivalent facets**, four **opposition/control** statements. Facets and controls are saved per review but are **not** averaged into core ensemble scores. For each core set: compare equal-probability mean, classwise median, classwise trimmed mean (normalized), and label majority (ties abstain). Compare removing each core candidate and recomputing mean. The full hypothesis/probability/candidate details remain auditable in the artifact.

## Whole-corpus descriptive results

| Metric | Calm | Inviting | Safe |
|---|---:|---:|---:|
| All **6** core labels unanimous | 76.17% (163/214) | 50.93% (109/214) | 74.30% (159/214) |
| Mean within-core max-min support probability | 0.1522 | 0.3790 | 0.1775 |
| Mean normalized model-output entropy | 0.2822 | 0.3387 | 0.2802 |
| Mean ensemble label unaffected by dropping **any one** core formulation | 95.79% (205/214) | 93.93% (201/214) | 94.86% (203/214) |
| Mean, median, trimmed mean, majority labels all agree | 98.13% (210/214) | 94.86% (203/214) | 95.79% (205/214) |

Unanimity with six hypotheses **cannot be directly interpreted as an improvement or deterioration** versus prior three-hypothesis unanimity: the family sizes and wording differ, and unanimity becomes more demanding with more candidates. The more comparable recurring observation is that inviting has much greater variability than calm/safe.

### Ensemble output class distributions across 214 reviews

| Emotion | Mean S | Mean C | Mean U | Majority abstentions |
|---|---:|---:|---:|---:|
| Calm | 48 | 38 | 128 | 3 |
| Inviting | 59 | 22 | 133 | 9 |
| Safe | 15 | 33 | 166 | 9 |

High agreement is compatible with predominantly neutral predictions. Stability is **not measured correctness**.

## Salient failure and semantic-shift cases

The biggest discrepancy recurring in `inviting` is between `inv_core_03` ("Visitors experience this place as inviting") and other near-paraphrases, especially `inv_core_02` ("The atmosphere of this place is inviting"). Their **pairwise label agreement is 56.07%** and mean absolute support probability difference is **0.3369**. Candidate `inv_core_03` returns Support for **122/214** reviews vs just **38/214** for `inv_core_02`, without independently established reason to treat either as more correct.

- **Row 181**: rambling praise ("Best happening place really close to Harvard Square ... where everyone wanted to be"). `inv_core_03` support **0.924**, while other core hypotheses return only 0.088–0.283 support (all U). May be respondent/visitor wording effect, or actual semantic distinction; not proven.
- **Row 139**: "This colage is very gooooooooood". `inv_core_03` support **0.851**, whereas others give 0.040–0.270 (all U). **Potential spurious location-enthusiasm-to-inviting inference**, but absent ground truth this is a case to examine, not an established error.
- **Row 113**: "Inspiring place with great location ... chance to walk in the buildings ... Hope to see again." `inv_core_01` S=0.839, `inv_core_02` S=0.084, `inv_core_03` S=0.887, and the six-core mean chooses U. **An ensemble can erase real minority evidence or suppress false positives; cannot distinguish which without a better test.**
- **Row 55**: detailed park review describing a welcoming gateway and comforting ambience: all six core hypotheses agree S (support probability range ~0.848–0.964). Example where the ensemble is uniform for a content-rich relevant review.
- **Calm row 187**: describes reception as "kindly and informative" but nothing explicitly calm; `calm_core_03` S=0.699 while other 5 return U. Possible misleading inference from visitor framing.
- **Safe row 123**: "Cute little park. Ada accessible." `safe_core_01/02/04` support 0.788/0.879/0.764, but `safe_core_05` just 0.052; accessibility is not automatically proof of physical safety.

## Interpretations and caveats

1. **Distinct wording matters even among near-paraphrases.** Intriguingly visitor-experience phrasing shifts inviting predictions more than simple noun-phrase claims. Investigate premise framing and third-person inference rather than immediately discard outliers.
2. **Ensemble results are internally stable**, especially under leave-one-out and aggregation choice. But a neutral-dominant majority can explain stability; not evidence that an ensemble recognizes atmosphere correctly.
3. **No model comparison yet.** All statements were tested using the same pretrained BART-large-MNLI checkpoint; model-dependent patterns need replication.
4. **No ABSA comparison yet.** Stage 1A remains a broader method program: compare NLI checkpoints, alternative ABSA/aspect extraction, retrieval baselines and integrated context-preserving workflows. See [project map](project-research-map-and-workstreams-2026-11-03.md).
5. **Do not freeze hypothesis vocabulary**; stable IDs/semantic roles are provisional. Need strict counterexample screening to verify supposed synonymy; a high disagreement could reflect true semantic difference.
6. **Data limits:** 214 reviews cluster within 43 locations; uneven source quality, potential token truncation, and missing independent annotation. No confident evaluation of emotional truth, score calibration or visual associations.

## Next research recommendation

Run a focused **cross-checkpoint** experiment on this frozen-for-testing 60-candidate registry (BART versus alternate NLI variants, accounting for incompatible label spaces), plus a small contrastive/null-premise set to distinguish semantic drift from artifacts. Keep alternative ABSA model comparison as a separate planned next workstream; do not reclassify it as obsolete. Use the same review/location IDs and preserve all raw outputs. Only make vocabulary-selection decisions after seeing patterns across models and a more rigorous evidence-grounding check.

**Note:** This is a completed test record, not evidence of methodological validity.

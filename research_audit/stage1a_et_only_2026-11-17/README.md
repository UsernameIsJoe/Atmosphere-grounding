# Place-level E/T-only experiment — 2026-11-17

Completed on Runpod, not GitHub Actions. Original codebook v0.5 emotion judgments are frozen. Only E/T attribution was retested under the v0.6 place-level codebook. Historical outputs remain unchanged.

## Results

| Model | E | T | Valid labels | Valid E/T calls |
|---|---:|---:|---:|---:|
| Qwen3.8 27B | 28 | 68 | 96/96 | 60/60 |
| Gemma4 31B BF16 | 37 | 58 | 95/96 | 59/60 |

Agreement: **86/95 (90.5%)**, with **9 claim disagreements across 6 segments**. All disagreements are Qwen T versus Gemma E. Gemma's unavailable label is a mistyped claim ID at N07__05; its raw response says T, but is excluded from strict comparisons. No silent corrections or retries were applied.

Original fixed pool: 88 claims, 87 comparable, 78 agreeing (89.7%). Completion extension: 8 claims, all agreeing. The shared pool is the deduplicated union of valid emotion outputs, keyed by segment, emotion, direction and exact quote. Quote variants remain separate claims. Both models receive every claim in the same pool, with original track and source identity hidden.

Against each model's own original valid claims, Qwen changes 48/74 E/T labels and Gemma changes 11/29. These changes reflect the revised definition and are not accuracy gains. Original Qwen tracks were 61 E / 13 T; original Gemma tracks were 25 E / 4 T.

## Completion of yesterday's emotion extraction

The missing/invalid extractions were attempted under unchanged v0.5 emotion instructions, separately from E/T classification. Qwen: 3/3 new valid, now 71/71 valid segments. Gemma: all 33 planned calls completed, 29 valid, now 67/71 valid segments. Four Gemma cases retain mechanical errors: T02__01 category order; N06__04, N06__05 and N07__01 nonexact target quotations. Every source segment has now been attempted by both models. Existing valid emotion cases were not rerun.

## Interpretation and limits

This is a consistency and attribution diagnostic, not an independent accuracy benchmark. The codebook was informed by examples already discussed in this cohort, including the Chelsea example; do not treat this cohort as unseen evaluation data. No human gold E/T labels are claimed. The prior assistant emotion audit was not used as a correctness reference.

The remaining disagreements concern whether interiors, patios, environment and design describe the place itself, and whether reviewers' stated feelings during a wedding count as the overall place experience. Qwen is more restrictive about assigning E in this run. Review DISAGREEMENTS.md before adjudicating these boundaries or selecting a model. No post-hoc prompt change or semantic retry was used.

## Reproduction and artifacts

Frozen source: fddbec48bd4efa151f75dbc4c1d4cbee991f5a9d. Prepared implementation: e1d446bc97640b5d14b86c528012dfb3494baa5b. Run scripts/stage1a_et_only_20261117.py prepare before leasing GPU, then run on Runpod. Model digests and input/instruction hashes are in manifest.json; runtime identity is in runtime_environment.json. Temperature 0, seed 42, context 8192, maximum output 2048, think false. No gate, cascade, emotion redetection for existing valid outputs, or 30-minute cutoff.

All 120 E/T calls and 36 completion calls finished, with process exit 0 and ALL_PLANNED_REQUESTS_FINISHED in experiment.log. See raw emotion_completion.jsonl, raw et_predictions.jsonl, fixed_claim_pool.json, summary.json, claim_comparison.csv and DISAGREEMENTS.md. Cleanup is recorded separately after verified archival.

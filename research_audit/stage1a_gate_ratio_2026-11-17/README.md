# Gate relevance-proportion experiment — 2026-11-17

Completed on Runpod with Qwen3:8B, the existing gate model: **36/36 valid review outputs**, covering **178 source-exact coarse clause units**. One relevance-labeling pass; all thresholds computed offline. No emotion extraction, no E/T calls, no model comparisons or semantic retries. The accepted v0.4 gate remains unchanged.

## Outcome: do not adopt this labeling protocol or a threshold

| Rule | KEEP | REJECT | Wedding T06 |
|---|---:|---:|---|
| Archived v0.4 gate | 23 | 13 | KEEP |
| New labels: any relevant unit | 31 | 5 | KEEP |
| Relevant-unit proportion >=25% | 30 | 6 | KEEP |
| Relevant-unit proportion >=50% | 29 | 7 | KEEP |
| Relevant-unit proportion >=75% | 21 | 15 | KEEP |

T06 wedding: **10 relevant / 11 substantive units = 90.9%**; one additional unit is boilerplate. Word-weighted proportion is **95.5%**. All three thresholds keep it under either measure. The labels count staff helpfulness, event management, drinks and guest enjoyment as place relevance, often reasoning from a particular event to the venue's general capability. This contradicts the intended individual-encounter boundary despite that boundary being stated in the labeling prompt. K01 elopement is labeled 100% relevant and also passes every threshold.

The important limitation is **relevance-labeling drift**, not arithmetic. The new any-relevant control keeps 31 reviews versus the original gate's 23. The 25/50/75% rules reject respectively 1/2/10 reviews relative to that control; they cannot be interpreted as pure threshold modifications to the original frozen gate. The labeling prompt and structured task differ from the original whole-review verdict task. The historical baseline did not record a model-weight digest, so exact old/new weight identity is also unverified; the installed digest and runtime are archived here.

## Previously adjudicated cases

| Case | Recorded researcher judgment | Old gate | New ratio | 25% | 50% | 75% |
|---|---|---|---:|---|---|---|
| T06 | REJECT | KEEP | 10/11 (90.9%) | KEEP | KEEP | KEEP |
| K01 | REJECT | KEEP | 8/8 (100.0%) | KEEP | KEEP | KEEP |
| T08 | REJECT | REJECT | 4/4 (100.0%) | KEEP | KEEP | KEEP |
| T11 | REJECT | REJECT | 5/6 (83.3%) | KEEP | KEEP | KEEP |
| N05 | REJECT | REJECT | 4/6 (66.7%) | KEEP | KEEP | REJECT |
| N12 | REJECT | REJECT | 2/3 (66.7%) | KEEP | KEEP | REJECT |
| N07 | KEEP | KEEP | 8/8 (100.0%) | KEEP | KEEP | KEEP |

These are selected documented judgments from the [v0.4 regression audit](../stage1a_review_gate_v04_regression_qwen8b_2026-11-16/README.md), not a complete gold set. The 75% rule rejects N05/N12 but still keeps T06/K01/T08/T11, and newly rejects seven previously kept reviews: K06, U04, U06, N04, N06, N10, N11. Those new rejections require audit; they are not automatically classified as errors. No overall accuracy, precision, recall or best threshold is claimed.

Word-weighted KEEP counts are 29 / 28 / 20 at 25 / 50 / 75%. This length sensitivity does not resolve the wedding or elopement problem. The clause-count measure uses coarse deterministic units, not a complete grammatical parse.

## Interpretation

The proportion idea remains a hypothesis, but counting permissively labeled units does not protect against incidental or event-bound relevance. A future test should improve or independently audit the context-sensitive relevance labels before tuning a threshold. Do not automatically strengthen the threshold or replace the accepted gate on this evidence. No additional GPU run was initiated.

## Artifacts and reproduction

- Frozen experiment: [protocol](../../Docs/STAGE1A_GATE_RATIO_V0_5_EXPERIMENT_2026-11-17.md), [prompt](../../Docs/STAGE1A_GATE_RATIO_PROMPT_V0_5_2026-11-17.txt), [runner](../../scripts/stage1a_gate_ratio_20261117.py).
- [inputs.jsonl](inputs.jsonl): all 36 original reviews, source offsets, unit texts and word counts.
- [predictions.jsonl](predictions.jsonl): every raw and parsed response, per-unit reason, duration, validation and model digest.
- [unit_labels.csv](unit_labels.csv): audit table, including the wedding's 12 units.
- [review_comparison.json](review_comparison.json), [summary.json](summary.json): all denominator counts, ratios, threshold decisions and flips.
- [manifest.json](manifest.json), [model_identity.json](model_identity.json), [runtime_environment.json](runtime_environment.json), [experiment.log](experiment.log), [experiment.exit](experiment.exit): provenance and completion evidence.

The process finished with exit 0 and ALL_36_REVIEWS_ATTEMPTED. SHA256SUMS.txt covers the experiment artifacts; the later cleanup receipt is recorded separately after archival and termination. The pod uses an ephemeral disk and no persistent mounts.

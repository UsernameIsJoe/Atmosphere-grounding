# Gemma: does softening provide a useful signal?

**Offline addendum, November 23, 2026. No new model inference.** The preceding evaluation established distribution shape, repeatability and sensitivity. Those observations did not establish that the probabilities identify dependable judgments or improve supervision. This addendum addresses that missing question as far as the existing reference data permits.

**Assessment: no robust added usefulness is established yet.** There are reproducible case-specific preferences, including lower confidence on K01's attribution failure. Against archived provisional reference fields, however, error detection is weak and any benefit over fixed smoothing is small, metric-dependent and sensitive to one case. This is insufficient to adopt the scores as validated confidence or training targets.

## Reference provenance limits the claim

The v0.5 runner's explicit `AUDIT` has only **two calm judgments**: K01 = none and U06 = supports. The other ten entries in the saved twelve-case reference are inherited/merged older labels. In particular, K03 and U01 are `opposes` in those merged fields but `none` in the older conservative target reference. The codebook and adjudications evolved. Neither twelve-case reference is independent current gold.

We retain separate checks for the two explicit judgments, all twelve merged provisional fields, and the older conservative reference (eleven determinate calm labels, excluding its uncertain U06). Results change with that reference choice. **Do not interpret the twelve-case numbers below as a validated calibration benchmark.** Source snapshots/paths are recorded in [reference provenance](gemma_reference_provenance.json); the [full numeric record](gemma_signal_check.json) preserves all reference variants.

## Actual comparison with a simple control

For each temperature, average the four captured mapping distributions per review; do not count mappings or repeats as independent examples. Compare those twelve model-specific vectors with fixed uniform label smoothing around the same model verdicts, choosing its single smoothing level to match their mean winning probability. This control asks whether case-specific confidence and alternative-state allocation help beyond simply making every label equally softer. It does not use the references to fit the smoothing level.

NLL and four-class Brier sum are reference-based probability losses (lower is better). Error AUROC uses `1 - winning probability` to rank reference disagreements (0.5 = chance ranking, 1 = perfect). All numbers use the **merged provisional twelve-case reference**; it disagrees with Gemma on K01, K03 and U01.

| T | Model NLL | Fixed-smoothing NLL | Model Brier | Fixed-smoothing Brier | Error-detection AUROC |
|---|---:|---:|---:|---:|---:|
| 1 | 3.501 | 2.014 | 0.497 | 0.499 | 0.519 |
| 2 | 1.824 | 1.402 | 0.476 | 0.493 | 0.556 |
| 4 | 1.012 | 1.011 | 0.432 | 0.463 | 0.556 |
| 6 | 0.815 | 0.868 | 0.404 | 0.429 | 0.556 |
| 8 | 0.782 | 0.837 | 0.397 | 0.417 | 0.556 |

At T=4, model-specific probabilities have essentially the same NLL as fixed smoothing (**1.012 versus 1.011**), a modest Brier improvement (**0.432 versus 0.463**), and weak error-ranking AUROC (**0.556**). T=6/8 improve both losses on this reference, but are not selected as optimal or calibrated.

**Case-influence check:** we calculated every leave-one-case-out comparison. Removing K01 reverses the model's Brier advantage at T=4: **0.363 versus 0.344**, and its NLL becomes worse: **0.957 versus 0.797**. The comparison rematches the control's mean softness on the retained eleven cases without using labels. The same direction of reversal occurs at T=6/8. The apparent benefit therefore depends heavily on the known K01 failure; it is not robust evidence of general added utility.

## What signal is visible in individual cases?

T=4 chosen-state confidence, averaged across mappings with the full mapping range:

| Case | Model verdict | Mean confidence | Mapping range |
|---|---|---:|---:|
| K01 | opposition_only | 73.97% | 68.20–82.40% |
| U03 | opposition_only | 98.68% | 98.26–99.33% |
| U06 | support_only | 92.15% | 88.39–94.82% |
| K04 | support_only | 94.86% | 92.48–97.03% |

K01 is the explicitly recorded personal-stress attribution failure. U03 is the explicit intrusive-traffic-noise example, aligned with the archived opposition reference. They share the same hard opposition verdict, yet the scores distinguish them strongly; this is a plausible coarse preference signal beyond the hard label. U06 is the other explicitly current calm adjudication (support). K04 remains highly confident despite the prior audit's low-crowding grounding concern; that concern is not a newly assigned error label here.

Fine confidence ordering is less robust: **6/25** pairs of reviews with the same winning state reverse their relative confidence under a common change of letter mapping. These are pairs, not independent new reviews. All six reversals concern high-confidence neither cases and have paired differences below one percentage point. Broad distinctions may survive while fine decimal differences do not.

## Practical interpretation

- **What is present:** stable model preferences, some coarse case distinctions and nonuniform alternative-state information beyond hard labels or one fixed smoothing level.
- **What is not established:** reliable identification of correct judgments, a calibrated confidence scale or better downstream image training. A transformed distribution is not validated merely because its values spread out.
- **Current use:** preserve the logits and candidate softened vectors as research artifacts. Their proper next comparison is against hard targets and fixed smoothing on codebook-aligned independent annotations or downstream held-out training; the present checks do not justify adopting them as reliable supervision.

The two explicit audit judgments are too few to validate an error detector. The wider provisional reference is useful for exploratory sensitivity checks, but its inherited conflicts materially change the evaluation. No model-generated judgments were introduced as ground truth, and no temperature or threshold was selected using these results.

Reproduce with [evaluate_gemma_signal.py](evaluate_gemma_signal.py), the original probability-repeat raw data, and the saved [reference snapshot](gemma_reference_provenance.json). The [case-level CSV](gemma_signal_cases.csv) exposes every target, reference source and temperature vector.

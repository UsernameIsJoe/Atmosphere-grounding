# Stage 1A — NLI Checkpoint Screening Results (2026-11-03)

## Provenance

[GitHub Actions run 41719297004](https://github.com/UsernameIsJoe/Atmosphere-grounding/actions/runs/41719297004), commit `fb1b47bdf43a53f1125507fe19dcd146c9fc88c0` or later workflow source in run; **both jobs succeeded**.
- DeBERTa job ID `126207508680`; artifact `13273584378` (`stage1a-nli-screen-deberta`).
- ModernBERT job ID `126207508944`; artifact `13272283200` (`stage1a-nli-screen-modernbert`).
- Matched BART comparison from [full 214-review vocabulary run 41696683666](https://github.com/UsernameIsJoe/Atmosphere-grounding/actions/runs/41696683666), artifact `13269858363`. BART's 50 rows were **filtered to precisely the same row indices and identical review text** as both screened checkpoints. No rerun or differing-sample comparison.
- All same registry hash `bb70add500f25ce7415416b31cbbdf1910c95306bacb7b4c8ae70b84306d6da1`; 50 reviews spanning all 43 locations; 60 hypotheses per review; 3,000 predictions per screened model; one previously registered sample (representative per location + difficult BART cases).
- **Zero human-rated ground truth**; all metrics are internal behavior and cross-model agreement, NOT accuracy.

## Native labels / interpretation

BART (`facebook/bart-large-mnli`) is a three-way **entailment / neutral / contradiction** NLI model. The screened `MoritzLaurer/deberta-v3-large-zeroshot-v2.0` and `MoritzLaurer/ModernBERT-large-zeroshot-v2.0` both actually exposed a **two-class** output: **entailment / not_entailment**. We must NOT say not_entailment = neutral or contradiction. For *binary support detection comparison ONLY*, BART entailment `S` is mapped to support and BART C/U combined into not-support, with the two checkpoints' native entailment versus not_entailment labels. This mapping discards BART's distinction between contradiction and insufficient evidence.

Raw softmax magnitudes across checkpoint families are not directly calibrated or interchangeable.

## Within-model descriptive results, matched 50 reviews

### All six core hypotheses agree (unanimity)

| Emotion | BART (three-way) | DeBERTa (binary) | ModernBERT (binary) |
|---|---:|---:|---:|
| Calm | 76% | 74% | 82% |
| Inviting | 48% | 54% | 62% |
| Safe | 74% | 84% | 96% |

Binary-class unanimity is potentially easier; these cannot be regarded as like-for-like quality rankings.

### Mean max-minus-min entailment probability within six core hypotheses

| Emotion | BART | DeBERTa | ModernBERT |
|---|---:|---:|---:|
| Calm | 0.173 | 0.240 | 0.146 |
| Inviting | 0.389 | 0.408 | 0.366 |
| Safe | 0.184 | 0.201 | 0.076 |

A lower spread is internal stability, not truth. DeBERTa and ModernBERT probability scales differ from BART.

### Core-hypothesis support-prediction counts (6 × 50 = 300 per emotion)

| Emotion | BART entailment predictions | DeBERTa entailment predictions | ModernBERT entailment predictions |
|---|---:|---:|---:|
| Calm | 67/300 | 85/300 | 63/300 |
| Inviting | 95/300 | 128/300 | 135/300 |
| Safe | 18/300 | 15/300 | 10/300 |

**Interpretive caution:** ModernBERT's 96% unanimity for safety occurs with only 10 support predictions out of 300; high stability can reflect predicting not_entailment for most hypotheses, rather than accurately recognizing safety.

### Cross-model binary-support agreement across 300 core hypothesis × review pairs per emotion

| Emotion | BART vs DeBERTa | BART vs ModernBERT | DeBERTa vs ModernBERT | All 3 same |
|---|---:|---:|---:|---:|
| Calm | 274/300 = 91.3% | 278/300 = 92.7% | 272/300 = 90.7% | 262/300 = 87.3% |
| Inviting | 251/300 = 83.7% | 242/300 = 80.7% | 253/300 = 84.3% | 223/300 = 74.3% |
| Safe | 281/300 = 93.7% | 284/300 = 94.7% | 287/300 = 95.7% | 276/300 = 92.0% |

These include potentially substantial negative-class prevalence. Agreement does NOT prove correct classification, and cannot distinguish BART contradiction vs neutral.

### Mean-probability core ensemble (binary support/not-support) on 50 reviews

For BART, take original three-class mean ensemble S label versus C/U; for binary checkpoints use mean entailment >= 0.5. (This is an exploratory comparison; different scoring normalization may change boundary behavior.)

| Emotion | BART/DeB agree | BART/Modern agree | All 3 agree |
|---|---:|---:|---:|
| Calm | 48/50 | 48/50 | 47/50 |
| Inviting | 42/50 | 38/50 | **35/50** |
| Safe | 48/50 | 47/50 | 47/50 |

## Runtime and input truncation

- DeBERTa: `2388.6 s` = 39.81 min (CPU forward/testing loop only, excludes setup/model download).
- ModernBERT: `1314.9 s` = 21.92 min; ~45% shorter measured inference time than DeBERTa in these Jobs. This comparison includes only the code's timed inference phase, not installation or downloads; runner variability is unmeasured.
- Both: **zero potentially truncated review–hypothesis pairs** using the experiment's length check and configured 512-token cap.
- Both jobs passed 50 reviews/43 places/60 candidates validation and uploaded native probability vectors.

## Examples where models disagree

- **Inviting row 139:** "This colage is very gooooooooood". Core mean ensemble = BART **not support**, DeBERTa **not support**, ModernBERT **support**. Is broad enthusiasm being interpreted as atmosphere? Cannot resolve without independent evidence evaluation.
- **Inviting row 113:** "Inspiring place with great location ... chance to walk in the buildings ... Hope to see again." BART **not support**; both DeBERTa and ModernBERT **support**. Could reflect meaningful indirect invitation or different inferential thresholds.
- **Inviting row 97:** Starts "I was a little disappointed to see that it no longer resembles a lot of the pictures online..." BART and ModernBERT **support**, DeBERTa **not support**. Inspect full original review before interpreting meaning.
- **Safety row 123:** "Cute little park. Ada accessible." BART **support**, both new checkpoints **not support**. Accessibility may or may not imply physical safety; a good controlled counterexample target.
- **Safety row 74:** "Cambridge has some of the best little parks nestled away. Ckean, well kept, and well patrolled by police..." BART and DeBERTa **support**; ModernBERT **not support**. Neither label is established as truth.
- **Calm row 187:** Review of a helpful reception without calm atmosphere content; BART and ModernBERT **not support**, DeBERTa **support**.

## Scientific interpretation and next decision

1. **All three checkpoints show inviting as the least stable / most model-dependent pilot emotion.** This conclusion is supported by within-model wording variation and matched cross-model disagreements.
2. ModernBERT is **faster** and less variable on this corpus than DeBERTa, but **no model can be declared more accurate** without independent ground truth or a stronger controlled evidence test.
3. Full 214 × 60 runs may be informative, but the sample already covers all 43 locations and enough challenging cases to reveal methodological issues. Prefer **controlled minimal pairs, negation and attribution tests** and optionally a larger full-corpus replication if the cost is justified.
4. **Critical unresolved three-way information:** binary models cannot distinguish contradicting vs missing evidence. To preserve Stage 1A's support/contradiction/unknown objective, retain three-way NLI or explicitly add/test a contradiction-aware second stage. Do not select binary solely for speed/stability.
5. The vocabulary is still provisional. Existing outlier cases could be semantic shifts, model bias, or valid rare evidence; do not automatically discard candidates.
6. Keep **ABSA model comparison** and context-preserving ABSA+NLI integration on the planned research roadmap.

## Source artifacts

Use full review-level output in run artifacts `13273584378` and `13272283200`, and matched BART output artifact `13269858363`. Each records exact IDs/hypotheses and model probability outputs.

# Stage 1A — Hypothesis Robustness Results (November 3, 2026)

## Execution and provenance

All three Actions runs succeeded but are **successive executions of the SAME hypothesis-robustness method**, not independent model comparisons:

| Run | Commit | Sample | Artifact |
|---|---|---|---|
| [41671900247](https://github.com/UsernameIsJoe/Atmosphere-grounding/actions/runs/41671900247) | `c366207` | original nonconsecutive 30 reviews / 7 places | `13248198225` |
| [41673176348](https://github.com/UsernameIsJoe/Atmosphere-grounding/actions/runs/41673176348) | `c8dab227` | **first 30 consecutive reviews / 6 places**, NOT original 30 | `13248719097` |
| [41673219260](https://github.com/UsernameIsJoe/Atmosphere-grounding/actions/runs/41673219260) | `c46f1648` | **all 214 reviews / 43 places** | `13253915204` |

**Authoritative run for full-corpus findings is the third run.** Its saved `historical_30_review_subset` exactly reproduces run 1's summary. Run 2 changed sampling inadvertently when the script switched to consecutive review indices, and must not be treated as a replicate of original 30.

## Experiment

Same pretrained `facebook/bart-large-mnli`; review text as full premise; **3 paraphrases + 3 distinct supporting facets + 1 loosely opposing statement per emotion**; 3 pilot emotions (`calm`, `inviting`, `safe`). 214 × 3 × 7 = **4,494 review–hypothesis pairs**. Model outputs original probabilities for support/contradiction/neutral plus argmax label, normalized entropy, and supporting-hypothesis ranges. No human-rated ground truth, accuracy, correctness, or calibrated confidence evaluated.

## All-214 results

| Metric | Calm | Inviting | Safe |
|---|---:|---:|---:|
| Paraphrase unanimity (all 3 predicted labels same) | 71.0% (152/214) | 57.0% (122/214) | 79.9% (171/214) |
| Mean range of entailment probabilities across paraphrases | 0.167 | 0.306 | 0.118 |
| Mean normalized predictive entropy | 0.263 | 0.297 | 0.235 |
| At least one paraphrase + opposing claim both predict support | 0/214 | 0/214 | 0/214 |

### Original diagnostic 30: direct controlled comparison

| Metric | Calm | Inviting | Safe |
|---|---:|---:|---:|
| Paraphrase unanimity | 70.0% | 70.0% | 76.7% |
| Mean support-probability range | 0.169 | 0.210 | 0.085 |
| Mean normalized entropy | 0.254 | 0.269 | 0.227 |

**Interpretation:** On the broader corpus, *inviting* is the least robust to phrasing. This should motivate a semantic review of how “inviting,” “welcoming,” and “encourages visitors to enter/stay” overlap, not selection of a winner by confidence.

### Example high-sensitivity cases (from full run output)

- **Inviting / row 55**, “A charming and cozy park ... A Torii ... welcomes you in ...”: support probabilities across three paraphrases **0.974, 0.457, 0.018**; labels S/U/U. Different implied constructs (welcoming vs desire to stay) and text length may matter. The discrepancy itself is observed, not its cause.
- **Inviting / row 81**, “I loke this cozy and quiet playground. It has nice shades ...”: **0.924, 0.703, 0.019**; S/S/U.
- **Calm / row 10**, “Nice place to unwind, jog, or dogwalk. There are quite a few seating areas.”: **0.954, 0.075, 0.241**; S/U/U.
- **Safe / row 86**, “Always great safe place ... to meet friends ...”: **0.917, 0.882, 0.028**; S/S/U.

These examples show genuine hypothesis sensitivity within a single checkpoint. Model semantics and review content, not verified real-world truth, were compared.

## Counts of individual predictions across paraphrases

Each category has 214 × 3 = 642 paraphrase predictions:

| Emotion | S | C | U |
|---|---:|---:|---:|
| Calm | 113 | 112 | 417 |
| Inviting | 116 | 77 | 449 |
| Safe | 28 | 131 | 483 |

Interpretation caution: High safe agreement can reflect frequent neutral predictions rather than actual competence. Facet predictions probe distinct qualities, not logically equivalent paraphrases.

## Methodological caveats

1. **No human-rated ground truth** and no validation claims. Unanimity is self-consistency, not accuracy.
2. The three paraphrases were authored by the assistant and **are not strict semantic equivalents**; “encourages visitors to enter and spend time” adds behavioral specificity beyond “welcoming.” Thus disagreement can be legitimately driven by *meaning* rather than mere wording, especially for inviting.
3. **Opposing hypotheses are not formal negations**; zero dual-entailment flags is weak evidence of logical coherence and can be inflated by conservative/neutral predictions. It must not be described as verified logical correctness.
4. The entropy is a distribution diagnostic, **not** calibrated correctness likelihood. A low-entropy incorrect prediction is possible.
5. Full review inference uses tokenizer truncation to 512 tokens; review length ranges 3–382 whitespace words; longer text can be cropped depending on token count.
6. Reviews are clustered within 43 places and are unevenly distributed; neither 214 records nor 43 places guarantees representative geographic/functional coverage.
7. Variation across facets is evidence that different attributes get different predictions, not an independent measure of *interpretability* or proof that NLI attended to an evidentiary span.

## Interpretation and next research decision

Hypothesis formulation merits additional investigation before choosing an NLI checkpoint. Tighten semantically equivalent paraphrase sets, distinguish **semantic decomposition** (different attributes, intended to vary) from **robustness** (same meaning, intended to agree), and include constructed minimal-pair reviews with explicit negation/mixed/off-topic emotions. Next compare NLI checkpoints on the **same** hypotheses; keep class-space differences (binary entailment vs three-way NLI) explicit. ABSA model tests and integration remain subsequent steps.

This is an executed result record. Per-example full review text, probabilities, facets and opposition outputs are retained in the GitHub Actions artifact of run [41673219260](https://github.com/UsernameIsJoe/Atmosphere-grounding/actions/runs/41673219260).

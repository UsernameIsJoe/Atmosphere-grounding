# Stage 1A M2 — Structured Evidence + NLI: Controlled Representation Pilot

**Date:** 2026-11-04. **Status:** Implemented and scheduled in GitHub Actions; **no run results verified**.

## Why AOS was introduced, and why it must not replace previous ABSA candidates

The original DeBERTa end-to-end ABSA and SetFitABSA checkpoints output **aspect target terms with polarities**, but not reliably linked **opinion expressions**. The subsequent AOS triplet checkpoint was a deliberate *task-level probe*: can pretrained generative extraction supply aspect→opinion links? The dependency baseline served as a transparent grammar-based comparator.

**We did not measure evidence that AOS is more accurate than DeBERTa or SetFit.** In the 20-review pilot, AOS produced 15 triples (12 uniquely source-matched) and the dependency approach 67 literal source-grounded grammatical links, many semantically dubious; both struggled with negation, attribution and implicit atmospheric claims. Source matching is not relation validity. No final extractor chosen.

To avoid accidental model lock-in, **M2 explicitly includes all four available sources** on their matched real review subset:
- `aos_t5`: pretrained AOS triplets (verified aspect/opinion strings only)
- `dependency`: grammatical noun→description pairing (source token offsets)
- `deberta_absa`: previously tested pretrained end-to-end aspect+polarity
- `setfit_absa`: previously tested restaurant-domain ABSA pipeline

The last two do **not** have opinion links in their existing artifact; their M2 condition is only an aspect-highlight context control, **not a comparable full relation structure**. Do not interpret differences as a fair extractor accuracy ranking. The full original review remains included in **every** input condition, including cases with zero annotations.

## Primary research question

**Does providing source-verified structured candidates change NLI behavior beyond directly providing the original review, or are observed changes explained by repetition/prompt perturbation?**

This is an experimental mechanism/probe, **not a test of which model is more accurate about atmospheric emotion**.

## Method

- Script: [`scripts/stage1a_m2_structured_nli.py`](../scripts/stage1a_m2_structured_nli.py).
- Workflow: [`.github/workflows/stage1a-m2-structured-nli.yml`](../.github/workflows/stage1a-m2-structured-nli.yml).
- **Source artifacts downloaded at runtime** from completed Actions run **41861834607** (AOS + dependency) and **41728835398** (DeBERTa ABSA + SetFitABSA). This reuses earlier extraction outputs, not new training/model runs.
- **20 exact matched real reviews / 19 locations**, three pilot emotions `calm`, `inviting`, `safe`. Use one fixed, representative direct hypothesis per emotion and one **3-way BART-large-MNLI** checkpoint across all conditions; these hypotheses are provisional, not a selected vocabulary.
- **8 conditions** × 20 reviews × 3 emotions = **480 NLI evaluations**:
  1. `full` original review.
  2. `duplicate` original review repeated as a perturbation control.
  3. `aos_t5` full review + exact-source-checked aspect/opinion candidate lines.
  4. `dependency` full review + source-offset-checked grammatical aspect/opinion candidate lines.
  5. `deberta_absa` full review + DeBERTa aspect-target highlighting (**no opinion link**).
  6. `setfit_absa` full review + SetFit aspect-target highlighting (**no opinion link**).
  7. `aos_t5_swapped` full review + intentionally rotated opinion pairing for those reviews with >=2 grounded AOS relations.
  8. `dependency_swapped` same adversarial rotation for dependency relationships with >=2 grounded relations.
- Swapped controls are flagged **ineligible when fewer than 2 grounded relations exist**; an unchanged swapped input should not be taken as non-sensitivity. Do not pool eligible/ineligible cases when interpreting effect size.
- The original text and full provenance are retained in `review_cases.jsonl`, alongside the exact constructed premise for each condition, all three NLI probabilities, labels, and source-annotation counts. The stored outputs support later audits of changed classifications and ungrounded annotation leaks.

## Evaluation and interpretation

- Compare **within each emotion**: change in NLI prediction label, absolute entailment-probability difference from original, neutral/support/contradiction distributions, plus change relative to duplicate and eligible swapped controls.
- Compare all four extraction representations **as different types of annotation** rather than claiming like-for-like model quality. AOS and dependency supply links; original DeBERTa and SetFit supply aspect names.
- An input that changes model output is not necessarily improved or more accurate. Greater confidence or variation is not validity; swapped-pair sensitivity reveals model dependence, not correct attribution.
- Source-exact matching does not prove a meaningful opinion–aspect relationship. Both baseline and AOS are error-prone, particularly for negation, opinion scope, and observer attribution.
- **Known limitation:** duplicate is not token-length-matched to each annotation, and preexisting AOS representation is sparse. This initial pilot **does not** resolve inferential correctness or fully test multi-claim controls; controlled contrastive examples and independent evidence-span assessment should follow.
- Core explicit research goal remains **additional useful location-attributed evidence**, beyond simple extracted aspect counts, in preparation for Stage 2 visual learning.

## Go/no-go after run

1. Ensure all 480 NLI evaluations completed and review IDs/text match across archived extractor runs.
2. Evaluate whether any relation-grounded condition differs from full review **more meaningfully than duplicate/context controls**, particularly where the review includes opposing environmental observations.
3. Inspect cases with swapped pairings and flag wrong/incoherent output; do not rank methods by label-change count alone.
4. If annotation signals seem meaningful, design a smaller **controlled logical minimal-pair experiment** focusing on negation, attribution and contradictory opinions. If outputs merely change arbitrarily, improve evidence records or extraction rather than scaling.

**Status note:** prior 30-review hard-filtered ABSA→NLI experiment already happened; this experiment is not that pipeline repeated.

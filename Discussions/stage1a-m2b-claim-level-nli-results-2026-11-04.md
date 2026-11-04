# Stage 1A — M2b controlled claim-level NLI: executed results

**Date:** 2026-11-04. **Status:** GitHub Actions experiment completed; descriptive logic tests only, no human-rated or real-review accuracy.

## Provenance

- [Successful run 41872973325](https://github.com/UsernameIsJoe/Atmosphere-grounding/actions/runs/41872973325), head commit `07f8b75892b230c881f690192f1bd4fdc7d2a069`.
- Artifact `13345377072`, `stage1a-m2b-claim-nli`: `controlled_cases.json`, `cases.jsonl`, `summary.json`.
- **18 authored cases × 3 emotional hypotheses = 54 case-emotion records, 345 BART-large-MNLI inferences**; timed inference **120.57 seconds**. Seven cases have two independently described claims and support actual swapped-pair ablations.
- This test uses **manually constructed, source-verifiable aspect/opinion records**. It does *not* evaluate the DeBERTa, SetFit, AOS or dependency extractors, or real text evidence.

## Whole-sample descriptive comparisons

Counts are reviews/cases changing NLI argmax class relative to direct original input; these **are not improvements or accuracy**.

| Metric (count) | Calm | Inviting | Safe |
|---|---:|---:|---:|
| Duplicate review versus full (18 eligible) | **9/18** | **7/18** | **6/18** |
| Structured reexpression versus full (18) | 4/18 | 6/18 | 4/18 |
| Mean over independent claim predictions versus full (18) | 3/18 | 5/18 | 3/18 |
| Swapped opinion relations versus correct structure (7 eligible) | **3/7** | **3/7** | **3/7** |
| Claimed support and contradiction co-occur in per-claim labels (18) | 2/18 | 2/18 | 3/18 |

Simple repetition is **at least as destabilizing** as structured reexpression. Better label stability, confidence or more entailments is not demonstrated accuracy; neither method should be called superior.

## Direct contrast pairs (case names and BART outputs)

| Contrast and emotion | Full-review labels | Structured labels | Claim-mean labels |
|---|---|---|---|
| `quiet_yes` / `quiet_no` — calm | entailment / contradiction | entailment / contradiction | entailment / contradiction |
| `noise_yes` / `noise_no` — calm | contradiction / entailment | contradiction / neutral | contradiction / entailment |
| `safe_yes` / `safe_no` — safe | entailment / contradiction | entailment / contradiction | entailment / contradiction |
| `welcome_yes` / `welcome_no` — inviting | entailment / contradiction | entailment / contradiction | entailment / contradiction |
| `parking_zero` / `parking_adequate` — inviting | contradiction / neutral | neutral / neutral | contradiction / neutral |
| `garden_traffic` / `garden_traffic_quiet` — calm | contradiction / entailment | contradiction / entailment | contradiction / neutral |

The first three core polarity/negation contrasts illustrate that original BART can already recognize **some elementary logical reversals** when directly stated; this test is not proof that ABSA is required. Some changes are less intuitive, such as converting “traffic is not deafening” into a structured form that predicts neutral rather than calm entailment.

## Important individual examples from case-level output

- `garden_traffic` — **calm**: independent clauses are neutral for “gardens are beautiful” and contradictory for “traffic is deafening”; full NLI and claim-mean both predict contradiction. So meaningful opposing **positive versus negative aspect sentiment** does **not** imply opposing calm evidence. This is a key distinction for ABSA integration.
- `mixed_welcome` — **inviting**: independently predicted labels are support and contradiction, but full review predicts support while arithmetic claim mean predicts contradiction. The difference illustrates why per-claim evidence should be stored before aggregation, though neither label has been independently validated.
- `mixed_safe` — **safe**: individual “path feels safe” and “stairs are dangerous” claims predict support and contradiction; full review predicts support and mean predicts contradiction. Both may genuinely coexist; losing the opposition hides information.
- `benches_lighting` — **safe**: per-claim labels are support/contradiction for “benches comfortable” and “lighting harsh”. **Potential spurious atmosphere inference**: a positive judgment about benches is not sufficient evidence of physical safety. Treat evidence flags as model predictions, not facts.
- `mixed_welcome` — **calm** also produces both support and contradiction across claims, even though a welcoming entrance and unsafe path do not entail calmness straightforwardly. The same error concern applies.
- `negative_review_with_park` — **inviting** produces both support and contradiction across “park beautiful” and “sirens loud”; their relation to inviting is not guaranteed.
- `benches_lighting` — **calm**: structured reexpression classifies as support while both original and swapped relation form classify as contradiction, showing susceptibility to unnatural paraphrase/word-order effects.
- `parking_zero`: original inviting label contradiction, despite no logical necessity that poor bike parking disproves inviting atmosphere; structured reexpression changes it to neutral. This is not an independent correctness adjudication.

## Absent / limited information

- Claim-level decomposition **preserves distinct model outputs** and can signal conflicting predictions, but does **not validate that the flags correspond to actual logical evidence**.
- All seven two-claim cases had operative swapped relations: 9 of 21 eligible case-emotion predictions changed; this demonstrates a **model input sensitivity effect**, not correctness of ABSA relation binding.
- The duplicate and rephrasing controls are not token-length matched and vary pragmatics and syntax. A generic NLI checkpoint is not optimized for synthetic structured relations.
- Evidence extraction is idealized: authored aspect/opinion spans bypass domain transfer, missed observations, speaker attribution, and negation errors measured in M1.
- The general cross-emotion hypotheses have uncertain semantics; broad inference can confuse environmental qualities with abstract atmosphere evidence.

## Recommendations / next scientific gate

1. **Do not use simple mean probability or max/any-support flags as final emotion scores.** They can hide true opposition or amplify spurious class outputs.
2. Next test should focus on **aspect-to-emotion relevance and evidence attribution**, not just whether adding structure changes labels. Distinguish direct atmospheric claims, related environmental observations, reviewer-specific affect and irrelevant/off-topic details with source spans.
3. Add *explicit negative/near-miss controls* where an apparently favorable attribute does **not** logically establish a chosen emotion: comfortable benches versus physical safety, good bike parking versus inviting, welcoming entrance versus calm.
4. Investigate clause-specific hypotheses (or relevance gating followed by NLI) and multi-claim aggregation with opposition retained. Compare to direct BART rather than taking any-support as correctness. Keep NLI checkpoint/vocabulary frozen per experimental block, and test multiple checkpoints only after the task has been defined.
5. After controlled relevance tests, return to **real reviews with actual ABSA/AOS/SetFit/DeBERTa extracted records**, evaluate source fidelity and failure cases, not just idealized author-authored relations.
6. Preserve Stage 1B visual feature extraction and Stage 2 location-level association as independent parallel priorities; don't indefinitely expand text-only Stage 1A.

**Bottom line:** A source-grounded claim structure is useful for keeping separate evidence, but current NLI predictions still need a validated notion of **which attributes really bear on which atmospheric emotion**. This is a hypothesis for subsequent experiments, not established task accuracy.

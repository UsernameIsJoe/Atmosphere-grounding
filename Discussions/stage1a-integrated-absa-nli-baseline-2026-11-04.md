# Stage 1A — Consolidated ABSA + NLI pipeline (implementation baseline)

**Date:** November 4, 2026  
**Status:** Integrated script and CI workflow committed. **Not yet validated as a successful end-to-end run.**

## Decision: stop adding isolated mini-experiments

M1/M2/M2b/M2c and previous NLI checkpoint and ABSA extraction screens established these practical conclusions:

1. We use **ABSA to locate and attach candidate aspects/opinions to the original text**, not to invent new sentences or assert extracted interpretations as facts.
2. We use **NLI on the original source sentences** for calm/inviting/safe pilot emotion hypotheses; run direct whole-review NLI as the comparator. ABSA is an evidence index, not a hard exclusion filter.
3. We **retain every original source sentence**, including passages with no extracted aspects, negated phrases, and source text missed by sentence splitting. The earlier M1/M2b pilots specifically showed errors due to loss of meaning, dropped evidence, rewording and misattribution.
4. **Relevance NLI is non-destructive metadata**, not a hard gate. M2c passed a small authored feasibility check but has not been validated on real review evidence.
5. Output is **verifiable evidence with offsets, ABSA tags, relevance/entailment/contradiction model outputs, conflict flags and direct-review comparator**. No synthetic accuracy percentage, unsupported confidence calibration or guessed emotion intensity.

## Locked engineering baseline (not model scientific winners)

- **DeBERTa ABSA** is the anchor for original text segmentation and extracted aspects because its prior artifact preserves source sentence offsets and polarity. **SetFitABSA** contributes additional source-aligned aspects. **AOS** contributes candidate relations only when both aspect and opinion have unambiguous exact source matches in the same original sentence. The thin evidence record never confuses an extracted triplet with the actual source text.
- **BART-large-MNLI** is held fixed as the already-tested 3-way NLI reference. This is a reproducible *engineering default*, not evidence that BART outperforms ModernBERT or DeBERTa NLI scientifically. The previous checkpoint comparison remains valid.
- **No default score aggregation** yet. Keep contradictory claims and unanswered claims separate instead of averaging away opposition. The downstream representation can be determined after auditing real outputs.
- **One 20-review matched real-data execution** reuses previously archived and frozen extractor outputs to avoid confounding an integration test with freshly retuned extractor checkpoints.

## Executable pipeline

- [`scripts/stage1a_integrated_absa_nli.py`](../scripts/stage1a_integrated_absa_nli.py)
- [`tests/test_stage1a_integrated_absa_nli.py`](../tests/test_stage1a_integrated_absa_nli.py)
- [`.github/workflows/stage1a-integrated-absa-nli.yml`](../.github/workflows/stage1a-integrated-absa-nli.yml)

Inputs: GitHub Actions run **41728835398** DeBERTa/SetFit artifacts and run **41861834607** corrected AOS artifact (same real reviews, intersected and identity checked).
Outputs: `reports/stage1a_integrated/review_evidence.jsonl` (each review × emotion with full original text, sentence offsets, source ABSA annotations, exact-source AOS relations, original sentence NLI, relevance NLI, no-hard-drop flags, full-review NLI, conflicts, extraction diagnostics); `summary.json` (coverage and conflict counts; no claimed accuracy).

## What counts as the next decision?

**Run it, inspect actual source-faithful evidence and errors, and decide whether the integrated architecture is serviceable.** Specifically verify that extraction does not silently lose text or negation, that ABSA annotations attach to intended source passages, and that per-claim support/contradiction signals are interpretable for calm/inviting/safe. If something fails, fix an *implementation defect*, not the broader task definition.

The pilot is not proof of calibrated emotion intensity. If usable, next step is to extend the **same pipeline** to the larger review set, retain provenance and aggregate at the location level (place_id), with independently reviewed evidence samples for validity. We should not keep creating a new architecture for each minor failure.

## Open scientific constraints stated honestly

- Model-produced aspect/opinion links and NLI labels are not human reference facts.
- Sentences, not finer discourse clauses, are the current provenance unit; some sentences contain multiple conflicting claims.
- The relevance prompt can be inaccurate or overinclusive; it never deletes evidence.
- Original review text can express speaker emotion or non-location experiences; no complete attribution resolution has been proven.
- Final nine emotions, selection among NLI checkpoints, emotion hypothesis vocabulary and location-level aggregation should not be reported as validated until tested.

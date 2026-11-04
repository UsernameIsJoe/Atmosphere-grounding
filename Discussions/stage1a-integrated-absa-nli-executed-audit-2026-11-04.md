# Stage 1A integrated ABSA–NLI: successful execution and architectural audit (2026-11-04)

## Verified run
[GitHub Actions run 41891532716](https://github.com/UsernameIsJoe/Atmosphere-grounding/actions/runs/41891532716), commit `f5a8f059164813abff799ecf7ef84394d68cf0f6`, completed **success**; all preflight tests, artifact retrieval, integrated evaluation, integrity assertions, and upload steps passed. Artifact `13354571825` (`stage1a-integrated-absa-nli`) contains `summary.json` and `review_evidence.jsonl`.

On the fixed 20 review subset, the integration emitted **60 review–emotion records** (three pilot emotions), **58 source sentences/passages** and **408 BART-large-MNLI calls**. No text was deliberately hard-filtered; an unsegmented hashtag fragment `#FreeRome` on row 123 was explicitly retained rather than dropped.

## ABSA extraction attached to original evidence

- **DeBERTa ABSA**: 29 source-verified aspect assignments.
- **SetFitABSA**: 88 source-verified aspect assignments.
- **AOS**: 11 source-verified, same-sentence aspect–opinion candidate relationships; 3 rejected as non-unique/invalid literal source grounding; 1 rejected as crossing sentence boundaries.
- **47/58 passages** contain at least one extracted DeBERTa/SetFit aspect; **11/58** contain none and were still evaluated. Eight of 20 reviews have at least one passage with no ABSA aspect annotation.
- These are **annotation counts**, not unique semantic aspects, coverage recall, extraction precision, or accurate aspect–opinion relations. Some example aspect polarity is questionable: `trees`, `shade` and `SPF` were labeled positive in a review explicitly saying there are **not too many trees for shade**, illustrating why the original sentence must remain authoritative.

## NLI outputs: descriptions, not accuracy

| Emotion | Whole review entail / neutral / contradict | Independent passage entail / neutral / contradict | Relevance-flagged passages |
|---|---|---|---|
| Calm | 2 / 15 / 3 | 1 / 49 / 8 | 6/58 |
| Inviting | 6 / 12 / 2 | 7 / 42 / 9 | 27/58 |
| Safe | 3 / 15 / 2 | 3 / 47 / 8 | 4/58 |

The `relevance_flag` is the **unvalidated 0.5 entailment softmax threshold** tested on authored M2c examples; it is only metadata. It must never be treated as a validated filter or ground truth. No final emotion intensity aggregation was built.

**Conflicting passage NLI predictions:** one review–emotion record (inviting) contains both entailment and contradiction; calm and safe have zero such records. Example: real review **row 97** includes a disappointment statement (NLI contradiction for inviting) and a positive statement about taking a break from urban bustle (NLI entailment for inviting). Whole-review NLI predicts inviting entailment. This is an interpretable demonstration of *preserving separate model output*, not proof the separate labels are correct.

## Crucial mechanism finding

**ABSA labels currently only annotate the passage records; the NLI premise is solely the unmodified original passage.** Therefore NLI outputs would be identical if ABSA annotations were withheld, given the same sentence boundaries.

This is a **successful joined data-processing pipeline**, but **not yet an experimentally demonstrated use of ABSA to improve NLI**. Do not claim the models are fully integrated in a way that changes inference quality or select a winning extractor.

## One direct next implementation milestone (no further branch proliferation)

Stay with the same integrated architecture and **make the ABSA evidence operational without rewriting claims**:
1. For each source passage, construct **aspect-linked evidence units with original text offsets**; include verbatim minimally scoped clauses where determinable, preserve negation and full-sentence fallback if the aspect–opinion relation is ambiguous.
2. **Run NLI on these source-faithful evidence units**, retaining the full-sentence NLI comparator *on the exact same reviews and hypotheses*. Do not promote AOS generated triples to independent facts; do not drop unmatched passages.
3. **Retain all separate model outputs**, and quantify the actual within-review effect of aspect-informed segmentation/selection: changed labels, contradictions, source coverage, exposure to negation/attribution errors. A non-operational annotation source should be reported as such.
4. Audit a few mismatches against original source, and report a directly answerable engineering decision. Do **not** launch a new unrelated hypothesis/model-screening experiment.

This change should occur in the current `scripts/stage1a_integrated_absa_nli.py` and its workflow/tests, not in another M2 variant.

## Scientific status

CI/integrity: **PASS**. Source-evidence retention: **PASS on current sample**. Actual ABSA impact on NLI: **NOT TESTED IN THIS IMPLEMENTATION**. Ground-truth emotional accuracy, calibration, passage relevance, aspect validity and generalizability: **NOT ESTABLISHED**.

The broader Stage 1A architecture remains research-in-progress, and the final nine emotions / intensity scoring are not locked.

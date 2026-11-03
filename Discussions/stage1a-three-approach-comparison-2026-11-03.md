# Stage 1A — Controlled Comparison of Three Text-Evidence Approaches

**Status:** Implemented as a GitHub Actions *experiment*, not an adopted research architecture. Pretrained comparison results must be inspected before any performance claims.  
**Date:** 2026-11-03  
**Code:** [scripts/stage1a_compare_abc.py](../scripts/stage1a_compare_abc.py)  
**Workflow:** [.github/workflows/stage1a-compare-abc.yml](../.github/workflows/stage1a-compare-abc.yml)

## Research question

Does decomposing reviews into finer emotional hypotheses or into aspect-focused evidence **improve identification of atmosphere-supporting, atmosphere-contradicting, and insufficient evidence** compared with a single, direct NLI hypothesis?

### Shared experiment conditions

- **Same 30 actual reviews from 7 places** used in the initial pilot; not synthetic fixtures.
- Pilot emotions: **calm, inviting, safe**, **not yet the final nine**.
- **Same provisional, single-analyst annotations**: S support; C contradict; U insufficient; X off-topic. X excluded from classification metrics, but cases kept for inspection.
- **Same NLI model:** `facebook/bart-large-mnli`, pretrained; no task-specific fine-tuning.
- Only review text as input; there is no image inference, cross-modal training, or score calibration here.
- Outputs: full case-level JSONL (review, extracted aspects, NLI label/probabilities per emotion) plus `summary.json`.

## Approach A — Direct NLI (control)

Original **whole review** as premise; **one broad emotion hypothesis** as hypothesis. Argmax of entailment / contradiction / neutral probabilities. Uses precisely the original pilot hypothesis phrases.

Example for calm: “This location has a peaceful, quiet, relaxing atmosphere.”

## Approach B — Multiple hypotheses NLI

Original **whole review** as premise; **three different narrower hypotheses** per emotion (e.g., peaceful, quiet, relaxing for calm). Score each with the *same* pretrained NLI model. Average class probabilities **equally** over the three hypotheses before argmax; do not cherry-pick the highest entailment claim.

This tests if decomposed, explicit attributes improve recognition of indirect evidence. It can also induce false contradictions where one attribute is absent; review individual hypotheses. Hypotheses are **exploratory**, not yet theory-ratified.

## Approach C — Pretrained ABSA extraction → NLI

1. Use a **real pretrained end-to-end aspect/sentiment token tagging model**: `yangheng/deberta-v3-base-end2end-absa`; its aspect-bearing spans have polarity metadata. Tokenizer: `yangheng/deberta-v3-base-absa-v1.1`. It is **not** the earlier keyword proxy.
2. Take the **original sentence containing each extracted aspect**, keeping its original wording and negation. Deduplicate sentences. The ABSA aspect name and polarity remain in the audit output, but **positive/negative aspect polarity is never treated as emotion support/contradiction**.
3. Pass each extracted context sentence as premise to the **same single NLI hypothesis** as Approach A.
4. Mean NLI class probabilities across context sentences, then argmax. If no aspects are identified, return **insufficient evidence (U)** and record missing aspect coverage.

This isolates whether ABSA's *selection* of locally meaningful evidence helps NLI compared with the raw whole review. It does not claim polarity is an emotion label; nor does it assume pretrained ABSA recognizes all spatial/atmospheric aspects.

**Caveat:** Sentence extraction, mean aggregation, and no-aspect handling are methodological choices, not proven optimal; the aspect extractor may miss important cues, or identify unrelated objects and services.

## Evaluation

Report for each approach and each of the three pilot emotions:

- 3-way accuracy on S/C/U, **including unknown/insufficient cases**.
- Per-class precision/recall/F1 and macro-F1, plus confusion counts.
- C coverage: number of reviews with no aspect extracted and mean extracted aspects.
- Raw error cases (including off-topic reviews) for qualitative diagnosis.

**Do not** compare only accuracy on S/C while dropping U: the prior test showed that can conceal false contradictions. No scores constitute definitive validity because reference labels were made by a single analyst and the sample was deliberately selected.

## Run and inspect

Open [GitHub Actions](https://github.com/UsernameIsJoe/Atmosphere-grounding/actions/workflows/stage1a-compare-abc.yml) and check the triggered run (the workflow is configured for push on its creation). If none starts, select **Run workflow** on `master`.

The experiment downloads model weights and runs CPU inference. If checkpoint loading fails or any stage errors, the run is **failed**, not a validated experiment. Inspect failure logs and correct before drawing conclusions.

Download artifact **stage1a-abc-comparison**: `review_cases.jsonl` and `summary.json`.

## Next decisions — conditional on actual results

1. Identify which errors are due to premise context, NLI hypothesis construction, or ABSA evidence selection.
2. Check multiple hypotheses individually, especially invitation/comfort and safety/injury distinctions.
3. Audit provisional annotations with independent raters before making strong comparative claims.
4. Try location-specific evidence filtering and span-preserving ABSA improvements *only if this pilot indicates they are warranted*.
5. Expand beyond three pilot emotions after confirming the desired **nine-emotion taxonomy**.

**This is an experimental comparison, not a locked pipeline.** Existing architecture and training choices remain open.

## Model references

- [BART-large-MNLI](https://huggingface.co/facebook/bart-large-mnli)
- [Pretrained end-to-end ABSA extractor](https://huggingface.co/yangheng/deberta-v3-base-end2end-absa)
- [Companion ABSA classifier/tokenizer and implementation example](https://huggingface.co/yangheng/deberta-v3-base-absa-v1.1)

# Stage 1A — ABSA / Aspect Extraction: Next Research and Experimental Plan

**Date:** 2026-11-03. **Status:** Phase A/B extraction comparison and controlled examples implemented in GitHub Actions; execution success and results are not yet verified. NLI integration remains future work.

## Why pivot now

The matched 50-review NLI checkpoint screen was completed; [findings](stage1a-nli-checkpoint-screening-results-2026-11-03.md). Different models vary in support predictions and hypothesis stability (particularly inviting), but their agreement/disagreement cannot measure differential accuracy without ground truth. Vocabulary/model selection remains provisional. The research goal still requires better location-grounded textual evidence, not merely a stable classifier.

## Initial ABSA test: what it actually established

[Completed 30-review A/B/C audit](stage1a-executed-results-evaluation-audit-2026-11-03.md): one `yangheng/deberta-v3-base-end2end-absa` token classifier extracted aspect terms/polarities; script `scripts/stage1a_compare_abc.py` retained ONLY sentences containing one extracted aspect as inputs to BART NLI. The method missed a relevant loud-sirens sentence and lost calm contradiction evidence. Average ~1.8 extracted aspects per diagnostic review; two had none. The comparison used assistant-authored provisional labels, **not independent human annotations**. Results do NOT establish that ABSA is bad or that NLI is more accurate.

**Important reframing:** Conventional ABSA focuses on aspect target terms (often nouns) and their polarity, while relevant place atmosphere may be expressed through *events, verbs, adjectives, global setting descriptions, or sensory experiences* without a clean nominal aspect. Thus **aspect extraction** and **location-attributed evidence extraction** are related but different tasks. This distinction is a key research question; do not assume conventional aspect coverage equals emotional-evidence coverage.

## Model / approach candidates (verify task, checkpoints, and licensing before running)

1. **Existing end-to-end baseline:** `yangheng/deberta-v3-base-end2end-absa`, token-level aspect extraction plus sentiment, returns text offsets. https://huggingface.co/yangheng/deberta-v3-base-end2end-absa
2. **SetFitABSA:** noun/noun-compound candidate detection via spaCy, aspect vs non-aspect filtering by a SetFit classifier, polarity classifier. **Requires a compatible pretrained aspect model or few-shot training for domain adaptation; not automatically a ready-to-run end-to-end equivalent.** https://huggingface.co/docs/setfit/how_to/absa
3. **Arctic-ABSA / other published extraction approaches:** evaluate model card/checkpoint reproducibility and inference mode before including. Do not claim a like-for-like test until independently runnable.
4. **Domain-neutral extraction baseline:** spaCy noun-phrase/entity extraction and syntactic phrase selection, without sentiment. This is an *aspect-candidate* baseline, not a complete ABSA sentiment system.
5. **Instruction-guided structured evidence extraction:** optional distinct method to retrieve observations/actions/sensory descriptions beyond noun aspects; constrained output with exact source-span verification. If attempted, keep separate from standard ABSA and record model/prompt.
6. **Aspect-conditioned sentiment checkpoints:** e.g. `yangheng/deberta-v3-large-absa-v1.1` need supplied aspect targets and are not interchangeable with an end-to-end aspect term detector.

Sources: end-to-end model card (https://huggingface.co/yangheng/deberta-v3-base-end2end-absa); SetFitABSA method (https://huggingface.co/blog/setfit-absa).

## Proposed sequence — avoid overcommitting to one implementation

**Phase A — fixed 50-review aspect/evidence probe:** Reuse exact selected IDs from the recent NLI model screening as input (sample manifest from artifact). Analyze original reviews first; **do not use NLI predictions as ground truth**. Run at least the existing ABSA extractor plus a distinct, technically available extraction baseline; add another genuinely comparable pretrained ABSA checkpoint once compatibility is verified. Store exact source offsets and full original review context, all extracted noun targets, sentiments (if model supports), model identity, inference/runtime/truncation diagnostics. Any manual qualitative review is an *inspection* rather than an accuracy benchmark.

**Phase B — label-free diagnostics:** Count extracted spans; coverage across reviews and location IDs; sentence retention; fractions of review text without any extracted aspect; overlap/differences across methods; examples of dropped evidence, negation, sensory descriptions, mixed opinions, reviewer-only events and location-attributed claims. Compare models on identical texts. **Coverage alone is not recall or precision**, because we have no independent reference spans.

**Phase C — controlled contrastive probes:** Construct small transparent *synthetic* examples where the intended location-attribute spans are explicit, absent, negated, or mixed. Tests can detect obvious coverage errors; they must not stand in for a representative real-world accuracy benchmark. Especially inspect no-noun observations, location vs reviewer attribution, temporal distinctions, and adverse evidence.

**Phase D — NLI integration (ONLY after extraction study):** Compare (i) original full-review NLI, (ii) aspect-only sentence filter (replicate failure), (iii) full-review NLI with aspect metadata/evidence retrieval, (iv) attribute-preserving passage selection that keeps unmatched sentences available. Hold NLI checkpoint and hypotheses fixed for the test; do not simultaneously tweak vocabulary. Retain support / contradiction / missing evidence, source provenance and confidence separately; do not map positive aspect polarity directly to calm/inviting/safe.

## Key research decisions after ABSA probe

- Does generic nominal ABSA capture atmosphere-relevant statements, or do we need a broader observation/evidence extractor?
- Is aspect extraction useful as a **complement** to NLI, not as a filter?
- Can we define a fixed, theory-grounded *textual evidence schema* without making it identical to the **separate, image-derived visual feature library**?
- Which candidate methods justify further scaling? No accuracy or winner claims before independent human-rated evaluation.

## Project-level constraints

Keep parallel Stage 1B visual-quality feature research, Stage 2 location-level association, and Stage 3 visual prediction intact. Emotion taxonomy (nine final categories), text aggregation/scoring meaning, data usage rights and independent labels remain unresolved.


## Implemented experiment — Phase A/B and synthetic probes

- Script: [`scripts/stage1a_absa_extractor_screen.py`](../scripts/stage1a_absa_extractor_screen.py).
- Workflow: [`.github/workflows/stage1a-absa-extraction-screen.yml`](../.github/workflows/stage1a-absa-extraction-screen.yml). Three parallel jobs, one each for:
  1. `yangheng/deberta-v3-base-end2end-absa`, original joint aspect + polarity model;
  2. pretrained `tomaarsen/setfit-absa-bge-small-en-v1.5-restaurants` **two-model restaurant-domain** SetFitABSA aspect/polarity pipeline. This is a reproducible but **domain-mismatched transfer baseline**, not a spatial-atmosphere model;
  3. `en_core_web_sm` spaCy noun chunks, **a candidate-extraction reference, NOT ABSA**.
- Inputs: exactly the **50 deterministic reviews spanning 43 locations** from prior NLI screening (same row selector). Review-level outputs explicitly retain full original review, verified text offsets for aspect spans, polarity metadata when available, source sentences containing aspects, and all sentences that an aspect-only filter would have discarded. SetFit's text-only spans are aligned to original reviews, marking ambiguous repeated matches instead of silently pretending offsets are precise.
- Label-free outputs: count of aspect spans per review, no-aspect count, counterfactual fraction of sentences retained by an aspect-only filter, unaligned-span count, 7 synthetic challenge inputs and extraction runtime. **These are not precision, recall or atmosphere accuracy**.
- Synthetic challenge cases include explicit negation, non-nominal atmosphere language, positive-negative mixed claims, a reviewer-only event, welcoming entry, a safety issue and an adjective-only observation. Diagnostic phrases are declared ahead of time; their detection is not a human-rated benchmark. A model's failure to produce a noun aspect for an adjective-only case is not automatically a model defect if its advertised task is noun-target extraction.
- Workflow checks sample and source-offset integrity, runs unit tests, and uploads whatever outputs are present even on failure. Each model has its own artifact.
- `Phase D` (NLI integration) is deliberately **not** included in this run; we first need to inspect whether aspect models capture relevant observations independently. No vocabulary or NLI model selection is implied.
- Verified methodology: [Hugging Face SetFitABSA documentation](https://huggingface.co/docs/setfit/how_to/absa) describes spaCy candidate extraction followed by separately trained aspect and polarity classifiers, and lists the pretrained restaurant checkpoints.

**Known limitations:** Automatic review sentence segmentation differs by parser. The source-offset reconstruction for SetFit is tentative when repeated identical terms appear; ambiguous examples are flagged. Current ABSA checkpoints were trained on domains unlike public-space atmospheric descriptions. Count-based metrics cannot rank model correctness without externally defined evidence spans.

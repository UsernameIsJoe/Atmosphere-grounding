# Stage 1A ABSA protocol audit — 2026-11-04

## Scope and decision
Stage 1A extracts source-supported aspect/opinion/polarity evidence from real place reviews for later atmosphere relevance/NLI and the nine-emotion mapping. This audit does **not** lock any single model as production-ready. It locks sentence-level inference on original reviews, explicit source provenance, and separate handling of implicit/paraphrased relations.

## Frozen real-review evidence
- Original fixed sample: 20 real reviews from `data/processed/reviews.jsonl`, 56 original spaCy sentence spans.
- Prior whole-review vs sentence-level *partial target recovery* on 29 assistant-authored reference pairs:
  - AOS-T5: 5 -> 8 initially; 13 after separate comma-delimited parser rescue.
  - GTS-BERT: 9 -> 14.
  - Dependency rules: 22 -> 22.
- These are NOT accuracy, full recall, precision, F1, or emotion classification metrics. The reference list is incomplete and not independently annotated.
- Original run: https://github.com/UsernameIsJoe/Atmosphere-grounding/actions/runs/41908682135
- Audit / model-card workflow: `.github/workflows/stage1a-checkpoint-protocol-audit.yml`
- Parser-corrected raw-output comparison: run 41911651443, successful real-review audit job.

## Confirmed technical issues
- AOS-T5 can produce comma-separated `aspect:opinion:polarity` triplets on a single line. Previous parser silently discarded such outputs; rescued 21 triplets across 9 sentences with five additional partial targets. Production parser updated in `scripts/stage1a_relation_pilot.py`.
- AOS generates semantically plausible paraphrases in some cases (e.g. `beautiful` -> `lovely`). Literal source-offset checks rightly reject them as exact quotations but this is not the same as semantic invalidity.
- AOS sometimes emits incomplete/malformed triplets. A parser update does not justify treating those as valid.
- GTS uses its author's `DecodeAndEvaluate.decode_predict_string_one` custom code with max length 128 and verbatim sentence input. It correctly reproduced the checkpoint author example with `display/great/positive` and `battery life/great/positive`.
- The GTS checkpoint's author example is not an independently held-out benchmark and does not imply benchmark F1 replication.
- On frozen review sample, dependency rules return many relations but their semantic precision and relevance are unknown.

## Locked research protocol
1. Do not add new pretrained candidate models at this stage.
2. Segment original real review text into sentence-level inputs; preserve exact source, review IDs and span offsets.
3. Preserve model raw generations, distinguish output parsing failures from inference errors, and count source-exact, implicit and paraphrased relations separately.
4. Evaluate aspect, opinion, linkage, polarity/negation and downstream atmosphere relevance separately.
5. Do not use partial lexical target recovery as accuracy.
6. Use dependency rules as a transparent baseline rather than presuming neural superiority.
7. Do not advance any model to production until an independently adjudicated complete gold sample of real reviews establishes actual precision, recall/F1, and task-relevant evidence recall. Avoid creating a circular gold set from model predictions.

## Interim candidate disposition
- GTS-BERT: keep as neural candidate; usage validated on official example but urban transfer quality remains unmeasured.
- Dependency rules: keep as transparent high-recovery baseline, not as a validated semantic extractor.
- AOS-T5: corrected parser in repository, but still shows low exact author-example reproduction and a polarity failure; **do not select as the sole Stage 1A extractor** without further domain validation.
- No model should be called finalized for production on these data.

## Still open
- **Completed:** AOS author-card examples with PyTorch >=2.6: 4/10 author-listed triplets reproduced by strict normalized text/polarity match across six sentences. Predicted outputs often contain useful close variants, but include missing triplets and an incorrect positive polarity for 'slow' elevator. This is NOT independent benchmark accuracy. GTS reproduced 2/2 example triplets on its author's single model-card sentence. Successful run: https://github.com/UsernameIsJoe/Atmosphere-grounding/actions/runs/41911920001
- Independently annotate all relevant aspects/opinions on a sufficiently sampled set of actual review sentences, including negatives and complex cases, with adjudication of span variants.
- Calculate exact- and overlap-matched triplet precision/recall/F1 and atmosphere-relevant evidence coverage; report sample uncertainty and failure types.
- The three-component pipeline remains a research hypothesis; current evidence is insufficient to lock the ABSA implementation as accurate enough for downstream use.

# Stage 1A ABSA — official-format inference on original real-review sentences

**Date:** 2026-11-04. **Status:** Implementation and GitHub Actions workflow committed; run [41908682135](https://github.com/UsernameIsJoe/Atmosphere-grounding/actions/runs/41908682135) triggered, completion pending verification.

## Research correction

The previous 20-review whole-review test did not reproduce the sentence-oriented inference setting of the two joint triplet checkpoint examples. We now compare **the same exact source reviews** under a *sentence-first, source-verified* protocol, without synthetic test data, changed model families or changed NLI/relevance architecture.

- **Source only:** original `data/processed/reviews.jsonl`, the **same deterministic 20 review rows** used in M1 relation pilot. No model-generated evaluation text, no fabricated sentence controls.
- **Preprocessing:** segment with spaCy `en_core_web_sm` parser, pass **verbatim original sentence text** to each extractor, keep source `review`, `place_id`, `review_index`, sentence offsets, per-sentence raw predictions, and original-review offset rebasing. Do not remove stopwords, negations, punctuation, adjectives or misspellings.
- **AOS-T5:** exact published prompt already in the previous script, `AutoTokenizer` + `AutoModelForSeq2SeqLM`, deterministic decoding; `max_new_tokens=250` as in the model card, and explicit >512-input-token skip with warning instead of silent truncation.
- **GTS-BERT:** author-provided custom `BertGTSOpinionTriple` + `DecodeAndEvaluate`, documented `max_len=128`; log source token count and flag sentences exceeding this bound. Preserve raw aspect/opinion/polarity and source alignment status. A model returning a polarity label doesn't prove it understands negation.
- **spaCy dependency:** same fixed dependency-rule baseline on source sentences. It is not a pretrained ABSA opinion model; it is a grammatical extraction control.
- **Comparison:** strictly paired sample and source verification, previous whole-review results from successful run [41906619654](https://github.com/UsernameIsJoe/Atmosphere-grounding/actions/runs/41906619654). Same **29 assistant-authored partial target pairs** used only for exploratory recovery. Full raw extraction records exported for subjective semantic review. Count changes cannot establish precision, fully labeled recall or model accuracy.

## Code and execution

- [Sentence input and inference script](../scripts/stage1a_absa_official_sentence_inference.py)
- [Paired scoring and provenance validation](../scripts/stage1a_absa_sentence_comparison.py)
- [Tests on original dataset](../tests/test_stage1a_absa_real_sentence_pipeline.py)
- [Three-method GitHub Actions workflow](../.github/workflows/stage1a-absa-real-sentences.yml)

Workflow matrix uses three separate jobs and a subsequent paired comparison. It uploads all original source-sentence predictions, provenance, input truncation flags, parsing status, and per-review comparison. Do not infer official model performance from any of these numbers. We are testing whether **our inference protocol** harmed model outputs.

## Non-negotiable constraints

1. No synthesized example reviews, created test passages, or fabricated reference cases in this phase. Software source-integrity tests use the existing review dataset.
2. No new models, no additional prompts beyond the published AOS prompt, no emotion-specific interpretation, no new NLI or relevance experimentation.
3. Numeric outcomes must be read from the actual successful GitHub Actions artifacts, not guessed or extrapolated. Evaluate meaningful attachment and polarity with original text in context.
4. If full review and sentence-level results are similar, that does not prove the model family intrinsically unsuitable; independent evaluation remains necessary.

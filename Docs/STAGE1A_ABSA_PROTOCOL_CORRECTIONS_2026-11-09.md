# ABSA historical-baseline protocol corrections (2026-11-09)

This audit does NOT replace or reopen the Qwen3 Component 1 provisional track. It improves the reproducibility and scientific interpretability of **historical challengers** only. No ABSA model's reported counts are independently adjudicated semantic precision/recall.

## Confirmed minimal fixes applied in code

1. **GTS overlength input:** `scripts/stage1a_absa_official_sentence_inference.py` now checks the tokenizer's **>128 token** input length **before** the checkpoint decoder call. It returns `parse_status=skipped_input_too_long`, `input_truncated=true`, and no relations rather than allowing an exception and falsely calculating the flag only afterward. The original complete sentence remains in the review record. The exact relationship between the model's own pretokenization and its internal length limit still deserves explicit audit.
2. **AOS model-card prompt:** `scripts/stage1a_relation_pilot.py` now matches `aspect:opinion:sentiment. \\n\\n` (one space after the full stop). This is prompt fidelity, not evidence of an accuracy gain.

## Issues assessed but NOT silently patched

**GTS shipped decoder vs original GTS algorithm:** the checkpoint-specific `post.py` decoder used by `stage1a_gts_joint_aste_probe.py` follows the checkpoint author wrapper, but the original NJUNLP GTS `code/BertModel/utils.py::find_triplet` uses first-subword grid cell votes and tie order 5>4>3 for relation labels 3/4/5. This distinction is real. Do **not** substitute the original decoder without first confirming the checkpoint's label meanings, wordpiece mapping and generation behavior. Corrected outputs should be stored alongside unchanged old outputs, not overwrite them.

**GTS tokenization:** official GTS data pipeline assumes word-tokenized input. Current checkpoint wrapper receives raw text. spaCy-space tokenization might move closer to training, but this must be verified against the checkpoint's own preprocessing and offsets before claiming equivalence. Compare (a) raw+checkpoint decoder, (b) tokenized+checkpoint decoder, and (c) tokenized+original-style decoder on the same original real sentences.

**GTS offsets:** old `standardize` / `unique_span` re-find decoded phrase strings and can misplace repeated tokens and substring matches. Better mapping requires retaining indices through the decoder and matching them to the original spaCy character offsets, including punctuation, punctuation normalization, accents and subwords; a decoder rewrite is a separate, controlled test. Unresolved matches must remain explicitly flagged.

**AOS implicit aspects:** `make_relation` calls `locate` for both aspect and opinion. The AOS checkpoint can generate normalized/implicit aspects. Preserve them as **model-inferred / non-literal aspects** rather than assert they are source spans; keep explicit `grounded` definition as *both source-string spans exact*. A candidate with grounded opinion and nonliteral inferred aspect is not source-grounded in the same sense, and must not be counted as proven correct. No semantic gold is available.

**AOS parsing:** comma-delimited triplets were previously rescued in `parse_triplets`. The count of `sentences_unparsed` is available in the official sentence summary. Any further parser changes require studying actual saved `raw_generation` strings, and distinguishing partial successful parses from unparsed suffixes.

**PyABSA:** the official `checkpoint="multilingual"` call is correct and raw outputs were consumed by later matched audits. This is not the same as an independently evaluated accuracy score. English-only checkpoint remains unverified for current available library/model versions.

## Safe next ABSA milestone

Build an **isolated GTS decoding parity probe** to compare checkpoint `post.py` against original NJUNLP algorithm on identical model logits and token alignments, then rerun 56 original sentences and reconciliation *only if parity and source offsets are established*. The old `27` GTS relationship count should be marked as **checkpoint-wrapper-specific** and not a validated model performance metric. None of this blocks Component 2 local experiment or Stage 1B.

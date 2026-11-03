# Stage 1A — Cross-Checkpoint NLI Screening (50 Reviews)

**Status: Implemented November 3, 2026; execution results not verified yet.**

## Why screen first

The completed full BART experiment [run 41696683666](https://github.com/UsernameIsJoe/Atmosphere-grounding/actions/runs/41696683666) processed all 214 reviews × 60 candidate hypotheses = 12,840 model evaluations, taking roughly two hours. Before repeating with different model families, screen them with an identical, frozen subset, then expand promising candidates to the full corpus.

## Two candidate checkpoints

- `MoritzLaurer/deberta-v3-large-zeroshot-v2.0` — https://huggingface.co/MoritzLaurer/deberta-v3-large-zeroshot-v2.0
- `MoritzLaurer/ModernBERT-large-zeroshot-v2.0` — https://huggingface.co/MoritzLaurer/ModernBERT-large-zeroshot-v2.0
- Existing BART reference: `facebook/bart-large-mnli`, full results in the previous run artifact.

**Important:** v2.0 zero-shot models are intended as **binary entailment vs not-entailment** classifiers, unlike BART's three-way contradiction/neutral/entailment output. The runner reads and validates actual `id2label` at runtime; if unrecognized, it fails rather than silently remap labels. Never claim that binary not-entailment is contradiction or neutral. Entailment probabilities may differ in calibration and normalization, so compare primarily within-checkpoint stability, patterns, and disagreement, and interpret direct numerical differences cautiously.

## Fixed test input and selection

- Registry `configs/stage1a_hypothesis_vocabulary_draft.json`: all **60 candidates**, unchanged across models.
- A deterministic **50-review sample**, computed **before either new model's output**:
  - one review with median-ish word length from each of the **43 places**;
  - the seven previously observed BART high-disagreement rows `55, 81, 113, 139, 181, 187, 123` (adding when not already included);
  - fill remaining slots with longest additional reviews if any of the seven overlap with location representatives.
- Every model receives the **same review IDs and hypothesis texts**. Selection is deliberately case-rich and place-diverse, **not a representative random sample**.
- Target per checkpoint: **50 × 60 = 3,000** premise–hypothesis evaluations. This is a comparison across checkpoints and a performance/compatibility pilot, **not** an accuracy benchmark without ground truth.

## Implemented files

- `scripts/stage1a_nli_checkpoint_screen.py`: selection; actual pretrained model inference; native labels; raw probability vectors and predictions; within-model core-paraphrase unanimity, pairwise comparisons, mean entailment probability range, leave-one-out robustness and top discrepancy rows; timing and token truncation counts.
- `tests/test_stage1a_nli_checkpoint_screen.py`: deterministic location-complete selection, label-space recognition, unknown-label rejection and binary robustness summary.
- `.github/workflows/stage1a-nli-checkpoint-screen.yml`: parallel model-specific CPU jobs, unit tests, full 50-row screening, manifest assertions and artifact uploads even if inference fails.
- Per-model artifact: `sample_manifest.json` (created before model weights download), `review_cases.jsonl` (flushed after each review), `summary.json` if complete.

## Review plan following model runs

1. Verify each model loaded successfully and inspect the discovered native label spaces.
2. Check identical review IDs, registry SHA, review counts and model execution times.
3. Compare within-model unanimity, pairwise wording sensitivity, leave-one-out stability, and review-level outliers.
4. Use original BART full-corpus artifact to filter the **exact same 50 review IDs**, not compare unlike samples. If necessary implement a small BART subset summary script; do not compare published 214-wide percentages directly with 50-wide ones.
5. Decide whether to run both models at the full **214 × 60** scale. Neither checkpoint is declared a winner on proxy agreement alone.
6. Preserve separate **ABSA model variation** workstream after NLI checkpoint comparison, then integration. Do not lock vocabulary or score mapping.

## Limitations

No independently human-rated review→atmosphere reference labels. Internal agreement is not correctness. A binary classifier cannot measure three-way S/C/U behavior the way BART does. Checkpoint outputs are uncalibrated; do not use probability magnitude as a universal emotional intensity scale. Existing review text may be constrained by source licensing; verify permissions before using as training data. Final nine emotions and the ultimate image-feature learning methodology remain open.

# Stage 1A — SetFit user-labeled atmospheric relevance gate

Date: 2026-11-11.

## User-authoritative real-review annotations

- All five complete batches stored verbatim at `data/evaluation/setfit_atmosphere_gate_user_labels_batch{1..5}.jsonl`.
- 100 original text excerpts copied exactly from `data/processed/reviews.jsonl`, with user-specified labels and source place/review IDs.
- TRAIN: 75 excerpts from 12 places; 56 relevant and 19 irrelevant.
- TEST (untouched): 25 excerpts from five distinct places; 20 relevant and five irrelevant.
- No train/test place ID overlaps; no duplicate (place ID, review index, excerpt text) keys; no original review text mismatch. Verified with GitHub source fetches and cross-file audit; automatic guard in `scripts/stage1a_setfit_audit.py`.
- All 100 labels are user-provided, none modified or inferred.
- Importantly, the 25-test set contains only five irrelevant texts, so specificity/rejection-rate estimates will have very wide uncertainty. The labels reflect user's broad view of atmosphere evidence, not narrower single-emotion relevance.

## Training experiment

- Implementation: `scripts/stage1a_setfit_gate_train.py`.
- Real pretrained base: `BAAI/bge-small-en-v1.5` using `setfit`.
- 75 examples, fixed 1 epoch and 10 pair iterations, random seed 42.
- Class 0 = irrelevant; class 1 = relevant.
- **Do not use any test samples for model training or threshold tuning.**
- Thresholds 0.20 (high-recall candidate) and 0.50 (baseline) are frozen in code before test execution; evaluation will report all per-example scores and list all false exclusions.
- No cutoff is recommended until actual test results have been inspected, and the model score is not automatically a calibrated probability.

## Execution tracking

GitHub Actions: [run 43098196485](https://github.com/UsernameIsJoe/Atmosphere-grounding/actions/runs/43098196485).

As last checked this run was **QUEUED with no jobs**, matching the stalled earlier agnostic embedding-gate runs 43095546637 and 43095984666. Source-data audit from GitHub tool succeeded; model training and held-out inference have **NOT YET EXECUTED**. Do not claim metrics or success until logs and predictions are available.

Stage 1A Step 4A is incomplete pending execution and error inspection.

# Segment representativeness: 100-review pilot

Purpose: test whether topic embedding similarity provides a useful segment representativeness signal before it is connected to emotion outputs. This experiment does not measure emotion classification accuracy.

100 real reviews are selected from the existing 214-review corpus by seeded, place-balanced round-robin sampling (seed 20261124). All 43 places remain represented. The sample has 379 original-offset clause segments: 80 multi-segment and 20 single-segment reviews. No new synthetic reviews are included. The requested staff-polarity check uses a separate diagnostic phrase pair and related/unrelated controls.

Main model: Qwen/Qwen3-Embedding-8B, identical topic instruction for segment, full review and remainder. Robustness model: sentence-transformers/all-mpnet-base-v2, native sentence encoding without instruction. Model revisions, package versions, GPU, actual token lengths and input checksum are recorded in manifest.json. Inputs above the actual model limit are excluded, never silently truncated. Cross-family agreement uses shared eligible reviews only.

Fixed proportional rule: w_i = max(cosine_i,0) / sum_j max(cosine_j,0). All-zero groups fall back to uniform. Single-segment weights equal 1 and are excluded from bias/association analysis. Cosines are similarity scores, not calibrated probabilities.

Checks:
- Raw cosine distribution and weight compression toward uniform.
- Segment length and normalized position associations, including within-review Spearman correlations.
- Review fixed-effects regression of raw cosine on log word count and position, with 1,000 review-cluster bootstrap samples. This separates observed associations; it does not establish causality.
- Cross-family agreement, both within reviews and after scaling weights by segment count. Pooled normalized-weight agreement alone is confounded by the common 1/n scale.
- Comparison with word-count length-share and uniform baselines.
- Self-match diagnostic: encode review with target segment removed; compare raw and normalized scores. Remainder similarity measures topic overlap with other content and is a diagnostic, not an automatic replacement for full-review representativeness.
- Position diagnostic: reverse clause order in the full review, holding target segment text fixed. Reversal may alter discourse as well as position.
- Separate diagnostic staff polarity pair, synonymous staff complaint, and unrelated building statement.
- Inspect all segments, highest and lowest ranks for 20 deterministically selected multi-segment reviews spanning segment-count ranges. Qualitative review is an assistant audit, not human gold validation.

No model tuning, sentiment embedding models or contextual chunk models are used. Harrier is omitted from this first pilot because the two requested model families provide the main comparison.

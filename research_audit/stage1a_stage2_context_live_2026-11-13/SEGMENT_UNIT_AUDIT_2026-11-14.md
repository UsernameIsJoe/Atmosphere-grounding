# Corrected Stage 2 segment-unit semantic audit (2026-11-14)

The evaluation unit is a single target segment, with the original whole review as background only for segment_context. 12 segments x 3 emotions = 36 reference category decisions per model per condition. Full-review-only predictions are excluded. Each decision is compared with the identical target-level reference.

Researcher-provisional reference, NOT independently blinded full gold. User-locked cases: K01 calm NONE, K02 safe OPPOSES, K05 safe OPPOSES, U05 inviting OPPOSES, U06 calm UNCERTAIN. Other verdicts are conservative semantic judgments (including U04 inviting NONE and K03 inviting NONE); these may be revised with further human audit.

Model | Segment only | Segment + background | Target verified quotations
---|---:|---:|---:
qwen3.6_27b-bf16 | 27/36 | 29/36 | 21/21; 22/29
gemma4_31b-it-bf16 | 29/36 | 30/36 | 15/15; 16/16

## Per-condition errors
- qwen3.6_27b-bf16 segment: K01/calm:opposes vs none; K02/inviting:none vs opposes; K02/safe:none vs opposes; K03/inviting:opposes vs none; K05/safe:mixed vs opposes; K06/safe:mixed vs opposes; U04/inviting:supports vs none; U05/inviting:none vs opposes; U06/calm:none vs uncertain. Non-exact target quotes: 0. Obviously incorrect animal referents: 0.
- qwen3.6_27b-bf16 segment_context: K01/calm:opposes vs none; K03/inviting:opposes vs none; K04/inviting:supports vs none; K05/safe:mixed vs opposes; U02/inviting:opposes vs none; U05/inviting:none vs opposes; U06/calm:none vs uncertain. Non-exact target quotes: 7. Obviously incorrect animal referents: 0.
- gemma4_31b-it-bf16 segment: K01/calm:opposes vs none; K01/inviting:mixed vs none; K02/inviting:none vs opposes; K02/safe:none vs opposes; K03/inviting:opposes vs none; K05/safe:uncertain vs opposes; U05/inviting:none vs opposes. Non-exact target quotes: 0. Obviously incorrect animal referents: 2.
- gemma4_31b-it-bf16 segment_context: K01/calm:opposes vs none; K01/inviting:supports vs none; K02/safe:uncertain vs opposes; K03/inviting:opposes vs none; K05/safe:uncertain vs opposes; U05/inviting:mixed vs opposes. Non-exact target quotes: 0. Obviously incorrect animal referents: 4.

## Qualifications
- These are category-verdict agreement counts, not complete extraction scores. Basis (direct/inference/both), source span, referent, rationale grounding must be scored separately.
- Full-review task used a different target scope; NEVER compare its labels against single-segment references.
- Exact substring checks miss subtle context-based reasoning leakage. Qwen segment+context did quote material from outside the target, e.g. K04 and U04.
- Prior 2/3, 1/3, 0/3 model ranking used review-level output and is withdrawn. No matched Qwen3 8B Stage 2 calls were made.
- Reference is researcher-provisional and should not be portrayed as an independently gold-labeled benchmark.

The full 36 x 4 comparison is in TARGET_SEGMENT_REFERENCE_AND_PREDICTIONS.csv. Original predictions retained in model+condition JSON files.

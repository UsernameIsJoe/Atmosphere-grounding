# Blind re-rating of shared segment-level disputes — 2026-11-15

This is an alternative, **user-blind provisional reference**, not a retroactively revised independent gold standard. The existing prior reference remains archived unchanged.

Seven target-segment emotion cases with disagreement among >=2 models were shown to the user without showing the previous reference or model predictions. Full-review context was for interpretation of target only.

| Case / emotion | Earlier researcher reference | User blind rating | Qwen3.6 | Gemma4 | Qwen3.8 | GPT-OSS |
|---|---|---|---|---|---|---|
| K01 calm | none | supports | opposes | opposes | opposes | opposes |
| K03 inviting | none | opposes | opposes | opposes | opposes | supports |
| K04 inviting | none | supports | supports | none | supports | supports |
| K05 safe | opposes | opposes | mixed | uncertain | mixed | opposes |
| U05 inviting | opposes | mixed | none | mixed | mixed | opposes |
| U06 calm | uncertain | supports | none | uncertain | supports | supports |
| K01 inviting | none | supports | none | supports | none | supports |

Agreement with user's seven blind ratings: Qwen3.6 2/7, Gemma4 3/7, Qwen3.8 4/7, GPT-OSS 4/7.

**Crucial:** Three user blind ratings conflict with that same user's previous explicit judgments (K01 calm previously none, now supports; U05 inviting previously opposes, now mixed; U06 calm previously uncertain, now supports). These are *within-annotator disagreements*, not automatically proof the researcher's previous reference was wrong. K01 stress is wedding logistical stress per full review and supports vs calm is semantically especially unclear. Prior user-locked labels MUST NOT be overwritten silently. Agreement is not validity.

If all seven new labels provisionally replace their earlier reference values, the 36 target/condition agreement counts become:
- Qwen3.6: previous 29/36; newly provisional 30/36; agreement with seven re-rated cases 2/7
- Gemma4: previous 30/36; newly provisional 31/36; agreement with seven re-rated cases 3/7
- Qwen3.8: previous 29/36; newly provisional 32/36; agreement with seven re-rated cases 4/7
- GPT-OSS: previous 27/36; newly provisional 29/36; agreement with seven re-rated cases 4/7

These recalculated rates are highly sensitive to disputed reference definitions and should not be used for ranking until a codebook is fixed and intra-rater conflicts adjudicated. The experiment itself has 12 segments only.

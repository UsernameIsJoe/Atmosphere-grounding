# Stage 3 matched segment-unit audit — 2026-11-14

## Protocol
Identical 12 frozen target review segments and original Stage 2 prompts/JSON schema, segment-only or target segment + full original review as disambiguating background. 3 emotion verdicts per target = 36 decisions per model/condition. User adjudications + researcher-provisional reference from TARGET_SEGMENT_REFERENCE_AND_PREDICTIONS.csv in prior Stage 2 audit; other reference values are researcher-provisional, not independent blinded gold.

## Matched provisional category agreement

| Model | Segment only | Segment + context |
|---|---:|---:|
| Qwen3.6 27B | 27/36 (75.0%) | 29/36 (80.6%) |
| Gemma4 31B | 29/36 (80.6%) | 30/36 (83.3%) |
| Qwen3.8 27B | 27/36 (75.0%) | 29/36 (80.6%) |
| GPT-OSS 120B | 28/36 (77.8%) | 27/36 (75.0%) |

IMPORTANT: A 1/36 difference = 2.8 percentage points; 12 source segments are far too few for significant model rankings. No evidence newer/bigger models outperform the previously tested Gemma4 31B on this protocol. In these four samples, added context helps 27B Qwen models by +2/36, helps Gemma4 by +1/36, and hurts GPT-OSS by -1/36.

## Evidence attribution and traceability
- Qwen3.8: segment 20/20 exact evidence spans; context 20/23. Some quotes are outside the target when context is present.
- GPT-OSS: segment 16/16 exact; context 16/16 exact.
- Qwen3.6: segment 21/21 exact; context 22/29 exact.
- Gemma4: segment 15/15 exact; context 16/16 exact.
- All four models made some erroneous referent='animals' allocations to people, locations, or other non-animals. Qwen3.8 and GPT-OSS show the same general referent issue, so this is not fixed by capacity.

## Qualitative audit risks
- K01 personal/event stress is repeatedly mislabeled as location calm OPPOSES across model families.
- K03 walking suitability still spills into inviting verdicts.
- K04 context leaks comfort/ease beyond target (including Qwen3.8, which produced target-nonexact citations in some cases).
- U05 negative cleanliness/amenities often underweighted or reduced to mixed/none.
- U06 uncertain calm often forced into supports or none.
- GPT-OSS 120B produced one initially malformed JSON response on K02 in segment+context, then succeeded on an **identical settings rerun**. Both raw attempts remain in archive.
- The evidence list is not an exhaustive recall benchmark; quote exactness alone does not establish reasoning validity.

## Decision
Do not substitute GPT-OSS 120B or Qwen3.8 for Gemma4 on the basis of this small sample. Next step should be matched **more segments** + scoring of source attribution, E/T basis, and category separately. Use full review strictly as *context* only; perform mechanical span containment and review for reasoning leakage. No GPU is running; data archived in this folder.

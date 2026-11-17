# Primary emotion model decision — 2026-11-17

The researcher selects **Gemma4 31B BF16 (`gemma4:31b-it-bf16`) as primary**, retaining **Qwen3.8 27B (`qwen3.8:27b`) for separate comparison and audit**. The researcher favors Gemma's more selective no-emotion judgments while considering Qwen's additional emotional interpretations defensible. This is a pilot selection, not a measured accuracy ranking or case-by-case human gold.

## Operating policy

- Keep the accepted whole-review relevance gate v0.4 / Qwen3:8B. Its model is distinct from the Qwen3.8:27B comparison extractor.
- Gemma's own detected claims are primary. Qwen's claims remain separate; they do not automatically fill Gemma's empty outputs or override Gemma.
- No emotion claim means no E/T for that model and emotion. Invalid outputs remain failures, not no-emotion judgments.
- E/T applies only to claims detected by the same model. Retain the agreed place-level definition and assign per claim/quote, not per entire segment.
- The archived shared-pool E/T test supplied claims to both models conditionally. Those cross-model classifications do not imply emotion detection or endorsement and are excluded from primary/comparison extraction outputs.
- Preserve historical prompts, runners, raw outputs and manifests. This decision changes the current model preference, not emotion definitions, the gate or experiment history. No automatic merge or new GPU run is authorized by this record.

The machine-readable selection is [stage1a_emotion_models_current.json](../configs/stage1a_emotion_models_current.json). This establishes the current research default; it does not imply completed end-to-end integration.

Both models attempted all 71 segments from 12 reviews. Qwen has 71 valid outputs; Gemma has 67 valid outputs and 4 mechanical failures. Across the 67 mutually valid segments, 22 emotion disagreements occur in 21 segments: all Qwen directional claims versus Gemma empty claims for the disputed emotion.

Sources: [original outputs](../research_audit/stage1a_v05_gate_passed_followup_live_2026-11-16/predictions.jsonl), [completion outputs](../research_audit/stage1a_et_only_2026-11-17/emotion_completion.jsonl), [conditional E/T test](../research_audit/stage1a_et_only_2026-11-17/README.md).

## Why wedding review T06 passed the gate

The archived **Qwen3:8B / gate v0.4** output is:

```json
{
  "keep": true,
  "anchor_quote": "State Park created the perfect atmosphere for our reception",
  "reason": "Describes the atmosphere and experience of the venue as a place-level characteristic."
}
```

This is the gate's actual recorded reason. Its anchor is source-exact. The review SHA-256 is `2b45c09dfa1ac11c238d508b7e681221968b283a3ed8601e4588408e5e3ab385`.

The gate allows mixed reviews to pass when any independent substantive place-level observation qualifies. It accepts atmosphere and visit-experience descriptions, while rejecting private celebrations where the venue is merely a backdrop. It interpreted this reception-atmosphere phrase as a venue characteristic. The unresolved boundary is whether event-specific praise supplies a substantive characteristic of the place. The [existing gate lock](STAGE1A_REVIEW_ELIGIBILITY_GATE_LOCK_2026-11-16.md) already records T06 as a known disputed false positive and explicitly defers this distinction; v0.4 did not fix it.

Sources: [gate T06 decision](../research_audit/stage1a_review_gate_v04_regression_qwen8b_2026-11-16/decisions.jsonl), [frozen prompt](STAGE1A_REVIEW_ELIGIBILITY_GATE_PROMPT_V0_4_2026-11-16.md), [codebook](STAGE1A_REVIEW_ELIGIBILITY_GATE_CODEBOOK_V0_4_2026-11-16.md).

**Gemma does not reject the wedding review completely:** 7 of its 12 valid wedding segments contain emotion claims, while 5 are empty. It retains reported calm/relaxation and several overall-experience/atmosphere inviting claims. Its selectivity removes some staff/drink/event praise but does not eliminate this review-level false positive.

No gate rules or historical decisions were changed. Any future gate amendment must be separately versioned and tested; this investigation is not a gate amendment or rerun.

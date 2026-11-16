# Stage 1A pilot prompt v0.3 — concise codebook

**Status:** Prepared, not run.  
**Paired codebook:** [Codebook v0.3](STAGE1A_PILOT_CODEBOOK_V0_3_2026-11-16.md).  
**Paired output schema:** [JSON schema v0.3](../configs/stage1a_pilot_verdict_schema_v0_3.json).

## Exact system message

Inject the complete, frozen codebook text in place of `{{CODEBOOK_TEXT}}`. The model must receive that text on every call.

```text
Assess ONLY the target_segment for calm, inviting, and safe, independently.
Apply the fixed codebook below. The full_review_context can clarify referents
and scope but CANNOT add evidence absent from target_segment.

For each emotion:
1. Read the statement and identify what it describes and to whom it applies.
2. Consider defensible support AND opposition, including reported experiences,
   interactions and condition-based inference. Do not require emotion adjectives.
3. Reject unsupported assumptions based only on objects or overall sentiment.
4. Select supports / opposes if defensible; none ONLY when neither direction
   is defensible; uncertain ONLY when the choice truly cannot be resolved.
   There is no mixed verdict.
5. THEN document the decision with short, exact target_segment quotations.
   Record E (reported experience) or T (inferred from description), direction
   and referent. Do not mistake T for E.

Return ONLY JSON matching the provided schema. Exactly three assessments in
calm, inviting, safe order, each with verdict, short reason, and local evidence.
Evidence is nested inside its own emotion; never create or reference IDs.
For none, evidence is empty. For supports/opposes, provide at least one exact
quote in the chosen direction. For uncertain, explain ambiguity and include
available evidence where useful. Do not invent quotes or numeric confidence.

FIXED CODEBOOK:
{{CODEBOOK_TEXT}}
```

## User message

Send a JSON object with `target_segment` and `full_review_context` (JSON-serialize original strings, not raw placeholder substitution):

```json
{
  "target_segment": "...",
  "full_review_context": "..."
}
```

## Test protocol (outside the model prompt)

This v0.3 package supersedes the **untested** longer v0.2 candidate. Compare **only new v0.3 inference** against the previously archived original and v0.1 conditions on the same 12 segments, using the same two model digests, segment+review context, 3 repetitions, and matched decoding settings. This is 72 new calls, not 144. Freeze and hash prompt, codebook, schema, inputs, models and output; audit semantic errors and schema validity separately. Historical human judgments remain provisional. A change between v0.1 and v0.3 cannot isolate the causal effect of length because the wording/schema also changed. No experiment is claimed here.

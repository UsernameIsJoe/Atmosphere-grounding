# Stage 1A — proposed evidence-routing gate (draft, 2026-11-16)

**Purpose:** Separate segmentation/referent problems from interpretation of emotions. Insert after segment creation/offset verification and before the main three-emotion classifier. This is a design proposal, **not implemented or validated**.

## Inputs and invariants

Consume authentic original segment text + its original full review and byte/character offsets. Never invent or synthesize review claims. No model label or emotion verdict from a previous run is included. Distinguish case context from evidence. Model must quote only from the finally selected target span.

## High-recall, inexpensive routing

For each segment, determine:

1. **Place-related evidence candidate:** Direct reported environmental/spatial/sensory/social experience, place-level appraisal/desirability, visitor-facing encounter, or a plausible condition affecting access/use, calm, inviting or safe. Send to emotion interpretation.
2. **Context dependent:** Contains unresolved referents, causal explanations elsewhere, or clause breaks that might change scope (e.g. stress from events rather than place). Send to **context resolution / segmentation repair** before emotion interpretation. Preserve source offsets; if combining with adjacent clauses, make the new enlarged span explicit and evaluate only that exact span. Otherwise use full review strictly for reference resolution.
3. **Clearly out of scope:** No place-attributed or visitor-facing atmosphere/appeal/use information even after context. Mark as a provenance-preserving skip (not a claim that the place lacks the three emotions).

**Safety against false negatives:** Any borderline, multi-topic, or unresolved case goes to interpretation, not automatic rejection. A spatial-only prefilter would falsely drop the staff-hostility/intimidation cases and place appeal that researchers now consider relevant. Do not classify topic solely using keywords.

## Output proposal

```json
{
  "segment_id": "...",
  "route": "interpret | resolve_context | out_of_scope",
  "referent": "place | surroundings | people | event | other | unclear",
  "needs_boundary_repair": false,
  "short_reason": "..."
}
```

A gate does **not** assign `supports`, `opposes`, `none`, or `uncertain`. Those are emotion-specific judgments made by the downstream LLM. Gate-level `out_of_scope` and emotion-level `none` should remain distinct in the research data. Retain input/output decisions to audit recall.

## Acceptance test before deploying

- Freeze a held-out sample of authentic segments and compare **no gate** vs **gate** using the same downstream codebook/model.
- Human-audit false exclusions and cases whose correct referent depends on another clause; examine both recall and improvements in E/T provenance.
- Require high recall for atmosphere-relevant material and explicitly track abstentions and boundary repairs. Avoid implementing the gate as an aggressive keyword filter.
- The gate should be cheaper/smaller than the main interpreter **only if** it preserves important information; complexity alone does not prove utility.

**Do not rerun previous experiments or deploy a pod as part of drafting this design.**

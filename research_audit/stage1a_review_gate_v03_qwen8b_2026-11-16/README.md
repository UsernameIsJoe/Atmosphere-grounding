# Stage 1A review gate v0.3 — Qwen3 8B pilot (2026-11-16)

**Task:** Full-review eligibility, **place-level** versus isolated meal/service/transaction. This v0.3 experiment targets **T11**, not T06.

**Model:** `qwen3:8b` with temperature 0, seed 42, num_ctx 8192, num_predict 512.  
**Prompt:** [v0.3](../../Docs/STAGE1A_REVIEW_ELIGIBILITY_GATE_PROMPT_V0_3_2026-11-16.md)  
**Codebook:** [v0.3](../../Docs/STAGE1A_REVIEW_ELIGIBILITY_GATE_CODEBOOK_V0_3_2026-11-16.md)  
**Input:** [12 previously unused authentic reviews plus 1 frozen T11 regression case](cases.jsonl). All are original full reviews. The dataset is deliberately selected for diverse boundaries, **not random or representative**. No emotion inference or segment processing. Outputs archive raw model text, exact source review, reason, quote and validation.

## Results

| Case | Model decision | Evidence/issue |
|---|---|---|
| R_T11 | **REJECT** | Correctly identifies single meal and service incident; user-adjudicated rejection |
| N01 | REJECT | "World Cup watch party" event only |
| N02 | REJECT | "We enjoyed being at The Taste of Cambridge in University Commons" without specific place character |
| N03 | REJECT | Concert performance only |
| N04 | KEEP | Model anchors visitor-readable museum signage; appears defensible as visitor-facing wayfinding/interpretation |
| N05 | KEEP | **Questionable**: model uses shelter's restaurant-grade kitchen, despite review focusing on food, refused donation and organizational critique |
| N06 | KEEP | Bar patio is described, alongside service incident |
| N07 | KEEP | Explicit "Good vibe, warm atmosphere" |
| N08 | KEEP | Explicit "Nice environment and friendly staff" |
| N09 | KEEP | Comfortable two-story study seating/outlets |
| N10 | KEEP | Site-specific permit parking/access policy |
| N11 | KEEP | "Good design, and comfortable" restroom condition |
| N12 | KEEP | Model anchors vague "The property is awesome" in a leasing-agent review; **borderline** as to whether the phrase is specific enough independently; area convenience is also mentioned |

**Counts:** 13/13 strictly valid outputs; 9 KEEP, 4 REJECT. R_T11 changed from KEEP under v0.2 to REJECT in v0.3, **consistent with the user-provided adjudication**.

**Limitations:** This does **not** establish measured gate accuracy without human labels for these new reviews. N05 and N12 should be reviewed. T06 was intentionally excluded from this test and no new claim is made about its resolution. Format validity/quote matching are not semantic accuracy. No model-capacity comparison was made during this run.

The model was run on Runpod community Tesla V100-SXM2-16GB at advertised rate $0.23/hour; billing totals were not retrieved. Pod terminated after result archive.

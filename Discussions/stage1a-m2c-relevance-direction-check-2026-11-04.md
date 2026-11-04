# Stage 1A M2c — bounded relevance gate viability check (2026-11-04)

**Goal:** Decide whether it is worth pursuing a relevance-filtered ABSA→NLI pathway, **without** continuing an open-ended text-model optimization loop.

## Research question

Does a single off-the-shelf BART-NLI *metarelevance* hypothesis distinguish plainly location-relevant evidence from unrelated reviewer experiences or irrelevant features? If it cannot separate easy controls, there is no reason to scale this specific gating method.

## Scope and methodological limits

- Exactly **20 deliberately authored short claims × 3 provisional emotions** (calm, inviting, safe) = 60 comparisons; **120 BART NLI calls**, one direct-emotion and one metarelevance hypothesis per comparison.
- Author-assigned `D` direct, `R` related-indirect, `N` unrelated/insufficient expectations are **test design labels, not independent human ground truth**.
- Negation and speaker attribution are deliberately included: e.g. `I felt calm while sitting beside the lake` vs `I felt calm because my exam was over`; `safe path` vs `comfortable benches`; adequate/zero adequate parking as intentionally weak evidence for inviting.
- Reuse frozen `facebook/bart-large-mnli`; **no model training, no ABSA extractor, no new embeddings, no prompt-search or threshold tuning**. Fixed entailment threshold `0.5` is a **stress-test operating point, not calibrated probability**.
- Report retained relevant and unrelated examples, false positives and mean score separation; preserve all per-case probabilities and labels.
- Limitations: authored cases and zero-shot metarelevance prompt may be too artificial; even a pass will **not** demonstrate better atmosphere predictions for real location reviews.

## Explicit stop/decision gate

**Stop after this one run and its audit.** Use the results for a *directional choice*, not further tuning on the 20 examples.

- **Promising enough for one real-data check** only if the fixed gate retains at least 75% of the `D/R` examples *and* erroneously retains no more than 25% of `N` examples **overall**, with similar directional separation across the three emotions.
- **Otherwise** do **not** optimize this BART metarelevance prompt repeatedly. Mark this mechanism weak and preserve Stage 1A's direct NLI + evidence extraction findings as exploratory.
- Even if promising, permit **at most one small, place-level real-review sanity check** with reviewed evidence spans. That is a separate decision, not automatic expansion.
- **Regardless of outcome** return project focus to **Stage 1B**: fixed theory-supported visual-quality extraction, then Stage 2 location-level text-image association. Avoid letting the text-only branch consume the project.

## Artifacts and files

- `scripts/stage1a_m2c_relevance_gate.py`: 20 fixed cases, 3 emotion hypotheses, direct and metarelevance NLI, frozen metrics.
- `tests/test_stage1a_m2c_relevance_gate.py`: consistency and special negative/attribution controls.
- `.github/workflows/stage1a-m2c-relevance.yml`: syntax/tests before BART model downloads; artifact upload.
- Output `reports/stage1a_m2c_relevance/`: `cases.json`, `results.jsonl`, `summary.json`.
- **Results not yet established** at the time this document is created.

## Perspective

This is **not** an ABSA bake-off and does not select AOS, DeBERTa, SetFit or a final NLI architecture. It asks only whether there is an easy relevance signal worth trying to preserve in the larger image-and-text project.

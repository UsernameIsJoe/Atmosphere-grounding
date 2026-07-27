# Visuals of pipeline steps

Generated from existing `data/` artifacts (no full pipeline re-run).

| Step | File | What it shows |
|------|------|----------------|
| 2 Collect | `step2_places_map.png` / `.html` / `step2_places_table.csv` | Map of places; reviews & images per place |
| 4 Pass A | `step4_passA_llm_examples.png` | Real comments → LLM atmosphere / phrase / nouns |
| 6 Pass B | `step6_passB_llm_examples.png` | Same comments + photo objects → fused LLM output |
| 7 Grounding | `step7_example_*.png`, `step7_ablation_winners_by_category.png` | Per-example ablations + scene/object/context winners |
| 8 Correlation | `step8_place_correlation.png` | Place-level text↔image alignment (+ plain-language note) |

## How to read Steps 7–8

### Step 7
- **Orange box**: detected region for the noun.
- **scene / object / context**: three crops; highest score = ablation winner.
- **`step7_ablation_winners_by_category.png`**: one clear winner from each category side by side.

### Step 8 (plain language)
- **Mismatch flag** now uses **SigLIP review↔photo cosine** (relative z-score), not noun-string overlap.
- Magenta = this place’s comment–photo cosine is unusually low vs other places (z < −0.75).
- Noun Jaccard is still stored for diagnostics only.

Regenerate:

```bash
.venv/bin/python scripts/visualize_pipeline_steps.py
```

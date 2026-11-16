# Stage 1A — review-level eligibility gate v0.1: quick Qwen3 8B test

**Date:** 2026-11-16  
**Model:** `qwen3:8b` (Ollama, temperature 0, seed 42, `num_ctx=8192`, `num_predict=512`)  
**Input:** 12 authentic **complete reviews**, same originals as Stage 1A earlier segment tests. **No segmentation or emotion extraction** performed in this test.  
**Protocol:** [binary gate specification](../../Docs/STAGE1A_REVIEW_ELIGIBILITY_GATE_V0_1_2026-11-16.md); [runner](../../scripts/stage1a_review_eligibility_gate_v01_20261116.py); [JSON schema](../../configs/stage1a_review_eligibility_gate_v01.json).

## First-pass results

| Metric | Outcome |
|---|---:|
| Reviews evaluated | 12 |
| Model KEEP decisions | 12 |
| Model REJECT decisions | 0 |
| Strictly valid outputs (including exact anchor quote) | 10/12 |
| Quote validation failures | 2 (K04, U04) |

- **K04**: a quoted clause lowercased `We` → `we`; the source phrase was otherwise substantially correct.
- **U04**: anchor used `it's` where the original says `it's`? The first-pass strict checker rejected an inexact substring. Inspect raw fields for the precise mismatch rather than assuming exact-copy compliance.
- **K01 correctly kept**: the personal photographer delay is embedded in a review with staff hospitality and use of the space. The model anchored the qualifying use-of-space passage.
- **U02 kept**, but **rationale is weak**: the model anchored `The three exhibits on display were quite underwhelming`, incorrectly treating exhibit appraisal itself as sufficient spatial/experiential evidence. The full review ALSO recommends exploring MIT buildings and campus public art; that later place-directed visit recommendation can justify KEEP independently. Thus this is an **anchor/rationale problem**, not a proven false keep.
- **K05 kept** (reasonable because the review contains a visitor-facing intimidating encounter), but the model selected the **security-camera mention as its anchor**, which alone does not demonstrate eligibility as strongly as the encounter does.

## Interpretation

The first-pass result demonstrates the prompt can process full reviews and preserve true positives plausibly (including mixed review K01). **It does not establish rejection performance** because all twelve originals contain some likely eligible experience/use/appeal material and the sample contains no human-confirmed review-level negatives.

For the next experiment, add human-labelled full reviews that are strictly history-only, exhibit-only, or unrelated-incidents-only, as well as mixed reviews. Audit **reject precision, recall of KEEP, and evidence-anchoring quality** separately.

**Files:** `decisions.jsonl` contains all original full reviews, raw model messages, parsed decisions, reasons and strict validation flags. `manifest.json` freezes source and prompt/schema hashes. This is an initial test, not a validated gate.

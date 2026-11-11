# Stage 1A — Step 4A: NLI relevance gate on five real Google reviews

**Executed:** November 11, 2026. [GitHub Actions run 43093636596](https://github.com/UsernameIsJoe/Atmosphere-grounding/actions/runs/43093636596): direct and metarelevance jobs both **success**.

## Experimental contract

- Same five **real** Google Places reviews from the previous five-review experiments, verified by source hash; 20 original clauses and 3 emotions (Calm, Inviting, Safe): **60 clause×emotion** cases per formulation.
- No synthetic source comments. No LLM annotation calls. No score threshold fitted or applied.
- `facebook/bart-large-mnli`, pretrained three-way NLI, `contradiction / neutral / entailment`.
- Two hypotheses fixed before inference:
  - **Direct:** "This place is [calm/inviting/safe]..." Relevance defined as `P(entailment)+P(contradiction) = 1-P(neutral)`. Direct direction remains separately identifiable.
  - **Metarelevance:** "This passage contains evidence about whether the place is [calm/not calm, inviting/uninviting, safe/unsafe]." Relevance defined as `P(entailment)`.
- Outputs saved as workflow artifacts `stage1a-nli-gate-5-direct` and `stage1a-nli-gate-5-meta`: complete score vectors per case and diagnostics.
- Existing hand-chosen source-exact `data/evaluation/stage1a_gate_anchor_cases.json` is used as a **behavior check**, not independent gold labels. Its `retain` expectation also covers borderline review-worthy ambiguous clues.
- Compared with executed two reranker experiments: [cross-encoder benchmark 43092641309](https://github.com/UsernameIsJoe/Atmosphere-grounding/actions/runs/43092641309).

## Aggregate observations

| Model/formulation | Completed | Median score | Score range | Selected 'retain' above 'reject' pair fraction |
|---|---:|---:|---:|---:|
| Direct three-way BART | 60/60 | 0.821319 | 0.002181–0.999900 | **0.9375** |
| Metarelevance BART | 60/60 | 0.020889 | 0.001318–0.232128 | 0.6667 |
| BGE v2 m3 reranker (prior) | 60/60 | 0.0000166 | 0.0000160–0.004187 | 0.7708 |
| MS-MARCO MiniLM reranker (prior) | 60/60 | 0.0003516 | 0.0000374–0.007838 | 0.4167 |

These comparison fractions are **selected-anchor pairwise ranking statistics**, not classification accuracy, model calibration, or independent scientific validity. Score scales and query formulations are not comparable; especially, 0.82 is not an 82% probability of relevance.

## Individual errors / successes

| Real corpus evidence / emotion | Direct BART relevance | Meta BART relevance | Interpretation |
|---|---:|---:|---|
| "the sides extremely slippery." / Safe | 0.9999 (contradiction) | 0.0247 | Direct recognizes physical hazard opposing safety; meta low absolute score |
| "slip and hit their head..." / Safe | 0.9999 (contradiction) | 0.0211 | Direct recognizes injury risk; meta low absolute score |
| "protected and comforted" / Safe | 0.1107 (mostly entailment) | **0.0015** | Serious metarelevance miss of explicit felt protection |
| "There are quite a few seating areas." / Safe | 0.0352 | 0.0034 | Both comparatively low on this clear negative |
| "dirty, chaotic mess" / Calm | 0.9999 (contradiction) | 0.2321 | Both detect some negative calm signal |
| "slip and hit their head..." / Calm | **0.99985** (contradiction) | lower | Direct clearly **over-generalizes** injury risk into not-calm |
| "dirty, chaotic mess" / Safe | **0.99990** (contradiction) | lower | Direct cross-emotion high confidence is not proof of a specific safety hazard |

## Research decision

**The direct 3-way NLI formulation is the strongest candidate for further controlled assessment of the tested models, not a validated gate.** It preserves critical concrete negative safety signals that both retrieval rerankers poorly detect. However, its overall median relevance is very high (0.82) and direct high scores occur on cross-category near-misses. Naively dropping `neutral` or using `P(E)+P(C)` as a hard gate will yield false positives, especially by mapping any unpleasant fact to negative emotional qualities. Meta NLI fails explicit protection and is unsuitable alone.

**Stage 1A / Step 4A remains open**. Do NOT apply a score threshold or connect downstream LLM yet. Review complete ranking errors, improve matching of hypothesis semantics to evidence types (felt experience vs environmental indicator), and test with independent, source-grounded audited examples beyond the original five reviews. Reuse saved inference data and don't rerun model unnecessarily. Any new hypothesis or sentence-boundary experiment must be separated from this frozen evaluation.

## Files

- `scripts/stage1a_nli_gate_5.py` — fully reproducible model inference script.
- `.github/workflows/stage1a-nli-gate-5.yml` — per-formulation GitHub Actions benchmark.
- `data/evaluation/stage1a_gate_anchor_cases.json` — source-grounded, hand-selected preservation/rejection cases.

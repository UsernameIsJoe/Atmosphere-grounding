# Adjective / NLI routing — completed 2026-11-12

**Status: executed, audited, archived. No gate approved for deployment.**

**Research question:** Can a cheap adjective or generic NLI screening signal select urban-place review segments suitable for one local LLM, so difficult segments receive additional review? This study does **not** reinstate or finalize any E/T ontology. The calm/inviting/safe categories were used as downstream classification probes.

## Files

| Path | Role |
|---|---|
| [SOURCE_AUDIT.md](SOURCE_AUDIT.md) | Full research findings, numerical tables, source-level errors, limitations and unresolved human boundary cases |
| [audit_123_segments.csv](audit_123_segments.csv) | All 123 source-aligned review segments, source-review context, gate scores, model verdicts, provisional human screen and uncertain-category judgments |
| [verify_results.py](verify_results.py) | Offline integrity and statistics recomputation from the user's original run ZIP; requires no ML inference |
| [../../scripts/stage1a_gate_adj_nli_30.py](../../scripts/stage1a_gate_adj_nli_30.py) | Sampling, POS, 3 NLI checkpoints, 3 hypotheses, original/V2 LLM prompts, validation, logging, comparison |
| [../../scripts/stage1a_gate_rescue_segment_only.py](../../scripts/stage1a_gate_rescue_segment_only.py) | Separately versioned Gemma segment-only recovery |
| [../../Docs/STAGE1A_GATE_ADJ_3NLI_30_2026-11-12.md](../../Docs/STAGE1A_GATE_ADJ_3NLI_30_2026-11-12.md) | Original experiment contract and step-by-step execution/recovery history |

**Raw provenance:** The user supplied the unmodified local result archive as **stage1a_gate_results.zip**. It was inspected on November 12, 2026. It contains the complete NLI native probabilities, input manifests, POS predictions, both V2 LLMs' ratings/errors/raw responses, and separate Gemma rescue results. **Raw output logs are not committed in this GitHub directory**; retain the ZIP to reproduce exact model statistics. Original review source already lives in the repository at data/processed/reviews.jsonl.

Manifest snapshot: random seed **42**, **30 real reviews from 30 distinct locations**, **123 original review segments**. Source reviews.jsonl SHA-256 is f08422c068b8e52a40a93d14a4a3d12955d7f52997409f974a481c77748c7328. Serialized sampled segments SHA-256 is 0dfa1e791f9f34e72e500ed79875eaf6bb5a17dc232997cc6d67d87e0966e036.

## Execution process and methods

1. Sample one real review from each of 30 seeded distinct places; segment into 123 source-addressable units. Preserve original full review and exact character offsets. Never synthesize review content.
2. Detect the presence of **any** adjective with spaCy English POS, without a hard-coded emotion vocabulary.
3. Evaluate each segment against three generic, emotion-agnostic NLI hypotheses using **each of three** checkpoints: BART-large-MNLI, DeBERTa-v3-large-zero-shot, ModernBERT-large-zero-shot. This is **9 NLI pairs per segment**, retaining each model's native label space and all per-hypothesis scores.
4. Evaluate **every segment**, regardless of gate result, with the same V2 atmospheric interpretation prompt under Qwen3:8b and Gemma3:4b, each with original full review for reference resolution. Outcomes per calm/inviting/safe category: supports, opposes, mixed, none or uncertain. Validate supporting quotation against **the target segment**, preserving raw outputs and logging failures.
5. Record implementation mistakes and repairs as protocol history, rather than disguising them as scientific improvements. V1 had overly strict quotation errors and context leakage. V2 introduced source-only citation checks and conservative quotation/case normalization. Literal matching verifies provenance, **not emotional correctness**.
6. Gemma's V2 failures prompted **a separate segment-only recovery protocol**: only the 43 V2-missing segments were rerun without the full review or any generated quotation. Save separate outputs; do not conflate with full-review V2 judgments.
7. Run a **retrospective hypothetical routing simulation**: any adjective, NLI median >=0.4/0.6/0.8, adjective OR/AND NLI >=0.6. A segment selected as easy would hypothetically skip one of two LLM calls; no actual end-to-end cascade or third-model adjudication was run.
8. Manually read all 123 segments and full reviews. Assign **provisional non-blind screening bins** D (direct experiential expression), I (indirect condition), G (generic evaluative statement), X (unrelated) and tentative category directions S/O/N/U. These are **not final ground truth**, not E/T channels, and require the user's adjudication on disputed examples.

## Execution coverage

| Part | Successful records |
|---|---:|
| Adjectives; each of BART / DeBERTa / ModernBERT | 123/123 |
| Qwen V2, full-review-context | 120/123 |
| Gemma V2, same full-review-context prompt | 80/123 |
| Gemma segment-only fallback for V2 gaps | 43/43 |
| Gemma combined coverage **across different protocols** | 123/123 |
| Comparable Qwen and Gemma V2 outputs | **79 segments** |
| Any category disagreement across those same-protocol segments | **51/79 (64.6%)** |

**Critical distinction:** Qwen's three missing V2 outputs remain missing. Gemma's 43 fallback rows are **not V2 results**. The 79 shared V2 segments are the only controlled model-to-model comparison here.

## Gate findings

| Routing signal | One-model candidates | Hypothetical reduction from 246 LLM calls | Same-prompt Qwen/Gemma disagreement among selected |
|---|---:|---:|---:|
| Any adjective | 91 | **37.0%** | 38/61 (62.3%) |
| Median NLI >=0.4 | 59 | 24.0% | 25/40 (62.5%) |
| Median NLI >=0.6 | 31 | 12.6% | 12/22 (54.5%) |
| Median NLI >=0.8 | 6 | 2.4% | 5/6 (83.3%) |
| Adjective OR NLI >=0.6 | 95 | 38.6% | 38/62 (61.3%) |
| Adjective AND NLI >=0.6 | 27 | 11.0% | 12/21 (57.1%) |

Adjective POS detected **30 of 33** provisionally direct-experience statements, but only **30 of its 91 selected** segments were in that bin. This is *text-type relevance*, not reliability of one-model decisions. Model agreement likewise does **not** establish semantic accuracy.

### Hypothesis instability

| Checkpoint | Mean entailment across hypotheses H1/H2/H3 | Segments with within-model spread >0.5 |
|---|---|---:|
| BART | 0.330 / **0.870** / 0.605 | 84/123 |
| DeBERTa | 0.153 / 0.412 / 0.615 | 66/123 |
| ModernBERT | 0.091 / 0.253 / 0.485 | 56/123 |

BART's second hypothesis scored >0.5 on 119/123 segments, with little screening selectivity. Binary NLI probabilities and three-class NLI probabilities are **not calibrated against one another**; their median is exploratory.

### Model failures, runtime and limitations

- Some exact quotations were attached to **incorrect emotional claims**. Qwen interpreted “Park is good” as opposing all three categories based on unrelated context. Gemma judged “Everyone was so nice and friendly” as opposing calm. Both models overgeneralized negative maintenance/graffiti statements across multiple categories.
- Three NLI checkpoints took **~141.8 seconds** forward inference on the tested machine, excluding loading/downloading. At the >=0.6 routing cutoff, avoiding 31 Gemma calls at roughly 3.58s/call would save ~111s, less than the three-model NLI forward time. These are **hardware-specific counterfactual estimates**, excluding retries and third-model adjudication.
- The source audit identified D=33, I=48, G=19, X=23, with **87/369 provisional category judgments marked uncertain**. The audit was by **one reviewer, not blinded to model outputs**, and does not validate accuracy.
- Original source segmentation sometimes split meaningful phrases into fragments, which confounds both screening and classification.

**Conclusion:** Neither adjective POS nor this 3-checkpoint/3-hypothesis NLI ensemble demonstrated a safe one-LLM fast path. No winning checkpoint, NLI threshold, causal interpretation, E/T boundary, or deployment architecture is selected. The remaining research target is **predicting downstream model reliability**, not simply detecting semantically related text.

## Reproduce the descriptive result metrics

Keep the original, unmodified ZIP on your local machine. From the GitHub repository root:

    python research_audit/stage1a_gate_adj_nli_30_2026-11-12/verify_results.py --zip stage1a_gate_results.zip

The verifier checks source offsets, CSV/ZIP alignment, model coverage, gate scores, hypothesis sensitivity, routing call counts, and provisional screening-label counts. It makes **no network or model calls**.

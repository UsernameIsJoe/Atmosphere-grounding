# v0.5 extraction follow-up on other gate-passed reviews — time-capped results

Run date: 2026-11-16. **Status: PARTIAL_TIME_LIMIT.** The predefined runner completed its bounded schedule without manual intervention. **It did not finish all planned sentences.**

## Exact scope and setup
- Prepared source commit: `450231c4eeda04485125cd2db071bc072823cdf3`.
- [Prepared inputs and protocol](../stage1a_v05_gate_passed_followup_prepared_2026-11-16/README.md): 12 other v0.4 KEEP reviews, 71 source-exact sentences, complete original review as reference context, no target quotes borrowed from context.
- Same frozen v0.5 codebook/prompt/schema, model digests and decoding as the latest pilot; source/offset/hash preflight passed on Runpod.
- Qwen3.8 27B Q4_K_M and Gemma4 31B BF16; one pass, no retries, no secondary model reviewer.
- Runpod A100 SXM 80GB, secure cloud, quoted/allocated GPU rate **$2.19/hour**, 180GB ephemeral disk. Ollama **0.40.16**, Python **3.12.3**. Runtime details in `runtime_environment.json`.
- Timer started before provisioning. Automatic model budgets and inference cutoff reserved time to archive and terminate within 30 minutes. Setup/downloads/cold loading consumed part of the ceiling.

## Completion, not semantic accuracy
| Model | Planned sentences | Attempted | Structurally valid | Invalid | Not attempted | Fully valid complete reviews |
|---|---:|---:|---:|---:|---:|---:|
| Qwen3.8 27B | 71 | 69 | 68 | 1 | 2 | 10/12 |
| Gemma4 31B BF16 | 71 | 41 | 38 | 3 | 30 | 5/12 |

**110/142 planned calls attempted; 106 structurally valid.** Both models touched all 12 reviews. **38 sentences** have valid outputs from both models; model comparison must use this shared subset.
Qwen's first call timed out during cold startup; Gemma's invalid outputs have category-order/quotation validation errors. All raw outputs, including failures, are retained. No invalid or missing record is counted as an empty or correct judgment.
Review- and sentence-level missing lists are explicit in `summary.json` and `segment_audit.csv`. Do not present this as full 12-review coverage for either model.
Qwen emitted 74 claims across valid outputs; Gemma emitted 29. These counts have unequal denominators and are not precision or recall.

## Files
- `predictions.jsonl`: original inputs, raw responses, parsed claims, validation errors, timings and metadata, including invalid outputs.
- `manifest.json`, `runtime_environment.json`, `preflight.json`: frozen inputs, configuration and integrity evidence.
- `summary.json`: completion and matched-valid coverage.
- `claim_audit.csv`, `segment_audit.csv`: initially blank semantic-audit fields, including empty/invalid/missing sentences.
- `execution.log`: inference progress and final runner summary.
- `SHA256SUMS.txt`: hashes of exported UTF-8 text contents.

This is a development-cohort diagnostic, not independent human gold or an estimate of population accuracy. A KEEP-only test measures remaining extraction problems; it cannot establish errors prevented by the gate. T06 remains a known gate false positive for a private event and must not be silently removed or automatically counted as an emotion error.

## Cleanup and cost
Results were committed before deletion. The pod was **terminated**, and a fresh list returned **no pods**. Total time from the conservative pre-provisioning timer to confirmed termination: **28m 20s**, under 30 minutes. GPU-only estimate **$1.034**, plus disk; final billing detail had not posted. `cleanup_receipt.json` records the evidence.
The user's spending limits were **$3/hour maximum and under $3 total**. No paid resources were retained.

[Initial source checks](SOURCE_CHECKS.md) distinguish residual semantic errors from invalid outputs and unattempted targets. Audit CSVs remain the unscored original exports.

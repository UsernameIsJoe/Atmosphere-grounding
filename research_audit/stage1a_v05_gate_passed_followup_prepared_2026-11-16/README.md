# Prepared test: v0.5 extraction on remaining gate-passed reviews

Status: **PREPARED ONLY — NOT RUN**. No pod creation, model pull, or inference is authorized by this preparation.

## Question
On the other reviews accepted by the locked v0.4 eligibility gate, what directional emotion claims does the latest v0.5 extractor produce, and which are defensible against the source?

## Fixed cohort
All **12** KEEP reviews absent from the latest 12-case extraction run: **T02, T04, T06, T10, T12, N04, N06, N07, N08, N09, N10, N11**.
Gate source: `../stage1a_review_gate_v04_regression_qwen8b_2026-11-16/decisions.jsonl`.
Exclusion source: `../stage1a_v05_directional_live_2026-11-16/qwen3.8_27b__repeat1.json`.
The other **11** KEEP reviews already tested are excluded. All 13 REJECT reviews are excluded.
These reviews were used in gate development. This is new extraction coverage, not independent gate validation.

## Input preparation
`segments.jsonl` freezes **71 original sentences**, with character offsets, review hashes, source identifiers and full original review context. Every non-whitespace source character is covered exactly once. Split after sentence punctuation followed by whitespace/end, except inside parentheses; retain contrasts within sentences. No LLM segmentation and no emotion-based sentence selection.
This sentence policy is new because the prior extraction pilot used one hand-selected target per review; document it as an input-coverage change, not an extraction-prompt improvement.
Full review is reference context only; accepted quotations must come from the current target sentence.

## Unchanged latest extraction setup
- Frozen codebook/prompt/schema v0.5, checked against the latest archive hashes.
- Qwen3.8 27B and Gemma4 31B BF16, exact previous model digests.
- Calm / inviting / safe; support and opposition kept separately; E/T and referents retained.
- Temperature 0, seed 42, context 8192, output ceiling 2048, thinking disabled.
- **One pass per model: 142 planned calls.** No repeatability study and no invalid-output retries.
- Sentence order is breadth-first across the 12 reviews, identical for both models. This spreads partial coverage across reviews rather than exhausting long reviews first.
- Models run in two batches to avoid repeated model loading.

## Thirty-minute ceiling
Start one wall-clock timer **before provisioning or model downloads**. Pass that epoch timestamp as `--started-at`.
Allocate the remaining inference time equally between the two models; stop inference by **minute 27**, reserve **3 minutes** to save results and terminate the pod. The runner bounds calls and preserves partial results. The execution operator must also enforce an external **30-minute pod termination deadline**, including stalled downloads/initialization and result-transfer failures.
Preparation creates no compute. At execution, use already cached model weights where possible. If setup consumes the budget, stop; do not quietly extend the run.
Full 142-call completion is a target, not guaranteed until actual throughput is observed. Missing, timed-out and invalid calls remain explicit. Do not substitute shorter targets, a smaller model, or altered decoding to finish.

## Ready commands (NOT executed)
From this preparation branch:
```bash
python scripts/stage1a_v05_gate_passed_followup_20261116.py --stage prepare
python scripts/stage1a_v05_gate_passed_followup_20261116.py --stage run --started-at <epoch_recorded_before_provisioning> --host <ollama_url>
```
Do not call `run` until the user asks to launch.
No automatic workflow trigger is added.

## Review and reporting
Preserve all raw responses, parsed claims, validation errors, timings, token counts and manifests in `predictions.jsonl`; export `summary.json`, `claim_audit.csv` and `segment_audit.csv`.
1. Read the original sentence AND whole review for every emitted claim. Audit direction, E/T, referent and whether evidence belongs to the reviewed place.
2. Inspect every valid empty sentence for missed directional evidence. Invalid or missing output is not an empty judgment.
3. Report **reviews with at least one incorrect emotion claim / fully audited reviews**, separately by model. Report claim errors and missed evidence separately, plus exact completion denominators.
4. Compare models only on matched valid sentences; neither agreement nor exact quotations prove correctness.
5. T06 is a known gate false positive for a private wedding event. Keep it in the cohort because the gate actually passed it, and report the gate error separately from emotion/attribution errors.
6. N07 contains both explicit atmosphere and food-only sentences: examine whether extraction correctly keeps these scopes apart.
No expected emotion labels are supplied to either model; audit columns start blank.
This KEEP-only test assesses errors remaining after the gate. It cannot establish how many errors the gate prevented.

## Preparation validation
Source cross-checks completed while assembling this package: 23 KEEP minus 11 prior KEEP = 12 new reviews; all 71 targets are original source substrings; no rejected or prior-pilot review included.
Python execution/preflight has **not** been performed: an execution environment was unavailable during preparation. Run the network-free `prepare` command before leasing compute; it checks complete source coverage, identities, offsets and frozen hashes. Do not treat source inspection as a passed runtime test.

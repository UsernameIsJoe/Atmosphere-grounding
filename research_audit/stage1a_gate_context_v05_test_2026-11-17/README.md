# Whole-review gate contextual prompt v0.5 test — 2026-11-17

**Outcome: do not adopt the revised prompt. The wedding target is not fixed and previously rejected cases are newly kept.** The active v0.4 gate and Gemma-primary emotion policy remain unchanged. No ratio, unit labeling, emotion extraction or E/T classification was run.

## Completed paired comparison

All 36 original regression reviews were evaluated under each of two frozen standalone system prompts, on the same Runpod CPU with the same Qwen3:8B weights and parameters: 72 requests, 72 parseable verdicts, process exit 0. No semantic retry or post-result prompt change was used.

| Condition | KEEP | REJECT | Exact-quote/schema-valid |
|---|---:|---:|---:|
| Archived v0.4 run | 23 | 13 | 34/36 |
| Fresh matched v0.4 control | 22 | 14 | 35/36 |
| Revised v0.5 context prompt | 26 | 10 | 34/36 |

These verdict totals include parseable KEEP judgments with nonexact quotation anchors; they must not be described as 36 mechanically valid outputs per condition. Fresh control: K03 nonexact quote. Revised: K04 and U04 nonexact quotes. All original full reviews were retained unchanged; no cases were dropped or truncated.

## Wedding T06: still KEEP, but with a different justification

Old control anchor: “State Park created the perfect atmosphere for our reception”. The revised model instead chooses “The bartenders absolutely crushed it. Every drink was amazing and they somehow kept the bar moving incredibly fast all night long.” Its reason is: “The review describes the sensory environment and operational efficiency of the bar area, which are substantive characteristics of the location as a place to experience.”

Thus the explicit generic-atmosphere restriction did not resolve the underlying boundary: the model promotes staff/drink/service success into a site characteristic despite the revised prohibition. The verdict is unchanged. K01 elopement also stays KEEP, using the same taking-photos-without-interference anchor and inferring accessibility/social atmosphere.

## Changes from the archived v0.4 decisions

| Review | Archived v0.4 | Revised | What the revised output treats as relevant |
|---|---|---|---|
| U02 | REJECT | KEEP | Art spread across the broader MIT campus, rather than the reviewed venue |
| T08 | REJECT | KEEP | Comfortable/welcoming phrase within the personal/service account |
| N05 | REJECT | KEEP | Restaurant-grade kitchen mention within the shelter food-policy complaint |

No archived KEEP verdict becomes REJECT. T08 and N05 conflict with the researcher's recorded REJECT judgments. U02 conflicts with the prior provisional codebook interpretation. These results do not establish overall accuracy, but show the intended safeguard did not hold and earlier distinctions weakened.

## Fresh-control qualification

The matched prompt-only comparison has four changes: U02, T08, N05, N10, all REJECT to KEEP. N10 is an explicit parking-permit access rule: it was KEEP historically, REJECT in the fresh v0.4 control, and KEEP under v0.5. It is therefore a restoration against the historical result, not one of the three newly kept historical rejections. The fresh control reproduces 35/36 historical verdicts. Historical v0.4 did not pin a weight digest; CPU/GPU/backend numerical variation is also possible. The fresh paired run shares exact pinned weights, runtime, hardware and options, so it is the appropriate within-run prompt comparison.

## What changed in the specification

The v0.5 draft keeps one full-review binary decision and the same three output fields. It adds explicit event/service outcome versus described-place-quality checks, blocks inferred venue capabilities from particular staff or meal outcomes, says generic atmosphere praise is insufficient, requires reasons to name a real place characteristic, and preserves substantive mixed-review observations without ratios or a blanket event exclusion. No literal cohort examples are embedded in its system message.

The observed model behavior does not reliably implement those distinctions: its anchor and explanation change without removing the wedding false positive. The revision is not evidence that all prompting approaches fail; it is evidence against adopting this exact draft on this gate model.

## Execution and provenance

- Gate model: qwen3:8b, Q4_K_M, digest 500a1f067a9f782620b40bee6f7b0c89e17ae61f686b92c24933e4ca4b2b8b41.
- Ollama 0.40.16. Both prompts: temperature 0, seed 42, context 8192, output limit 512, think false, CPU threads 8.
- Runpod CPU3 compute-optimized, 8 vCPU / 16GB RAM, $0.24/hour. GPU allocations advertised by the catalog failed; no GPU pod was rented. The matched CPU control was used to account for the runtime change. No persistent mounts.
- Initial CPU preflight selected 32 threads automatically and was abnormally slow. It was stopped before any verdict was recorded; its manifest, log and exit 143 remain under preflight_default_threads/. The runner was then explicitly pinned to 8 threads equally for both conditions before collecting the full 72-record comparison. This changed execution settings, not either frozen prompt or codebook. The scored batch finished without interruption.
- Both system messages are standalone, matching the v0.4 runtime contract. Codebooks are supporting specifications with recorded hashes, not separately injected text; no downstream emotion codebook is fed to the gate.
- The 36 reviews are previously used development/regression material, not a blind holdout. No full human gold set or independent accuracy claim is supplied.

## Artifacts

[manifest.json](manifest.json) records input, prompt, supporting-codebook, schema and runner hashes. [runtime_environment.json](runtime_environment.json) records exact weights/runtime/CPU. [decisions.jsonl](decisions.jsonl) preserves all raw outputs, reasons, quotes, validation errors, timing and original reviews. [comparison.json](comparison.json) joins historical, fresh-control and revised outputs. [comparison.csv](comparison.csv) is a compact audit table. [summary.json](summary.json), [experiment.log](experiment.log) and [experiment.exit](experiment.exit) document completion. Cleanup is recorded separately after verified archival.

Frozen source inputs: research_audit/stage1a_review_gate_v04_regression_qwen8b_2026-11-16/cases.jsonl. Frozen drafts: Docs/STAGE1A_REVIEW_ELIGIBILITY_GATE_PROMPT_V0_5_CONTEXT_DRAFT_2026-11-17.md and its corresponding codebook. Runner: scripts/stage1a_gate_context_v05_test_20261117.py. Use prepare before renting compute; use run on Runpod. No active-gate configuration changed.

# V5 scenario-aided gate test — 2026-11-17

**Outcome: mixed results, not a clear adoption win.** V5 rejects the wedding and elopement without the focus-first version's broad over-rejection, but loses one previously kept mixed review and newly keeps two previously rejected reviews. Keep v0.4 as the front runner pending review. No further prompt editing or inference was initiated.

## Completed decisions

Same 36 original full reviews and pinned Qwen3:8B model; fresh v0.4 control and saved v5 scenario prompt on the same Runpod CPU8 setup. 72 requests finished, all 72 verdicts parseable, exit 0. No semantic retry, data truncation, ratio, focus-first labels, emotion extraction or E/T calls.

| Condition | KEEP | REJECT | Strict mechanical validity |
|---|---:|---:|---:|
| Archived v0.4 | 23 | 13 | 34/36 |
| Fresh matched v0.4 | 22 | 14 | 35/36 |
| V5 scenarios | 22 | 14 | 36/36 |

Equal fresh KEEP/REJECT totals mask six changed decisions. Control K03 has a nonexact anchor; v5 has no schema/quote errors. Mechanical validity is not semantic accuracy.

## Changes versus matched v0.4

| Review | Control | V5 | Interpretation against existing project judgments |
|---|---|---|---|
| K01 elopement | KEEP | REJECT | Desired target correction: personal event and individual kindness |
| T06 wedding reception | KEEP | REJECT | Desired target correction: event/service success is not independent place evidence |
| U01 birthday/dance-floor space | KEEP | REJECT | Loses explicit spatial-use information; prior KEEP was provisional; review needed |
| U02 exhibits/other campus sites | REJECT | KEEP | Reintroduces the previously rejected/provisionally labeled other-site recommendation case |
| N05 shelter food policy/kitchen | REJECT | KEEP | Conflicts with the researcher's recorded REJECT judgment; incidental facility mention again becomes the anchor |
| N10 parking-permit access restriction | REJECT | KEEP | Restores the historical v0.4 KEEP; access rule is valid under the retained gate criteria |

Compared with archived v0.4, five verdicts change: K01, U01, U02, T06, N05. N10 was already KEEP historically, so it is a restoration versus the fresh control, not a new improvement over the archived front runner. The fresh control reproduces 35/36 archived verdicts, with only N10 differing, as in the previous CPU tests.

T08, T11 and N12 remain REJECT. K02 restroom, K05 park/chickens, U04 museum, U05 station, N08 environment and N11 design/handwashing remain KEEP. Thus the scenario version avoids most of the v0.6 focus-first losses while retaining the original any-qualifying-place-observation policy. This is a developmental regression comparison, not a complete independent accuracy/precision/recall evaluation.

[CHANGED_REVIEWS.md](CHANGED_REVIEWS.md) contains all six paired changes, exact original reviews, anchors and reasons. [comparison.csv](comparison.csv) contains all 36 cases.

## What the explanations reveal

For the wedding, v5 explicitly says the positive comments concern the reception's event/service experience rather than independent site conditions. For the elopement, it distinguishes individual kindness and event management from place qualities. These are the intended general scenario distinctions.

For U01, v5 dismisses the space reserved for dancing as temporary/tangential despite the explicit preservation of mixed-review spatial and use information. For N05, it treats the kitchen equipment as meaningful facilities evidence despite the exclusion for incidental equipment in a food-policy dispute. For U02, it attributes public art across the campus to the reviewed location. These show the scenario exceptions and reviewed-entity boundary are still not applied consistently. Do not automatically assume every changed case has independent human gold: U01/U02 prior labels were explicitly provisional.

## Measured speed

One sequential block per condition, same model/CPU/options, first case K01 excluded from both warmed medians (35 remaining reviews each):

| Measure | V0.4 | V5 |
|---|---:|---:|
| Warm median seconds/review | 5.720 | 6.716 |
| Warm p90 seconds/review | 9.207 | 9.966 |
| Total inference seconds, all 36 calls | 243.889 | 279.887 |
| Median output tokens | 46 | 56 |
| Median input-evaluation seconds | 1.986 | 2.065 |
| Median generation seconds | 3.572 | 4.313 |

The warmed median increases **17.41%**, approximately **1.0 second per review**. Total inference time increases **14.76%** (about 36 seconds across 36 reviews). V5 still uses one model call per review. Longer generated reasons are associated with much of the extra measured generation time; that is an inference from token/duration records, not a separately controlled causal test.

This is a one-pass CPU batch measurement with fixed control-first order and prompt-cache reuse within each block. It is not a universal GPU latency claim, uncached-request benchmark or repeated-load performance estimate. Median differences also reflect different decisions and output lengths. Raw per-case times, token counts and API durations are preserved.

## Specification and comparison limits

V5 is the scenario-aided draft, not the earlier v0.5 context rewrite or v0.6 focus-first version. It retains the v0.4 three-field output and mixed-review policy, adds four common insufficient-evidence scenarios plus exceptions, and does not implement keyword bans, main-focus requirements or ratios.

**The candidate also removes v0.4's inherited quotation examples and case-level calibration to avoid reusing test material as examples.** Therefore this tests the complete saved v5 package, not an isolated addition of scenario rules. The draft and manifest disclose that example-inventory change. The scenarios themselves were motivated by development-case errors, so the same 36 reviews remain a regression set rather than an unseen holdout. No fresh reviews or expected verdicts were added to the per-review model payload.

Executable prompts are standalone; supporting codebooks are versioned policy specifications with recorded hashes, not extra text injected into each model call. Prompt/codebook source files remain as-authored snapshots with their original untested headers; current tested status is recorded in the separate draft configuration and handoff note. No active v0.4 prompt, codebook, schema, runner or pointer changed.

Both conditions receive full review text without semantic place name/type. U02's scope error may involve ambiguity about the reviewed entity; this is a possible explanation, not a demonstrated fix. The historical run lacks a pinned weight digest; the fresh paired comparison pins weights/runtime/settings and shares the same hardware.

## Runtime and artifacts

Runpod CPU3 compute-optimized, 8 vCPU / 16GB RAM, $0.24/hour, explicit num_thread 8. Qwen3:8b Q4_K_M digest 500a1f067a9f782620b40bee6f7b0c89e17ae61f686b92c24933e4ca4b2b8b41, Ollama 0.40.16. Temperature 0, seed 42, context 8192, output limit 512, think false. No persistent mounts.

[manifest.json](manifest.json) records frozen hashes and the speed protocol. [runtime_environment.json](runtime_environment.json) records exact model/runtime/hardware. [decisions.jsonl](decisions.jsonl) preserves all raw/parsed outputs, source reviews, validation, timing, token counts and API duration fields. [comparison.json](comparison.json), [comparison.csv](comparison.csv) and [summary.json](summary.json) contain the joins and aggregate counts. [experiment.log](experiment.log) and [experiment.exit](experiment.exit) document ALL_72_REQUESTS_FINISHED and exit 0. Cleanup is recorded separately after verified archival.

Reproduce with scripts/stage1a_gate_scenarios_v5_test_20261117.py prepare, then run on Runpod. The accepted v0.4 gate remains active; Gemma-primary emotion extraction and retained Qwen comparison are unchanged.

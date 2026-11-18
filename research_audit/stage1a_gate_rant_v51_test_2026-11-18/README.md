# V5.1 hostile-rant gate test — 2026-11-18

Completed all 72 calls on Runpod. Tested, not adopted; active v0.4 unchanged.

| Measure | Fresh v5 control | V5.1 rant draft |
| --- | ---: | ---: |
| Reviews | 36 | 36 |
| KEEP | 22 | 22 |
| REJECT | 14 | 14 |
| Strictly valid outputs | 36 | 35 |
| Warm median seconds | 9.727 | 11.406 |
| Total inference seconds | 443.388 | 517.523 |

**0/36 KEEP/REJECT changes** between fresh v5 and v5.1. All fresh v5 verdicts reproduce archived tested v5. N05 remains KEEP in both, failing the motivating researcher adjudication. V5.1 still cites "They have a nice restaurant grade kitchen, too." and describes it as a physical facility characteristic. The new instruction did not produce the requested exclusion for that review.

K01 elopement and T06 wedding remain REJECT; U01 remains REJECT and U02 KEEP. Both conditions agree with 2/3 current researcher adjudications (U01, U02, N05); these are not full-cohort accuracy estimates.

V5.1 U04 KEEP has a nonexact anchor: it collapses doubled spaces in the original. Preserve its raw verdict and mark strict validation failed; do not count it as a valid downstream acceptance or silently change it into REJECT. No calls retried or outputs repaired.

Compared with historical v0.4 (23 KEEP / 13 REJECT), both conditions differ on K01, U01, U02, T06, N05. This reproduces prior v5 changes; it is not a new v5.1 improvement.

## Interpretation

The hostile-rant amendment had no verdict benefit on this development regression set and increased warm median latency 17.26% (9.727 to 11.406 seconds). This single fixed-order CPU test has prompt caching and unequal output lengths; it is not a general hardware speed estimate. The model may have treated N05 as covered by safeguards for allegations/accountability requests, or simply failed to enforce the instruction; the final output does not establish which.

Do not adopt this draft based on these results. No new prompt tuning or automatic rerun follows. Spam and duplicate filters were suggested but are not implemented or tested here. No emotion extraction or E/T calls occurred.

## Protocol and artifacts

Same 36 complete original reviews, same Qwen3:8B Q4_K_M model digest, temperature 0, seed 42, context 8192, output limit 512, think false, CPU threads 8. One full-review gate call per condition/review. No test labels, case IDs or prior verdicts in model input. Codebook is supporting specification; exact standalone system message comes from the prompt fence. Whole-review hostile-rant screen is the amendment versus tested v5. Prompt/codebook draft text is frozen byte-for-byte for reproducibility; its pre-run status header is superseded by this report and candidate config.

Source commit: 628e3fda8a48ffcf73900d9d95038a35a3506392.
Runner: scripts/stage1a_gate_rant_v51_test_20261118.py.
Runpod pod: dswqmlpyt888wn, cpu3c / 8 vCPU / 16 GB, US-CA-2, $0.24/hour.
Georgia placement failed for capacity before a pod was created; California succeeded at the same rate.
All 72 calls finished normally with exit code 0; no interruption.
See manifest.json, runtime_environment.json, decisions.jsonl, comparison.json, summary.json, run.log, run.exit and pod_creation.json. Cleanup receipt is recorded after archiving.

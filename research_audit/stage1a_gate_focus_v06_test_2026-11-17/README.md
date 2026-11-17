# Focus-first gate v0.6 test — 2026-11-17

**Outcome: wedding and elopement are rejected, but the gate over-rejects relevant place information. Do not adopt v0.6; keep the accepted v0.4 coarse gate.** This completes the proposed final prompt-polishing test on the current 8B gate model. No further prompt or model run was initiated.

## Completed results

Same 36 authentic full reviews, same pinned Qwen3:8B weights, same Runpod CPU and inference settings for both conditions. All 72 requests finished; exit 0. Prompts, supporting codebooks and schemas stayed unchanged during inference. No ratio, emotion extraction, E/T assignment, semantic retry or early cutoff.

| Condition | KEEP | REJECT | Mechanical validity |
|---|---:|---:|---:|
| Historical v0.4 | 23 | 13 | 34/36 |
| Fresh matched v0.4 | 22 | 14 | 35/36 |
| Focus-first v0.6 | 12 | 24 | 36/36 |

The control's only mechanical error is K03's nonexact quote. All v0.6 responses satisfy the five-field schema, emit focus first, provide nonempty summaries/reasons, and obey encounter => REJECT. Mechanical success does not mean semantic correctness.

## Target cases

- **T06 wedding: KEEP -> REJECT.** Focus: encounter. The model summarizes the review as planning and executing a reception, praising particular staff and the event outcome.
- **K01 elopement: KEEP -> REJECT.** Focus: encounter. The model treats the review as a personal event and interactions with specific people, rather than a place assessment.
- Previously rejected T08, T11, N05 and N12 remain REJECT. The failed v0.5 context draft's new keeps of U02/T08/N05 are not reproduced.

## Cost in previously kept material

Against the fresh matched v0.4 control, 10 reviews change, all KEEP -> REJECT:
K01, K02, K05, U01, U04, U05, T06, N06, N08, N11.

Two are the target event reviews; **eight others are also rejected**. Against historical v0.4 there are 11 changes: those ten plus N10. N10 (parking-permit restriction) was already rejected by the fresh control, so its difference from the historical run must not be attributed to this focus-first intervention.

Examples of relevant information lost:

- **K02 restroom:** graffiti, dirt, darkness and a broken handwashing station. The model calls this an encounter with restroom maintenance and says there is no place observation “beyond the restroom,” even though the restroom is the reviewed place in the existing codebook.
- **U05 station:** cleanliness and a closed restroom. The model reduces the review to an encounter with bathroom closure and ignores place condition/access information.
- **N11:** “Good design, and comfortable. Hand wash not working, but probably gonna be fixed.” The model calls this an encounter with a handwash station and dismisses its functionality as minor, despite explicit design and comfort content.
- **U04 museum:** all-age suitability, visit experience, relative cost and commute. These are now characterized as an encounter/general impression rather than venue visitor experience.

Other changes (K05, U01, N06, N08) need review against the intended policy. Some loss of minority place evidence in encounter-centered reviews is an intentional consequence of the new main-focus requirement; do not automatically label every changed verdict an error. K05's prior KEEP interpretation was explicitly provisional. No complete independent human gold set or overall accuracy estimate is claimed.

See [CHANGED_REVIEWS.md](CHANGED_REVIEWS.md) for all 11 historical changes, full original reviews, focus summaries and reasons; it identifies which ten also differ from the fresh control.

## Diagnostic pattern and interpretation

Focus labels: **12 place, 24 encounter, 0 mixed**. The model never uses the intended mixed category. It does identify the target event narratives, but also places ordinary facility conditions and visitor experiences under encounter. Thus the target improvement comes with clear loss of useful place evidence; this is not a reliable gate fix.

The test changes the eligibility policy AND adds a focus-first response format; it does not isolate the effect of either component alone. Both executable system messages are standalone and their supporting codebook hashes are archived, as with v0.4. Historical development examples inherited from v0.4 remain development guidance, not an unseen holdout.

Both conditions receive only the complete review text, not a semantic place name/type. The restroom rejection's explanation reveals a reviewed-entity misunderstanding. Missing target-place context is a possible contributor, not a tested causal explanation or proof that adding metadata would fix the gate. No post-hoc input amendment or rerun was performed.

The fresh control reproduces 35/36 historical v0.4 verdicts (N10 differs), matching the previous CPU control run. Historical weight identity was not recorded; backend/hardware variation can also matter. Use the fresh paired comparison for prompt-package changes, while retaining the historical comparison requested by the researcher.

## Runtime and reproducibility

Runpod CPU3 compute-optimized, 8 vCPU / 16GB RAM, $0.24/hour; explicit num_thread 8 from the first call. Qwen3:8b Q4_K_M digest 500a1f067a9f782620b40bee6f7b0c89e17ae61f686b92c24933e4ca4b2b8b41; Ollama 0.40.16. Temperature 0, seed 42, num_ctx 8192, num_predict 512, think false. Both conditions use identical full-review inputs; v0.4 returns three fields, v0.6 five. No persistent mounts.

[manifest.json](manifest.json) records input, prompts, supporting codebooks, schemas and runner hashes. [runtime_environment.json](runtime_environment.json) records weights and hardware. [decisions.jsonl](decisions.jsonl) preserves all raw/parsed responses, exact original reviews, quotes, reasons, validation and timing. [comparison.json](comparison.json) and [comparison.csv](comparison.csv) join historical/control/focus outputs. [summary.json](summary.json), [experiment.log](experiment.log) and [experiment.exit](experiment.exit) document complete execution. SHA256SUMS.txt covers these artifacts; a later cleanup receipt documents verified archival before termination.

Reproduce with scripts/stage1a_gate_focus_v06_test_20261117.py prepare, then run on Runpod. Active configs/stage1a_review_eligibility_gate_current.json remains v0.4; Gemma-primary downstream emotion policy is unchanged.

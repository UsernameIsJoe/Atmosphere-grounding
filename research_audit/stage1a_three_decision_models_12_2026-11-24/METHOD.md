# Three native decision-model tests: method

November 24, 2026. The researcher authorized testing the first three shortlisted candidates: Mammoth-1, Karpo-decision-31B and GLiDE 27B. This document describes the design frozen before inference. Results are reported separately.

## Task and inputs

Use the same twelve real review targets as the earlier Qwen, Gemma and PPLX-Decider tests, with the same full-review context and v0.5 codebook. Calm is the only measured emotion. The target supplies evidence; context may clarify attribution, referents and scope but may not supply a separate target claim. The separate relevance gate is not rerun. Some deliberately difficult targets can fail that gate, so this is not production acceptance-rate or accuracy measurement.

The four mutually exclusive alternatives remain neither, support only, opposition only and both. Neither means no qualifying calm evidence. Both means qualifying claims in both directions. Neither is not an abstention option, and both is not uncertainty between support and opposition. No extra "I don't know" option is introduced into this matched comparison. In particular, Mammoth's public abstention-related consistency result cannot be presumed to apply to these four alternatives.

Every original-wording native request is structurally identical to its saved Decider request, including criteria insertion order. Model-specific rendering, answer codes, attention and inference precision follow each native runtime. These are complete-system comparisons, not an isolated test of a decision head or base architecture.

## Frozen artifacts

| Candidate | Checkpoint revision | Runtime |
|---|---|---|
| `baselabs/mammoth-1` | `858aab610d4d124315ebf72d2f36c5e7341f758f` | OneJev `81ce62f1597c91e46767d4d02d6ac2e18534fe94`, with the checkpoint author's `serve.patch` |
| `MachinePulseAI/karpo-decision-31B` | `b8e6fd7463cea8662c556d6257955d7ef9c10d19` | Native `karpo-decision`, commit `c52d3507a254d3ad8423726c6bc6568c99113e7d` |
| `fastino/GLiDE-27B` | `061c7d4312670f98261c007f5fd24851a64124dc` | Native `glide` package included in that exact checkpoint |

GLiDE is the current recurrent 27B checkpoint, not the earlier v1.2 artifact. Its published `midloop` configuration is retained; no adaptive-thinking toggle is invented. The same 96 GB RTX PRO 6000 Blackwell Server Edition is used serially for all three candidates. Mammoth has a separate torch 2.8/CUDA 12.8 environment and the published inference dependency constraints. Karpo and GLiDE share the GLiDE-pinned torch 2.14/transformers 5.17 stack, with Karpo's own native package added. Installed versions and actual accelerator paths are retained in runtime records and logs.

Mammoth uses supported sequential branches, avoiding its automatic synthetic fork-selection probe. A new prefix is computed for each request, with the native within-request prefix cache and suffix computation retained. Karpo and GLiDE use their full native decision forwards. There is no cross-request cache, generative sampling, new quantization, fitted temperature or runtime probability softening. These different attention/cache designs are declared, rather than replaced with a shared generic chat runner.

## Conditions and counts

| Component | Per model |
|---|---:|
| Original wording: 12 cases × 4 cyclic criteria orders × 10 shuffled repeats | 480 decisions |
| Two extra task-instruction wordings: 12 cases × 4 orders × 3 shuffled repeats | 288 decisions |
| Original wording/canonical order after one model unload/reload | 12 decisions |
| **Total** | **780 decisions** |

The planned three-model total is 2,340 decision records on twelve development targets. Repeats and variants are not independent review samples. Actual completed counts must be checked against this plan. Mammoth's native prefix/suffix route uses two model forwards for a one-question decision, while the other two use one; counted module forwards are recorded per call rather than inferred from the number of records.

Four cyclic orders let each criterion occupy every position once. Native reordering changes positions and internal answer-code assignments jointly. This is not Gemma's earlier isolated letter-assignment factor, and it is not all 24 permutations.

The two extra instruction wordings preserve the codebook, criterion definitions, review text, evidence scope and logical task. Only the terminal task explanation is paraphrased. This is a bounded instruction-wording check; it does not test paraphrases of the reviews, emotion definitions or every plausible equivalent prompt. Existing Decider, Gemma and Qwen data are reused only for their matched original-task comparisons; no matched new paraphrase results are assumed for them.

## Native scores and checks

Every scored evaluation calls the native decision API. Raw pre-temperature option scores are captured from that same evaluation: Mammoth's documented debug diagnostics, Karpo's native logits method observed without changing its returned values, and GLiDE's native logits method observed the same way. The returned probabilities are retained intact. Reapplying each runtime's own temperature and softmax is checked against every native response.

"Raw" here means the native pre-temperature, pre-softmax option scores. It does not assert that every family has the same head, internal soft-cap or numerical scale. Native score scales and API fields named `confidence` must not be treated as comparable independent correctness measurements across models.

### Formatter correction recorded during execution

Mammoth's official `make_choice` formatter normalizes probabilities and rounds each to six decimals. The initial common harness compared that displayed output with the unrounded softmax using a tighter numerical tolerance, and stopped during its second decision. One successful readout and that attempt's logs/runtime were preserved in `attempts/mammoth_initial_rounding_guard/`; the second decision had run but its scores were not appended because the assertion came first. These two extra native decisions account for four additional top-level model forwards outside the completed primary schedule.

The explicit `MAMMOTH_FORMATTER_AMENDMENT.json` records the correction before the complete Mammoth rerun. `run_model.py` remains the original execution source for Karpo/GLiDE and the failed initial Mammoth attempt. `run_mammoth.py` compares through the official formatter, retains both the native six-decimal probabilities and the unrounded normalized native softmax from the same captured scores, and runs the unchanged full input schedule. Mammoth's analysis uses the unrounded vector to avoid display rounding masking tiny alternatives. No weights, temperature, wording, codebook or decision computation were changed.

Karpo's formatter also renormalizes the float32 softmax. The original harness's largest difference from its pre-formatter calculation was 1.61e-7 in absolute probability. An offline check using the full official formatter reproduced all 780 saved native vectors exactly, without model inference. These are formatting checks, separate from observed repeat variation.

The native published temperatures are used as supplied, without fitting to these twelve targets. Full four-state distributions, selected states, all four logits, exact request hashes, rendered token IDs, token counts, timings and actual forward counts are saved. Requests must fit their context limits without truncation or splitting; the harness checks that each one-question request remains a single valid condition.

## Analysis

For identical-input repeatability, group by case, wording and order. Report exact equality of native probability and raw-logit vectors, largest max-minus-min state-probability range, and changed winners. Compare reload observations directly with the first original observation; comparisons with an arithmetic mean can add irrelevant floating-point averaging roundoff.

For each target's original-wording order sensitivity, average repeats within each order, then take the largest max-minus-min probability range of any one semantic state across the four orders. Report the median, mean and maximum of these twelve target-level gaps. Record verdict changes separately.

For combined predictions, average four full probability vectors after aligning their semantic state names. The primary comparison uses original-wording vectors only. It does not take component-wise medians, average code letters or apply softmax to mean logits.

For wording sensitivity, first obtain that four-order probability mean for each of the three wordings. Measure the largest state-probability range across the three means per target, plus changed mean winners and total-variation distance from the original. Also retain the largest wording difference with order held fixed; averaging over orders can hide a sensitive individual presentation.

Compare native hard verdicts and distributions with saved Qwen semantic-order, Gemma T=1/T=4 mapping-mean and Decider native order-mean baselines. Their wrappers, precisions, temperature settings and factor definitions differ, so these are descriptive practical comparisons.

## Qualitative evaluation and limits

The current assistant reads the original targets and full context against the unchanged codebook, then assesses whether the actual probability alternatives are semantically defensible. The earlier discussion is visible, so this is not a blinded audit. Prior human agreement on a Gemma case does not establish a human-assigned probability distribution for a new model.

No inherited verdict table is promoted to independent ground truth, and no NLL, Brier, accuracy, calibration or training-utility claim is made from these twelve cases. Lower saturation, agreement with Gemma, stable computation and a larger probability margin are distinct observations. None by itself establishes a correct attribution of the visitor's emotion to the place.

## Budget and preservation

One owned pod is rented at the live quoted $2.69/hour, below the researcher's $3/hour ceiling. The new run targets under $3 total. The frozen protocol stops new inference after 50 minutes from pod creation, leaving time to preserve results and terminate the pod before the stated budget. Original logs, failures if any, source hashes, weight checksums, raw results and exact completed counts are retained. Termination and cost are reported from observed timestamps, with compute estimates distinguished from an invoice.

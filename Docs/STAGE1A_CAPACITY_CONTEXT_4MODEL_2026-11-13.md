# Stage 1A — Model capacity × context, 4-model controlled capability study
**Freeze:** November 13, 2026. **Status: implemented, offline tests prepared; no new GPU inference performed.**

## Decision being tested
We do not know whether the errors in the earlier 12-whole-review experiment came primarily from limited model ability, weak inference rules, or review-context confusion. This is a paired **practical capability test**, NOT a pure model-parameter causal experiment. We test larger models and context on exactly matched real target segments.

Existing 12-review results: qwen3 8B Q4 23/36 verdict agreement; qwen3.6 27B BF16 27/36; gemma4 31B BF16 29/36 against an AI-prepared, partly human-adjudicated reference. Small and purposive, not population-level accuracy. Those old results used `think=false` and a different whole-review prompt; NEVER treat their raw scores as matched results here.

## Models (official Ollama tag; record immutable model digest before inference)
1. `qwen3.6:27b-bf16` — ~55GB, existing stronger Qwen comparison.
2. `gemma4:31b-it-bf16` — ~62GB, existing best verdict comparator.
3. `qwen3.5:122b` — ~81GB Q4_K_M, larger Qwen mixture-of-experts, about 125B total/10B active.
4. `gpt-oss:120b` — ~65GB MXFP4, independent large reasoning architecture, about 117B total.

Models 3 and 4 do NOT have uniform weight precision or active-parameter count with the dense BF16 baselines. A win is an *operational* capability win. No GPU memory-fit or quality is promised before the `ollama ps` GPU check.

## Fixed real dataset and input conditions
Reuse only frozen `research_audit/stage1a_gate_adj_nli_30_2026-11-12/audit_123_segments.csv` (collected real reviews). Original 30 selected target indices, same 10 D, 10 I, 5 G, 5 X pre-screen composition. Screening codes are *not* gold labels.

- `segment`: target segment alone.
- `context`: exact same target segment, plus the original unmodified full review **for interpretation / referents only**.
- `repeat`: target segment twice without any additional review text. Pre-frozen context-stress subset of 10 cases only (indices 9, 10, 24, 26, 27, 32, 53, 59, 74, 87).

An evidence quote or claim drawn solely from a non-target sentence of the full review is leakage. Review context can disambiguate referents or negation, but never furnish extra target evidence. The runner flags literal context-only quotes; narrative-only leakage requires semantic audit.

## Two separate tasks, matched across 4 models and contexts
- **Evidence**: extract source-grounded claims, exact contiguous quotations from target, direct/inference/both, referent, justification. Do not assign emotions. Zero claims is a permissible correct answer.
- **Emotion**: for calm / inviting / safe, separate direct versus inference channels, verdict supports/opposes/mixed/none/uncertain, each with an ordinal -2 to +2 textual-support score and short source-specific reason. A score is not an emotion probability. The emotion task sees original text, not the other task's extraction output. This avoids cascading error.

The frozen prior prompts, validation, and screen data are reused. This trial increases `num_predict` to 4096 to allow reasoning models to finish, sets `num_ctx=8192`, `temperature=0`, `seed=42`, and retains raw responses and decoding failures. Do not tune prompts after inspecting early output.

## Thinking-mode protocol
**Primary mode: `--reasoning native`**. Do NOT send `think` at all: Ollama uses each model's supported default. Record each model's `/api/show` thinking metadata and Ollama version when deployed. Reasoning depth may differ, so between-model comparisons reflect available capability, not a standardized reasoning budget.

**Secondary mode: `--reasoning off`**, explicitly sends `think=false`, segregates outputs/manifest from native. Ollama may map this to a *lowest available reasoning level* for a model that cannot disable thinking (not necessarily literal zero thinking). Use on the 10 frozen difficult cases for the two original models, not as a second 560-response run, to investigate whether our previous no-thinking protocol suppressed capability. No manual intermediate text should enter subsequent evaluation.

## Run phases, sample counts
1. **Offline preflight now:** pull code, run `python3 scripts/test_stage1a_capacity_context_offline.py` (no new synthetic evaluation cases) and generate blank `01_gold_first_BLANK.csv` before reading model outputs.
2. **One-case smoke test:** First target from the frozen 30 × four models × both tasks in segment-only mode = **8 calls**, included in the subsequent full total. Check schema validity and `ollama ps` = 100% GPU, including both large quantized models. Fix only execution/runtime problems, not the frozen task prompt.\n3. **Capacity and correctness pilot:** 10 frozen difficult indices × 4 models × 3 inputs × 2 tasks = **240 model calls**. Verify full GPU residency for each model; capture model digests, response success, time, and context-only quote leakage. Do not change prompts after the pilot.
4. **Complete paired data:** 30 × 4 × 2 inputs (segment/context) × 2 tasks = 480 calls, plus the 80 repeat-control calls already made in step 2. This is **560 total native calls**, *including* the pilot, not 560 additional calls.
5. **Optional old-model reasoning ablation:** 10 × 2 models × 2 inputs × 2 tasks = **80 extra off-mode calls**. Can be run before or after native as long as protocol frozen.
6. **Blind evaluation:** Independent reference for 30 segments; blinded A/B/C/D outputs per target per input mode; assess quotes, missed relevant claims, referents, negation, direct/inference correctness, false positive emotion inference, emotion-channel scores, ambiguity. Analyze case-level *paired deltas* context minus segment, and 10-case repeat-minus-segment control. Stratify D/I/G/X and identify failures where model capacity and context interact. Errors stay in denominator. Since multiple segments may originate from one review, avoid pretending 90 emotion rows per mode are 90 independent reviews.

## Why this is preferable
If the large models fix errors under segment-only input, the limiting factor is model selection. If those same models fail without context but pass with context, segmentation needs better referent context. If the context mode merely copies non-target sentences, full-review context hurts auditability. If all four fail the same way, target specification / evidence mapping may be the main bottleneck. The 10-case repetition control identifies whether duplicate exposure alone matters.

## Hardware and storage, when GPU becomes available
**Preferred:** one H200 141GB Pod (pricing in your Runpod checkout is authoritative; Secure Cloud list price about $5.29/hr as of Nov. 13, 2026). Qwen3.5 122B Q4 81GB needs >80GB GPU for reliable headroom, making the previous A100 unsuitable for this arm. An RTX PRO 6000 96GB *might* load it with restricted context, but H200 is safer; check `ollama ps` for 100% GPU before any full run.

For a **new** Pod: 50GB container + **400GB persistent volume mounted `/workspace`**, SSH-over-TCP 22, Ollama only on 127.0.0.1:11434, `OLLAMA_MODELS=/workspace/ollama_models`, `OLLAMA_MAX_LOADED_MODELS=1`. ~55+62+81+65 = **263GB of models** before caches/temporary download overhead. The old Pod's stopped legacy volume is not automatically attached to a fresh Pod; do NOT assume its old downloads transfer or stop paying storage without checking. Verify model store configuration before pulling models.

Download only when the GPU and storage are ready:
```bash
ollama pull qwen3.6:27b-bf16
ollama pull gemma4:31b-it-bf16
ollama pull qwen3.5:122b
ollama pull gpt-oss:120b
ollama list
ollama ps
```
The existing Runpod SSH tunnel procedure remains the same, using ACTUAL current Connect-page host/port and Mac private key `~/.ssh/runpod_ed25519`. Do not expose port 11434 publicly.

## Commands — on Mac from repository root

Before renting GPU:
```bash
cd ~/Atmosphere-grounding
git pull --ff-only origin master
python3 scripts/test_stage1a_capacity_context_offline.py
python3 scripts/stage1a_capacity_context_2026_11_13.py --stage report
```
The report creates the independent 30-segment gold packet and blank blinded 70-case packets. Reference annotations must be made without seeing model answers; AI-assisted annotations should be labeled as such, and ambiguous cases may be escalated to the researcher.

Once Pod + SSH tunnel are working at `http://127.0.0.1:11435`, verify names and digests:
```bash
python3 scripts/stage1a_capacity_context_2026_11_13.py --stage check --base http://127.0.0.1:11435
```

Smoke-test one real segment in each model/task (these records are reused later):
```bash
for model in qwen3.6:27b-bf16 gemma4:31b-it-bf16 qwen3.5:122b gpt-oss:120b; do
  for task in evidence score; do
    python3 scripts/stage1a_capacity_context_2026_11_13.py \
      --stage run --base http://127.0.0.1:11435 \
      --model "$model" --mode segment --task "$task" \
      --reasoning native --limit 1
  done
done
```

Phase 1 — frozen 10 cases, all three context conditions, both tasks, all four models:
```bash
for model in qwen3.6:27b-bf16 gemma4:31b-it-bf16 qwen3.5:122b gpt-oss:120b; do
  for mode in segment context repeat; do
    for task in evidence score; do
      python3 scripts/stage1a_capacity_context_2026_11_13.py \
        --stage run --base http://127.0.0.1:11435 \
        --model "$model" --mode "$mode" --task "$task" \
        --reasoning native --pilot-context-10
    done
  done
done
```

Phase 2 — 30 target segments in paired segment/context conditions (pilot cases resume without duplication):
```bash
for model in qwen3.6:27b-bf16 gemma4:31b-it-bf16 qwen3.5:122b gpt-oss:120b; do
  for mode in segment context; do
    for task in evidence score; do
      python3 scripts/stage1a_capacity_context_2026_11_13.py \
        --stage run --base http://127.0.0.1:11435 \
        --model "$model" --mode "$mode" --task "$task" --reasoning native
    done
  done
done
```

Optional **80-call** prior-model reasoning-off diagnostic on the same 10 frozen indices, segregated results:
```bash
for model in qwen3.6:27b-bf16 gemma4:31b-it-bf16; do
  for mode in segment context; do
    for task in evidence score; do
      python3 scripts/stage1a_capacity_context_2026_11_13.py \
        --stage run --base http://127.0.0.1:11435 \
        --model "$model" --mode "$mode" --task "$task" \
        --reasoning off --pilot-context-10
    done
  done
done
```

Generate blind native and off packets locally without using GPU:
```bash
python3 scripts/stage1a_capacity_context_2026_11_13.py --stage report --reasoning native
python3 scripts/stage1a_capacity_context_2026_11_13.py --stage report --reasoning off
```

All results are saved on your **Mac** under `reports/stage1a_capacity_context_2026-11-13/`; raw model predictions are separated by reasoning setting, model, input condition, and task. Never unblind `04_blinding_key_KEEP_PRIVATE.json` before the blind human/AI-assisted error audit is frozen.

No GPU inference has been performed for this new study as of the protocol commit. Stop paid GPU compute after saving local outputs; stopped volumes may still bill and stopped GPUs may not restart if capacity is exhausted.

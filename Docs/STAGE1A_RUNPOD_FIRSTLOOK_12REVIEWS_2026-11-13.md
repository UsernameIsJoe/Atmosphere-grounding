# Runpod first look: are larger LLMs substantively better?

**Protocol freeze: 2026-11-13. Status: offline-tested, no GPU inference yet.**

This is intentionally a CAPABILITY pilot, not an E/T pipeline, a benchmark of
JSON compliance, a prompt tournament, or a new architecture. It replaces the
earlier 30-segment / two-task Runpod drafts **for the FIRST GPU run**; keep those
earlier protocols for future methodological investigations only.

## Research decision and real sample

One identical full-review prompt is used across the exact 3 models:

- qwen3:8b: previous-model baseline, same task and same full-review input.
- qwen3.6:27b-bf16: larger Qwen family.
- gemma4:31b-it-bf16: independent larger family.

The frozen input consists of **12 unmodified COMPLETE real visitor reviews**,
at research_audit/stage1a_runpod_12review_firstlook_2026-11-13/cases.jsonl.

- K01-K06: six different places/reviews containing previously identified local
  model failures, including person/place attribution, generic review praise,
  bathroom darkness/cleanliness, negation on 'looking for a walk', event
  experience, chicken/safety scope, and children/traffic danger.
- U01-U06: six additional reviews from different places that did NOT appear
  in the earlier 30-review gate audit; choose and freeze before running any
  new model. These have not been claimed globally unseen by every older
  experiment.
- Exactly 12 places, 12 reviews, 6+6. No arbitrary segment breaks. A code
  preflight verifies each complete review exactly matches collected
  data/processed/reviews.jsonl text and original place/review_index.
- No fabricated review text or external LLM-generated evaluation cases.

For each complete review, models identify direct, inferred, or both evidence
and make separate support/opposition judgments for calm, inviting and safe.
Model evidence items retain source phrases, referent and why; verbatim
matching is flagged but NOT substituted for semantic accuracy.
For each emotion the output verdict is
supports/opposes/mixed/none/uncertain, with source-basis
direct/inference/both/none/uncertain and a short source-specific reason.

We deliberately do NOT demand a numeric 0-10 emotion score here. Numeric
calibration and inference fusion are subsequent **method** questions, not
evidence that a larger model understands review meaning.

**Total:** 12 reviews x 3 models = 36 equivalent prompts. No NLI, batching,
claim-voting, segmentation choice, or tuned gates. This cannot establish
population-wide accuracy; it's a deliberate falsification-friendly first look.

## Research integrity

Before looking at predictions, fill or freeze the independent review-based
human reference CSV in the local output folder. The model cannot read this
reference. The audit should compare:

- Which source claims are present but missed, or invented? Is source quotation
  precise, and does it preserve negation and its referent?
- Did model say direct when the author only mentioned a potential inferential
  condition? Did it falsely promote generic aesthetic praise or a described
  activity to reported atmosphere? Did it recognize dual-scope statements?
- Did each calm/inviting/safe decision match the review and available
  evidence? False positives and negatives matter more than response length.
- Did a negative cleanliness/maintenance remark result in unreasonable blanket
  opposition to multiple emotions? Did it transfer people's actions or
  animals to a sweeping place-wide claim?
- Did the 27B improve vs the 8B in the SAME prompt/context? Did the 31B
  perform more reliably across the six historically troublesome reviews and
  the six less-reviewed places?

Gold annotations may be uncertain; do not force a 'correct' verdict for
reasonable disagreement. The case-level model A/B/C comparison has a separate
private reversible key. Do not call model consensus correctness.
Preserve complete raw response, decode failures, Ollama model digests, response
time and token metadata; failures remain in denominator.

## Mac (new computer): preflight BEFORE renting a Pod

Open macOS Terminal and run:

    sw_vers
    system_profiler SPHardwareDataType | grep -E "Model Name|Model Identifier|Chip|Memory"
    python3 --version
    git --version
    ssh -V
    ls -l ~/.ssh/*.pub 2>/dev/null

Mac only needs Python 3.10+, Git and SSH. DO NOT install the models, Ollama,
PyTorch, spaCy, CUDA, or NLI dependencies on the Mac for this first run.

Get code if needed:

    git clone https://github.com/UsernameIsJoe/Atmosphere-grounding.git
    cd Atmosphere-grounding

Or, for an existing repo:

    cd path/to/Atmosphere-grounding
    git pull origin master

Freeze the human review packet without any GPU/API connection:

    python3 scripts/stage1a_runpod_firstlook_12reviews.py --stage prepare

This creates reports/stage1a_runpod_firstlook_12reviews_2026-11-13/
01_human_reference_FILL_BEFORE_READING_MODEL_OUTPUTS.csv .
Fill the original-text judgments independently; leaving explicitly unresolved
cases marked uncertain is preferable to making up a reference label.
A later report run will never overwrite this file.

## Runpod account already exists: Pod + SSH key setup

1. Check whether Mac has an SSH public key. If not, generate with
   ssh-keygen -t ed25519 . Do NOT overwrite an existing key. Add ONLY the
   public .pub key to your Runpod account SSH keys BEFORE creating Pod.
2. In Runpod Pods -> Deploy, choose one on-demand **A100 80 GB** (not 40GB).
   Use the official Runpod PyTorch/SSH-capable template. Estimate ~200GB
   storage volume mounted at /workspace for about 56+63+5GB model downloads,
   plus space for caches. Confirm CURRENT displayed GPU-hour and storage
   prices before confirming any Pod. The previous verified GPU list price is
   not necessarily the displayed cost in your account.
3. Enable TCP SSH (22 inside Pod, mapped external TCP port). Do NOT expose
   port 11434 publicly. Real reviews and unauthenticated Ollama endpoints
   should never be sent to random public internet APIs. Confirm data rights
   for computing on Google-derived user reviews before cloud submission.
4. Pod web terminal, Linux, run:

       nvidia-smi
       df -h /workspace
       command -v ollama

   If missing, follow current official Ollama Linux installation
   instructions, e.g. download and review install.sh before execution.
   Verify whether an Ollama service already exists with:

       curl -s http://127.0.0.1:11434/api/tags
       ps aux | grep '[o]llama'

   Configure Ollama to use /workspace/ollama_models (rather than an
   undersized container root disk), and run it on
   OLLAMA_HOST=127.0.0.1:11434. If no process already exists:

       mkdir -p /workspace/ollama_models
       nohup env OLLAMA_HOST=127.0.0.1:11434 OLLAMA_MODELS=/workspace/ollama_models ollama serve > /workspace/ollama.log 2>&1 &

   Ensure there is only one server using the intended model store.
   The exact Ollama tags are found at
   https://ollama.com/library/qwen3.6/tags and
   https://ollama.com/library/gemma4/tags .

5. Download models sequentially:

       ollama pull qwen3:8b
       ollama pull qwen3.6:27b-bf16
       ollama pull gemma4:31b-it-bf16
       ollama list
       df -h /workspace

   These are large downloads and Pod GPU time accrues while running.
   Do not leave a paid Pod waiting for your next terminal session.

## Mac: private SSH tunnel to remote Ollama

The Runpod Connect page provides the REAL TCP SSH host and port. In a Mac
terminal use your own key filename and replace placeholders:

    ssh -N -L 11435:127.0.0.1:11434 -i ~/.ssh/id_ed25519 -p YOUR_TCP_PORT root@YOUR_POD_IP

Keep it open. In another Mac terminal from repo root:

    python3 scripts/stage1a_runpod_firstlook_12reviews.py --stage check --base http://127.0.0.1:11435

Run ONE real review per model as smoke test:

    python3 scripts/stage1a_runpod_firstlook_12reviews.py --stage run --base http://127.0.0.1:11435 --model qwen3:8b --limit 1
    python3 scripts/stage1a_runpod_firstlook_12reviews.py --stage run --base http://127.0.0.1:11435 --model qwen3.6:27b-bf16 --limit 1
    python3 scripts/stage1a_runpod_firstlook_12reviews.py --stage run --base http://127.0.0.1:11435 --model gemma4:31b-it-bf16 --limit 1

Review raw response and check Ollama ps plus nvidia-smi on the Pod:
the 27B/31B must fit on GPU; if they silently offload to CPU or malformed
schema output appears, log it and diagnose BEFORE full run. Verify
'think=false' is supported by the running Ollama/model versions. Do not
rewrite prompts or reference labels after seeing early results.

If all three are valid, finish all 12 reviews per model:

    python3 scripts/stage1a_runpod_firstlook_12reviews.py --stage run --base http://127.0.0.1:11435 --model qwen3:8b
    python3 scripts/stage1a_runpod_firstlook_12reviews.py --stage run --base http://127.0.0.1:11435 --model qwen3.6:27b-bf16
    python3 scripts/stage1a_runpod_firstlook_12reviews.py --stage run --base http://127.0.0.1:11435 --model gemma4:31b-it-bf16

After the three runs, build the anonymized comparison:

    python3 scripts/stage1a_runpod_firstlook_12reviews.py --stage report

The 02_blind_models_A_B_C.csv file has predictions side by side without
model names. Human annotators should compare it to the already frozen
01_human_reference file BEFORE looking at
03_blinding_key_KEEP_PRIVATE.json. Raw prediction folders still hold
model-name metadata for audit.

## Finish

Save the local result directory, including the original raw JSONL and
manifests. No files are produced solely on the Pod; model output is delivered
through the SSH tunnel to the Mac. Then TERMINATE the GPU Pod in Runpod and
check for any remaining storage/network charges. Merely closing the terminal
does NOT stop billing.

**Decision after 12:** If the bigger models still commit the same semantic
mistakes, do not optimize segmentation or NLI around them yet. If there is a
materially better model, then and only then design a larger human-gold test
and research how to divide claims, select contexts and score atmospheres.

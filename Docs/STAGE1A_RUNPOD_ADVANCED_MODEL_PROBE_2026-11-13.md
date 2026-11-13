# Runpod advanced LLM first-capability probe — Nov 13, 2026

**Status: experiment implemented and tested offline, but NO cloud model inference has been performed. This is a research plan, not a favorable result.**

This test directly addresses the observed local-model failures: Qwen3 8B and Gemma3 4B often conflate category meaning, mistake full-review claims for target claims, assign multiple negative emotions from generic dirty/dark/graffiti descriptions, and mishandle negation/attribution. The prior 123-segment gate study had only 79 comparable full-review LLM results, with 51 disagreements. A model's ability to generate JSON or reproduce literal quotes is not an acceptable substitute for semantic correctness. See [the completed source audit](../research_audit/stage1a_gate_adj_nli_30_2026-11-12/README.md).

## Hardware and models

Use ONE **A100 80GB GPU** on Runpod, with sequential loading of:

1. **Qwen3.6 27B (dense BF16)**, exact Ollama tag: qwen3.6:27b-bf16, model size ~56GB.
2. **Gemma 4 31B (dense instruction BF16)**, exact Ollama tag: gemma4:31b-it-bf16, model size ~63GB.

These are officially listed Ollama model tags. BF16 avoids Q4/Q8 quantization as a separate precision variable. They should fit individually on 80GB; if GPU utilization or memory residency differs, report it. They MUST NOT be held in GPU memory simultaneously. Sources: https://ollama.com/library/qwen3.6/tags and https://ollama.com/library/gemma4/tags.

**Runpod Secure Cloud A100 80GB current advertised price (Nov 13, 2026): $1.79/hr**, excluding storage. GPU time starts when Pod is running, including download/setup/idle time; 2 running hours roughly $3.58 GPU, 3 hours $5.37 GPU, PLUS volume/storage charges. Verify the LIVE price in dashboard. Give yourself a budget target (e.g. $10 GPU and storage combined), but it is NOT an automatic spending cap. Source: https://www.runpod.io/pricing.

## Frozen benchmark and exactly what it measures

Script: [scripts/stage1a_runpod_advanced_probe.py](../scripts/stage1a_runpod_advanced_probe.py). Uses Python stdlib; no extra Python libraries, no local Ollama installation, no NLI downloads.

The frozen **30 actual review segments** come directly from the previously audited 123 segments: 10 direct experiential, 10 indirect physical-condition, 5 generic evaluative, 5 unrelated. Case selection is purposive to surface earlier failures, **not random and not representative of all reviews**.

Primary controlled head-to-head: **30 segments x 2 models = 60 calls**. Both models see identical segment-only text, same system prompt, same schema, the same three categories (calm/inviting/safe), and the same five options (supports/opposes/mixed/none/uncertain). Return brief reason and place/person/other/ambiguous attribution, NO copied quotations; any malformed output is logged as failed and is not silently corrected or repeatedly retried. Use temperature=0, seed=42, think=false, context 4096, max output 500. The exact prompt and model digest are frozen in per-model manifests. Validate think=false support in smoke tests.

Second stress arm: **10 high-risk original segments x 2 models = 20 calls**, keeping the task unchanged but adding the full original review **for reference resolution only**. Analyze within-model context leakage and differences separately; never mix these with primary segment-only results.

### Quality comparison (not output formatting)

Measure false emotion assertions from unsupported positive/negative cues, appropriate none/uncertain judgments, person-vs-place attribution, negation errors, and **cross-segment context leakage**. Keep schema failures, latency, GPU residence, token counts and compute costs as separate columns. The script creates a per-case **model-blinded human A/B comparison CSV**; inspect the actual text and adjudicate each of the three emotions rather than using Qwen-vs-Gemma agreement as accuracy. Existing provisional reference annotations are **not validated ground truth**. Do not select a winner simply because a few models agree or the JSON is valid. If results are close, expand the evaluation or run small-model controls with the SAME prompt and inputs.

## Mac — start with these environment checks

Run from your Mac's Terminal. Do not install anything yet:

    sw_vers
    system_profiler SPHardwareDataType | grep -E "Model Name|Model Identifier|Chip|Memory"
    python3 --version
    git --version
    ssh -V
    ls -l ~/.ssh/*.pub 2>/dev/null

The Mac needs only Terminal, Git, Python 3.9+, and SSH. Local memory does **not** determine the VRAM available on Runpod.

## Runpod account, key, Pod

1. Sign up/log in at https://www.runpod.io/ . Examine balance, live A100 price, the trial budget and any data-use limitations for real third-party reviews.
2. Create a local SSH key **only if none exists**: ssh-keygen -t ed25519. Do not overwrite any existing key or share a private key. Copy the PUBLIC .pub key from your Mac to Runpod dashboard **Settings -> SSH public keys**. Do this BEFORE creating the Pod; Runpod injects keys at startup.
3. In Runpod, **Pods -> Deploy**; choose one **A100 80GB**, preferably Secure Cloud on-demand; template **official Runpod PyTorch**. Enable SSH access 22/TCP. No publicly exposed HTTP 11434. Select about **200GB Volume Disk mounted at /workspace** for both ~56GB and ~63GB model downloads plus overhead, and a 20-30GB container disk. Check storage pricing and actual space before confirming.
4. Click Deploy. Use the Pod's **Connect -> SSH over exposed TCP** command to obtain actual IP and port (not an invented address). Use the Pod browser terminal for initial bootstrapping.
5. Guide: https://www.runpod.io/blog/how-to-connect-to-your-pod-with-ssh-and-move-files-with-scp-and-filezilla

## On Runpod Linux terminal: start Ollama bound to localhost

    nvidia-smi
    df -h /workspace
    command -v ollama || (curl -fsSL https://ollama.com/install.sh -o /tmp/install_ollama.sh && sh /tmp/install_ollama.sh)

Before starting a new server, check for an already-running one:

    curl -s http://127.0.0.1:11434/api/tags
    ps aux | grep '[o]llama'

If no server exists, run (persistent model store and no HTTP public exposure):

    mkdir -p /workspace/ollama_models
    nohup env OLLAMA_MODELS=/workspace/ollama_models OLLAMA_HOST=127.0.0.1:11434 ollama serve > /workspace/ollama.log 2>&1 &

Verify server/model store. If the installer already started a service, ensure it is configured for /workspace before pulling models (do not start two competing Ollama processes).

    curl -s http://127.0.0.1:11434/api/tags
    ollama --version
    ollama pull qwen3.6:27b-bf16
    ollama pull gemma4:31b-it-bf16
    ollama list
    df -h /workspace

**Warning:** These are ~119GB total downloads, charged as running GPU time. If storage/billing is higher than expected, stop before pulling and reconsider the run. Securely check any data-processing restrictions before sending real review text to the Pod.

## On Mac: secure tunnel and run the actual benchmark

If you do not have the repository on this new Mac:

    git clone https://github.com/UsernameIsJoe/Atmosphere-grounding.git
    cd Atmosphere-grounding

Use Runpod's exposed-TCP SSH host and port in the following LOCAL Mac command. Port **11435** on your Mac avoids colliding with a local Ollama.

    ssh -N -L 11435:127.0.0.1:11434 -i ~/.ssh/id_ed25519 -p YOUR_TCP_PORT root@YOUR_POD_IP

Keep this window open. Open **second Mac Terminal** in repo root:

    python3 scripts/stage1a_runpod_advanced_probe.py --stage check --base http://127.0.0.1:11435

Three-case smoke tests:

    python3 scripts/stage1a_runpod_advanced_probe.py --stage run --base http://127.0.0.1:11435 --model qwen3.6:27b-bf16 --mode segment --limit 3
    python3 scripts/stage1a_runpod_advanced_probe.py --stage run --base http://127.0.0.1:11435 --model gemma4:31b-it-bf16 --mode segment --limit 3

On Pod check GPU usage with nvidia-smi and ollama ps; the models must not silently fall back to CPU offloading. Investigate any JSON-schema or thinking-API errors **before** running all cases.

Then finish the same-prompt segment-only comparison:

    python3 scripts/stage1a_runpod_advanced_probe.py --stage run --base http://127.0.0.1:11435 --model qwen3.6:27b-bf16 --mode segment
    python3 scripts/stage1a_runpod_advanced_probe.py --stage run --base http://127.0.0.1:11435 --model gemma4:31b-it-bf16 --mode segment

Optional full-review leakage arm (10 cases each):

    python3 scripts/stage1a_runpod_advanced_probe.py --stage run --base http://127.0.0.1:11435 --model qwen3.6:27b-bf16 --mode context
    python3 scripts/stage1a_runpod_advanced_probe.py --stage run --base http://127.0.0.1:11435 --model gemma4:31b-it-bf16 --mode context

Create model-blinded source review packet:

    python3 scripts/stage1a_runpod_advanced_probe.py --stage report

Outputs stay in the Mac repository under reports/stage1a_runpod_advanced_probe_2026-11-13 . Retain both raw JSONL and blinded review CSV for independent inspection. The Python script NEVER uploads the whole corpus or opens a public API port; it sends only the specified actual review inputs through the encrypted SSH tunnel.

## Stop billing

Save results to the Mac BEFORE **terminating** the GPU Pod from Runpod. Closing SSH or Terminal does NOT stop billing. After termination, inspect any remaining storage/network volumes. Source prompts may contain real reviews; protect the outputs and avoid public, unauthenticated Ollama endpoints.

**Scope of this test:** It gives an early model-selection signal on a small, purposely difficult, real-text sample. It does not prove advanced models have solved atmospheric grounding or establish an accuracy score without blind human adjudication. No change to the existing adjective/NLI routing research is implied.

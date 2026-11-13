# Runpod V2 — Direct/Inference Evidence Detection + Emotion Scoring

**Status (2026-11-13):** Implementation passed offline tests; neither advanced model has been run. This protocol supersedes the older single-task Runpod probe for new inference.

## Scientific questions

**A. Evidence detection.** Does an advanced LLM extract every source-supported claim, distinguishing explicitly described experience/atmosphere (direct) from physical, sensory, activity, social and access conditions used to infer an atmosphere (inference)? The categories are not mutually exclusive: the same passage may contain BOTH. For each individual claim, log exact source quote, referent and reason. Do not prematurely map extracted claims to emotions. Copying a correct quote is not the same as interpreting it correctly.

**B. Emotion scoring.** Independently, without seeing extraction outputs, does that same LLM correctly infer the degree and direction of support for calm, inviting and safe? Score EACH emotion separately for direct versus inferred claims, keeping none/mixed/uncertain distinct. Signed ordinal score ranges -2 to +2; it is textual support strength, NOT calibrated emotion intensity, probability, or a place-level score.

Earlier researcher rulings were important: some claims are BOTH direct and inferred; meditative walking is inference-only for calm, not automatically direct calm; quiet surrounding neighborhoods and harmless animals require preserving their referent rather than transferring uncritically to the whole park; a metaphorically welcoming gateway can directly express inviting.

## Controlled experiment

- **Authentic frozen source:** 30 purposively difficult segments drawn unchanged from the Nov 12 human audit of 123 real segments. 10 provisionally direct, 10 condition/inference, 5 generic, 5 unrelated, with known ambiguity. This is an enriched diagnostic sample, NOT a random generalization benchmark. Its screening bins are NOT fixed human ground truth.
- **Two candidate models:** Qwen3.6 27B BF16 and Gemma 4 31B BF16. Sequential execution on one A100 80GB GPU through Ollama. An optional Qwen3 8B same-prompt control can help isolate whether model scale genuinely improves performance.
- **Two independent tasks:** both tasks applied to every one of the 30 segments for each model, so 30 x 2 models x 2 tasks = **120 primary inference calls**. Task B is NOT a cascade fed from Task A. Both share original source text and comparable generation settings; prompts are separately frozen.
- **Context stress:** optional 10 fixed previously difficult segments per task/model (40 more calls). The original full review is provided only to resolve references. This arm is kept separate, because full-review context may cause leakage. No prompt tuning after observing results.
- **Settings:** temperature=0, seed=42, think=false, num_ctx=4096, num_predict=1050. Save the Ollama model digest, prompt/schema hash, raw responses, per-request latency and token-count metadata.
- **Outcomes:** direct and inference claim completeness, source-grounding and referent/scope; unsupported claims; correct none decisions; category/direction and signed score; loss of negation; leakage from outside source segment. Rejected/invalid JSON counts separately rather than being relabeled as success.

**Human reference, not another LLM judge:** Build a complete gold reference from the source texts BEFORE viewing either candidate's answers. The script creates a blank gold-first sheet and model-blind A/B comparison sheets, with a separate private model-key file. Record ambiguity explicitly. Score claim-level precision/recall (including independent direct/inference channel tags and both-channel cases) and per-emotion/channel category error + ordinal score error only on human-resolved labels; report how many cases remain uncertain. Model agreement and literal quote existence do not prove accuracy. The previous audit was provisional and nonblind.

## Mac environment: no machine-learning packages required

The user already has a Runpod account. Before provisioning anything, run on the new Mac in Terminal:

    sw_vers
    system_profiler SPHardwareDataType | grep -E "Model Name|Model Identifier|Chip|Memory"
    python3 --version
    git --version
    ssh -V
    ls -l ~/.ssh/*.pub 2>/dev/null

Only Python >=3.9, Git and SSH are needed on the Mac. Do not locally install Ollama, CUDA, PyTorch, spaCy or model weights.

The detailed Pod deployment and SSH setup are still covered in the previous guide [Runpod hardware + SSH instructions](STAGE1A_RUNPOD_ADVANCED_MODEL_PROBE_2026-11-13.md), but **its single-task inference commands are obsolete**. For this V2 use the commands here.

## After confirming SSH public key and Pod deployment

Set up a 1x A100 80GB on-demand Runpod GPU Pod; choose a compatible official Runpod PyTorch template, about 200GB volume at /workspace for both BF16 model weights, and enough container disk. Verify displayed GPU/storage prices before deploy. Never expose Ollama port 11434 publicly. Use Runpod Settings to register the Mac's PUBLIC SSH key before creating the Pod. On Pod, check nvidia-smi and disk, install/start Ollama if needed with OLLAMA_MODELS configured on /workspace, and pull:

    ollama pull qwen3.6:27b-bf16
    ollama pull gemma4:31b-it-bf16

Optional baseline:

    ollama pull qwen3:8b

On Mac, clone or update the repo:

    git clone https://github.com/UsernameIsJoe/Atmosphere-grounding.git
    cd Atmosphere-grounding

For an existing clone, enter it and run git pull origin master instead.

Using the actual IP and TCP SSH port from Runpod Connect, tunnel Mac port 11435 to the private Pod Ollama port 11434 (replace placeholder host and port, adjust key filename if different):

    ssh -N -L 11435:127.0.0.1:11434 -i ~/.ssh/id_ed25519 -p YOUR_TCP_PORT root@YOUR_POD_IP

Leave this SSH terminal running, open a second Mac terminal in the repo, and check:

    python3 scripts/stage1a_runpod_evidence_score_probe.py --stage check --base http://127.0.0.1:11435

### Smoke tests (two real cases per model/task)

    python3 scripts/stage1a_runpod_evidence_score_probe.py --stage run --base http://127.0.0.1:11435 --model qwen3.6:27b-bf16 --task evidence --limit 2
    python3 scripts/stage1a_runpod_evidence_score_probe.py --stage run --base http://127.0.0.1:11435 --model qwen3.6:27b-bf16 --task score --limit 2
    python3 scripts/stage1a_runpod_evidence_score_probe.py --stage run --base http://127.0.0.1:11435 --model gemma4:31b-it-bf16 --task evidence --limit 2
    python3 scripts/stage1a_runpod_evidence_score_probe.py --stage run --base http://127.0.0.1:11435 --model gemma4:31b-it-bf16 --task score --limit 2

Inspect outputs, confirm Ollama lists both model digests, verify GPU residency with ollama ps and nvidia-smi. If unsupported options, CPU offloading or repeated invalid JSON occur, diagnose them before the full 120-call run. Do not loosen source semantics to force passing outputs.

### Main 30-case runs

    python3 scripts/stage1a_runpod_evidence_score_probe.py --stage run --base http://127.0.0.1:11435 --model qwen3.6:27b-bf16 --task evidence
    python3 scripts/stage1a_runpod_evidence_score_probe.py --stage run --base http://127.0.0.1:11435 --model qwen3.6:27b-bf16 --task score
    python3 scripts/stage1a_runpod_evidence_score_probe.py --stage run --base http://127.0.0.1:11435 --model gemma4:31b-it-bf16 --task evidence
    python3 scripts/stage1a_runpod_evidence_score_probe.py --stage run --base http://127.0.0.1:11435 --model gemma4:31b-it-bf16 --task score

Optional same-prompt 8B baseline uses --model qwen3:8b with --task evidence and --task score. Optional full-review stress arm adds --mode context to each main run.

### Results and billing

    python3 scripts/stage1a_runpod_evidence_score_probe.py --stage report

All outputs are saved locally on the Mac in reports/stage1a_runpod_evidence_score_v2_2026-11-13 . Review 01_gold_first_BLANK.csv BEFORE 02_blind_evidence_A_B.csv and 03_blind_scores_A_B.csv. Keep 04_blinding_key_KEEP_PRIVATE.json unrevealed until gold judgments and A/B reviews are frozen. The script does not upload the full source corpus; only the fixed real-source cases are sent to the private SSH tunnel.

**Stop billing by terminating the Pod in Runpod after saving the local results; closing Mac Terminal is not enough.** Cloud GPU on-demand billing and storage both apply. Never paste SSH private keys or payment credentials into ChatGPT.

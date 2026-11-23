# Adaptive cache control

Added during execution after the native Qwen repetitions showed identical-request probability variation. It is separate from the frozen 1,248-call experiment and is not a prespecified validation set.

- Same Qwen GGUF and the exact Ollama-bundled llama-server executable; use the original server-rendered prompt for each input.
- Three diagnostic cases (K01, K06, U06), four mappings, ten repetitions under each of two conditions: 240 additional readouts.
- Randomly interleave `cache_prompt=true` and `cache_prompt=false` calls. These settings are the sole request difference for a given prompt; retain the complete native backend response, including actual cached/evaluated token counts.
- Call the direct `/completion` endpoint. Check its cached condition against native `/api/chat` results before generalizing to the public API.
- Leave Ollama's model/backend defaults, including its enabled MTP configuration, unchanged. This is a cache experiment, not an MTP ablation.
- Pause the bootstrap parent after Qwen, finish this control, unload Qwen, then resume Gemma's native study. Preserve the pause/resume timestamps.

The control tests a practical stabilizer for these twelve selected prompts. It does not prove universal deterministic inference, eliminate letter sensitivity, or establish that stable probabilities are calibrated.

# Native probability repeatability and letter mapping diagnostic

Frozen before inference, November 23, 2026. Development diagnostic using the same twelve original reviews/target segments and exact Qwen3.8 27B Q4_K_M and Gemma4 31B BF16 digests as the preceding pilot. No new gold labels or synthetic review cases.

## Questions

1. Do changes between letter mappings exceed variation between identical requests?
2. Does probability saturation conceal movement in Gemma's relative logits?
3. On the identical Gemma GGUF weights, what do captured pre-softmax scores and the analytic inverse of soft-capping show? Do not call these new values calibrated confidence.

## Native experiment

- Preserve original Ollama 0.40.17 payloads byte-for-byte for the original ABCD and first BCDA mapping, checked against the previous request hashes. Add CDAB and DABC, preserving semantic option order and all question wording.
- Same four states: neither, support only, opposition only, both. Calm only; full review resolves context; target remains the source unit.
- Ten repetitions per case/mapping/model, interleaved in reproducible shuffled blocks. Reload each model, then repeat three times per case/mapping. Total: **1,248 native decision readouts** (624 per model).
- Preserve temperature 0, seed 42, context 8192, top_k 0, top_p 1, min_p 0, repeat_penalty 1, disabled thinking output, one decision token and top twenty native alternatives. Explicitly limit parallelism to one; record hardware/environment/version.
- Save complete requests and responses, schedule, hashes, timing, cache metrics, native log probabilities, four-state probabilities or missing-alternative bounds, and available pairwise logit margins. Never replace missing candidates by zero or infer omitted mass by subtracting a float32-rounded dominant probability from one.
- Within-request variation is evaluated separately within each phase and across the intentional reload. Mapping effects are compared within phase and repeat blocks; report differences rather than attributing all variation to letters in advance.
- Debug-render requests after the measurement blocks capture the server's actual formatted prompts. They are excluded from the 1,248 decision readouts.

## Gemma direct-logit diagnostic

- Load the exact downloaded Gemma GGUF model layer using a separately versioned llama-cpp-python backend. This is an additional backend condition; agreement with native Ollama must be assessed rather than assumed.
- Use the rendered prompts and save token IDs, all four code logits, top-twenty logits and the full-vocabulary log-normalizer. Keep complete vocabulary vectors additionally for original-map K01, K06 and U06. Capture 48 case/mapping combinations once and repeat the 16 combinations for K01, K06, U03 and U06: **64 direct forward passes**.
- Clear context before every direct pass. Keep GPU layers, context, batch/microbatch and attention settings explicit.
- Reconstruct full-vocabulary and four-code softmax distributions. Record capped logits and compute relative margins.
- For capped score s and verified/declared Gemma constant c=30, reconstruct u=c*atanh(s/c) only when abs(s)<c. Mark boundary values non-invertible. These are analytic reconstructions from finite-precision outputs, not an internal pre-cap hook. Check that c*tanh(u/c) returns s.
- Compare the original softmax against a counterfactual without soft-capping and a diagnostic temperature grid 1,2,4,6,8. These transformations require no further model calls and are not calibrated on this reused development set.
- If the optional binary backend cannot be installed or aligned, preserve the failure, finish the native experiment and resolve the blocker separately. Do not silently substitute weights or claim absolute logits were captured when only log probabilities were available.

## Interpretation and operations

This pilot estimates repeatability and mapping effects in this exact environment; ten repeats plus a three-repeat reload check do not guarantee every future run. A proposed one-percentage-point tolerance from the discussion is not a literature standard or an adopted semantic-quality threshold. Stable outputs may still be wrong; no model accuracy, calibration or downstream training benefit is established here.

Use one transient 96 GB RTX PRO 6000 Blackwell Server Edition GPU, catalog price $2.69/hour. Prepare code before leasing, monitor progress and cost, download and hash-check results, then terminate the owned pod. No persistent network volume is needed. Target a bounded lease under 45 minutes; if setup or the optional backend fails, preserve partial evidence and avoid indefinite paid retries.

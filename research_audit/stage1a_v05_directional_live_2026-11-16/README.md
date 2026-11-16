# Stage 1A v0.5 — live directional evidence pilot (2026-11-16)

**Status:** Completed on real previously selected 12 target segments and their full reviews. **Development/audit data, not an independent held-out validation set.** No relevance gate or cascade was run.

## Run definition

- Codebook: [v0.5](../../Docs/STAGE1A_PILOT_CODEBOOK_V0_5_2026-11-16.md)
- Prompt: [v0.5](../../Docs/STAGE1A_PILOT_PROMPT_V0_5_2026-11-16.md)
- Output schema: [v0.5](../../configs/stage1a_pilot_directional_schema_v0_5.json)
- Runner: [v0.5](../../scripts/stage1a_codebook_v05_directional_benchmark_20261116.py)
- Same authentic target segments, source reviews and two model digests as the archived v0.3 experiment.
- Models: `qwen3.8:27b` (SHA256 `aaee06c39dcf2437cde036998d960e1fc1494b8191be7cc9657d01e509097813`), `gemma4:31b-it-bf16` (SHA256 `df1661a2a6aaa94faf24bbaf23a691877a27d0e6052598f105a225618a079e76`).
- Three repetitions per model, 12 cases each: **72 total inference calls**, temperature 0, seed 42, num_ctx 8192, num_predict 2048, no invalid-output retries.
- Each original model response is stored with metadata, exact target, parsed output, claim-level validations, and manifest hashes.

## Measured result

| Metric (per repeat) | Qwen3.8 27B | Gemma4 31B BF16 |
|---|---:|---:|
| Structurally valid cases | 12/12 | 12/12 |
| Extracted directional claims | 16 | 12 |
| E-origin claims | 13 | 9 |
| T-origin claims | 3 | 3 |
| Non-exact quotes | 0 | 0 |
| Stable emotion-direction combinations across three repeats | 36/36 | 36/36 |

The stability metric checks *directional claim presence per emotion*, not proof of identical reasoning or claim semantics. Results are not empirical model precision/recall.

## Comparison with user's nine adjudications

Two adjudications were `uncertain` (K02 inviting/safe) and therefore are **excluded** from the simplified v0.5 directional benchmark. Among the **seven evaluable** researcher judgments, compare whether at least one matching directional claim exists (`none` requires an empty claim set):

- **Qwen:** 6/7 agreement, with **K01 calm** incorrectly opposed. The full review attributes the reported stress to a late photographer, not the place's atmosphere.
- **Gemma:** 4/7 agreement. **K01 calm** incorrectly opposed; **K01 inviting** missed the reported positive staff interaction; **U06 calm** missed relaxed sitting under lights and music.

These counts are descriptive *agreement on development cases* only. They do not measure claim-level correctness, independent generalization, or extraction precision.

## High-priority conceptual discrepancies

- Both models output `calm/opposes` for **K01** based on the phrase “It was so stressful,” despite its personal-event cause in the full review. The context-attribution failure persists after codebook v0.5.
- Both models infer `calm/supports` from **K04** being “surprisingly uncrowded,” despite the codebook boundary that low crowding is not inherently tranquil. This is an apparent T-grounding overreach to audit.
- Both emit `inviting/opposes` from **K02** restroom darkness. This is in tension with the human `uncertain` audit, but v0.5 does not classify uncertainty; it should be inspected for sufficient specific directional reasoning, not counted as an automatic incorrect score.
- Gemma emits fewer directions and omits two researcher-confirmed supports (K01 inviting and U06 calm).
- Qwen extracts both `inviting/supports` and `inviting/opposes` for **U05** (“epic and famous, but not the cleanest”), illustrating that v0.5 can preserve conflicting claims rather than force one verdict. The negative hygienic cue may not itself meet the new stricter directional threshold.
- In v0.5, both models detect **K05 safe/opposes** from aggressive accusations (missed by both in v0.3) and **U05 inviting/supports** from positive place appraisal (also missed by both in v0.3). These cases are not independent holdout evidence.

## Files

- `qwen3.8_27b__repeat1.json`, `repeat2.json`, `repeat3.json`: model raw responses and strict validation.
- `gemma4_31b-it-bf16__repeat1.json`, `repeat2.json`, `repeat3.json`: model raw responses and strict validation.
- `summary.json`: quantitative diagnostics and provisional legacy-reference comparison (not independent gold).
- `claims_by_emotion.json`: per-case/emotion direction presence, including historical and researcher reference fields.

## Cost and cleanup

The Runpod pod was created at an advertised **$1.69/hour** community-cloud rate. It was **terminated** after archiving the eight data files; the Runpod pod list was checked and found **empty**. Runtime was approximately 25 minutes, implying a compute-cost estimate well below **$3 total** (not an itemized billing statement).

**Next research action:** researcher audit of individual claims, especially K01 and K04; do not interpret 100% structural validity or same-seed stability as evidence of semantic validity. The planned relevance/context gate and cascade remain deferred.

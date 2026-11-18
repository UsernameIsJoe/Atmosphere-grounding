# Unchanged v5 gate: Qwen3 8B versus 14B — 2026-11-18

All 72 requests finished normally, exit 0. Same 36 full original reviews, same frozen v5 executable system message, schema, and generation settings. No prompt or codebook tuning. Tested, not adopted.

| Measure | Qwen3:8B | Qwen3:14B |
| --- | ---: | ---: |
| Calls | 36 | 36 |
| KEEP | 22 | 23 |
| REJECT | 14 | 13 |
| Strictly valid outputs | 36 | 35 |
| Warm median seconds, excluding first review | 0.667 | 1.130 |
| Sum of request seconds | 60.849 | 65.549 |

**One verdict change: U01 REJECT -> KEEP**, against the researcher's current REJECT adjudication. 14B accepts the birthday review's half-empty dance-floor area as a spatial-layout observation. Full review and both reasons are in CHANGED_REVIEWS.md and comparison.json.

**N05 remains KEEP**, with the same restaurant-grade-kitchen anchor. Wedding T06 and elopement K01 remain REJECT. U02 remains KEEP. On the three explicit current human labels U01=REJECT/U02=KEEP/N05=REJECT, 8B agrees 2/3 and 14B 1/3. This is a narrow development audit, not full-cohort accuracy. The other reviews have not all received a new researcher audit.

Fresh GPU 8B reproduces all 36 archived CPU v5 verdicts. 14B has one validation error: N06 anchor "their patio is nice" lowercases source "Their patio is nice". Preserve raw KEEP and flag nonexact_keep_quote; do not treat it as valid downstream acceptance, silently repair it, or relabel it REJECT. No retries.

## Conclusion

No improvement from 8B to 14B in this small same-set test. The only changed verdict is a known regression, N05 is unresolved, and one additional quote fails validation. Keep the existing gate versions unchanged. This does not establish that larger models generally cannot help. V5 remains the leading candidate; v0.4 remains the active configured version.

## Reproducibility and limits

- Both checkpoints Q4_K_M, verified model digests recorded in manifest.json; 14B resolved digest checked against bdbd181c33f2 prefix from catalog.
- temperature=0, seed=42, num_ctx=8192, num_predict=512, num_thread=8, think=false; one full-review call per model/review.
- Same A40 GPU, Ollama 0.40.16, sequential model blocks, both warmed, GPU residency logged. One pass, no speed generalization; cache effects, first-request prefill and different output lengths affect timings. Larger checkpoint also changes learned weights, not parameter count alone.
- Codebook is supporting specification; standalone system message is exactly frozen v5. No prior labels/verdicts or case IDs in model input.
- No emotion extraction, E/T, classifier training, external moderation model, or automatic adoption.
- Runner: scripts/stage1a_gate_v5_qwen14b_test_20261118.py. Source commit and artifact hashes are in manifest.json.
- Pod k5nbvyaaqfrlsj, NVIDIA A40, EU-SE-1, $0.59/hour, ephemeral disk, no persistent service. Cleanup receipt is saved after archive verification.

All decisions, source review texts, comparisons, model metadata, logs and exit status are retained.

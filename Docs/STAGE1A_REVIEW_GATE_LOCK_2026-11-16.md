# Stage 1A Review Eligibility Gate — Locked v0.4

**Accepted on 2026-11-16:** Gate v0.4 is the current **approved pilot baseline** for the full-review eligibility check **before segmentation**, not an independently validated production classifier.

## Frozen, authoritative references

- [Prompt v0.4](STAGE1A_REVIEW_ELIGIBILITY_GATE_PROMPT_V0_4_2026-11-16.md) — frozen Markdown SHA-256 `e93b288cff5608409c08836b2e0a4c1515c9366431bf2fdb6303f51d743b8ab4`.
- [Codebook v0.4](STAGE1A_REVIEW_ELIGIBILITY_GATE_CODEBOOK_V0_4_2026-11-16.md) — frozen Markdown SHA-256 `6304dc44befa80392bb4fff4bbb3be7c839d94700d437d7f608cbdc3daa99c87`.
- [Runner v0.4](../scripts/stage1a_review_eligibility_gate_v04_20261116.py).
- [Three-field JSON output schema](../configs/stage1a_review_eligibility_gate_v01.json) — schema SHA-256 `127a02d26eacc0c3c4897b33afdb8edb8d9e7afd2462a733534029ae53e30393`; the schema filename is historical, but its fields are retained for v0.4.
- [Active configuration pointer](../configs/stage1a_review_eligibility_gate_current.json).
- [36-review regression audit with original texts and model outputs](../research_audit/stage1a_review_gate_v04_regression_qwen8b_2026-11-16/README.md).

**Do not edit the frozen v0.4 prompt or codebook in place** or invalidate their recorded manifest hashes. Make a new v0.5 and repeat evaluation before superseding this accepted baseline. Prior v0.1–v0.3 artifacts remain historical and intact.

## Pipeline contract

```text
Original full review → [v0.4 binary eligibility gate] → KEEP original full review → segmentation → Stage 1A extraction / validation
                                                       → REJECT audit/archive only
```

1. One LLM decision per **original full review**, never per segment. The model evaluates whether the review contains any substantive, context-relevant **place-level** observation rather than an incidental reference, private anecdote, isolated food/service incident, or vague praise.
2. KEEP allows the original review to proceed; **downstream segmentation and extraction still filter unrelated content**. A small legitimate place observation may qualify even in a mixed review.
3. REJECT excludes the review from downstream extraction **without destroying it**; preserve original text and all decisions for false-negative audits.
4. `anchor_quote` and `reason` are **diagnostic fields**, not a replacement for the source review or an emotion-evidence segment. Quote-exactness alone does not validate its semantic adequacy.
5. **No second reason/verdict-only LLM**; it cannot validate the decision without seeing the original review.
6. This lock is for the review gate alone. **End-to-end integration, complete corpus execution, downstream emotion codebook, E/T/I research design and independent validation remain separate tasks.**

## Locked inference and invocation

- **Ollama `qwen3:8b`**, `temperature=0`, `seed=42`, `num_ctx=8192`, `num_predict=512`, `think=false`.
- One `/api/chat` call per whole review, schema fields `keep` (boolean), `anchor_quote` (string), `reason` (string).
- Use explicit operational input/output paths, as versioned runner defaults refer to historical pilot data:

```bash
python scripts/stage1a_review_eligibility_gate_v04_20261116.py --stage prepare --input data/processed/reviews.jsonl --output reports/stage1a_review_gate_v04_full_corpus
python scripts/stage1a_review_eligibility_gate_v04_20261116.py --stage run --model qwen3:8b --input data/processed/reviews.jsonl --output reports/stage1a_review_gate_v04_full_corpus
python scripts/stage1a_review_eligibility_gate_v04_20261116.py --stage report --output reports/stage1a_review_gate_v04_full_corpus
```

## Adoption evidence and limitations

The regression test used **36 distinct authentic full reviews** collected in previous development/test sets. Outcomes: **23 KEEP, 13 REJECT; 34/36 strict-format/quote-valid**. Four decisions changed from earlier Qwen3 8B runs — **U02, T08, N05 and N12** — all accepted as better rejections by the researcher. **T11** remained REJECT.

- **N07** is a correct KEEP with a semantically inadequate food-based anchor quote despite the review's independent atmosphere evidence. The original full review remains the source of truth downstream.
- **T06** (wedding reception atmosphere) and **K01** (private elopement/courtesy) remain known, preexisting false-positive edge cases. No targeted event rule is added.
- Minor capitalization mismatches in two quotes, K03 and N04, remain mechanically invalid but not substantive gate failures.
- These 36 reviews are **not independent holdouts**: some were seen during prompt development. Do not quote statistical accuracy, precision or recall; perform independent review-level auditing as Stage 1A scales.

**Next step:** proceed with Stage 1A segmentation and explicit evidence extraction; monitor false negatives via archived REJECT reviews instead of endlessly retuning this gate.

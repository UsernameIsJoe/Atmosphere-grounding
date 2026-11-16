# Stage 1A — v0.4 gate, complete 36-review regression audit (2026-11-16)

## Protocol

- Exact revised [v0.4 prompt](../../Docs/STAGE1A_REVIEW_ELIGIBILITY_GATE_PROMPT_V0_4_2026-11-16.md), [v0.4 codebook](../../Docs/STAGE1A_REVIEW_ELIGIBILITY_GATE_CODEBOOK_V0_4_2026-11-16.md), [runner](../../scripts/stage1a_review_eligibility_gate_v04_20261116.py).
- Model: `qwen3:8b` via Ollama. Run settings unchanged: temperature 0, seed 42, num_ctx 8192, num_predict 512, think false, format schema with fields `keep`, `anchor_quote`, `reason`.
- Input: [36 authentic full reviews](cases.jsonl), each unique by place ID and review index, formed by de-duplicating: original 12 K/U development examples, 12 T cases from v0.2, and 13-case v0.3 test including one duplicate T11/R_T11. Case IDs preserve prior names; T11 appears only once. **No expected eligibility labels or previous verdicts sent to the model.**
- [Raw original texts, model outputs, reasons, quote-validation flags](decisions.jsonl) and [manifest](manifest.json).
- This is a **retrospective regression set**, not unbiased held-out data: v0.4 prompt explicitly addresses N05/N12 and prior review discussions. It does not measure generalization.

## Quantitative outcomes

- 36 model decisions returned, **34 strictly validated / 2 invalid** exact anchor matches (K03 and N04). These two nevertheless have parseable KEEP decisions.
- Model verdict totals (including the two validation failures): **23 KEEP, 13 REJECT**.
- Compared with prior small-LLM results, decision changes were U02, T08, N05 and N12 (four cases); T11 remained REJECT. These changes are not all errors; cases require review-level human adjudication.

## Targeted outcomes and regressions

| Review | Previous verdict | v0.4 verdict | Assessment |
|---|---|---|---|
| N05 shelter food-policy/kitchen | KEEP (v0.3) | **REJECT** | Correct per user’s adjudication |
| N12 apartment/agent/generic praise | KEEP (v0.3) | **REJECT** | Correct per user’s adjudication |
| T11 cold meal/waitress | REJECT (v0.3), KEEP (v0.2) | **REJECT** | Correct, maintained |
| T08 “The place is so comfortable and welcoming!” | KEEP (v0.2) | **REJECT** | **Likely false-negative regression**: v0.4 incorrectly requires physical/spatial conditions and overlooks explicit place atmosphere |
| K01 private elopement and courtesy | KEEP (v0.1) | **KEEP** | **Still wrong by user’s adjudication**; anchor is incidental photo access |
| T06 one wedding reception atmosphere | KEEP (v0.2) | **KEEP** | **Still wrong by user’s adjudication**; event-boundary not changed in v0.4 |
| U02 exhibits-only/other-site recommendations | KEEP (v0.1) | **REJECT** | Consistent with v0.2 codebook's provisional expected judgment |
| K03 | KEEP (v0.1) | KEEP, **invalid quote** | Nonexact verbatim quote |
| N04 | KEEP (v0.3) | KEEP, **invalid quote** | Nonexact verbatim quote |

**Additional observation:** N07 was kept, appropriately based on explicit “Good vibe, warm atmosphere, no frills” elsewhere in the full review, **but** the model’s chosen anchor refers to kale Caesar food quality instead. The verdict may be right while the purported evidence is not independently sufficient; strict substring validation alone cannot catch such a semantic error.

## Important caveats

This trial does not establish precision/recall. Only selected cases have user adjudications. The user requested testing prior cases for regressions, not running a previous model again. The model did **not** receive segmented input; it received each full review as a single message, and selected its anchor after making a binary decision (as instructed).

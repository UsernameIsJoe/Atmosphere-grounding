# Stage 1A full-review eligibility gate — ACCEPTED PILOT BASELINE (2026-11-16)

**Decision:** Lock **gate v0.4** as the **current approved pre-segmentation review eligibility gate** for Stage 1A research. Freeze its system prompt, codebook, review-level binary schema, inference parameters, and runner. This is an **operational/research decision**, not a claim of externally validated accuracy or production maturity.

## Authoritative frozen sources

- [v0.4 system prompt](STAGE1A_REVIEW_ELIGIBILITY_GATE_PROMPT_V0_4_2026-11-16.md) — SHA-256 (entire Markdown file): `e93b288cff5608409c08836b2e0a4c1515c9366431bf2fdb6303f51d743b8ab4`
- [v0.4 gate codebook](STAGE1A_REVIEW_ELIGIBILITY_GATE_CODEBOOK_V0_4_2026-11-16.md) — SHA-256: `6304dc44befa80392bb4fff4bbb3be7c839d94700d437d7f608cbdc3daa99c87`
- [Frozen review-level runner](../scripts/stage1a_review_eligibility_gate_v04_20261116.py) — invokes **one LLM over the whole original review**, before segmentation.
- [Binary output schema](../configs/stage1a_review_eligibility_gate_v01.json) — SHA-256: `127a02d26eacc0c3c4897b33afdb8edb8d9e7afd2462a733534029ae53e30393`. Schema file retains its historical v0.1 name; v0.4 reuses its identical three-field format, not the v0.1 prompt.
- [Current-version configuration](../configs/stage1a_review_eligibility_gate_current.json) — version pointer, not a replacement prompt.
- [36-review v0.4 regression archive](../research_audit/stage1a_review_gate_v04_regression_qwen8b_2026-11-16/) — immutable input, raw outputs, model manifest and analysis.

**Freeze policy:** Earlier v0.1–v0.3 experiments stay archived. Do **not** edit the frozen v0.4 prompt or codebook in place: their file hashes are recorded in the regression manifest. If research requires a semantic change, create **v0.5** plus fresh regression evidence and a new acceptance decision.

## What the gate does

```text
Original full review + place_id
       |
[Gate v0.4] one Qwen3:8b whole-review decision: KEEP / REJECT
       |                       |
      KEEP                   REJECT
       |                       |
Original review proceeds     Review retained in reject/audit ledger;
to segmentation              not supplied to downstream segmentation
       |
Stage 1A explicit emotion evidence extraction / later recall and validation
```

- `KEEP` = at least one substantive, contextually relevant place-level observation. Mixed reviews can pass when any qualifying observation exists.
- `REJECT` = no independently sufficient place-level observation, despite possible anecdotes, event narration, generic praise, food/service incidents, institutional criticisms, or incidental physical mentions.
- **No review text is segmented before this gate.** The `anchor_quote` and `reason` document the model's decision; they **do not substitute** for the original review or control which segments are retained.
- Do **not** add a second LLM to review only the first model's reason/verdict. A reason-only checker lacks the review's original context.
- Subsequent segmentation and extraction can discard irrelevant parts of a KEEP review. **REJECT cases must remain auditable** because false negatives cannot be recovered downstream.
- Keep original text, review ID, place ID, verdict, quote, reason, exact quote-validation flags, model/prompt/codebook hashes and run settings; the review-level quote is *diagnostic*, not authoritative evidence for a downstream emotion.

## Locked model/protocol

- Model: **`qwen3:8b`** (Ollama).
- Temperature `0`; seed `42`; `num_ctx=8192`; `num_predict=512`; `think=false`.
- One `/api/chat` call per complete review; JSON schema `{keep: boolean, anchor_quote: string, reason: string}`.
- The v0.4 prompt includes no T06-specific exception; the private-event/venue-atmosphere ambiguity is **deferred**.

Example invocation with explicit operational input/output paths (the versioned runner's historical defaults point at earlier pilot data):

```bash
python scripts/stage1a_review_eligibility_gate_v04_20261116.py \
  --stage prepare --input data/processed/reviews.jsonl \
  --output reports/stage1a_review_gate_v04_full_corpus

python scripts/stage1a_review_eligibility_gate_v04_20261116.py \
  --stage run --model qwen3:8b \
  --input data/processed/reviews.jsonl \
  --output reports/stage1a_review_gate_v04_full_corpus

python scripts/stage1a_review_eligibility_gate_v04_20261116.py \
  --stage report --output reports/stage1a_review_gate_v04_full_corpus
```

**Status boundary:** The standalone gate runner has been executed on prior pilot reviews. Integration into the Stage 1A end-to-end segmentation/extraction implementation, a complete corpus run, and independent held-out performance validation **are not implied by this acceptance decision**.

## Evidence for acceptance — not an accuracy claim

On **36 distinct real full reviews** assembled from previous development and test cases:

- 36 binary decisions; **23 KEEP / 13 REJECT**.
- 34/36 outputs passed the strict schema/verbatim anchor checker; K03 and N04 had minor quotation capitalization differences.
- From the previous small-LLM verdicts, four changed: **U02, T08, N05, N12**, all accepted by the researcher as appropriate rejections. **T11** stayed REJECT.
- **N07**: KEEP is appropriate because the review describes its venue's warm atmosphere, but the chosen quote referred to food quality. This demonstrates that quote accuracy alone does not establish semantic sufficiency; use the original full review downstream.
- **T06**: model KEEP is a known disputed false positive under the researcher's interpretation of event-specific atmosphere, deliberately **not** addressed in this version.
- **K01**: model KEEP for private elopement/courtesy is also a known unresolved false positive; no semantic fix is claimed.

**Decision standard:** adequate for **provisional Stage 1A pilot progression**, not statistically verified precision/recall. The 36 reviews include development cases and prompted corrections; they are not an independent, representative blind holdout. Independently adjudicate fresh whole reviews later, emphasizing false-negative retrieval, and monitor the downstream extractor before treating the gate as validated.

**Next work:** Proceed with segmentation and the Stage 1A extraction/evidence pathway under its separate codebook; do not re-open the eligibility gate or spend additional GPU time on model-capacity tuning absent new evidence.

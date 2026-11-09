# Stage 1A Component 1 — Qwen3 readiness prompt check (2026-11-08)

## Purpose / stop criterion

The goal is **not to optimize the entire Stage 1A** or begin a model zoo. It is to make Component 1 a **trustworthy provisional evidence source** so parallel research on Component 2 (Relevance), Component 3 (NLI), and Stage 1B (images) can proceed without being contaminated by unrecognized extraction distortions.

**Operational readiness is NOT scientific accuracy.** The critical question is whether source-grounded claim extraction is sufficiently faithful, complete, and auditable *with safeguards* for the next experiments. Do not claim a verified accuracy score without human-adjudicated claim/omission labels.

We already have a fully completed local `qwen3:8b` run on 20 real reviews / 56 original sentences (`source_sha256=144aee54fd70fdd2b440bc1e0f05fc71b63e79e26bf525b995a6260c0936d00e`). It produced 88 candidate claims; 72 passed the same-model verification + exact-quote mechanism. **72/88 is NOT semantic precision.**

## Controlled design

- **A0 baseline:** same existing, unmodified `qwen3:8b` local `predictions.jsonl`, with original extraction and same-model verification.
- **A1 — ambiguity/attribution:** original prompt **plus** focused instructions not to resolve typos, remove hedges, rewrite a person's experience as environmental fact, or fabricate causal relations.
- **A2 — evidence-first:** original prompt **plus** quote-first claim assembly, explicit preservation of full source-supported clauses, abstention on unresolved relations, and experience attribution.

Freeze all other variables: same installed `qwen3:8b` checkpoint, JSON schema, `temperature=0`, `num_ctx=8192`, original sentence text, 2-pass verifier prompt, extraction function, and source provenance.

**Caution:** Ollama temperature 0 does not necessarily guarantee deterministic GPU execution. Model weights and quantization are addressed by recording the original `ollama list` ID and version when reporting results. The verifier is the **same model** as extractor; its verdicts remain fallible.

### Step 1 — fixed real diagnostic set first

12 original source sentences, selected by prior known failures *before seeing either new prompt's output*: source `(row,sentence_index)`:

`(55,0),(55,1),(55,2),(74,0),(74,1),(97,0),(97,2),(113,0),(123,0),(139,0),(181,0),(187,0)`.

Includes park/charming, Torii/unique vibe, trees/paths/protection, typo/park care, loss of sunlight with uncertainty, accessibility, and ambiguous evaluations. No synthesized reviews.

On the researcher's Windows PowerShell terminal, from the already cloned repo root:

```powershell
git pull
python scripts/stage1a_component1_prompt_readiness.py --check-only
python scripts/stage1a_component1_prompt_readiness.py
```

To resume incomplete work without overwriting valid previous results:

```powershell
python scripts/stage1a_component1_prompt_readiness.py --resume
```

Output: `reports/component1_prompt_readiness/diagnostic/predictions.jsonl` and `summary.json`. A0 is **read-only** at `reports/component1_ollama_qwen3_8b/predictions.jsonl` and never overwritten.

Export side-by-side human review rows, blank by design:

```powershell
python scripts/stage1a_component1_prompt_review_packet.py
```

Output: `reports/component1_prompt_readiness/diagnostic/review_packet.csv`.

Only if the initial diagnostic review indicates no important regressions and the goal needs an independent wider check, run remaining comparison on all 56 original sentences:

```powershell
python scripts/stage1a_component1_prompt_readiness.py --full
python scripts/stage1a_component1_prompt_review_packet.py --test reports/component1_prompt_readiness/full/predictions.jsonl --output reports/component1_prompt_readiness/full/review_packet.csv
```

Outputs for diagnostic and full runs are intentionally isolated. Don't treat the fixed 12 known failures as an unbiased holdout; they are an error-focused development diagnostic.

## Human readiness rubric

Before treating Qwen3 observations as safe to rely on **as model candidates**, review:

1. **Grounding:** Does the original verbatim review entail the actual meaning of each candidate claim? Does a source quote include the relationship, not just a keyword? An exact quote is necessary for provenance, not sufficient to establish faithfulness.
2. **Coverage:** For each source sentence, what independently recognizable, distinct, substantive observations were omitted? Never judge only the claims the model happened to produce.
3. **Relations/attribution:** Are physical elements, environmental conditions and specifically attributed human experiences connected correctly? In the real park review, do the trees/paths cause a reported feeling, or has the model dropped that dependence?
4. **Negation/uncertainty:** Is `loss of sunlight` represented as loss, not abundance? Is the office-expansion explanation still attributed to the reviewer's speculation?
5. **Noise and ambiguities:** Does the model avoid confident unsupported fixes to `circulous` and `Ckean`? Is an unclear source represented as unclear rather than rewritten?
6. **Verifier limitations:** Does a change remove wrong claims without discarding source-supported good claims? A Qwen3 self-verdict is not independent truth.

**Go / conditional go / no-go:**

- **Conditional go** for further Stage 1A/1B research if source text, offsets, and *all* candidate/flagged claims remain available; critical observed errors are explicitly flagged; no candidate is silently promoted into an established fact; reference audit finds no systematic loss of negation or invented environment→experience links. Continue sampling and measuring independently.
- **No-go** for using Component 1 as a sole factual source if the model repeatedly invents causality, drops important opposite evidence, or systematically changes hedged claims to factual assertions. Use original sentences as premises and/or demand manual adjudication instead.
- A real **accuracy-based go** requires an independently annotated, complete set of observations and relationships on a held-out sample; this test alone cannot certify it.

The pipeline boundary remains: Component 1 **source-grounded extraction** (no nine-emotion labeling) → Component 2 **emotion-specific relevance with source checks** → Component 3 **directional three-way NLI**. Stage 1B image research can proceed in parallel because it is independent of the unvalidated extraction model; correlation/training across modalities must not treat unvalidated Qwen3 output as gold labels.

## Scripts / checks

- `scripts/stage1a_component1_prompt_readiness.py`: A1/A2 local Ollama runs, frozen baseline matching, resume, separated 12-case and full runs.
- `scripts/stage1a_component1_prompt_review_packet.py`: side-by-side original source and A0/A1/A2 candidates for independent human review.
- `.github/workflows/stage1a-component1-prompt-readiness.yml`: syntax/import/config checks **without pretending remote GitHub Actions can call the researcher's local Ollama**.
- Existing `Docs/STAGE1A_COMPONENT1_OLLAMA_PILOT_2026-11-06.md` has the initial A0 protocol.

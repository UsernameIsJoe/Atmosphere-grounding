# Stage 1A — Explicit-atmosphere evidence and recall expansion

**Decision date:** 2026-11-11  
**Status:** Agreed high-level architecture and research execution plan; **not implemented or validated**. Model, training loss, and thresholds remain experimental.  
**Scope:** Text Stage 1A only; Stage 1B and Stage 2 remain separate.  
**Supersedes:** The November 10 Stage 1A clause-first three-LLM-panel → consensus → NLI-student approach as the *planned default architecture*. The older plan, implementations, tests, and audits remain available as historical evidence.

## Goal and invariants

Measure **review-reported, place-attributed atmosphere**, not atmosphere inferred from objects or environmental features. Produce source-grounded, category-specific evidence profiles that can scale beyond the Cambridge pilot to reviews from any city or number of places.

- Input: `place_id`, original review text, and optional source metadata.
- Preserve exact text, review context, source offsets, hashes, attribution, negation, direction, and codebook/model versions.
- Taxonomy: **11 categories** from `configs/lexicon.yaml`; initial pilot uses calm, inviting, safe.
- **No mandatory hard relevance gate** and no free-form claim paraphrasing as a required intermediate representation.
- A missing report is **not** a negative atmosphere report.
- Stage 1A does **not** convert environmental facts into felt emotions; such conditions are deferred to an explicitly separate track (3B) if needed.
- Human involvement is limited to scientific **milestone audits** (M0–M3), not routine per-review production annotation.

## Approved high-level architecture

```text
Reviews (any city or scale: place_id + text)
         |
[0] Versioned category codebook                 <-- M0 approve
         |
[1] Preprocess: sentences + original offsets + hashes + review context
         |
[2] High-precision explicit extractor
    high-recall cue search -> LLM verifies place attribution,
    explicit experience, negation, and support/opposition
    | confirmed evidence + rejected candidates (with reasons)
    v
[3A] Explicit-recall student (candidate)
    search sentences missed by [2] for uncued experience reports
    | adds new evidence; NEVER overwrites [2]
    v
[4] Automatic provenance/schema/consistency validation   <-- M1/M2 scientific audits
         |
[5] Place profiles: [2] only; [2]+[3A]; incremental [3A]  <-- M3 sign-off
         |
      Stage 2

[3B] Reported non-visual conditions: DEFERRED, distinct
      from explicit-experience targets if later justified.
```

These numbered steps are logical responsibilities, **not a requirement for a separate model per step**.

## Research phases, deliverables, and decisions

| Phase | Work | Deliverable / milestone |
|---|---|---|
| 0 — Codebook | Version definitions, explicit/negative examples, attribution, directional rules, exclusions, ambiguous cases and scope for 11 categories. | **M0:** Researcher approves taxonomy/rubric before labeling. |
| 1 — Data preparation | Sentence segmentation while retaining entire review context; stable IDs, offsets and hashes; deterministic reprocessing across cities. | Auditable input, context and data manifests. |
| 2 — High-precision explicit extraction | Broad cue matching produces candidates; an LLM confirms genuinely experienced/observed atmosphere, relevant place, qualifiers, and direction using exact source spans. Preserve confirmed and rejected candidates with reasons. | Versioned precision-focused evidence ledger. No recall claim from cue matching alone. |
| M1 — Scientific extraction audit | Independently inspect a predefined diverse sample of full reviews, **including uncued sentences**, for missed explicit evidence, incorrect confirmation, opposition, negation and source fidelity. Pilot proposal: around 30 full reviews, adjusted if sparse categories make this uninformative. | Judge whether [2] is sufficiently reliable as training-label source; estimate missed uncued evidence. |
| 3A — Recall expansion | Compare a direct uncued-sentence LLM, an unfine-tuned NLI model, embeddings baseline, and fine-tuned student only when sample sizes warrant. | Recall candidate that adds distinct, source-supported reports without overriding [2]. |
| M2 — Independent recall audit | Check 3A-only predictions, new expressions, negative/ambiguous cases, lexical holdouts, and generalization on place-disjoint unseen data. | Accept 3A per category, keep it exploratory, or return to [2]-only. |
| 4 — Automatic validation | Schema, provenance, exact offsets, missingness, duplicate handling, model/version manifests, label conflicts, drift and consistency diagnostics. | Reliable batch QA; not a claim of automated semantic truth. |
| 5 — Place aggregation | Preserve separate support/opposition counts, review-level coverage, uncertain/contested evidence, sample denominators, and extraction route. Provide [2]-only, [2]+3A, and 3A-added-coverage profiles. | **M3:** Researcher signs off on evidence quality and suitability for Stage 2. |

**Merge invariant:** If [2] confirms, its label stands even if 3A disagrees; disagreement is logged. If [2] does not flag a sentence and 3A finds an explicit report, append a `recalled` record with model score/version and source evidence. Do not count 3A output as independently validated just because its score is high.

## 3A — Candidate training design (subject to evidence and M1)

**Task:** Condition on a category definition and original sentence marked within its full review context (a local +/-2-sentence window can be an efficiency variant). Predict `supports | opposes | none`, with no claim that absence of evidence is opposition. One shared category-conditioned model is a candidate, not an established winner.

**Training sources:** confirmed [2] supports/opposes as **silver positives/directional evidence**; independently reviewed true negatives where possible; rejected cue matches as **candidate** hard negatives only after verifying they are genuinely negative rather than ambiguous; all uncued sentences remain **unlabeled**, not automatically negative. Other-category labels are not negative labels by default.

**Approaches to compare:**
1. Frozen NLI inference on original review context, with hypotheses tested for logical validity rather than automatically mapping every contradiction to felt opposition.
2. Direct LLM assessment of uncued original passages.
3. Frozen-embedding baseline.
4. Fine-tuned NLI-initialized encoder/student if data volume supports it; model size and NLI backbone are not locked.

**Controlled training comparisons:** ordinary supervised training with audited negatives; cautious, down-weighted unlabeled negatives as one baseline; investigate PU/nnPU only if selection and class-prior assumptions can be justified. Cue masking (including category-crossing cue sets) and physical-feature-word masking are optional ablations, **not** presumptively valid fixes. Feature masking should not turn physical observations into emotional evidence or remove essential experience context.

**Evaluation:** place-disjoint train/development/test; later city/place-type generalization. Predeclare development-only thresholds; evaluate held-out cue phrases **and** independently reviewed genuinely uncued expressions. Entire held-out lexical families and their corresponding reviews must be excluded from training for a valid lexical test. Audit recalled-only precision, incremental recall, directional fidelity, opposition sensitivity, source spans, feature-only false positives, and per-category results. Place-level performance remains the downstream criterion.

**Important:** NLI checkpoint `entailment/contradiction/neutral` is only a candidate baseline for *explicitly reported* statements. It is not an automatic ground truth or a safe way to infer a reviewer's feelings from physical conditions. Model confidence requires calibration before interpreting scores as probabilities.

## Data sufficiency and sequencing

**Pilot:** 214 stored reviews / 43 places are an engineering and evaluation pilot, **not a dataset-size constraint on the method**. The proposed rough cue-hit estimates from the discussion (before LLM confirmation) are calm about 52 support / 12 opposition, inviting about 16 / 0, safe about 4 / 5; they are **unverified counts**, not labeled training examples. An estimate of ~46 reviews with any cue is likewise provisional.

Consequences:
- First build [0]–[2] and conduct M1 on real source reviews.
- At pilot scale, compare basic inference baselines and smoke-test training/evaluation infrastructure, perhaps on calm; **do not claim 3A is trained or validated for all categories**.
- Scale across permitted, diverse sources/places before substantive student training; check category-by-direction counts and learning curves rather than asserting that a fixed number of examples is sufficient.
- Negated/opposing statements and rare categories may require targeted evaluation sampling; retain representative, place-disjoint holdouts.
- Resolve data-use rights, permitted storage, and training terms **before** expanded acquisition.

**Stop/go rule:** If [2] fails precision/source-faithfulness audit, repair [2] before student training. If 3A's additional recalled evidence is unreliable or does not improve measured recall at acceptable precision, use [2]-only for that category. Proceed to Stage 2 only after M3, with explicit-only profiles as the primary track.

## Why the design changed

Archived Stage 1A experiments found claim omissions/distortions in extraction, misrouting in relevance filters, NLI hypothesis/context sensitivity, and near-universal `not_relevant` outputs in the initial LLM panel. Existing counts, model agreement and source-quote matching did not independently establish semantic correctness. Relevant references:
- `research_audit/stage1a_final_2026-11-10/README.md`
- `Docs/STAGE1A_REFINED_DESIGN_2026-11-10.md`
- `Docs/STAGE1A_PROMPT_C_10_REVIEW_AUDIT_2026-11-11.md`
- `Discussions/stage1a-nli-relevance-gate-real-reviews-2026-11-11.md`
- `Discussions/stage1a-semantic-relevance-gate-real-reviews-2026-11-11.md`

**Documentation-only update (2026-11-11):** No new experiments, scientific acceptance thresholds, codebook revision, code deployment, or training run is implied by this plan.

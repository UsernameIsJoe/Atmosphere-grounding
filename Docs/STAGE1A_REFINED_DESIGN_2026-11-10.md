# Stage 1A — Refined text-grounding design

**Decision date:** 2026-11-10  
**Status:** Agreed research-method direction; **not implemented or empirically validated**.  
**Authority:** This is the current Stage 1A design, refining Section 4 of the proposed *Atmosphere Grounding: Project Design (v2)*. Earlier Stage 1A audit data and failed methods remain archived without alteration. 

## Research objective and evaluation stance

Use local LLM annotators to extract **source-grounded evidence of location-attributed atmosphere** from original real reviews for nine target categories, construct **silver** labels by agreement, fine-tune an **NLI-pretrained student**, and aggregate review evidence at the place level for later cross-modal association learning.

**No human labeling is planned for Stage 1A.** Consistency, inter-model agreement, repeatability, source-offset integrity, model-to-panel fidelity, prompt sensitivity and downstream annotator robustness can be measured. They **cannot establish human-judged accuracy or model correctness**. Report Stage 2 outcomes as associations with *LLM-annotated reported perception*, not the objective atmosphere of places.

The existing repo has a **three-category pilot (calm, inviting, safe)**, a historical lexicon file with 11 terms, and a current research goal of **nine categories whose exact membership is not frozen**. Do not invent/select the final nine.

## 4.1 Rubric / construct definition

- Version one authoritative taxonomy with nine names, definitions, inclusion/exclusion criteria, legitimate bipolar relationships (otherwise unipolar), and 2–3 **real development-review** examples per category when available.
- Distinguish **explicit reported atmosphere**, **source-grounded direct indicators** and **indirect inferred evidence**. E.g. police patrol may be a direct safety *indicator*, not evidence of felt safety. Visual indicators such as lighting do not automatically entail a feeling.
- Document overlapping categories, negation, temporal qualifiers, attribution, and not-relevant examples.
- Any substantive rubric change requires re-annotation; preserve versions and provenance. Do not use held-out data as rubric examples.

## 4.2 Units — clause-first, then arrays if needed

- **Input context:** entire original review; keep review ID, place ID and offsets.
- **Annotation units:** deterministic **clause-level segmentation first**, with stable IDs and offsets. Prefer linguistically sensible clauses (including handling coordination, punctuation and dependent clauses); log segmentation uncertainty and boundary issues without treating segmentation as semantically perfect.
- Each panel model sees the **same numbered clauses and the entire review context**. All clause × emotion votes align directly.
- A clause ordinarily has one directional evidence judgment. **Only when necessary**, allow multiple evidence records within a single clause to preserve distinct, conflicting or differently conditioned evidence. Do **not** default to independent, free-form extracted claims or paraphrases.
- When multiple evidence records occur, match them across models using original offsets/span overlap and direction, with ambiguous alignment marked contested rather than silently forced.
- **Stage 2 unit:** place, not review or clause. Never treat correlated clauses of one place as independent training/test places.

## 4.3 Independent LLM panel

- Three pinned local models from distinct families (example: Qwen, Gemma, Llama), independent of each other, without seeing others' outputs.
- Two independently worded prompts per model with **the same fixed rubric**, same original review context and same clause boundaries. Prompt **A** supplies candidate silver training labels; prompt **B** measures sensitivity only, with optional sensitivity downstream.
- Record exact model tags/digests, prompt IDs/text, decoding settings, schema and source provenance. Temperature 0 improves repeatability but does **not** guarantee identical outputs.
- The standard output is **one evidence judgment per clause × emotion**, with an optional `evidence_records` array for genuine intra-clause multiplicity:

```json
{
  "unit_id": 3,
  "emotion": "calm",
  "relevance": "supports",
  "strength": "weak",
  "type": "explicit",
  "condition": "in the morning",
  "evidence_span": "peaceful in the morning",
  "attribution": "first_person",
  "rationale": "one sentence",
  "evidence_records": []
}
```

- Allowed `relevance`: `supports | opposes | mixed | not_relevant | uncertain`; `strength`: `weak | strong | null`; `type`: `explicit | direct_indicator | indirect | null`; `attribution`: `first_person | secondhand | hedged | general`. Empty/null fields only where schema permits.
- `not_relevant` is the default for generic praise, bare location facts and unrelated service/food/price complaints. Weak negation (e.g. not particularly calm) is weak opposition; a strong counter-description (chaotic) is strong opposition, subject to contextual definitions.
- Evidence spans must be **literal source substrings**; no paraphrased assertions; no same-model self-verification used as a validity certificate.

## 4.4 Consensus / silver supervision

- Keep **every per-model raw annotation**, per prompt, indefinitely within permitted research data handling.
- Primary baseline: majority of the **three prompt-A model judgments** (at least 2/3) on relevance/direction; no clear majority = `contested`, excluded from hard training targets and reported.
- A **soft target is a complete vote distribution** over mutually exclusive outcomes (e.g. supports 2/3, not_relevant 1/3), **not a scalar 0.67 confidence**. Construct separate conditional distributions/valid masks for evidence direction, type and strength; do not silently turn missing/irrelevant types into negatives or treat `mixed` as `not_relevant`.
- Keep the agreed simple majority baseline; do not initially fit a reliability-weighted Snorkel-style label model from only three potentially correlated model sources without reference truth. Model agreement reflects consensus, **not probability of correctness**.
- Contested counts, category-wise rates and model identity must survive into downstream sensitivity reports.

## 4.5 Automated trust checks (diagnostic unless explicitly described as a mechanical failure)

| Check | Measurement / decision |
|---|---|
| Literal evidence provenance | `review[start:end] == evidence_span` with hash, place and clause offsets; mismatch = hard mechanical failure |
| Repeatability | Rerun fixed inputs/settings; report per-model/prompt/emotion agreement, not presumed bitwise determinism |
| Prompt sensitivity | Compare prompt A versus B per model, emotion, evidence type and direction; shifts indicate instability |
| Inter-model agreement | Class-specific positive/negative agreement, pairwise agreement and appropriate kappa with prevalence reported; no arbitrary kappa-based validity cutoff |
| Three-model split diagnostics | Frequency and identity of 3–0, 2–1, and three-way splits; measure each model's agreement with the **other two only when they agree**; no fictitious two-model majority |
| Rate differences | Compare per-model support/opposition/not-relevant rates across categories; flag disparities for review |
| Leakage probe | Frequency of unrelated complaint clauses labeled atmospheric opposition; counts are **potential errors**, not verified false positives absent an independent standard |
| Real hard-case subsets | Mine original-review clauses with negation, contrast, hedge, secondhand reports, sarcasm, emojis and conditions; report coverage/consistency separately |
| Evidence-type breakdown | Run all relevant diagnostics for explicit, direct_indicator, and indirect, and per category; do not hide weaknesses in aggregate rates |

Check original-source traceability and output schema before any training. Automatic agreement and span checks do not establish semantic completeness.

## 4.6 NLI-first student adaptation

**Current preference:** adapt a pretrained NLI checkpoint, rather than train a classifier from random initialization. This is motivated by transfer learning and limited silver-label volume, but is an experimental choice, **not a proven best model**.

Compare two prioritized students on matched panel-A supervision:
- **S1:** fine-tune `MoritzLaurer/DeBERTa-v3-large-mnli-fever-anli-ling-wanli` using source clause (with context) and atmosphere hypotheses. Only map labels to entailment/contradiction/neutral when that interpretation is logically defensible.
- **S2:** the **same NLI-pretrained backbone** with separate evidence-direction/type/strength heads where direct indicators, uncertainty and indirect relevance are not naturally NLI entailment. Keep this an NLI-initialized evidence model, not a base classifier trained from scratch.

A base-DeBERTa classifier is optional **later**, not a mandatory third model.

- Preserve **original full review context** and conditional qualifiers; do not use decontextualized fragments as NLI premises.
- Use place-disjoint, preferably **spatial-block-disjoint**, partitions for student development and held-out evaluation. Never split correlated clauses between train and test.
- Predeclare selection metrics and error groups before final holdout: **panel-relative** macro precision/recall/F1 for relevance, conditional direction fidelity, evidence-type fidelity, hard-case stability, and per-emotion results. Compare against simple panel agreement and zero-shot baselines as context, without calling the outcome human accuracy.
- Calibration, if attempted, concerns **fit to panel-defined target distributions**, not probability of true perception. Favor sigmoid/temperature approaches when held-out calibration data are small; isotonic only if enough independent development examples justify it.
- Check learning curves using 25%, 50%, 100% **by place**. Growth at 100% suggests more independent places may help; don't assume it proves more data is the only solution.
- A student may provide efficiency and standardized scores, but **not automatically higher accuracy, determinism or semantic truth** relative to the panel.

## 4.7 Reporting / acceptance gates

- Gates measure **panel reproducibility/consistency and student fidelity**, not independently verified correctness. Thresholds are fixed after development and **before final held-out evaluation**, not retroactively adjusted to pass.
- Report panel-relative precision/recall, direction, type, contested rate, prompt A/B stability, repeats, leakage probes, real hard-case subsets, and per-emotion results.
- Categories failing precommitted consistency/fidelity gates are **unresolved** and excluded from Stage 2's primary findings; can be retained in exploratory reporting.
- Claims must say **agreement with independent LLM annotators** rather than `accuracy`, `ground truth`, or verified human perception.

## 4.8 Place text profile

For each place × emotion, preserve **three separate measures** without premature collapse into a single unqualified scalar:

1. **Coverage:** fraction of *available reviews* with any qualifying evidence (not fraction of clauses, which would overweight long reviews); describe sampled-review coverage, not the prevalence among all visitors.
2. **Direction:** support and opposition counts/distributions separated by strength, evidence type and qualifiers; allow both signs in the same review, without double-counting one review as independent observations.
3. **Uncertainty/coverage diagnostics:** number of contributing reviews/clauses, contested proportion, mean panel agreement and student score stability; distinguish these model-consistency diagnostics from statistical intervals or calibrated factual uncertainty.

Primary target: **explicit, location-attributed reported perception**, particularly first-person evidence. `indirect` remains secondary. `direct_indicator` is primary only when **non-visual** and separately identified, not silently equated with a felt experience.

Missing mention ≠ negative evidence or a zero atmosphere value.

## 4.9 Stage 2 annotator and shared-bias sensitivity (mandatory)

Recompute the **same Stage 2 association specification** separately using:
1. prompt-A **majority** labels; and
2. each of the three prompt-A **individual model** label sets.

Optionally repeat using prompt-B labels. A finding is **annotator-robust** only when the following are reported together:
- **Direction** of the estimated association across all label sets (same sign is a first diagnostic, **not enough alone**).
- **Magnitude** and practical differences (ranges of coefficients/effects, not only sign).
- **Statistical stability**, including appropriate place/spatial-block uncertainty and null tests. Predeclare tolerances or descriptive criteria; do not overinterpret a significance threshold.

**Additional explicit-versus-indirect shared-bias check (agreed adjustment):**
- **Primary association:** explicit reported atmosphere alone, keeping appropriate coverage and support/opposition measures.
- **Secondary analyses:** (a) add non-visual direct indicators; (b) include indirect evidence, clearly separated by type.
- Report which effects persist from the explicit-only track and which arise or strengthen primarily when indirect evidence is added. **Indirect-only discoveries are especially susceptible to shared LLM priors** about features such as greenery and calmness; flag as hypothesis-generating rather than independently observed associations.
- This check is *diagnostic*, not proof that shared bias has been eliminated: **all panel models may share a systematic prior**, including on ambiguous explicit judgments.

Do not describe agreement across panel models as human validation.

## 4.10 Archived methods not to revive as validated components

| Historical element | Repo audit reason |
|---|---|
| Paraphrased claims | Row 86 omitted an explicit `safe` observation |
| Same-model semantic verifier | Could approve extractor errors |
| Untuned zero-shot NLI as definitive judge | Sentiment leakage, including unrelated complaints |
| Metalinguistic relevance hypotheses as hard routing | Broad overfiring/positivity detection |
| Contextless fragment premises | Changed conclusions for rows 52 and 92 |
| Argmax category counts interpreted as accuracy | Near ties and no reference truth |

Archived reference: `research_audit/stage1a_final_2026-11-10/README.md`. Preserve original results and scripts.

## 4.11 Required limitation

> Stage 1A uses no human reference labels. It measures reproducibility, panel agreement, prompt sensitivity and student agreement with its LLM-defined teacher, and tests how downstream associations change across annotators and evidence types. This does not establish independent semantic accuracy or correspondence to the full population's perceived atmosphere.

## Next research tasks (not implementation claimed)

1. Freeze the versioned nine-category rubric and clause-segmentation specification.
2. Pilot the three-model/two-prompt panel on eligible source data with mechanical provenance checks.
3. Quantify disagreement and evidence-type stability **before** selecting silver training targets.
4. Define valid NLI hypotheses and type-specific supervision masks before student adaptation.
5. Set development-based gates and spatial-block evaluation design without using the final holdout to tune.
6. Predefine the Stage 2 annotator-by-evidence-type sensitivity analysis.

**No training, annotation run, or empirical validation is claimed by this document.**

### Research basis (guidance, not direct performance evidence for this project)
- Ratner et al. (2017), Snorkel / correlated weak supervision: https://arxiv.org/abs/1711.10160
- Ma et al. (2021), limitations of entailment-based zero-shot text classification: https://aclanthology.org/2021.acl-short.99/
- Laurer et al., `Political Analysis`, NLI text-classification transfer: https://doi.org/10.1017/pan.2023.20
- Kulmizev et al. (2026), LLM-based NLI annotation variation: https://aclanthology.org/2026.acl-long.752/
- scikit-learn classifier calibration documentation: https://scikit-learn.org/stable/modules/calibration.html

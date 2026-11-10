# Stage 1A — Final three-test audit and repair plan

**Status: archived for independent review — NOT a validated emotion-inference pipeline.**  
**Date:** 2026-11-10  
**Repository:** `UsernameIsJoe/Atmosphere-grounding`  
**Scope:** text-side Stage 1A: Component 1 extraction, Component 2 evidence relevance, Component 3 NLI inference. Image-side Stage 1B is not assessed.

> **Research-integrity notice.** This archive records a methodological failure: tests repeatedly produced model outputs and agreement statistics without independent truth labels, stable acceptance gates, or adequately controlled comparisons. Some *earlier* ABSA/NLI exploratory tests used synthetic authored examples. The final three tests archived here used **18 original excerpts of the repo's Google Places API-derived review corpus, not synthetic review premises**. That correct source provenance does **not** establish semantic correctness. Earlier research conclusions should not be represented as measured performance.

## Contents

| File | Meaning |
|---|---|
| [`scripts/stage1a_final_three_tests.py`](scripts/stage1a_final_three_tests.py) | **Actual final runner**; `--test 1`, `--test 2`, `--test 3` |
| [`scripts/stage1a_component1_ollama.py`](scripts/stage1a_component1_ollama.py) | Exact snapshot of extraction and same-model verification implementation |
| [`scripts/stage1a_component2_v3.py`](scripts/stage1a_component2_v3.py) | Exact snapshot of relevance prompt and mechanical checks |
| [`scripts/stage1a_component3_abc.py`](scripts/stage1a_component3_abc.py) | Exact snapshot of prior A/B/C NLI comparison and fixed hypothesis definitions |
| [`scripts/stage1a_component3_real_google_diagnostic.py`](scripts/stage1a_component3_real_google_diagnostic.py) | Exact snapshot of prior real-review NLI relevance diagnostic |
| [`results/test1.json`](results/test1.json) | **Original byte-for-byte** uploaded extraction results, including 18 original sentences, all claims, flags and full source metadata |
| [`results/test2.json`](results/test2.json) | **Original byte-for-byte** uploaded relevance results, including per-emotion annotations, source quotes and flags |
| [`results/test3.json`](results/test3.json) | **Original byte-for-byte** uploaded NLI results, including original/selected premises, native three-way probabilities and labels |
| [`SHA256SUMS.txt`](SHA256SUMS.txt) | Independent checksums of the three uploaded result files |
| [`source/reviews.jsonl`](source/reviews.jsonl) | Exact snapshot of the **214-record input corpus** at the time of testing |
| [`source/collect_summary.json`](source/collect_summary.json) | Exact snapshot of the Google Places collector's non-dry-run source summary |

The five scripts and two source files are **exact snapshots of existing repo files**; they remain separate from the active implementations in the repository's root `scripts/`. The snapshots refer to supporting modules and data that remain at repository root. **This folder is an audit bundle, not a self-contained Python application.** No experiments have been rerun or altered while archiving.

### Provenance and reproducibility

All three JSON results report status `complete`, the identical source manifest SHA-256 `04df89e7d2fa7a4018eeca8f2188c15ab8b69be3286f0ededb71cdcb8d15a791`, and the source dataset SHA-256 `f08422c068b8e52a40a93d14a4a3d12955d7f52997409f974a481c77748c7328`.

- Input: `data/processed/reviews.jsonl`, 214 reviews / 43 places. The source collector at `src/atmosphere_grounding/collect/pipeline.py` reads Google Places API review text; `data/processed/collect_summary.json` reports `dry_run=false`.
- **18 sampled source sentences across 18 place IDs**, excluded from the preceding 20-review extraction pilot and 40-sentence NLI diagnostic. Literal source text, character offsets, place IDs, original-review hashes and dates are retained.
- **Limitation:** the raw Google API response cache is not committed; therefore, these reviews are authenticated *against the stored processed corpus and collector*, not independently refetched or attested by Google. Do not strengthen that statement.
- Sampling groups (`reported_word_candidate`, `environmental_word_candidate`, `other_control_candidate`) are **lexical heuristics, not human labels**. Example: “The lights are so beautiful and calming” fell into the last group even though it clearly contains an atmospheric descriptor.
- Framework: Qwen3 8B (structured extraction and relevance), BART-MNLI (directional and metalinguistic hypothesis checks). Same-model Qwen verification is **not** independent ground truth.
- The three tests assess three pilot emotions: **calm, inviting, safe**, not the full nine-emotion target.

Run the *original active version* from the repo root (only for reproducing these tests, **not** part of the proposed new repair experiments):

```powershell
python scripts/stage1a_final_three_tests.py --test 1
python scripts/stage1a_final_three_tests.py --test 2
python scripts/stage1a_final_three_tests.py --test 3
```

Original local outputs: `reports/stage1a_final_three_tests/test1.json` through `test3.json`. They have already been run and are archived here; **do not overwrite them or reuse this inspected set as an untouched holdout.** Compare source and result checksums before any reproduction.

## 1 — Audited results and identified problems

### Test 1 — Source-grounded extraction: **conditional, not validated**

**Observed counts:** 18 sentences; 35 proposed claims; 34 literal unique source quote matches; 2 claims flagged by the same-model verifier; every sentence yielded at least one claim.

**Actual semantic failures:**

- **Row 86:** the original comment explicitly calls the place `safe`, but Component 1's extracted claims cover meeting friends, sitting in the sun, and `7days a week`, without carrying **safe** into any claim. Component 2 later recovered it from an original quote by reading the original sentence. That is *not* proof that extraction preserved it.
- **Row 56:** “that you don't expect to see” became “The space is not expected to be seen,” an awkward change in viewpoint; same-model verification marked it supported.
- **Row 86:** `7days a week!` became “available for enjoyment 7 days a week,” a potentially unsupported availability claim; this one was correctly flagged.
- Claims sometimes retain an emotion only as an adjective embedded in a different proposition instead of representing it consistently. Conversely, **the row 6 'peaceful park' was not completely lost**: it is present in an extracted claim. The actual issue is inconsistent claim semantics and completeness.

**Meaning:** quote matching checks literal alignment, not whether extracted meaning is complete and source-faithful. Neither extraction recall nor semantic precision is measured.

### Test 2 — Relevance / evidence routing: **fails as a hard filter**

**Observed counts:** 35 claims; 34 labeled place-related; 8 claims carry some mechanical inconsistency flag. Per emotion: calm direct 5 / indirect 5 / not applicable 25; inviting direct 3 / indirect 15 / not applicable 17; safe direct 1 / indirect 5 / not applicable 29.

**Actual failures:**

- **Row 24:** road closed to automobile traffic was labeled not applicable to **all three emotions**. It could be relevant as indirect or conditional evidence, especially for calmness or safety, depending on the scope and definitions. Its applicability must be **adjudicated**, not presumed positively.
- **Row 41:** “a little off the beaten path” was connected indirectly to **all three** emotions with unverified rationales — indiscriminate extrapolation.
- **Row 6:** 'peaceful' was extended to inviting and safe, and decorative bollards were extended to calm and inviting, but several indirect classifications had **empty required source quotations** and were flagged. The model created relevance without a traceable supporting span.
- **Row 6:** the artist attribution was labeled `unrelated_personal` although it describes a place feature's authorship, not an unrelated visitor event; the place-relatedness/type conflict was flagged.
- **Row 86:** Component 2 could tag the explicit word `safe` from the original quote even though Component 1 had omitted that meaning in its claim. This masks an extraction failure if stages are evaluated only at the end.

**Policy clarification:** The researcher's preferred treatment of source-grounded **police patrol as direct safety evidence** is retained as a legitimate operational interpretation. Do **not** automatically call it a classification error. What 'direct evidence' means must be defined before measuring performance, separate from 'first-person reported feeling'.

**Meaning:** this component can annotate candidate relationships, but it is not defensible as an irreversible relevance gate, especially for potentially contradictory/negative evidence.

### Test 3 — NLI / emotion inference: **fails as a definitive judge**

**Observed counts:** 54 original sentence–emotion pairs; 25 selected quotation-level NLI evaluations; no selected evidence for calm in 10/18 cases, inviting 9/18, and safe 14/18. The direct-atmosphere and metalinguistic relevance hypotheses disagreed on 2 calm, 11 inviting and 2 safe sentences. These are **model behaviors, not accuracy**.

**Actual failures:**

- **Row 13:** “I just ate there and, it was a very disappointing meal.” Whole-sentence BART NLI labeled **contradiction for calm, inviting, and safe** — unjustified global conclusions from meal dissatisfaction. Component 2 correctly selected no evidence, demonstrating why full-sentence NLI alone is also unreliable.
- **Row 52:** full peaceful-atmosphere sentence: calm **entailment**; selected quote `peaceful contemplation`: calm **neutral**. Context and premise length change the decision, even though the core emotion cue survives.
- **Row 92:** full `Peaceful cute bit of green space`: calm **entailment**; quote `Peaceful`: calm **neutral**. Selection destroys useful context.
- **Row 75:** “feel like a working, living community” yields whole-sentence calm **entailment** despite no explicit calm description; potentially unwarranted inference.
- **Row 27:** “The lights are so beautiful and calming” is rightly a plausible calm statement, but was sampled as a control by lexical heuristics — group aggregates must not be interpreted as reference-class performance.

**Meaning:** a sentence's relevance to an atmosphere is a distinct question from entailment of that atmosphere. Generic MNLI does not automatically solve indirect/evidence-conditioned reasoning, and isolated quotes can damage well-formed NLI premises.

### Cross-cutting failure

**The critical missing component is independent correctness assessment.** Previous work emphasized output counts, consistency, prompt changes and model comparisons without a fixed human-adjudicated reference. No reliable accuracy, recall, calibration, or pipeline improvement estimate currently exists. Previous synthetic demonstration cases cannot support real-review performance claims.

## 2 — Proposed repair plan (NOT implemented or tested)

**Rules for every stage:** original Google review text only; frozen provenance; pre-registered question, metric, acceptable failure rate and stopping decision; independent annotations; one controlled variable changed per experiment; separate development from untouched holdout; preserve negative evidence, hedge/negation/context and raw source; no endless prompt iteration.

| Phase | Action and one core question | Evaluation and gate | Next step dependent on outcome |
|---|---|---|---|
| **0. Independent reference benchmark** | Define what counts as an atomic source claim, place attribution, explicit versus indirect evidence, emotional relevance, contradiction, neutrality and uncertainty. Create a human-adjudicated set of **new, real reviews** with separate development and untouched, ideally place-disjoint holdout. | Two annotators (or researcher plus genuinely independent adjudicator) mark source spans and omitted claims; record agreement, disagreements and a fixed adjudication guide. No model output can define the reference. Freeze sample, metrics and numeric pass thresholds **before** running models. | **If incomplete/ambiguous:** stop model work and repair definitions/annotation. **If frozen:** Phase 1. The 18 previously inspected cases may inform annotation guidelines, not count as blind holdout. |
| **1. Repair extraction** | Is Qwen3 extracting complete and faithful claims, or would directly using source spans be safer? Compare frozen current extractor against a **verbatim-span baseline** on the same reference sentences. | Score claim/span precision and recall against independent annotations; additionally audit omissions of emotion words, scope, negation, attribution, causation and hallucinations. Keep source text in every handoff. | **Pass:** freeze extraction. **Fail:** choose span-based/source-original fallback; don't feed unsupported paraphrases to later stages. Proceed only once a safe evidence representation exists. |
| **2. Repair relevance** | Does Component 2 locate evidence for or against each emotion without inventing links or discarding environmental indicators? Test first on **gold source observations** (isolates this stage), then on frozen Component 1 output (tests error propagation). | Independent relevance precision/recall **by emotion, evidence type, and direction**; especially recall of negative/counterevidence, and literal source support. Distinguish direct-to-place evidence from explicit felt experience. | **Pass:** freeze routing. **Fail:** mark advisory only and retain all original source text for downstream checks. No irreversible filter. |
| **3. Repair inference** | Can NLI distinguish true entailment/contradiction from merely relevant context? Evaluate identical source statements with frozen BART and **one explicitly registered evidence-conditioned formulation**; avoid bare, contextless adjective fragments. | Human-judged 3-way inference labels on gold relevant evidence; confusion matrix, false contradiction/entailment rates, coverage by explicit vs indirect evidence and changed-length contexts. No calibration or emotion intensity claims from softmax. | **Pass for a subset:** lock only supported case types. **Fail for indirect evidence:** return `relevant_but_inference_unresolved` rather than forced emotion. **Fail globally:** disable NLI emotion adjudication. |
| **4. End-to-end holdout validation** | Is the assembled chain better than using unchanged source sentences directly? | On untouched place-disjoint reviews compare complete pipeline, original-text baseline and safety fallbacks; assess error propagation, claim/selection/inference metrics and reproducibility. | **Pass precommitted gates:** version-lock only measured capabilities. **Fail:** freeze a conservative source-preserving research representation with clearly disabled inference claims. |

**Budget discipline:** Phase 0 is prerequisite. Each subsequent phase has one primary comparison with precommitted decision metrics; no new model search or retrospective prompt selection. If a phase fails, activate its predetermined conservative fallback. The numeric thresholds are **not yet set**, because setting them responsibly requires agreeing on task definitions, annotation quality and error costs; inventing numerical success bars now would repeat the earlier mistake.

## 3 — What is actually locked versus proposed

- **Archived/fixed:** all three original result files, source manifest and dataset identifiers, source-preserving sampling protocol, original scripts and their original frozen prompts and model checkpoint names.
- **Not validated:** completeness of Component 1; Component 2 accuracy and filtering; Component 3 emotion inference; generalization to all nine emotions, other locations, or images.
- **Proposed next action only:** build and freeze an independent real-review annotation benchmark. **No repairs have been implemented and no new experiments have been authorized by this archive.**

## 4 — Review questions before any future work

1. Is the researcher's operational distinction between *direct safety evidence* and *first-person felt safety* correctly represented?
2. For each emotion, when is an environmental fact **relevant**, and when does it actually support or contradict the emotion? Can reviewers agree?
3. Is the primary output a **source-linked evidence inventory**, or a **valid emotion assertion**? Those require different loss functions and validity standards.
4. Which failures are unacceptable (missing an explicit negative feeling, false safety claim, lost original quote)? Assign priorities *before* setting pass criteria.

**Decision as of this archive:** retain source-grounded extraction only as provisional; make relevance advisory; treat NLI as exploratory; do not claim that the end-to-end emotion inference is validated.

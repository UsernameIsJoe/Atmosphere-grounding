# Stage 1A — Roadmap after Qwen3-8B Component 1 pilot (2026-11-08)

## Decision snapshot

Do not make a premature choice between **(a) prompt revision**, **(b) Component 2 relevance/filtering**, or **(c) another local LLM** based on a self-verifier pass rate. All three are testable, but there is a clear dependency order:

1. **Measure first**: independently annotate a fixed real-source reference of atomic observations and relations, including omissions; split an untouched holdout before optimizing prompts or choosing models.
2. **A — focused prompt revision first**, on the existing Qwen3-8B checkpoint. It addresses actual errors in an inexpensive one-variable experiment. Compare the current prompt with narrowly specified alternatives; do not tune on the final holdout.
3. **B — evaluate Component 2 with high recall**, using the *same frozen extracted claims* and source context. Initially compare no gate vs location-attribution gate vs emotion-specific relevance soft weighting; keep Component 3 unchanged for ablation.
4. **C — independent challenger local LLM**, using the best frozen extraction prompt and the *same identical input cases*. `gpt-oss:20b` is already installed on the researcher's Ollama machine and supports structured output, making it the lowest-friction size-diverse candidate. Model family / resource consumption must be recorded; do not assume that larger necessarily means more faithful claims.

This order is a recommendation rather than a claim of validated performance. The original architecture is **source-grounded extraction → emotion-specific relevance → directional NLI**. Do not collapse relevance with NLI, or force Component 1 to output one of nine emotions.

## Empirical observations from actual Qwen3 outputs

The researcher's complete local run used **20 real reviews and 56 sentences**, model `qwen3:8b`; 88 candidate claims, 81 exact unique quotations, 72 candidates passing same-model semantic self-verification plus source quote checks, 16 flagged; zero runtime failures. Hash of frozen sentences: `144aee54fd70fdd2b440bc1e0f05fc71b63e79e26bf525b995a6260c0936d00e`. This is **not** 72/88 semantic accuracy.

- Real row 55: Qwen3 makes an environment→felt-protection/comfort connection that the earlier GLiNER+GTS setup failed to link. But `circulous paths` became `winding paths` in a passed candidate, demonstrating potential semantic normalization without justification.
- Row 74: `Ckean, well kept, and well patrolled by police.` becomes candidate `The area is Ckean.`, and the same-model verifier marks it supported, although `Ckean` is ambiguous/noisy source text. A good extractor should be able to abstain or mark uncertain, not invent an interpretation.
- Row 97: the generator converted a reviewer's speculative causal explanation about sunlight loss to a definite claim; the verifier flagged this as unsupported. Proper extraction should preserve the reported uncertainty up front, avoiding generation of unsupported candidates.
- Row 123: the verifier flagged `Ada is accessible` as unsupported because the source reads `Ada accessible.` This is an **overliteral semantic check**, not reliable evidence of factual error.
- Row 139 and 187: generated evidence-quotation fields include `/think` material not in the source; exact quote checking flags them despite some underlying claims being recoverable. Inspect whether model thinking-mode boundaries leak into the content; do not simply strip evidence text post hoc and mark it supported.
- Row 19 sentence 1 `Unbelievable!` yielded no claims, appropriately retaining original-source fallback, but whether an expressive fragment should become a grounded observation needs explicit adjudication.

For a complete evaluation, label **each original meaningful observation**, not just outputs. Otherwise a model that returns too few claims can appear more precise. Track claim faithfulness, observation coverage/recall, relation precision, uncertainty/negation fidelity, invalid quoted spans, and abstention rate. Select a primary target weighting that penalizes hallucinated relations and omitted relevant observations, rather than optimizing candidate counts.

## A: prompt experiments — narrowly scoped

Keep the model/quantization/checkpoint, input corpus, sentence boundaries, JSON schema, temperature and context settings identical.

- **A0 baseline:** original `EXTRACT_SYSTEM` and `VERIFY_SYSTEM` in `scripts/stage1a_component1_ollama.py`.
- **A1 attribution / ambiguity discipline:** require claims to be explicit about subject and source; mark unclear referents as uncertain instead of silently resolving; preserve speculation, temporality, negation, experience vs environmental fact. No emotion target labels.
- **A2 evidence-first:** extract **exact quoted evidence spans** first, then link subjects/predicates to these spans; explicitly permit abstention on ambiguity and avoid semantic rewriting of misspellings. Keep original sentence fallback.
- **A3 verifier ablation:** separately compare deterministic exact-offset validation, same-model verification, and a **different model** or human review; same model approving its own claim does not establish semantic correctness.

Important nuance: exact quotation is a *provenance* test, not a semantic entailment check. An entire original sentence as quote can contain an incorrect LLM paraphrase. Sentence-level context can resolve pronouns; prior full-review GLiNER experiments did **not** demonstrate improved semantic extraction, and cannot be assumed to transfer to an LLM.

## B: Component 2 must not become a destructive filter

Component 2's task is **emotion-specific relevance of a claim *as evidence about the location***; it is distinct from Component 3 direction (`entailment`, `contradiction`, `neutral`). A statement can be highly relevant evidence *against* calmness without containing the word `calm`.

Prefer an experimentally tested **two-factor, high-recall gate**:

- **Location-attribution:** Does the original review attribute this observation/experience to the place, its physical environment, use, or perceived atmosphere? Distinguish unrelated visitor events.
- **Emotion applicability:** Is the evidence potentially informative about each target emotion, including *contradictory* evidence, not just positive cues?

Compare:
- **B0:** no gating: all grounded claims (and source sentence fallback) enter fixed NLI.
- **B1:** preserve all observations but add location-attribution annotations; no hard deletion.
- **B2:** emotion-specific relevance probabilities or ranking, tested against human labels. Initially **soft-weight or abstain** rather than permanently removing claims. Audit false-negative relevance (particularly implicit evidence such as traffic noise and environmental neglect).
- **B3:** compare original unaltered sentence premise vs extracted claim premise with the same NLI checkpoint and hypothesis template. Without this control, an apparent NLI gain may actually come from paraphrase artifacts.

A premature strict gate risks suppressing precisely the indirect evidence we need: `traffic is deafening` may be **relevant to calmness as counter-evidence**, despite containing no emotion term. Relevance accuracy needs independently labeled true/false examples that reflect the location attribution and the nine emotion definitions. The current pilot hypothesis set covers only `calm`, `inviting`, `safe`; the nine-label definitions are not yet a complete operational evaluation set.

Keep the downstream NLI model fixed for these experiments; record uncertainty, calibration, and hypothesis-language sensitivity. NLI softmax is not a calibrated location-emotion intensity.

## C: another local model — why not immediately?

The user already has `gpt-oss:20b` installed in Ollama. It supports structured-output formats (model capabilities documented at https://ollama.com/library/gpt-oss), so it is a practical **single challenger** to `qwen3:8b`; larger model size does not guarantee extraction quality. Compare only after freezing prompt, schema, dataset and human gold. Differences in memory/latency/decoding and thinking mode must be logged. A second challenger such as `gemma3:12b` can be deferred rather than starting a model zoo.

Use paired comparison of each model's **same real review sentences**. Do not create synthetic example reviews for headline results. Same-model verification outputs must not be called accuracy.

## Research grounding

- Metropolitansky & Larson, ACL 2025, *Towards Effective Extraction and Evaluation of Factual Claims*, https://aclanthology.org/2025.acl-long.348/ : claim extraction is limited by coverage, atomization, decontextualization and ambiguity; Claimify provides a useful precedent, not directly validated on urban reviews.
- Li et al., ACL 2025, *Task Calibration: Calibrating Large Language Models on Inference Tasks*, https://aclanthology.org/2025.findings-acl.362/ : NLI inference can rely spuriously on premise or hypothesis alone; treating one fixed NLI as an objective measurement requires calibration/validation.
- Kulmizev et al., ACL 2026, *Label and Explanation Variation in LLM-Based Annotation: a Case Study in NLI*, https://aclanthology.org/2026.acl-long.752/ : model annotation judgments can diverge from human variation; same-model confirmation is not independent ground truth.
- Ollama model docs: https://ollama.com/library/gpt-oss ; https://ollama.com/library/qwen3%3A8b .
- For existing ABSA methods, code and run/artifact provenance are indexed at [experiments/stage1a_component1/](../../experiments/stage1a_component1/README.md).

## Minimal next milestone

**Freeze a human-adjudicated reference** on the known real-review failures before making prompt changes. Then test A0/A1/A2 on a development subset and a held-out set with explicit criteria:

- no decrease in meaningful-observation coverage,
- fewer unsupported links and lost negation/uncertainty,
- equal or better preservation of environment→experience attribution,
- valid source quotations and traceable offsets,
- preserved original-source fallback.

Once that meets standards, test B0/B1/B2 relevance with NLI fixed and perform the independent C challenger if A's errors remain material. No scientifically justified claim of a winning model or pipeline until that comparison exists.

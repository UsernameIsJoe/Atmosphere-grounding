# Stage 1A M2c — executed relevance-gate results and closeout (2026-11-04)

**Status:** Complete. The preregistered *overall* direction gate passed; no further prompt/threshold optimization is planned on these examples.

## Verified execution

- [GitHub Actions run 41888211091](https://github.com/UsernameIsJoe/Atmosphere-grounding/actions/runs/41888211091), head commit `978bbba504633a801a7d4bc016a36e7aabc49bda`, **success**.
- Artifact `13350819660`, `stage1a-m2c-relevance`: `cases.json`, `results.jsonl`, `summary.json`.
- 20 authored short claims × three emotions = **60 case–emotion decisions**, **120 BART-large-MNLI evaluations**. One fixed zero-shot metarelevance prompt and frozen 0.5 entailment-probability operating threshold. No tuning, fitting or independent annotators.
- Categories `D` = direct, `R` = related/indirect, `N` = unrelated/insufficient, assigned for **experimental design**, not third-party ground truth.

## Preregistered gate evaluation

| Measure | Observed | Passing criterion | Overall decision |
|---|---:|---:|---|
| Expected relevant (`D/R`) retained | **13/16 = 81.25%** | ≥75% | Pass |
| Expected irrelevant (`N`) retained | **8/44 = 18.18%** | ≤25% | Pass |

Per-emotion descriptive breakdown:

| Emotion | Expected relevant retained | Expected irrelevant retained | Mean relevance entailment: relevant / irrelevant |
|---|---:|---:|---:|
| Calm | 4/5 = 80% | 4/15 = 26.67% | 0.8036 / 0.3322 |
| Inviting | 6/7 = 85.71% | 2/13 = 15.38% | 0.7306 / 0.3044 |
| Safe | 3/4 = 75% | 2/16 = 12.5% | 0.6594 / 0.2490 |

**The overall predetermined criteria both passed.** Calm's per-emotion false-positive rate is *slightly* above 25%, so do not portray perfect per-emotion performance. Per-emotion sample sizes are extremely small. These proportions are **not real-world accuracy claims**.

## Actual failure cases (from `results.jsonl`)

Numbers are NLI relevance-entailment softmax probabilities, not calibrated relevance or emotion strengths.

**Calm:** missed related `The traffic is deafening` (0.460). Incorrectly retained `The entrance is welcoming` (0.516), `The benches are comfortable` (0.838), `The path feels safe` (0.896), `The path does not feel safe` (0.687). The labels for cross-emotion relevance are conceptual assumptions, and some borderline features could be indirectly related; this illustrates scope ambiguity as well as model overreach.

**Inviting:** incorrectly retained `The path feels safe` (0.738), `The path does not feel safe` (0.600); missed related `The trees are beautiful` (0.226).

**Safe:** incorrectly retained `The entrance is not welcoming` (0.674), `The benches are comfortable` (0.730); missed related `Broken glass covers the sidewalk` (0.312). The broken-glass miss is especially important for safety.

Direct-NLI baseline output in artifact is **not** a matched relevance classifier, so its support rates must not be construed as an apples-to-apples accuracy improvement.

## Interpretation and stop decision

- **Direction supported, very narrowly:** even an off-the-shelf BART NLI metarelevance hypothesis can screen some obviously irrelevant short observations without being tuned. This is useful as a *potential* evidence-preservation/filtering mechanism, not proven gains to emotion inference.
- **Do not further optimize this particular gate on the 20 authored cases.** The preregistered direction gate is decided.
- **Do not choose AOS or any ABSA extractor.** The pilot contains authored statements without automatic aspect extraction; it does not adjudicate between DeBERTa, SetFitABSA, AOS triplets or dependency parsers.
- **One optional bounded real-data check** may determine if this signal survives review-style language and attribution (e.g. 20–30 real clauses across multiple locations, sample selected before scoring, inspect source fidelity and cases flagged for inclusion/exclusion). It must not be mistaken for independent measured emotion accuracy without external annotations. No automatic expansion into a model-tuning loop.
- **Return project priority to Stage 1B** theory-supported image/visual-quality feature library and then Stage 2 location-level image–text associations. Stage 1A remains exploratory; preserve raw text and contradictions, never hard-delete claims only because a relevance gate rejects them.

## Scope note

The apparent high retained fractions on designed examples can mask domain shift, semantic disagreement about `R` vs `N`, low support counts, binary threshold artifacts, and lack of calibration. This experiment therefore passes only the *feasibility* gate, not validation of atmosphere grounding.

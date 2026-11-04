# Stage 1A — M2b: controlled claim-level NLI and relation ablation

**Date:** November 4, 2026. **Status:** Code, unit tests and GitHub Actions workflow committed; successful experiment output not yet verified.

## Why this experiment

[Completed M2](stage1a-m2-structured-evidence-results-2026-11-04.md) showed that appending extracted annotations changes BART predictions, but duplicating the source review changes predictions too. Worse, the AOS swap test was inoperative on all 20 real reviews (not enough grounded relations), and negation errors such as `0 adequate bike parking → adequate` could produce misleading support. **Do not scale that M2 format unchanged**.

## Hypothesis and isolation

Test whether **per-claim original-source NLI**, conflict-preserving aggregation and correctly/incorrectly linked aspect–opinion representations behave differently from full-review NLI on *controlled inputs*. This is a test of the **inference and fusion mechanism**, not a new ABSA checkpoint comparison.

**18 researcher-authored controlled cases**, including six directional contrast comparisons, seven two-claim examples with operative swapped aspect–opinion controls, and a reviewer-only emotional claim. Each has verified literal aspect/opinion source offsets, including explicit negation and quantity. The cases are purpose-built logic probes, **not independently human-rated samples or representative real reviews**.

## Fixed inference design

- NLI: `facebook/bart-large-mnli`, native entailment/neutral/contradiction.
- Fixed exploratory hypotheses: calm, inviting, safe (one direct phrase per emotion).
- Every case/emotion is evaluated with:
  1. **Full review** unchanged.
  2. **Duplicate review** (a formatting/repetition sensitivity control).
  3. **Structured reexpression** built from the authored aspect–opinion records.
  4. **Swapped relations** — rotate the opinions among aspects when there are 2+ pairs, preserving the same word inventory.
  5. **Reordered original clauses** — word order perturbation on the same claims.
  6. **Each original source clause independently** through NLI.
- Claim outputs are retained individually. Also compute **unweighted mean probabilities** as a deliberately naive baseline and **separate any-support / any-contradiction flags** that do not silently erase conflict. This flagging is a *model-output diagnostic*, not independently validated evidence logic.
- **18 cases × three emotions = 54 case–emotion records**; each takes five aggregate/text-format evaluations plus one or two independent claim evaluations; expected **345 inference calls** (7 two-claim cases, 11 single-claim cases: `3 × (7×7 + 11×6) = 345`).
- Artifacts: `controlled_cases.json`, `cases.jsonl`, `summary.json`; all complete source text, offsets, NLI class probabilities, swapped eligibility, and contrastive comparisons retained.

## Design limitations

- **Actual DeBERTa, SetFit, AOS, dependency extraction outputs are deliberately not used in M2b**: M2 has already compared them as representations and showed extraction errors. Here, authored source-faithful relations isolate inference/fusion before returning to real extractor outputs. This is not selection of AOS as a final model.
- Structuring rephrases a source claim, so changes may reflect paraphrase sensitivity rather than correct use of structure. Duplicate and reordered controls detect some, not all, format sensitivity; no token-length match.
- The claim sets are not necessarily logically sufficient for broad atmosphere hypotheses; directional predictions are exploratory, not a simple counted accuracy test.
- A swapped relation is intentionally false and should not be treated as valid evidence; changes are sensitivity tests, not proof of correctness.
- Genuine fusion must later handle speaker attribution, negation scope, original-source provenance, contradictions and missing claims for real reviews; this pilot does not solve them.
- No ground-truth accuracy, calibrated emotion intensity, nine-category ontology or downstream image association is established.

## What will be inspected next

1. **Logic minimal pairs**: quiet/not quiet; safe/not safe; welcoming/not welcoming; adequate vs *zero adequate*; changing loud to quiet while other context is held fixed.
2. **Seven effective swap controls**: exact changes in NLI results for correct vs false aspect–opinion pairings.
3. **Independent claim aggregation**: whether it exposes simultaneous supportive and contradictory results that whole-review or mean hides.
4. **Repetition/reordering**: whether observed prediction shifts exceed simple input perturbation effects.
5. **Next decision**: If claim-level evidence is useful on transparent controls, prototype source-grounded clause extraction on a small real-review subset while preserving *unmatched* sensory and adjectival statements; then compare against original NLI without pretending it is human-validated accuracy.

## Implementation

- [Script](../scripts/stage1a_m2b_claim_nli.py)
- [Tests](../tests/test_stage1a_m2b_claim_nli.py)
- [Workflow](../.github/workflows/stage1a-m2b-claim-nli.yml)

# Stage 1A — ABSA-indexed source-clause NLI (implementation and evaluation)

**Date:** 2026-11-04  
**Status:** Implemented with CI workflow; execution results not yet verified.

## Decision: make ABSA operational without rewriting evidence

The successful integrated pilot (run [41891532716](https://github.com/UsernameIsJoe/Atmosphere-grounding/actions/runs/41891532716)) produced 20 aligned reviews, 58 source passages, 29 DeBERTa aspects, 88 SetFitABSA aspects and 11 original-source-aligned AOS pairs. It did not exploit ABSA to isolate evidence when a source sentence contains contrasted observations.

We now preserve that frozen output and **index clauses by source-verified ABSA targets and aspect/opinion relationships**. All NLI premises are verbatim substrings with absolute offsets; no rewrites, positive/negative sentiment inference from ABSA polarity, or hard deletion. The existing original sentence-level NLI predictions are retained as a comparator.

Implementation: [`scripts/stage1a_absa_guided_nli.py`](../scripts/stage1a_absa_guided_nli.py), tested by [`tests/test_stage1a_absa_guided_nli.py`](../tests/test_stage1a_absa_guided_nli.py), run by [`.github/workflows/stage1a-absa-guided-nli.yml`](../.github/workflows/stage1a-absa-guided-nli.yml).

## Mechanics

1. Reuse all 60 review–emotion records from the **actual integrated** ABSA+NLI artifact.
2. Split original sentences only at identifiable contrastive markers (but, however, whereas, semicolon). Preserve literal character offsets and the negation in each clause; retain the discourse marker with the following clause. Do not claim this covers every subordinate clause or quote.
3. Assign an `absa_guided` index to a clause if a source-verified DeBERTa/SetFit aspect or both source-verified AOS relation spans fall **within that clause**. If a relation crosses a clause split, explicitly keep the original whole sentence as a fallback.
4. Run unchanged BART-large-MNLI on **every** original clause, with matched emotion hypotheses from the source pilot. Distinguish **indexed** clauses from **unmatched retained** clauses. Compare outputs to the precomputed **whole sentence** and **whole review** NLI results.
5. Report affected/refined clause count, ABSA index coverage, unmatched evidence retention, new NLI class decisions, and contradictory evidence, with all passages and source offsets.

## Scientific interpretation and limitation

This makes ABSA operational as an **evidence attribution/index**, rather than decoration appended to the premise. However, on its own it **does not prove** ABSA improves NLI, because the same clause-level NLI results could be obtained by a blind segmentation method. The causal value of ABSA would require validating whether ABSA indexing prioritizes *correct* and *emotion-relevant* source observations compared with a non-ABSA ranking, ideally against reviewed evidence. We explicitly do not call class changes accuracy gains.

Additionally, the fixed pilot contains only a few original contrastive sentences. If too few source clauses are split or attributed, conclude **insufficient sample coverage** rather than escalating model tuning or making strong claims. This bounded implementation is one concrete step within the integrated approach; it does not reopen the model bake-offs.

## Next check

Audit this execution, then make a direct keep/adjust judgment on the real source examples. Avoid claiming robust interpretation or final emotion intensities from these model-only diagnostics.

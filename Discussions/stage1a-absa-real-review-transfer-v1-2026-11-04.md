# Stage 1A ABSA — Real-review relationship extraction transfer test

**Date:** 2026-11-04. **Status:** code, partially annotated comparison references, unit tests, and GitHub Actions workflow committed. New workflow results **not yet verified**.

## Question

Do AOS-T5, rule-based spaCy dependency relations, or joint GTS-BERT ASTE extract appropriate **aspect–opinion** relationships from **the same actual urban-place reviews**?

This is a **bounded improvement of the ABSA component only**. Relevance, emotion NLI, and the full Stage 1A pipeline remain frozen.

## What is actually tested

- Use the existing fixed **20 real reviews** from the successful AOS/dependency run [41861834607](https://github.com/UsernameIsJoe/Atmosphere-grounding/actions/runs/41861834607). Reuse *original* AOS and dependency predictions unchanged. No new dataset or source filtering.
- Run GTS-BERT joint ASTE on the exact same 20 source reviews using the corrected source-offset alignment and the existing author-provided decoder.
- Include **29 source-phrased target relationships across all 20 reviews** in [`data/evaluation/stage1a_absa_real_review_targets_v1.json`](../data/evaluation/stage1a_absa_real_review_targets_v1.json). Those references are **assistant-authored, partial, and not independent**. They are not an exhaustive annotation of every valid relationship in a review.
- Strictly validate source offsets and compare **whether each predeclared target pair was recovered**. Report count and fraction of predefined targets recovered; DO NOT interpret model-emitted other relations as false positives because reference annotations are incomplete.
- Save the complete 20-review side-by-side evidence including raw GTS predictions, original texts, full AOS/dependency predictions, matching status, and all ungrounded relations. Include explicit caution for negation and quantities: `0 adequate bike parking` can have the lexical pair `bike parking → adequate` yet be semantically misrepresented.
- Review quality should additionally be **manually adjudicated with clear full-reference annotation** before a model choice. This experiment measures *partial target recovery*, not precision, full recall, F1, reliability, or independent accuracy.

## Reproducibility

- [Workflow](../.github/workflows/stage1a-absa-real-review-transfer.yml): performs Python preflight tests, downloads existing fixed artifacts, runs joint GTS ASTE on all 20 original reviews, computes same-source target recovery, validates case and target counts, uploads all per-case predictions.
- [Evaluator](../scripts/stage1a_absa_real_review_comparison.py)
- [GTS real-review adapter](../scripts/stage1a_gts_joint_aste_probe.py)
- [Unit tests](../tests/test_stage1a_absa_real_review_comparison.py)

## Interpretation guardrails

1. A model with a high target recovery fraction could still emit many incorrect extra pairs; precision is **not determined**.
2. A model with a low recovery fraction may still extract other genuinely useful pairs not included in the partial reference set.
3. Lexical reference pair matching is insensitive to actual negation or polarity correctness; inspect full sentence and raw relation data.
4. Domain shift (restaurant/laptop to urban place descriptions) and GTS truncation of long reviews remain possible failure causes.
5. An exhaustive independently reviewed held-out reference set is required before saying a model is trustworthy or selecting it for production.

**Do not count this workflow as completed until a confirmed successful GitHub Actions run and artifact have been audited.**

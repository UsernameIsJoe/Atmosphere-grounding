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

## Execution audit — fixed workflow, successful run

The initial [run 41906201659](https://github.com/UsernameIsJoe/Atmosphere-grounding/actions/runs/41906201659) **failed during Python compile before any extraction**: a literal `\\n` had been inserted between two `parser.add_argument` statements in `stage1a_gts_joint_aste_probe.py` (`SyntaxError: unexpected character after line continuation character`). This was an implementation mistake, not a model-capability result.

The source was fixed in commit `d539175f02abd864b606fcf8959f85db8665ae5a`.

The corrected [run 41906619654](https://github.com/UsernameIsJoe/Atmosphere-grounding/actions/runs/41906619654) **completed successfully**: Python compilation, unit tests, frozen-source artifact downloads, dependencies, GTS inference on 20 source reviews, three-method comparison, provenance assertions and artifact upload all passed. Artifact `13360447177`, containing `gts_reviews.jsonl`, `side_by_side.jsonl`, `summary.json`.

### Partial-reference relationship recovery on the 20 real source reviews

| Method | Recovered /29 prespecified assistant-authored relationships | Fraction | Literal source-aligned emitted relationships |
|---|---:|---:|---:|
| AOS T5 | 5/29 | 17.2% | 12 |
| spaCy dependency | 22/29 | 75.9% | 67 |
| GTS-BERT joint ASTE | 9/29 | 31.0% | 12 |

**These are NOT independent accuracy, full recall, precision or F1.** The fixed 29 target pairs are an *incomplete assistant-authored reference set*, prepared after earlier outputs were inspected. The additional 67 dependency rule matches have unmeasured semantic quality. This benchmark cannot establish which model is trustworthy.

Examples from artifact:
- Row 53 `The staff were so friendly and helpful.`: dependency finds **staff→friendly** and **staff→helpful**; GTS finds only **staff→friendly**; AOS finds neither as accepted grounded relations.
- Row 57 `beautiful green plants`: dependency recovers **plants→beautiful**; GTS predicts **green plants.→beautiful** (a plausible longer target span), which the strict lexical benchmark does **not** credit as the exact pair. Thus the metric can *understate* true semantic usefulness.
- Row 26 `0 adequate bike parking`: AOS and GTS both recover the lexical pair **bike parking→adequate**, yet GTS gives **positive** polarity even though `0 adequate` indicates an absence. **Lexical pair recovery is not semantic validity**.
- Row 55 `a charming and cozy park`: dependency recovers **park→charming** but does not recover **park→cozy** in the strict benchmark; AOS and GTS recover neither.
- Row 97 `neat spot`: dependency recovers the expected pair; GTS returns no relationship, and AOS produces `garden→redesign` instead.

### What we can conclude

On these **partially annotated real reviews**, dependency rules provide the broadest recovery of our selected candidate relations; AOS and GTS are relatively sparse. We **cannot pick the production ABSA extractor** based on this because no exhaustive, independently annotated test yet measures the relationship precision or true opinion/polarity correctness. GTS also may truncate long reviews at its fixed input limit; verify this before comparing full-review coverage.

The proper bounded next step is a **small but exhaustively annotated real-review relation test**, ideally with an independent human reviewer, and separately assess (i) correct target attachment, (ii) negation/polarity, (iii) implicit location-attributed observations. Do not tune models against these 29 hand-selected targets and then cite them as unbiased validation.

# Stage 1A — Research Sequence and First Hypothesis Robustness Experiment

**Current working plan, confirmed November 3, 2026.** No human-rated ground truth currently exists. Prior assistant-generated provisional labels are retained for historical diagnostics, **not** for choosing an experimental winner.

## Agreed research order

1. **Hypothesis formulation first:** Compare emotional hypotheses and paraphrases on the same reviews using one NLI model. Inspect all three NLI probabilities, predicted labels, wording sensitivity, apparent logical conflicts, and evidence coverage; do not call these accuracy.
2. **NLI model variations:** Compare BART-MNLI, DeBERTa-v3-large-zeroshot-v2.0, and ModernBERT-large-zeroshot-v2.0 on identical inputs. Note binary entailment/not-entailment models cannot be evaluated as three-way contradiction/neutral classifiers without a separate scheme.
3. **ABSA model variations:** Compare selected pretrained extractors (not only current end-to-end DeBERTa), prioritizing evidence-span coverage and context preservation; ABSA aspect polarity is not emotion truth.
4. **Integration:** Compare direct NLI, improved hypotheses, and ABSA-supported evidence (prefer additions/context rather than discarding unmatched sentences). Inspect when ABSA helps or hurts.

**Parallel exploratory probes allowed**, but change one variable at a time. Nothing is locked or claimed to generalize.

## First experiment: hypothesis wording without labels

**Script:** [stage1a_hypothesis_robustness.py](../scripts/stage1a_hypothesis_robustness.py)  
**Workflow:** [stage1a-hypothesis-robustness.yml](../.github/workflows/stage1a-hypothesis-robustness.yml)  
**Data:** all 214 currently available real reviews across 43 locations, pilot calm/inviting/safe. The original diagnostic 30-review subset remains separately summarized for comparison.  
**Model:** pretrained BART-large-MNLI, no training.  
**Hypothesis groups:** three paraphrases of each overall atmosphere; three different supporting facets per atmosphere; one opposing atmospheric claim. Entire review remains the premise.

**Outputs:** per review/hypothesis raw support/contradiction/neutral softmax probabilities, predictions, normalized predictive entropy, paraphrase support-probability range, counts of unanimous paraphrase classifications, descriptive facet distributions, and cases where both an overall atmosphere and an opposing claim receive entailment.

**Interpretation:**
- Paraphrase disagreement or large shifts in entailment scores = wording sensitivity and a reason to inspect.
- Probability entropy measures *model distribution uncertainty*, **not calibrated correctness**.
- Different supporting facets are not synonymous. Divergent predictions can be valid, not model failures.
- Opposing claims may not be logical negations; dual entailment is a **review flag**, not definitive inconsistency.
- Neutral means NLI finds insufficient support or contradiction for that hypothesis, not a negative sentiment score.
- No percent from this experiment should be marketed as predictive accuracy, because **independent human reference labels do not exist**. The script evaluates the full review corpus in batched CPU inference and checks sample coverage, while retaining the original 30-case subset. The corpus is still mostly Cambridge-area public places; 214 reviews are not 214 independent places.

## Next discussion after reviewing artifact

Inspect highest-sensitivity cases and concrete examples first. Decide which hypothesis forms deserve closer scrutiny, not which one is "most accurate". Keep theory-supported emotion definitions and user-specified nine-category framework separate from exploratory pilot prompts. Later introduce controlled logical examples and possible human annotation if the research calls for validation.

## Model comparison caveat

The planned DeBERTa and ModernBERT zero-shot checkpoints may output different label spaces (e.g. entailment vs non-entailment). Compare common quantities, and do not treat 'not entailed' as 'contradicted' or automatically as 'neutral'.

**Not a claim of finished experiment results.** Results belong to the GitHub Actions run artifact after actual execution.

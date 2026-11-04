# Stage 1A — ABSA → relevance → NLI evidence-ledger execution audit

**Execution:** [GitHub Actions run 41899410822](https://github.com/UsernameIsJoe/Atmosphere-grounding/actions/runs/41899410822), head `ce2a87fa59f4035d3d18d5687b442ff0c7328e7e`, completed **successfully**, including unit tests, frozen-artifact retrieval, source checks, output validation and artifact upload. Artifact: `13355604431` (`stage1a-evidence-ledger`) with `summary.json` and `evidence_ledger.jsonl`.

**Scope:** 20 real reviews, 58 original source sentences, 60 review–emotion records (calm, inviting, safe). **This run replays previously executed ABSA and BART NLI predictions**; it is an integration/accounting audit, **not newly trained/evaluated models or new inference calls**.

## Component coverage and overlap

| Emotion | All source passages | ABSA indexed | Relevance selected | Both | Relevance-selected, ABSA missed |
|---|---:|---:|---:|---:|---:|
| Calm | 58 | 47 | 6 | 6 | 0 |
| Inviting | 58 | 47 | 27 | 26 | 1 |
| Safe | 58 | 47 | 4 | 3 | 1 |

- **Calm:** Original sentence-level BART labels: 1 support, 8 contradiction, 49 neutral. The relevance-selected group contains only 1 support and 1 contradiction; **14/20 reviews have no relevance-selected calm sentence**.
- **Inviting:** Original: 7 support, 9 contradiction, 42 neutral; relevance-selected group: 5 support, 4 contradiction, 18 neutral. **3/20 reviews have no relevance-selected inviting sentence**.
- **Safe:** Original: 3 support, 8 contradiction, 47 neutral; relevance-selected group: 2 support, 2 contradiction. **16/20 reviews have no relevance-selected safety sentence**.

These figures are counts of **model-produced classifications and selection flags**, not accuracy, recall, calibrated confidence, prevalence, or correctness.

## Exact source-recovered observations

- **Safe, row 74:** “Ckean, well kept, and well patrolled by police.” was *relevance selected and NLI support*, yet had **no source-aligned ABSA aspect annotations**. A strict ABSA gate would discard the review's potentially relevant observation.
- **Inviting, row 33:** “There are lots of other more engaging park literally a few walks away.” was *relevance selected and NLI contradiction* with **no ABSA aspect annotation**.
- **Inviting, row 113:** “Inspiring place with great location.” had an AOS relation and NLI support but was *not relevance selected*. Similar for row 123, “Cute little park.” These show potential false-negative relevance gating.
- **Safe, row 123:** “Ada accessible.” had a source-aligned ABSA aspect and NLI support but was *not relevance selected*. Neither the entailment judgment nor the relevance rejection is independently adjudicated.
- Several negative BART judgments not relevance-selected were clearly ambiguous or not obviously atmospheric (e.g., row 26 “absurd for hsq” being scored as calm/safe contradiction). This also cautions against treating raw NLI contradictions as trustworthy evidence.

## Architectural decision

1. **ABSA:** locate and index source-verifiable aspects/relations, not determine emotions.
2. **Relevance:** emotion-specific priority evidence view; **never delete original sentences or suppress contradictory evidence silently**.
3. **NLI:** assess entailment/neutral/contradiction on the **original source passage**, and retain scores and offsets separately for audits.
4. **All raw source evidence is retained**, including zero-ABSA and low-relevance sentences. Conflicts remain visible.

## Research interpretation and next actual validation

- **Successful software integration and provenance accounting are established.**
- A scientific improvement in emotional interpretation **is not established**. No independent labeled evidence comparison was run, and this workflow computes selection summaries over *unchanged pre-existing predictions*.
- The most useful next verification is a **small blinded source-evidence review** on already-frozen real passages: mark (i) aspect/opinion attachment fidelity, (ii) emotion relevance, (iii) support/contradiction/insufficient direction. Compare direct sentence NLI, relevance-selected view and ABSA-indexed view **using the same passages**. This should settle whether the components add useful evidence rather than reopen model-search or prompt-optimization loops.
- No need to introduce another model, change architecture, or claim that narrow relevance selection implies lack of emotions.

**Conclusion:** The three responsibilities are separated and operational. **Trustworthiness of the evidence decisions remains the unresolved scientific milestone.**

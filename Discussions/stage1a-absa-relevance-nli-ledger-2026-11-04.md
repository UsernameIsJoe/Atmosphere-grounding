# Stage 1A — ABSA → relevance → NLI evidence ledger: execution and decision baseline

**Date:** 2026-11-04. **Status:** Implementation committed and **locally tested** on the exact successful real-review integrated artifact. GitHub Actions execution of the new workflow not yet independently confirmed.

## Concrete implementation

- [Script](../scripts/stage1a_evidence_pipeline.py), [tests](../tests/test_stage1a_evidence_pipeline.py), [GitHub Actions workflow](../.github/workflows/stage1a-evidence-ledger.yml).
- Reuses **frozen completed integrated run 41891532716**: 20 reviews, 58 distinct source sentences, 60 review–emotion records. Reuses existing DeBERTa + SetFitABSA aspects, source-grounded AOS relations, BART relevance and BART direct emotion NLI.
- **Important distinction:** the workflow performs a deterministic *integration replay*, **not new NLI or ABSA model inference**. This prevents confounding integration with changed checkpoints or prompts. Do not count it as another independent validation experiment.
- Three responsibilities:
  1. **ABSA:** Which original sentence/aspect/opinion relationship is supported by literal offsets? Three evidence tiers: source-verified relation, aspect-only, untagged.
  2. **Relevance:** Existing BART metarelevance output prioritizes the evidence for the individual emotion; threshold is the frozen exploratory .5, **not calibrated**. Low relevance NEVER causes deletion.
  3. **NLI:** Existing BART 3-way entailment, contradiction, neutral on the **original unchanged source sentence**. Keep direction and source text in the evidence ledger.
- ABSA-only, relevance-only, intersection, and relevant-but-unmatched **rescue** sets are all evaluated using the same frozen NLI outputs. The complete evidence set is also retained as a no-hard-filter baseline.
- Output is a sentence-level evidence ledger and explicit per-component counts, not a claimed final review/location emotion score.

## Local results on frozen artifact (before new Actions workflow)

| Emotion | Original sentences | ABSA-indexed | Relevance-selected | Intersection | Relevance-rescued without ABSA |
|---|---:|---:|---:|---:|---:|
| Calm | 58 | 47 | 6 | 6 | 0 |
| Inviting | 58 | 47 | 27 | 26 | 1 |
| Safe | 58 | 47 | 4 | 3 | 1 |

Observations:
- ABSA-only indexing covers **47/58** source passages. It is not a sufficient sole evidence gate: among BART-relevant evidence for `safe`, **1 of 4** would be omitted. Actual source example: **“Ckean, well kept, and well patrolled by police.”** (spelling retained verbatim from review). Review row 74.
- `inviting` has 1 relevant unmatched sentence (row 33, a comparison to “other more engaging park” locations), labeled contradiction by direct NLI.
- Relevance-only misses/does not prioritize many sentences: **14 of 20** reviews have no relevance-selected `calm` sentence; **16 of 20** have none for `safe`. This is an **essential warning against hard filtering**, not evidence that those locations lack those emotions.
- The fixed full original source remains in every case. ABSA does not overwrite the NLI premise with inferred `aspect:opinion` claims; candidate relations are metadata only. The intersection is a **priority view**, not the only evidence permitted for reasoning.
- We intentionally do not rank ABSA model precision, compare emotion accuracy or infer calibrated intensity from these counts. This replay makes the roles *operationally distinct*; it does not show causal predictive improvement.

## Engineering checks

- Local syntax compiled; **4 deterministic unit tests passed** on local implementation, including real-artifact integrity checks, source spans, non-destruction and preservation of positive/negative evidence.
- Local run produced `summary.json` and `evidence_ledger.jsonl` for 60 aligned cases.
- GitHub workflow runs syntax/unit tests, downloads the frozen original artifact, generates the ledger, validates all source offsets and the intersection/rescue accounting, and uploads results.
- CI outcome and artifact should be checked before labeling **GitHub-executed**.

## Core research decision

We have one coherent working software interface: ABSA = annotation/provenance, relevance = prioritization, NLI = directional emotional inference, conflict/unmatched observations = retained. This is a proper *separation of concerns*.

**Do not claim model validation yet.** The next meaningful verification is **evidence-level correctness against the actual reviews**, especially whether ABSA's aspect/opinion attribution improves the reviewed evidence list relative to relevance-only selection. No new model architecture or additional prompt optimization should be added merely to change counts.

The output is usable as a traceable evidence ledger, while the reliability of emotional inference remains an empirical question.

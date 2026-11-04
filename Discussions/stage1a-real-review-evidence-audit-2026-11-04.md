# Stage 1A — First real-review evidence correctness audit

**Date:** 2026-11-04. **Status:** Executed manual diagnostic audit of actual frozen ledger outputs; **not independent ground truth, not population accuracy**.

## Provenance

Input: completed [ABSA → relevance → NLI ledger run 41899410822](https://github.com/UsernameIsJoe/Atmosphere-grounding/actions/runs/41899410822), artifact `13355604431`, containing 20 reviews, 58 distinct source sentences, and three NLI emotion predictions per sentence. No new model inference or fine-tuning performed.

We selected **30 passage–emotion decisions (10 per calm/inviting/safe)** to include typical examples, positive/negative semantic cues, attribution errors, ABSA-tagged and ABSA-untagged cases. A researcher-style interpretive audit was authored by the assistant after seeing the examples; **the selection is purposive, not random, and the judgments are not blinded or independent**. Counts are **agreement with these provisional judgments**, not precision/recall/accuracy of the production task.

Audit category: emotion relevance (yes/no); if relevant, expected source-evidence direction (support / contradict). If non-relevant, expected neutral. This category scheme is deliberately conservative and may exclude weak indirect evidence. Human raters could disagree, especially for atmosphere terms such as `inviting`.

## Results against provisional source judgments

| Emotion | Relevance agreement | NLI class agreement | Relevant evidence recognized by NLI | Notes |
|---|---:|---:|---:|---|
| Calm | 9/10 | 7/10 | 2/4 | Misses meditative walking and escape from urban hustle |
| Inviting | 7/10 | 5/10 | 4/9 | Misses friendly staff, great place for kids, and positive activity |
| Safe | 10/10 | 8/10 | 3/3 | Mistakes ADA accessibility as evidence of safety; reacts to negative parking complaint |
| **All** | **26/30** | **20/30** | **9/16** | Directional diagnostic only; model predictions do not prove semantic correctness |

On this selected sample, **emotion NLI interpretation is a larger visible problem than the binary relevance gate**. Of 16 selected source observations judged to provide clear directional evidence, NLI produced the expected label for nine, returning neutral on seven. The irrelevance examples include some ambiguous candidates; the findings should be replicated with independent raters before reporting task accuracy.

**Important:** The combined ABSA+relevance ledger currently organizes and selects *pre-existing predictions*. It does not improve these NLI interpretations by itself. A claim that ABSA made emotion inference more accurate is **not supported**.

## Exact examples (source phrases retained)

| Source passage | Emotion | Audit interpretation | Model result and issue |
|---|---|---|---|
| `The staff were so friendly and helpful.` | inviting | Supporting; relevant | **relevance rejected, NLI neutral** |
| `My favorite spot for a meditative walk through a labyrinth` | calm | Supporting; relevant | Relevance selected, **NLI neutral** |
| `), but it is still a neat spot to visit to take a break from the urban hustle and bustle.` | calm | Supporting; relevant | Relevance selected, **NLI neutral**; upstream sentence segmentation includes orphan parenthesis |
| `This is a very nice park with a playground nearby.` | inviting | Supporting; relevant | Relevance selected, **NLI neutral** |
| `Great place to bring your little kid's` | inviting | Supporting; relevant | Relevance selected, **NLI neutral** |
| `Inspiring place with great location.` | inviting | Supporting; relevant | **Relevance rejected**, NLI entailment |
| `Cute little park.` | inviting | Supporting; relevant | **Relevance rejected**, NLI entailment |
| `The supposedly artistic fixtures are pointless and dangerous.` | safe | Contradicting; relevant | Relevance selected, NLI contradiction |
| `Ckean, well kept, and well patrolled by police.` | safe | Supporting; relevant | Relevance selected, NLI entailment; **ABSA missed aspect** |
| `Ada accessible.` | safe | Not sufficient evidence of physical safety | Relevance rejected, **NLI entailment** |
| `cool park, 0 adequate bike parking.` | calm | Not sufficient evidence of calm | **Relevance selected**; source also exposes polarity/scope hazard for AOS |

The first group of examples suggests the generic NLI checkpoint is often **overly literal** when interpreting indirect atmospheric implications. It may classify `helpful staff` as neutral for `inviting` even though a reader can reasonably connect them. Conversely, positive general sentiment is sometimes overinterpreted for `safe`. Hypothesis wording is a plausible factor, but **we have not proved its cause**.

## Direct source audit of all 11 uniquely grounded AOS triplets on these 20 reviews

Only 11 AOS pairs survived the previous exact-span checks, so we can inspect all, not just a subsample.

- **Clearly interpretable connections (4):** `park → nice` (row 2), `parks → best` (row 74), `park → Cute little` (row 123), `colage → gooooooooood` (row 139).
- **Partial, contextual, or negation-risk (2):** `walk → favorite` (row 45, opinion more naturally attaches to `spot`); `bike parking → adequate` (row 26, source states **0 adequate**, and the extracted representation loses the essential quantity despite negative polarity).
- **Questionable or misattached connections (5):** `drive → Save` (row 19), `river → Great` (row 21), `sprinklers → Love` (row 38), `garden → redesign` (row 97), `location → Inspiring` (row 113).

These are **manual semantic assessments**, not independent annotations. Source-exact offsets alone are clearly insufficient to establish a valid aspect–opinion relation. The 11 triplets also represent a selected subset with high coverage constraints, not the full AOS generation output. Our current evidence-first strategy correctly keeps these as candidate metadata, not asserted truths.

## Decision

**Engineering integration: working. Semantic trustworthiness: not established.**

Focused next actions on the *same* architecture:

1. Avoid interpreting the relevance gate as truth or silently deleting observations; the full ledger already preserves this.
2. Treat source-grounded AOS relations as **candidate evidence with contextual warnings**, especially quantity/negation and obviously incorrect target attachment. Source matching ≠ factual link.
3. Examine why BART fails on simple but indirect place → emotion implications, particularly `friendly staff → inviting` and `meditative walk → calm`. Compare against existing checkpoint screening and fuller vocabulary work **without beginning another unbounded model/prompt search**.
4. Before asserting improved real-world accuracy, have an **independent human** annotate a sufficiently defined held-out evidence set. These assistant-authored judgments must remain exploratory.
5. Preserve the Stage 1A source-evidence ledger as the working interface. No architecture restart is warranted from this audit.

The central bottleneck in this selected audit is **evidence-to-emotion inference**; the separate aspect/opinion relationship quality is also notably weak. The relevance stage's preliminary performance looks more serviceable than directional NLI but needs independent validation.

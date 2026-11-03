# Stage 1A — Executed Experiment Results and Evaluation Audit

**Status:** Completed real pretrained-model pilot, November 3, 2026. **Not an independently validated accuracy benchmark.**

## Run provenance

| Experiment | Run | Artifact | Commit | Status |
|---|---|---|---|---|
| Earlier NLI + embeddings pilot | [41652001938](https://github.com/UsernameIsJoe/Atmosphere-grounding/actions/runs/41652001938) | [13237802057](https://github.com/UsernameIsJoe/Atmosphere-grounding/actions/runs/41652001938/artifacts/13237802057) | `66730d9` | Success |
| A/B/C comparison, first successful execution | [41663682994](https://github.com/UsernameIsJoe/Atmosphere-grounding/actions/runs/41663682994) | [13246910206](https://github.com/UsernameIsJoe/Atmosphere-grounding/actions/runs/41663682994/artifacts/13246910206) | `3212310` | Success |
| A/B/C comparison, regression-tested execution | [41663748624](https://github.com/UsernameIsJoe/Atmosphere-grounding/actions/runs/41663748624) | [13246355588](https://github.com/UsernameIsJoe/Atmosphere-grounding/actions/runs/41663748624/artifacts/13246355588) | `f689f11` | Success |

Both successful A/B/C artifacts contain `review_cases.jsonl` and `summary.json`. The two A/B/C **summary.json files are byte-for-byte identical (SHA-256 `9e6adf2bb931a59c818c1c7f969bf9d9c9eed964d5ed1d3f4180f03a5bceaafb`)**, although the case-file bytes differ slightly. These are **two runs of the same experiment, not two independent tests**. Full per-review model probability vectors, ABSA spans/polarities, and labels remain in the downloadable run artifacts.

## Data, labels, and evaluation construction

- **Data:** 30 selectively chosen real review rows from 7 places, drawn from `data/processed/reviews.jsonl` (original rows 0–34, skipping certain rows). These were *diagnostic examples*, not a random or representative sample.
- **Reference labels:** Provisional manual judgments **written by ChatGPT/the assistant**, embedded as the `GOLD` dictionary in `scripts/stage1a_text_pilot.py`. **Not** crowdsourced, independently annotated, or adjudicated by multiple humans.
- **Three pilot emotions:** `calm`, `inviting`, `safe`. The final nine-emotion taxonomy was not established in these tests.
- **Each review × emotion reference:** `S` = supportive evidence, `C` = contradictory evidence, `U` = insufficient evidence, `X` = off-topic. One selected review is X for all three emotions.
- **Actual 3-way metric sample size:** 29 non-X review–emotion judgments **per emotion**. Emotions are evaluated separately. Total counted judgments = 87. No independent test set, no human inter-annotator agreement.
- **Accuracy:** (number of exact matches for S/C/U) / 29. Thus 0.690 means 20/29, **not** that 69% of all 214 reviews are correctly scored.
- **Precision/recall/F1:** computed separately for S/C/U with each class treated as positive; macro-F1 = mean of the three class F1 values for an emotion. If there are no predicted positives for a class, the script defines its precision/F1 as 0. The average of macro-F1 across three emotions is an additional descriptive average, not statistical generalization.
- **No emotional intensity / 0–100 scales were validated.** The model outputs probabilities over entailment/contradiction/neutral, which are not calibrated emotional strength or truth.

### Provisional reference-label distribution (all 30)

| Emotion | S | C | U | X |
|---|---:|---:|---:|---:|
| Calm | 7 | 4 | 18 | 1 |
| Inviting | 9 | 8 | 12 | 1 |
| Safe | 3 | 3 | 23 | 1 |

The safe reference labels are especially sparse; **82.8% three-way accuracy** can hide poor positive-class recognition or a trivial tendency to choose U. More evaluation is needed.

## Executed methods

- **A — direct NLI:** Whole review and one broad emotion hypothesis; `facebook/bart-large-mnli`.
- **B — multi-hypothesis NLI:** Whole review and three narrower hypotheses per emotion, same NLI model. Equal-mean NLI class probabilities before selecting S/C/U.
- **C — pretrained ABSA then NLI:** `yangheng/deberta-v3-base-end2end-absa` extracts aspects/polarity; collect original sentences containing identified aspects, deduplicate, feed those sentences to the same single NLI hypothesis as A. Equal-mean class probabilities across selected sentences; no extracted aspect => predict U. **ABSA polarity was recorded, not mapped directly to emotion labels.**
- **Initial baseline:** Legacy `data/processed/mentions.jsonl` positive mentions, and the earlier direct NLI plus `sentence-transformers/all-MiniLM-L6-v2` cosine similarities, from the initial run. The lexicon/aspect regex proxy from that run was **not** a pretrained ABSA model.

## Results: three-class accuracy, including U

| Emotion | A direct NLI | B multi-hypothesis | C ABSA → NLI |
|---|---:|---:|---:|
| Calm | 20/29 = 69.0% | 22/29 = 75.9% | 19/29 = 65.5% |
| Inviting | 17/29 = 58.6% | 15/29 = 51.7% | 15/29 = 51.7% |
| Safe | 24/29 = 82.8% | 22/29 = 75.9% | 24/29 = 82.8% |

## Results: macro-F1 by emotion

| Emotion | A direct NLI | B multi-hypothesis | C ABSA → NLI |
|---|---:|---:|---:|
| Calm | 0.704 | 0.726 | 0.607 |
| Inviting | 0.500 | 0.446 | 0.409 |
| Safe | 0.761 | 0.481 | 0.655 |
| **Mean across pilot emotions** | **0.655** | **0.551** | **0.557** |

### Support (S) recognition

| Emotion | A recall | B recall | C recall |
|---|---:|---:|---:|
| Calm | 6/7 = 85.7% | 5/7 = 71.4% | 3/7 = 42.9% |
| Inviting | 0/9 = 0% | 1/9 = 11.1% | 0/9 = 0% |
| Safe | 2/3 = 66.7% | 0/3 = 0% | 1/3 = 33.3% |

**Do not confuse the high safe overall accuracy with good safety-evidence recall.** B detected 0/3 supportive safety cases, yet achieved 75.9% overall because most reviews were U.

## Detailed confusion counts (gold → predicted)

All counts sum to 29 per emotion and approach.

- **A / Calm:** C→C 4; S→S 6; S→U 1; U→C 8; U→U 10.
- **A / Inviting:** C→C 7; C→U 1; S→U 9; U→C 1; U→S 1; U→U 10.
- **A / Safe:** C→C 3; S→S 2; S→U 1; U→C 4; U→U 19.
- **B / Calm:** C→C 3; C→U 1; S→S 5; S→U 2; U→C 4; U→U 14.
- **B / Inviting:** C→C 3; C→U 5; S→S 1; S→U 8; U→S 1; U→U 11.
- **B / Safe:** C→C 3; S→U 3; U→C 4; U→U 19.
- **C / Calm:** C→C 3; C→U 1; S→S 3; S→U 4; U→C 5; U→U 13.
- **C / Inviting:** C→C 4; C→U 4; S→U 9; U→C 1; U→U 11.
- **C / Safe:** C→C 2; C→U 1; S→S 1; S→U 2; U→C 2; U→U 21.

## ABSA evidence-extraction diagnostics

- **1.8 aspects/review on average**; **2 reviews with no aspects extracted**.
- In a review describing an ambulance station and loud sirens, ABSA selected the first sentence about a nice walking spot and benches, dropping the sirens sentence. A correctly identified *calm contradiction* became U in C.
- A short review explicitly describing lights as “beautiful and calming” was labeled calm=U even in direct NLI; this is a **hypothesis/model failure**, not a reason to trust ABSA filtering.
- ABSA often extracts generic targets (e.g. “park”, “spot”, “courts”) rather than all atmosphere-relevant observations.
- Because C chooses **only sentences with an extracted aspect**, valuable claims may disappear. Its poor outcome does **not** prove every ABSA-based strategy or every pretrained ABSA checkpoint is unsuitable.

## Earlier single-hypothesis NLI + embeddings experiment (run 41652001938)

The earlier run confirmed pretrained BART-MNLI and MiniLM successfully executed on the same 30 reviews. Its **S/C-only** accuracy calculation excluded U and X: calm old extraction 54.5% vs NLI 90.9%; inviting 17.6% vs 41.2%; safe 33.3% vs 83.3%. **This is not a full/fair comparison** because the old extraction had no contradiction class and most insufficient-evidence cases were excluded.

Embedding cosine similarities were computed in the earlier run but were not evaluated as calibrated evidence classifiers. They must not be interpreted as validated atmosphere-strength scores. Refer to that run's artifact for complete per-review similarities.

## Interpretation and required next safeguards

1. **No A/B/C superiority is established beyond this diagnostic sample.** A is the most promising of the three current variants by mean macro-F1, but the sample is small and manually labeled by the assistant.
2. **Human benchmark first:** Have independent annotators rate a diverse held-out set with a clear rubric for location-attributed atmosphere, evidence spans, and S/C/U/X. Check agreement and adjudicate ambiguity.
3. **Review ABSA candidates strategically:** Test an alternate aspect extractor, ideally one tuned to location/spatial or general-domain statements, and evaluate **aspect/evidence recall on human-labeled spans** before inserting its output into NLI. Do not exhaustively try many checkpoints against the same 30 assistant-generated labels.
4. **Avoid conflating aspect sentiment and emotion entailment.** ABSA polarity does not determine whether a place is calm, inviting or safe.
5. **Test context-preserving variants**: direct NLI baseline; different theory-derived hypotheses; aspect annotations as *additional* evidence rather than exclusive filtering. Use held-out, human-rated labels to decide changes.
6. **Data restrictions:** Verify rights to train or retain Google-derived reviews/photos; these pretrained inference tests are not evidence of permission to use data for later model training.

**No final architecture, hypothesis set, or nine-emotion taxonomy is locked by these runs.**

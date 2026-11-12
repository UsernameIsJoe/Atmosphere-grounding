# Adjective vs NLI routing — independent source audit

**Experiment:** 30 real Google review texts, 30 places, 123 original source segments. Uploaded local results reviewed 2026-11-12. The central question is whether a cheap routing signal selects *reliably easy* text for one-LLM classification of calm / inviting / safe. No E/T channel distinction is assumed.

## 1. Integrity and inference coverage

| Component | Finished source segments |
|---|---:|
| spaCy adjective POS | 123/123 |
| BART, DeBERTa, ModernBERT | 123/123 each, with 3 hypotheses each |
| Qwen3 8B, V2 prompt | 120/123 |
| Gemma3 4B, V2 prompt | 80/123 |
| Gemma3 4B, **segment-only recovery** | 43/43 previously missing |
| Qwen and Gemma both V2, truly same-prompt overlap | **79** |

The combined 123/123 Gemma coverage is **not** 123 comparable V2 results. The segment-only recovery omits full-review context and asks no model-generated supporting quotation. Its zero failures demonstrate schema acceptance under a different task, **not** a gain in semantic accuracy. The 3 missing Qwen V2 segments are missing data, not negatives.

Across the 79 same-prompt segments, Qwen and Gemma disagreed on at least one emotion in **51/79 (64.6%)**. Disagreement by category: calm **41/79**, inviting **26/79**, safe **8/79**. These are agreement statistics, not accuracy estimates.

## 2. Routing predictions and computational savings

Here “simple” means a segment would get one LLM call under the proposed routing rule; all remaining segments would get two. The hypothetical baseline is **246 LLM calls** (123 × 2), excluding adjudication retries and the NLI cost. The final column examines only the same-protocol V2 overlap.

| Candidate shortcut | Sent to one LLM | Hypothetical saved LLM calls | Call reduction | Qwen/Gemma disagreement among comparable selected segments |
|---|---:|---:|---:|---:|
| Any adjective | 91/123 | 91 | **37.0%** | 38/61 = **62.3%** |
| 3-model median NLI ≥ 0.4 | 59/123 | 59 | **24.0%** | 25/40 = **62.5%** |
| 3-model median NLI ≥ 0.6 | 31/123 | 31 | **12.6%** | 12/22 = **54.5%** |
| 3-model median NLI ≥ 0.8 | 6/123 | 6 | **2.4%** | 5/6 = **83.3%** |
| Adjective OR NLI ≥ 0.6 | 95/123 | 95 | **38.6%** | 38/62 = **61.3%** |
| Adjective AND NLI ≥ 0.6 | 27/123 | 27 | **11.0%** | 12/21 = **57.1%** |

**Inference:** No tested gate established a low-error shortcut. Even a high NLI score did not guarantee model agreement, and the highest-threshold sample is tiny. Model agreement itself is *not* an adequate validity label, so even the disagreement rates above are only a diagnostic proxy.

## 3. Source-audited screening, not a new emotion ontology

I read all 123 segments and their full originating reviews. For this *temporary routing audit only*, I marked:

- **D / direct:** text explicitly expresses an atmosphere, place experience, visitor comfort, stated suitability, or direct perceived character (33 segments);
- **I / indirect:** physical, social, sensory or activity conditions that could inform experience but require interpretation (48);
- **G / generic:** praise, endorsement, event preference or vague impression that doesn't establish a specific atmospheric dimension (19);
- **X / unrelated:** background, services, pricing, broken fragments, unrelated people or objects without meaningful experiential claim (23).

These are operational bins used to test screening. They are **not E/T**, are **not final ground truth**, and are sensitive to the user's eventual definition of an admissible experience. The detailed decisions and all original review contexts are in the accompanying 123-row audit CSV.

| Gate predicting *direct* reports (D only) | D captured | Precision among selected | Recall of 33 D segments |
|---|---:|---:|---:|
| Adjective present | **30/33** | 30/91 = **33.0%** | **90.9%** |
| Median NLI ≥ 0.4 | 28/33 | 28/59 = 47.5% | 84.8% |
| Median NLI ≥ 0.6 | 19/33 | 19/31 = 61.3% | 57.6% |
| Median NLI ≥ 0.8 | 6/33 | 6/6 = 100%* | 18.2% |

\*6 high-scoring segments only; no independently validated performance. Scores are from this exact manually inspected dataset (in-sample). **This measures source-screening relevance, not which segments are easiest for an LLM to classify.** One direct statement can still trigger erroneous classification into other emotions.

Examples missed by adjective POS despite experiential meaning: “Just relax and enjoy sunset in spring, summer and fall season!”; “It gives some character to the area”; “I wouldn't go here if your looking for walk.” The final two are category-ambiguous even though they express visitor preference/character.

## 4. NLI hypothesis wording and score comparability

Each of the 3 NLI checkpoints evaluated **all 3 hypotheses**. The average entailment scores differ drastically depending on wording, despite the intention to triangulate one generic target:

| NLI checkpoint | Hypothesis 1 | Hypothesis 2 | Hypothesis 3 | Segments with within-checkpoint range >0.5 |
|---|---:|---:|---:|---:|
| BART-large-MNLI | 0.330 | **0.870** | 0.605 | **84/123** |
| DeBERTa v3 zero-shot | 0.153 | 0.412 | 0.615 | **66/123** |
| ModernBERT zero-shot | 0.091 | 0.253 | 0.485 | **56/123** |

The actual hypotheses were:

1. “This passage describes how the atmosphere of a place is experienced.”
2. “The writer conveys a feeling or perception about spending time in this location.”
3. “The text directly expresses an experiential quality or perceived character of the place.”

BART gives H2 >0.5 on **119/123** texts, including mundane statements; as an absolute gate it hardly filters anything. **The three wordings are not interchangeable as NLI inputs.** Also, BART uses 3-way entailment/neutral/contradiction while the two other checkpoints use 2-way entailment/not-entailment. Their raw softmax values have different scales and are **not calibrated probabilities of human atmospheric relevance**. A simple median of their mean entailment probabilities is exploratory, not statistically validated.

For the first-pass D vs non-D separation, the *in-sample* AUC of the pooled median was **0.835** (BART mean 0.768; DeBERTa mean 0.829; ModernBERT mean 0.792). One isolated ModernBERT H2 score had exploratory AUC **0.856**, but **selecting a winner using the same audit set would overfit**; it would need a fresh held-out sample. These scores measure ranking of my D-bin judgments, not model verdict accuracy or routing easiness.

## 5. Cost comparison: NLI is not free

Measured per-segment forward inference time accumulated from the run outputs (excludes model downloads and initialization):

- BART: **37.9 seconds** over 123 segments;
- DeBERTa: **59.7 seconds**;
- ModernBERT: **44.1 seconds**;
- **all three combined ~141.8 seconds**, or **1.15 sec/segment**, excluding model loading.

The original Gemma V2 raw attempts averaged **~3.58 sec per attempt** in this machine's saved run. If a routing shortcut saves one Gemma call per simple segment, median NLI ≥0.6 saves an estimated 31 × 3.58 ≈ **111 seconds of Gemma inference** at a preloading cost of ~142 seconds of NLI — **net slower**, even before checkpoint loading. NLI ≥0.4 would nominally skip ~211 seconds of Gemma calls for ~142 seconds of NLI work, but its reliability advantage was not established. These are rough, hardware-specific counterfactuals; the real run also involved multiple retries and differences in model response length. A future **single-checkpoint NLI** design may be cheaper than this 3-checkpoint pilot; that has not been validated.

## 6. Source-level error audit

The V2 quotation validator verifies *literal traceability*, not category correctness. The following real mistakes or concerns were found by comparing the quoted target to its full originating review:

| Segment from real reviews | Observed error / ambiguity |
|---|---|
| “Park is good.” | Qwen marks **calm, inviting, and safe all `opposes`**, rationalizing from problems in other sentences. The quote is exact but the verdict is polarity- and target-inconsistent. **Semantic context leakage survived strict quote validation.** |
| “Everyone was so nice and friendly.” | Gemma marks **calm `opposes`**, arguing friendliness is the opposite of calm. This is a category-level error, not a quotation issue. |
| “I wouldn't go here if your looking for walk.” | **Both models mark calm `supports`** despite the negative walking suitability; neither interpretation is supported by calm language in the target. |
| “It was completely covered in graffiti.” | Both models mark **all three categories `opposes`**. Unwelcoming condition is plausible; a specific lack of calm or safety is **not directly established** merely from graffiti. |
| “It was completely unclean, with tissues all over the place.” | Both models again mark **all three `opposes`**; this may support an uninviting place and hygiene concerns but does not automatically establish all emotional directions. |
| “Its calm environment makes you feel comfortable and welcome.” | Qwen marks calm and inviting `supports`; Gemma only calm `supports`, **missing explicit welcoming evidence**. NLI median here was high (~0.98). |
| “We were able to take photos throughout the space and no one gave us a hard time.” | Qwen calm `supports`; Gemma calm `opposes`, even though Gemma's rationale says there was a lack of disturbance. A plain semantic/polarity error. |
| “Also he has a security camera pointing at the park.” | Both accept safe `supports`; Gemma additionally says calm `opposes`. Whether surveillance itself is safety support is a user-defined boundary; the added negative calm judgment is weak. |
| “My favorite spot for a meditative walk through a labyrinth” | Both accept calm `supports`, but prior human adjudication considered this **indirect evidence** rather than explicit reported calm. Keep as a boundary case. |
| “The AC made it better on a hot day where you can sit and admire the paintings too.” | Comfort is conveyed, but the extrapolation to **calm** is not necessarily warranted. |

More broadly, all three emotion directions were marked `opposes` by Qwen for **“Park is good,” “The chickens will chase you,” “graffiti,” “unclean,” “dark,” and a vague “maintenance issue.”** There is a repeatable negative-generalization error, separate from quotation fidelity.

## 7. Provisional judgment accuracy — interpret carefully

Separately from the four source-screen bins, I manually marked each of the 123 segments with tentative calm / inviting / safe judgments. Labels are `S` (supports), `O` (opposes), `N` (insufficient category evidence), or `U` (meaningfully uncertain). **87 of 369 category cells were marked `U`, across 74 segments**, because the task definition remains unsettled. This audit is **single-reviewer and not blind to model outputs** and must not be presented as a validated benchmark or population-level accuracy.

On the **79 same-prompt V2 overlap**, among **181 non-`U`** category cells:

- Qwen V2's positively/negatively asserted claims aligned with provisional judgments in **36/46** cases.
- Gemma V2's asserted claims aligned in **32/72** cases.

Gemma made **more category claims** and overgeneralized broad negative conditions to calm in particular. This is a more important observation than full-category accuracy dominated by `none` decisions. Results are conditional on Gemma's 80 successful V2 outputs (selection bias) and are not a fair overall comparison between model families. The fallback's different context means it should be audited separately.

## 8. Remaining human decisions

Before assigning an operational gate threshold, the following boundary cases materially affect what “related to emotion/experience” means:

1. **Generic praise:** Does “Really beautiful park” count as an inviting atmospheric experience, or only a generic aesthetic judgment?
2. **Physical indicators:** Is “Has green areas, benches, gardens, and trash cans” enough to route directly to one model, or should it trigger additional contextual interpretation?
3. **Human interaction:** “I'm so thankful for her empathy, consideration and warmth.” Does this count as place experience (inviting) despite referring to one staff member?
4. **Safety proxy:** Does “A security camera pointing at the park” directly support safety, or represent a contextual clue requiring interpretation?
5. **Experiential activity:** Is “My favorite spot for a meditative walk” directly about calm or an indirect activity description?
6. **Negative physical condition:** Does “It was completely unclean, with tissues all over the place” oppose *inviting* only, or also *safe* and *calm*?
7. **Feeling without adjectives:** “Just relax and enjoy sunset...” conveys experience despite the adjective gate returning false.
8. **Full-review scope:** Should “Park is good” be interpreted solely as a positive generic target statement even when the full review describes negative experiences? The current task prompt explicitly says yes for *target evidence*, although full-review context could legitimately disambiguate references.

These are not requests to reopen E/T design. They matter specifically because **a gate that filters for easy cases must be based on actual downstream reliability, not mere lexical or semantic relatedness**.

## 9. Conclusion and next experimental choice

**The adjective rule is cheap and high-recall for direct expressions (30/33), but too broad to certify easy examples.** The 3-checkpoint × 3-hypothesis NLI has better selectivity for direct-experience text at high thresholds but significant wording instability, uncalibrated cross-model score pooling and nontrivial runtime. Neither established a trustworthy one-LLM fast path on this 30-review sample. On directly experiential texts both LLMs can still mislabel other categories, so “emotionally related” and “simple for one LLM” are distinct screening targets.

The next question is therefore **not yet which NLI cutoff to deploy**, but whether we can *predict model reliability* from cheap signals, and whether full-review context improves semantic accuracy enough to outweigh observed leakage. Keep source segmentation defects (e.g. “The Richard A.” / “and Susan F.”; standalone “Sunny” / “but fresh...”; “Last” / “but not least...”) separate from the capability question. These incomplete fragments can induce avoidable errors before any gate or model is evaluated.

**Audit status:** 123 original segments inspected; screening bin and 3-category provisional labels logged; 79 same-protocol comparisons isolated; unresolved scope/ontology questions explicitly flagged; no new model calls or repository changes.

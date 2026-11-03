# Stage 1A — ABSA Extraction Screening Results and Handoff

**Date:** November 3, 2026  
**Status:** Three methods executed successfully; extraction-only comparison complete. **No ABSA+NLI integration has run in this experiment.**

## Execution and data

[GitHub Actions run 41728835398](https://github.com/UsernameIsJoe/Atmosphere-grounding/actions/runs/41728835398) — all three independent jobs passed syntax/unit tests, 50-review source-span validation and artifact upload.

| Method | Job ID | Artifact ID |
|---|---|---|
| spaCy noun chunks | `126240556556` | `13276086498` |
| DeBERTa joint ABSA | `126240557076` | `13275773327` |
| SetFitABSA restaurant-domain pretrained | `126240556892` | `13275663857` |

Same fixed 50 reviews / 43 distinct locations used by earlier NLI-model screening. Methods differ in task: spaCy returns noun phrases without sentiment, whereas both other systems produce aspect/polarity predictions. Exact per-review source text, aspect spans, sentence context, unselected sentences and seven synthetic controls are saved in artifacts (`review_cases.jsonl`, `controlled_cases.json`, `summary.json`, `sample_manifest.json`).

## Quantitative extraction observations

| Measure | DeBERTa ABSA | SetFitABSA | spaCy noun chunks |
|---|---:|---:|---:|
| Extracted spans across 50 reviews | 98 | 372 | 721 |
| Mean spans/review | 1.96 | 7.44 | 14.42 |
| Reviews with no extracted spans | 2 | 1 | 0 |
| Total segmented sentences (per method) | 195 | 194 | 194 |
| Sentences containing ≥1 extracted span | 72 | 143 | 190 |
| Fraction of sentences retained by **hypothetical hard aspect filter** | **36.92%** | **73.71%** | **97.94%** |
| Unaligned spans reported | 0 | 0 | 0 |
| Recorded inference/extraction time | 20.53 s | 83.28 s | 3.32 s |

**Important:** The fraction measures sentence retention if a method's output were used as an aspect-only sentence filter. It is **NOT** semantic evidence recall, precision, accuracy, or the portion of atmosphere information preserved. spaCy's high coverage is expected for inclusive noun chunks, including pronouns and irrelevant candidates. Different sentence parsing can produce slightly different denominators. Measured timing excludes some setup and download costs.

## Predefined controlled examples

| Synthetic input probe (diagnostic target) | DeBERTa | SetFitABSA | spaCy |
|---|---|---|---|
| “The park is not quiet; sirens make it stressful.” (sirens) | not extracted | not extracted | extracted |
| “It feels peaceful and calming here.” (peaceful) | not extracted | not extracted | not extracted |
| “The gardens are beautiful, but the traffic is deafening.” (traffic) | extracted | not extracted | extracted |
| “I was happy because I found my lost phone.” (phone) | extracted | extracted | extracted |
| “The friendly entrance welcomes every visitor.” (entrance) | extracted | extracted | extracted |
| “Broken glass covers the sidewalk and makes it dangerous.” (glass) | extracted | extracted | extracted |
| “Relaxing, quiet, and serene.” (serene) | not extracted | not extracted | not extracted |

These target matches are **diagnostics only**. Failing to extract an adjective is not necessarily a fault for a nominal aspect extractor; extracting `phone` in a personal-event review is not proof of atmosphere evidence.

## Actual review examples (full source retained in artifact)

- **Review row 74:** “Cambridge has some of the best little parks nestled away. Ckean, well kept, and well patrolled by police. This one even has a little toddler bed section across the street with a water fountain”. DeBERTa extracted only “parks” and thus would drop the police-patrol and amenity sentences. SetFit selected “water fountain” and would drop the entire patrol sentence. spaCy recovered noun phrase “police” and other candidates. The patrol sentence could matter for a *perceived safety* investigation, but whether it warrants a safety score is unresolved.
- **Review row 123:** “Cute little park. Ada accessible.” DeBERTa selected “park” and would omit the accessibility sentence. SetFit and spaCy find the “Ada” noun candidate, but extraction alone does not understand that accessibility and perceived physical safety are different.
- **Review row 97:** DeBERTa selected “spot” from a complex review about garden redesign, urban bustle, return plans and public accessibility; multiple other potentially relevant sentences were unselected. SetFit retained more named aspects but still omitted public access.
- **Review row 187:** “Not much to see here inside the building, the reception is kindly and informative. You can get a map to see 50+ sculpture scans in the campus free”. DeBERTa extracted “reception” but would discard the map sentence. SetFit extracted “map”/“sculpture scans” but discarded the reception sentence. These methods sometimes recover *different* facets, rather than one universally subsuming another.
- **Review row 55:** All three retained all sentences for the park/gateway/trees review. DeBERTa extracted site objects, while SetFit and spaCy extracted a wider range of nouns. This supports checking specific evidence, not assuming coverage is always insufficient.
- **Review row 139:** “This colage is very gooooooooood” yields a nominal target under all three approaches. That is an important counterexample to interpreting an extracted aspect as evidence of a specific emotional atmosphere.

## Scientific interpretation

1. The initial failed ABSA→NLI variant depended on **hard filtering of sentences by nominal aspect extraction**. Measured retention of 36.9% for DeBERTa and the controlled examples give concrete reason to reject that filter as a default for future integration.
2. SetFit returns more aspect candidates and higher potential sentence retention, but may be broad/noisy, and its restaurant-trained domain is not validated for urban spaces. **Do not declare SetFit more accurate or more useful based on span quantity.**
3. spaCy is a useful permissive candidate detector, **not sentiment ABSA**. Its near-complete retention may come with substantial irrelevant noun phrases.
4. Atmosphere is often expressed via adjectives, relational clauses, subjective perception and events that do not correspond neatly to a noun aspect. Extraction must preserve or retrieve these passages by other means if it is to benefit our emotional-evidence task.
5. This experiment does **not** identify an emotion-specific “best ABSA model,” calculate precision/recall against independent reference spans, or establish improvement over NLI.
6. All original reviews and unmatched sentences were saved. **Polarity remains independent metadata** rather than an emotion classification.

## Next experiment recommendation / tomorrow's handoff

**Main next step is a context-preserving integration design and small controlled comparison**, rather than immediately running a bigger ABSA extraction sweep.

Compare on the same preselected 50 reviews and frozen NLI hypotheses/checkpoint:
- **A.** Full-review NLI, existing reference.
- **B.** Aspect-sentence-only NLI, *failure diagnostic* (reproduces information loss; never a recommended production default).
- **C.** Full-review NLI + aspect metadata / aspect-indexed supporting passages, while keeping unmatched sentences accessible.
- **D.** More general *location-attributed observation* extraction that includes adjectival and sensory claims, with traceable spans; assess separately before integration if new model/prompt is introduced.

Identify which test can genuinely add signal rather than simply repeat the unchanged full review. Hold NLI model/vocabulary fixed within this experiment. Use controlled negation, conflicting evidence and reviewer-only experience probes; no subjective accuracy claims without independent labels.

**Other project scope retained:** The full nine-category taxonomy, Stage 1B visual-quality feature library, Stage 2 location-level association and Stage 3 visual prediction remain open. Do not treat NLI or ABSA findings as final cross-modal evidence.

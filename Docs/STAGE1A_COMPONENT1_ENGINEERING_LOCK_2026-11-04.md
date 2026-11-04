# Stage 1A / Component 1 — EXTRACTOR ENGINEERING LOCK (2026-11-04)

**Decision status:** Operational implementation selected and executed on frozen real data. **NOT** a scientific conclusion that the model has best independently measured precision, recall, or F1. This document supersedes any informal recommendation to use GLiNER + NuExtract as the first-component default.

## Actual research architecture (not negotiable)
1. **ABSA / structured extraction:** Discover what is said about the place; collect aspect, description, opinion, experience and *candidate* relationship evidence. Ground all extractable spans in the original review. NO emotion categorization in this stage.
2. **Relevance:** Independently decide which observations matter to each of the nine atmosphere/emotions. Do not equate positive sentiment or an explicit human feeling with relevance, and do not silently delete negative, untagged, or off-topic evidence until independently evaluated.
3. **NLI:** Independently evaluate the relevant source passages against the theory-defined emotion hypotheses as entailment/support, contradiction, neutral/insufficient. Preserve opposing evidence and reviewer attribution. Do not collapse probabilities into intensity.

**Component 1 must NEVER emit authoritative nine-emotion labels or make relevance/NLI judgments.**

## Evidence and matched assessment
- Frozen original text: **20 actual reviews, 56 identical source sentence spans**, reconciled by review row, sentence index, full sentence text and original offset.
- Comparison completed: https://github.com/UsernameIsJoe/Atmosphere-grounding/actions/runs/41920533478
- Operational contract and ablation: https://github.com/UsernameIsJoe/Atmosphere-grounding/actions/runs/41921120203

| Candidate | Sentence with any annotations | Relationship candidates | Mechanically source-exact links | Known major limitation |
|---|---:|---:|---:|---|
| GTS-BERT | 22/56 | 27 | 27 | Sparse coverage, no way to capture all implicit experiences |
| AOS-T5 (historical frozen artifact) | 36/56 | 36 | 31 | Some invented/incorrect links and parsing sensitivity |
| PyABSA | 41/56 | 84 | 82 | Severe over-linking, 2 internal failures; exactness is not correctness |
| GLiNER2.5 | 46/56 | 34 | 34 | Wrong relation types and incomplete environmental-experience links |
| NuExtract 2.0 | 5/8 | Not the same output type | N/A | Small pilot; 3 empty results; does not consistently map aspect/opinion spans |

Counts describe model output and literal provenance, **not semantic accuracy**. No model has an independently adjudicated complete real-review gold score. The 29-pair partial reference list is incomplete and assistant-authored; its recovery counts do not establish a winner.

**Abnormal substantive cases:**
- GLiNER: `park → charming and cozy` reasonable; `park → Cambridge` under `has_feature` wrong.
- GLiNER: captures `trees`, `paths`, `protected`, `comforted`, but misses the induced-experience relation in the same sentence.
- PyABSA: 12 cross-combined links across `park`, `trees`, `circulous paths` and `enveloped`, `feel`, `protected`, `comforted`; many are implausible.
- GTS: `park → cozy` correct-looking on one original review, but misses the longer park/trees/protected passage.
- NuExtract: extracted `protected and comforted` in one sentence but returned no observations for `A charming and cozy park...` and `Inspiring place with great location.`.
- A relevant passage `Ckean, well kept, and well patrolled by police.` remains unlinked / poorly covered by these methods. Do not filter it out.

## Selected operational implementation
**A. GLiNER2.5 (`fastino/gliner2.5-base-v1`) — primary span candidate provider.** Retain identifiable source-referenced physical features, experiential expressions and descriptive phrases. Its generated relation labels are *candidates, not asserted claims.*

**B. GTS-BERT (`gauneg/bert-gts-absa-triple`) — supplementary aspect→opinion relationship candidate provider.** Preserve directed aspect/opinion/polarity candidates with original-text alignment. Do not treat the polarity as an emotion signal. GTS adds source evidence in 2 more sentences not annotated by GLiNER, and supplies relationships in 11 sentences lacking GLiNER relationship candidates. Candidate relations still require future semantic verification.

**C. Original source text — mandatory authority and fallback.** Preserve complete review and verbatim source sentence independently of any extractor result, including source offsets, untagged sentences, negation, sentence errors, ambiguity and all negative evidence. No sentence is dropped. Keep confidence scores separate from evidence strength.

**Not selected for production Component 1:** NuExtract (not sufficiently reliable/complete on this pilot), PyABSA (overlinks; internal errors), AOS (parsing/false linkage and no demonstrated advantage over selected components). These remain research comparators; we do not claim they are universally inferior.

This **engineering lock** is the specific model-role choice for subsequent Stage 1A development, rather than open-ended model discovery. Changing it requires evaluation evidence, not a new model-search whim.

## Executable contract
- Implementation: `scripts/stage1a_component1_contract.py`.
- Workflow: `.github/workflows/stage1a-component1-contract.yml`.
- Verified artifact `stage1a-component1-contract`, with `component1_evidence.jsonl` and `summary.json`. The final handoff explicitly includes candidate evidence units (`handoff.relevance_candidates`): observed entity/quality spans and directed relationship candidates retain their source text and offsets; unannotated sentences receive a full-source fallback unit. No relevance result is invented.
- Source integrity asserts all 56 sentence offsets against the original `data/processed/reviews.jsonl`; re-resolved spans require unique original-source occurrence; unresolved multiple-occurrence cases stay recorded rather than silently bound.
- Relevance input and NLI fallback are both **verbatim original sentence text**; no emotion label, relevance flag or NLI prediction is generated here.
- Observed audit: GLiNER annotated 46/56; GTS has links in 22/56; union annotated 48/56; GTS adds 2 sentences to annotated coverage and 11 sentences to **relation-candidate coverage**; 8 remain unannotated but preserved. The final successful handoff created 181 candidate or fallback evidence units (112 entity/quality span records + 34 GLiNER relation candidates + 27 GTS relation candidates + 8 unannotated source fallbacks). These are **not 181 correct or unique claims**. Two entity spans and two links cannot be uniquely positioned by this replay's phrase resolver; all are kept explicitly unresolved, not treated as validated spans.

## Hard limits and next verification
- This run does not prove the extracted links are semantically correct, nor that passing these annotations to relevance and NLI improves the emotion judgments. The existing Stage 1A integrated evidence ledger (run 41899410822) replayed NLI results over unchanged source sentences, so it **cannot** serve as a test of ABSA causal impact.
- An independent human-adjudicated real-review reference is still necessary before any scientific model-selection/performance claim. Do not market source exactness as precision, recall or emotion accuracy.
- Next task is to freeze Component 1 and test Component 2 **on both the original sentences and the extracted evidence proposals**, comparing source-fidelity and false omission; leave Component 3 checkpoint/hypotheses unchanged for that experiment.
- Defer location-level aggregation and nine-emotion score interpretation until evidence attribution and NLI validity are established.

**Operational conclusion:** Freeze GLiNER2.5 + GTS-BERT + non-destructive original-source fallback as the Component 1 software contract; **do not** freeze unverified semantic precision or promote models' candidate links to factual relations.

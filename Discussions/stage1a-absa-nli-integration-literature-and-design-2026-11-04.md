# Stage 1A — Evidence-Structured ABSA × NLI: Literature and Experimental Design

**Date:** November 4, 2026. **Status:** Literature-backed research design, **not executed**, no architecture or vocabulary locked.

## Correct continuity with already-executed work

- Historical `scripts/stage1a_compare_abc.py` performed A whole-review NLI, B multiple hypotheses on whole review, and C ABSA **sentence selection** -> NLI on the 30-example diagnostic sample. That C did **not** pass aspect–opinion structure to NLI; only the selected original sentences were passed. Its assistant-authored labels are **not independent human ground truth**.
- [214-review expanded 60-hypothesis study](stage1a-expanded-vocabulary-results-2026-11-03.md): more stable core ensembles, but inviting remains formulation-sensitive. The vocabulary is a frozen *experimental input*, not validated emotion language.
- [50-review 3-checkpoint study](stage1a-nli-checkpoint-screening-results-2026-11-03.md): BART is 3-way NLI, DeBERTa/ModernBERT zero-shot v2 are binary; no proven model-to-emotion accuracy differences.
- [50-review ABSA-extraction study](stage1a-absa-extraction-screening-results-2026-11-03.md): DeBERTa ABSA kept 72/195 (36.9%) sentences if hard filtering; SetFit 143/194 (73.7%); spaCy 190/194 (97.9%), but spaCy noun chunks are not sentiment ABSA. Therefore **hard aspect-only filtering is not a promising default**.
- These studies did **not** test the actual novelty of interest: how **structured aspect–opinion relations, aspect-targeted emotional inference, or evidence-set fusion** improve interpretation without deleting original context.

## Literature: direct precedents vs relevant adjacent approaches

### I. Aspect–opinion relationships (direct ABSA task precedents)

1. **Naglik & Lango (2024), ASTE-Transformer: Modelling Dependencies in Aspect-Sentiment Triplet Extraction**, Findings of EMNLP. https://aclanthology.org/2024.findings-emnlp.129/  
   ASTE extracts **(aspect phrase, opinion phrase, polarity)** triplets; investigates joint dependencies among predicted elements. **Direct precedent for relation extraction**, not evidence that ASTE results imply built-environment emotion ratings.
2. **Yan et al. (2021), A Unified Generative Framework for Aspect-based Sentiment Analysis**, ACL. https://aclanthology.org/2021.acl-long.188/  
   Defines several ABSA extraction tasks as sequence-generation outputs, including targets/opinions/polarities. **Supports experimenting with richer structured outputs**; it is not an off-the-shelf atmosphere inference method.
3. **Varia et al. (2023), Instruction Tuning for Few-Shot Aspect-Based Sentiment Analysis**, WASSA. https://aclanthology.org/2023.wassa-1.3/  
   Multi-task extraction of aspect term, category, opinion term, polarity. Provides an alternative structured-extraction family, but few-shot tuning/benchmark results may not transfer to places.
4. **Peper & Wang (2022), Generative Aspect-Based Sentiment Analysis with Contrastive Learning and Expressive Structure**, Findings EMNLP. https://aclanthology.org/2022.findings-emnlp.451/  
   Discusses ACOS quadruples and difficulty of **implicit** opinions/aspects; motivates capturing adjective/sensory descriptions instead of assuming every meaningful claim has an overt noun aspect.
5. **Zou et al. (2025), A survey on aspect sentiment triplet extraction methods and challenges**, Computer Science Review. https://www.sciencedirect.com/science/article/pii/S1574013725000371  
   Categorizes pipeline, end-to-end, generative, MRC-based, table-filling, span-based ASTE. Useful survey of method space, **not proof that one family wins on our domain**.

### II. Aspect-conditioned reasoning (adjacent precedent, not validated atmosphere NLI)

6. **Ma et al. (2018), Targeted Aspect-Based Sentiment Analysis via Embedding Commonsense Knowledge into an Attentive LSTM**, AAAI. https://ojs.aaai.org/index.php/AAAI/article/view/12048  
   Target-level and sentence-level attention for classifying sentiment about a *specified target*. This is an architectural rationale for **conditioning inference on a particular location attribute**, but sentiment classification ≠ entailment of atmosphere.
7. **Wang et al. (2024), Refining and Synthesis: A Simple yet Effective Data Augmentation Framework for Cross-Domain Aspect-based Sentiment Analysis**, Findings ACL. https://aclanthology.org/2024.findings-acl.615/  
   Uses an **NLI filter** to quality-control synthetic cross-domain ABSA training data. **Important distinction:** this is an actual ABSA–NLI combination, but NLI is used for data refinement, not as our proposed atmosphere inference module. Do not miscite as direct validation of ABSA -> NLI scoring.

### III. Evidence fusion and conflict-preserving aggregation (adjacent fact-verification research)

8. **Subramanian & Lee (2020), Hierarchical Evidence Set Modeling for Automated Fact Extraction and Verification**, EMNLP. https://aclanthology.org/2020.emnlp-main.627/  
   Combines multiple pieces of textual evidence in sets for support / refute / insufficient-information fact verification; argues neither naive concatenation nor independent evidence averaging always captures interactions. Transfer idea: **preserve multiple observations and joint context**. Fact verification is not subjective atmosphere.
9. **Si et al. (2021), Topic-Aware Evidence Reasoning and Stance-Aware Aggregation for Fact Verification**, ACL. https://aclanthology.org/2021.acl-long.128/  
   Critiques equally weighting evidence and proposes topical coherence and stance-aware combination. Transfer idea: distinguish **supporting and contrary evidence** when building per-review/per-location evidence.
10. **Li et al. (2025), Minimal Evidence Group Identification for Claim Verification**, TrustNLP. https://aclanthology.org/2025.trustnlp-main.8/  
    Studies small evidence sets whose combination supports a claim; an analogy for testing interactions between observations rather than indiscriminately averaging probabilities.

**Literature limitation:** These are *three neighboring literatures* (ABSA relation extraction, targeted sentiment reasoning, evidence fusion), plus one direct NLI-in-ABSA precedent with a different role. I found **no direct paper in this focused search establishing that an off-the-shelf ABSA+NLI ensemble accurately predicts environmental emotional atmosphere**. Combining them here is a research hypothesis, not a prevalidated standard pipeline.

## Target representation: experimental evidence record, NOT a locked ontology

Each recovered observation might be stored as:
- `place_id`, `review_id`, `sentence_id`, exact original `text` + `start/end` offsets;
- `aspect_target` if explicit (e.g., traffic; trees), plus `aspect_category` if defined;
- `opinion_expression` (e.g., unbearably loud; beautiful), linked to target through an explicit relation; `polarity` optional *independent metadata*;
- `attributed_to` = location / visitor-specific / unknown; `negation` and `contrast` flags; optional implicit/sensory observation with **no nominal target**;
- `extraction_method`, model provenance and source-verification status;
- `emotion_hypothesis_id`, per-claim NLI evidence **S/C/U** (when 3-way checkpoint used), `nli_model`, retaining disagreement and uncertainty rather than silently converting polarity into atmosphere.

Any structured extractor must output **original source spans**, not hallucinated normalized premises. Attribute→emotion hypotheses are inferential claims to **test**, not fixed lookup weights. The image-side visual-quality library remains a separate theory-supported object.

Example: “Beautiful gardens, but unbearably noisy traffic.”
- aspect–opinion relation 1: gardens — beautiful (positive);
- aspect–opinion relation 2: traffic — unbearably noisy (negative);
- for **calm**, the second can provide counterevidence while the first is *not necessarily calm support*. For inviting, garden beauty could be relevant but not logically sufficient. This is a proposed reasoning analysis, **not established gold labels**.

## Three mechanisms, experimentally separated

**M1. Evidence decomposition.** Recover relation-linked aspect + opinion and sensory/implicit claims, preserving source. Contrast against previous aspect-token-only extracts. Detect missing atmospheric adjectives and erroneous attribution. **Does structured extraction discover meaningful additional information?** Without independent reference spans, report coverage, fidelity, and known synthetic counterexamples; do not call counts precision.

**M2. Aspect-conditioned inference.** Run **same fixed BART 3-way NLI** with (a) full review, (b) original aspect-opinion source sentence, (c) exact attributed clause/span context, (d) aspect-targeted formulation conditioned on explicit record but retaining source context. Compare how the *same target emotion* is inferred at different granularities. For an attribute with no evidence of an emotion, record U, not negative sentiment. **Do not label a span as atmosphere-supporting just because ABSA polarity is positive.**

**M3. Complementary evidence fusion.** Test whether structured evidence contributes beyond direct whole-review NLI. Preserve original review branch as baseline, structured evidence separately, and both support and contradiction flags. Compare naive mean, strongest-evidence heuristic (flagged as at-risk of cherry-picking), support/contradiction-separated aggregation, and context-aware evidence-set hypothesis. Prioritize transparent descriptive disagreements before learned fusion, since there are no human labels.

## Controls that make the experiments identifiable

1. **A: full-review NLI** baseline; reuse previously saved exact BART predictions where input/hypothesis unchanged.
2. **B: previous hard-filtered ABSA-sentence NLI** negative-control reproduction (already executed on 30 cases; can reuse when comparable; don't claim new novelty).
3. **C: relation-linked aspect–opinion evidence, exact raw source context** -> fixed NLI, not noun terms alone.
4. **D: target-conditioned evidence**, with explicit source grounding; distinguish information selection effects from changing hypothesis semantics.
5. **E: original full-review + structured evidence fusion**, scores separately logged, not merely repeated text.
6. **Controls:** text-length-matched *shuffled or unrelated aspect records*, plain duplicate original sentences, polarity-removed records, aspect–opinion **swapped** pairings, source-only records and **no-aspect / implicit-sensory** cases.
7. **Controlled minimal pairs**: same environmental aspect and opinion flipped (quiet / not quiet); different target (trees beautiful / traffic loud); personal emotion vs place attribute; conflicting observations; hypothetical vs realized; single vs multiple claims.
8. **Across reviews per place:** store all provenance and **do not silently pool review IDs**; contradictory reviews are potentially real disagreement.

A full 50-review × all-60-hypothesis × multiple prompt-formats sweep is **not** a good first experiment. Avoid combinatorial compute blowup and confounded prompt changes. **Pilot 12–20 deliberately selected reviews, 3 pilot emotions, one stable representative direct hypothesis per emotion plus controlled variants**; inspect whether the new mechanism creates grounded changes. Only scale after the mechanism and prompt formats are shown to be technically distinct and source-faithful.

## Evaluation without pretending to have accuracy

- **Extraction fidelity:** source-span match, linked aspect/opinion consistency, no fabricated source text, unmatched/implicit observation count.
- **Evidence preservation:** share of original sentences retained *in the record* (must be 100%), share of relevant synthetic observations retrieved, negation/attribution robustness.
- **Ablation effects:** change in NLI outcome versus original; change versus redundant, shuffled and polarity-removed controls; effect on contradictory vs single-claim cases.
- **Uncertainty and abstention:** neutral prevalence and explicit co-occurring S/C evidence; cross-hypothesis volatility.
- **No correctness claims** on 214 real reviews until independent annotation or transparent source-grounded controlled tests are available; consistent model ensembles can all be wrong.
- Small domain-specific human evidence-span rubric remains a future validation option, but **not needed to inspect experimental mechanisms**.

## Practical sequencing / next action

**First prototype M1 (relation-linked evidence extraction) and verify outputs on source text.** Our current DeBERTa and SetFit artifacts contain aspect spans/polarity, **not reliable linked opinion spans**. Test a suitable ASTE/ACOS method or explicitly controlled aspect-opinion pairing baseline. Verify inference/checkpoint/licensing and exact span alignment before integrating it with NLI.

Then do a small M2 *pair-level NLI* experiment using the same frozen NLI model/hypotheses. Finally design M3 fusion using source-faithful evidence and explicit controls. This isolates mechanism and avoids reproducing old ABSA-filter experiment with a new label.

**Not in scope yet:** final nine-category ontology selection, definitive atmosphere scores, LoRA/fine tuning, text-to-visual co-training. These remain unchanged project stages.

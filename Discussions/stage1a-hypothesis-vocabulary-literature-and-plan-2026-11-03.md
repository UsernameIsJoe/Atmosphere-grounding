# Stage 1A — Hypothesis Vocabulary Research, Literature, and Experimental Roadmap

**Date:** November 3, 2026 · **Status:** Research proposal and completed-pilot synthesis; the expanded-vocabulary experiment has **not yet run**.

## Motivation from executed Stage 1A test

Full real-review test: [GitHub Actions run 41673219260](https://github.com/UsernameIsJoe/Atmosphere-grounding/actions/runs/41673219260), artifact `13253915204`; [full results](stage1a-hypothesis-robustness-results-2026-11-03.md). BART-large-MNLI; 214 reviews, 43 places, 3 emotions, 7 hypotheses/emotion = 4,494 premise–hypothesis evaluations. No independent human-rated ground truth.

| Measure | calm | inviting | safe |
|---|---:|---:|---:|
| Unanimity of the 3 'paraphrase' predictions | 71.0% | 57.0% | 79.9% |
| Mean entailment-score range | 0.167 | 0.306 | 0.118 |

**Finding:** Inviting appears particularly formulation-sensitive. **Critical confound:** some earlier 'paraphrases' differ in meaning (e.g., welcoming vs encouraging a visitor to stay). This is evidence for distinguishing genuine synonyms/paraphrases from *related but non-equivalent facets*, not grounds for discarding a rare hypothesis that may capture novel information.

## Literature and precedents (external sources, not experiments performed by this repo)

1. **Picco et al. (2024), 'Description Boosting for Zero-Shot Entity and Relation Classification,' Findings of ACL.** https://aclanthology.org/2024.findings-acl.562/  
   Reports sensitivity of zero-shot classification to text descriptions, develops varied candidate descriptions, heuristic ranking and ensembles. **Closest computational precedent** for our proposed hypothesis-vocabulary pipeline. Their success on entity/relation classification does not establish results for atmosphere inference.

2. **Ma et al. (2021), 'Issues with Entailment-based Zero-shot Text Classification,' ACL.** https://aclanthology.org/2021.acl-short.99/  
   Demonstrates uneven transfer and lexical pattern issues when class labels become NLI hypotheses. Motivates model- and hypothesis-sensitivity diagnostics.

3. **Poliak et al. (2018), 'Hypothesis Only Baselines in Natural Language Inference,' *SEM.** https://aclanthology.org/S18-2023/  
   Shows models can exploit hypothesis-only artifacts. Motivates null/off-topic/perturbed-premise controls and discourages ranking hypotheses on concentrated probabilities alone.

4. **Russell (1980), 'A Circumplex Model of Affect,' Journal of Personality and Social Psychology.** https://doi.org/10.1037/h0077714  
   Describes affective term relations via valence/arousal. **Conceptual context only**; not a validated ontology for built-environment 'calm/inviting/safe'. In particular 'safe' can be a perceived appraisal rather than a discrete emotion.

5. **Princeton WordNet, 'A Lexical Database for English.'** https://wordnet.princeton.edu/  
   Separates word-sense synonym sets from broader lexical-semantic relations such as antonymy/hypernymy. Vocabulary candidates should be sense- and context-specific rather than a raw thesaurus list.

6. **Political DEBATE (2025/2026), hypothesis augmentation section.** https://www.cambridge.org/core/journals/political-analysis/article/political-debate-efficient-zeroshot-and-fewshot-classifiers-for-political-text/8D0B3E2AAF711F4812E42466DE503A13  
   Generates synonymous hypotheses and **manually reviews them for true semantic equivalence**. Supports an explicit semantic-screening step before scoring variation.

7. **Chausson et al. (2026), 'The Insight-Inference Loop: Efficient Text Classification via Natural Language Inference and Threshold-Tuning.'** https://pmc.ncbi.nlm.nih.gov/articles/PMC13038153/  
   Warns that a universal entailment threshold can be unreliable and describes active threshold tuning requiring some annotations. **Our no-human-ground-truth setting cannot claim calibrated thresholds.**

8. **Kulmizev et al. (2026), 'Label and Explanation Variation in LLM-Based Annotation: a Case Study in Natural Language Inference.'** https://aclanthology.org/2026.acl-long.752/  
   LLM ensemble judgments can also share idiosyncratic variation; their agreement is not automatic validation.

## Research proposal: separate four semantic roles

A. **Core atmosphere statements:** direct location-attributed propositions of one target atmosphere, e.g., 'The place feels calm.' These are the candidate measurements.

B. **Sense-checked paraphrase families:** different linguistic realizations of **the same core proposition**. Change surface wording without changing scope, severity, population, or implied behavior. **Within-family robustness** is meaningful; do not force across-family equivalence.

C. **Related/emergent facets:** properties potentially supportive of an atmosphere, but not logically equivalent: quietness, relaxation, welcoming appearance, ease of staying, perceived security, lack of hazards, etc. Treat these as separate predictors or evidence channels. Do not simply average them into a 'synonym' ensemble. Facets must ultimately respect theory and the target nine-emotion taxonomy; examples are exploratory only.

D. **Opposing/negative and irrelevant controls:** explicit negation of the same proposition, antonymic but not strictly logical opposites, and reviews that describe the visitor's personal emotional state rather than attributes of the location. Separate the controls in reports.

### Candidate vocabulary construction

1. **Define the emotional construct** in location-attributed terms before words. Record intended sense, physical vs social scope, likely ambiguity, and clear non-examples.
2. **Generate candidates broadly:** domain literature, WordNet sense relations, review vocabulary, and manually authored prompts (optionally LLM-generated, with provenance). Do not assume WordNet semantic adjacency is synonymy.
3. **Assign each candidate an explicit group:** core paraphrase family, facet, opposition (strict negation or looser antonym), control/invalid, or uncertain. Preserve stable IDs and provenance.
4. **Semantic screening:** use independently described criteria and explicit counterexample pairs. If two sentences can have different truth values for the same review/location, they are not interchangeable paraphrases.
5. **Run all candidates on the same 214 reviews:** save S/C/U softmax outputs, full predicted labels, rates by group and by location, and raw review IDs/text. Cluster by location rather than treating all reviews as independent.
6. **Analyze robustness:** within-family unanimity, pairwise support-score differences, rank correlations, lexical-construction effects, negative/null-premise flags, and sensitivity across review lengths/places.
7. **Keep rare, divergent hypotheses pending inspection:** outliers can signify model brittleness, semantic shift, or genuinely distinct signal. No winner selected based solely on agreement/high entailment.
8. **Compare ensemble rules explicitly:** equal-mean probabilities, median, trimmed mean, majority label, or disagreement-aware abstention. Compare coverage/stability on held-out **locations**, not only same-corpus statistics. With no labels these remain proxy metrics; no accuracy/optimality claims.

### Experiment shape / safeguards

- Initial target: approximately **15–30 candidate formulations per pilot emotion** *including* related facets and controls; at least 2–3 genuine paraphrase groups per construct when meaningful. Exact number is not a quality metric.
- Retain **original single hypotheses** as baselines, and repeat NLI on same 214 reviews. BART first so change is hypothesis vocabulary, not model.
- **Do not aggregate facets with synonyms** or optimize for maximal entailment; avoid treating consistent neutral as evidence of model quality.
- Use human-readable candidate registry with `id`, `emotion`, `family`, `role`, `text`, `construct_note`, `source`, and `review_status`.
- Semantic equivalence screening can be explicit research judgment even without full human labeling of all reviews. It is distinct from *human-rated text/emotion ground truth*.
- **Controlled mini-tests** with known logical relations (negation, same-meaning paraphrase, off-topic feeling, mixed attributes) may be manually created as falsification checks; do not confuse them with representative accuracy.
- Record descriptive robustness under alternate model as the **next** phase; don't prematurely lock candidate weights or emotional scoring formula.
- Maintain a separate source audit for Google-derived review/photo reuse rights.

## Planned deliverables and gates (not completed)

- [ ] Reviewed candidate registry for calm/inviting/safe, with sense boundaries and provenance
- [ ] Expanded vocabulary NLI script and Actions run on 214 reviews, full probability outputs
- [ ] Within-family stability and counterexample report; inspect outliers
- [ ] Ensemble comparison evaluated on unobserved **locations** using label-free robustness metrics
- [ ] NLI checkpoint comparison with same frozen candidate registry
- [ ] ABSA extractor comparisons and integration after NLI hypothesis experiment

## Research position

The goal is **not** to prove a single sentence is perfect. It is to design an **auditable, semantically structured hypothesis vocabulary**, and test whether a robust core-hypothesis ensemble plus separately evaluated facets offers better stability and evidence coverage. Without independent labels, these are proposed measurement properties, not an established accuracy gain or physical-world causal claim.

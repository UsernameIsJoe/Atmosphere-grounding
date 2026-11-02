# Atmosphere Grounding — Current Research Baseline and Open Methodology

**Status:** Current discussion baseline (2026-11-01), **research in progress, not a design lock**.  
**Authority:** The researcher's latest description in the November discussion takes precedence when interpreting goals. Prior repo architecture, code, and discussion notes remain historical references until intentionally revised. This file documents decisions and candidate methods; it does **not** claim they are implemented or validated.

## 1. Research objective

Learn **how observable image qualities relate to nine theory-supported atmosphere/emotion categories**, using descriptions/reviews of the *same physical locations* as a source of emotional evidence. The ultimate aim is an **emotion-aware visual predictor**, not simply a multimodal classifier that always needs text.

Earlier CLIPSeg-based evaluation struggled because atmosphere terms are often adjectives, experiential attributes, or intangible concepts, whereas visual segmentation is more naturally suited to objects and regions. The project therefore separates **visual observations** from **textual emotional evidence**, then learns their relationship.

The exact nine categories and supporting attributes are part of the conceptual framework but are not fully enumerated in this discussion. Do not invent or lock a taxonomy.

## 2. Dataset and correspondence

- Each physical location has **multiple images** and **multiple human-written texts** (e.g. descriptions/reviews).
- Images and texts are related by **shared location**, *not* known one-to-one image–review pairs.
- Working estimates from earlier handoff (not locked dataset counts): ~1,000–10,000 locations, ~5 photos and ~5 reviews each.
- Place identity is the unit of cross-modal association and must also be the unit of holdout for evaluation.
- Verify permitted training, storage, and reuse of Google Maps-derived content before implementation.

## 3. Research structure — three substantive stages

### Stage 1A. Text → evidence concerning nine emotions (OPEN METHOD)

**Input:** Human-written comments/reviews grouped by location.  
**Question:** How can text be consistently and fairly evaluated *for evidence about a place's atmosphere*, rather than merely for the writer's own emotions or lexical similarity to adjectives?  
**Desired output:** Location-grounded, emotion-specific textual evidence, preserving **support / contradiction / insufficient evidence**, the passages that justify decisions, and uncertainty/coverage. How these observations become per-location scores remains to be designed.

Example distinction:
- "The park makes me feel peaceful" supports an atmosphere claim.
- "I felt happy when I found my wallet here" describes the reviewer but need not support a happy atmosphere.
- A missing mention of quietness is **not** evidence of noise.

**Methods to investigate and compare (not selected):**

1. **Natural Language Inference (NLI) — promising primary candidate.** Use a *premise* (review or extracted passage) and a theory-grounded *hypothesis* about an emotion, and evaluate entailment, contradiction, or neutral/insufficient evidence. Pretrained NLI checkpoints can be tried **without new training labels initially**. Still need independent human assessments to measure domain validity; NLI output probabilities are **not automatically emotion-intensity or calibrated location scores**. Study hypothesis wording, multiple paraphrases, context/negation and neutral handling before choosing a scoring method.
2. **Aspect-Based Sentiment Analysis (ABSA) / aspect and opinion extraction — promising complement.** Extract *what about the location is described* and the stated evaluation, e.g., appearance: positive; crowding: negative; noise: negative. **ABSA does not inherently infer “calm” from such aspects.** An explicit second inferential step is necessary, potentially NLI over extracted evidence. Domain-grounded aspect extraction may be more valuable than generic polarity.
3. **Embeddings — baseline or evidence retrieval.** Compare semantics of passages with **well-defined descriptions** of categories, not isolated adjectives; potentially retrieve relevant passages. **Semantic proximity is not proof of entailment or of atmospheric quality.** Example: greenery may be semantically associated with peaceful settings even when the review says the place is loud and crowded.
4. **Co-occurrence / lexicon — low-priority baseline.** Researcher is skeptical that surface co-occurrence reliably captures relational or contextual meaning; do not make it the primary explanatory mechanism.
5. **Direct emotion classification/regression — defer for now**, at the researcher's request.

**Promising combination to test:** Aspect extraction identifies location-grounded observations → NLI assesses each observation's relevance to theory-grounded emotion hypotheses → embeddings optionally retrieve/group passages and provide a comparative baseline. These components are **not yet mandatory**, nor should their scores simply be averaged without validation. Evaluate contradictory and missing evidence explicitly.

### Stage 1B. Image → fixed visual-quality library (CONFIRMED PRINCIPLE)

**Input:** Images from each location.  
**Question:** How can observable features be measured consistently?  
**Desired output:** Per-image vectors using a **fixed, theory-supported visual quality/feature library**, applied consistently across all examples. Examples mentioned: object types/presence, object density, visual contrast, and spatial/compositional qualities.

- The library is **fixed across data** for comparability, but can be revised through explicit research/versioning.
- It must remain interpretable and atmosphere-agnostic at extraction: **do not hard-code “trees = calm”** or similar mappings.
- Existing repo visual-category ontology and extractors may provide starting materials; their exact correspondence to the current desired library should be audited rather than assumed.
- Assess feature quality and extraction reliability separately from atmosphere learning.

### Stage 2. Cross-modal association via shared location (CORE LEARNING PROBLEM)

**Inputs:** Per-location collections of image-quality vectors from Stage 1B, and emotion-specific textual evidence from Stage 1A.  
**Question:** Which observed visual qualities, singly or in combinations, predict the emotional/atmospheric evidence from text across locations?

- Use shared location as **weak correspondence**, without fabricating review-to-photo matches.
- Learn associations *from the corpus*, not manually or through an LLM's prior guesses.
- Compare interpretable feature-based association/regression, multiple-instance/set learning, and possibly representation-learning objectives. The best architecture and losses are **not decided**.
- Avoid treating associations as causal effects; control for category/geography and recognize reviewer biases.
- Some experiences (e.g. noise, smell, interpersonal treatment, perceived safety) may be poorly observable from photographs; visual prediction should have evidence limits and uncertainty.
- Guard against circular learning and evaluation when the same reviews supply weak labels and text-model inputs.

### Stage 3. Visual atmosphere predictor / model adaptation (DESIRED OUTCOME)

- **Primary realistic goal (B):** image **plus measured visual-quality features** → nine atmosphere/emotion scores.
- **Stretch goal (A):** raw **image alone** → nine emotion scores (the model may internally derive the features).
- At prediction time, the desired visual scoring route **should not require fresh reviews as mandatory inputs**; reviews support learning.
- Possible methods: train a lightweight predictor on measured features; fine-tune a pretrained CLIP/VLM or vision model; use **LoRA** for parameter-efficient adaptation where technically appropriate; or distill a validated teacher. **No intention to build an LLM from scratch**, and no model family is locked.
- Decide later how to aggregate supporting attributes into nine scores, their numerical meaning, confidence/evidence coverage, and comparability across locations.

## 4. Validation and scientific safeguards (to design)

- Establish a modest independently human-annotated benchmark for **location-attributed** atmosphere, separate from review-derived weak targets.
- Split by **whole location**; test image-only, visual-features-only, image+features and text-derived baselines where appropriate.
- Test NLI/ABSA/embedding text-evidence quality independently before training the cross-modal learner.
- Evaluate across place types/geographies and test shuffling/null baselines, missing reviews, contradictory claims and uncertainty.
- Evaluate visual feature extractors independently; record which atmospheric attributes are not identifiable from images.
- Separate success at reproducing weak review-label rules from agreement with **independent judgments**.

## 5. What is decided versus unresolved

**Established direction**
- Two parallel evidence-production branches: text → emotion evidence and images → fixed theory-grounded visual qualities.
- Connect the branches through common location identity; no forced image-review pairing.
- Learn visual–emotion relationships and work toward a visual predictor.
- Main practical endpoint: image + fixed features; image-only is a stretch.
- Do not presume direct whole-input VLM prompting, co-occurrence, or building an LLM from scratch is the solution.

**Open research decisions**
- Exact nine-emotion taxonomy, supporting attributes, and meaning of scores.
- NLI emotion-hypothesis library and its wording/robustness.
- Whether ABSA adds meaningful information over direct NLI; whether embeddings help retrieval.
- Emotion evidence aggregation across review passages and reviews, missingness and disagreement.
- Independent human annotation scope and data usage rights.
- Feature-library implementation/version; location aggregation and weak correspondence modeling.
- Which learner and training objective works; whether/where fine-tuning or LoRA genuinely helps.
- Accuracy, robustness, and uncertainty requirements.

## 6. Immediate next research focus

**Text Stage 1A:** research how to construct consistent, theory-grounded NLI hypotheses for all nine emotions; compare direct review-to-NLI with aspect extraction followed by NLI, and an embeddings baseline. Test on a small annotated set before fixing a scoring formula. Do not conflate the sentiment of a review with emotional qualities attributable to the location.

## 7. Relationship to earlier repository materials

- [Five research questions](location-sentiment-five-research-questions.md) remains a **general educational/research agenda** (representation, learning, multimodal reasoning, prediction, validation).
- Historical `Docs/PROJECT.txt`, `Docs/ARCHITECTURE.txt`, and `Docs/DESIGN_LOCK.txt` describe earlier implementations or design positions, notably co-occurrence-first learning and an optional LoRA narrator. **Do not infer that those earlier descriptions override this newest research baseline.**
- No implementation change or experimental result is claimed by this memo.

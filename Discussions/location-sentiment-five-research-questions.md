# Location Sentiment Scoring — Five Research Questions

**Status:** Exploratory research and learning agenda, not a locked implementation plan.  
**Scope:** A possible learned multimodal approach for estimating nine location sentiments from sets of photos and human-written reviews. This note does not replace the repository's current technical architecture or design decisions.

## Working research context

- A location may have approximately five photos and five reviews, grouped at the location level rather than paired image-to-review.
- Tentative scale: 1,000–10,000 locations.
- Sentiments are composed of supporting emotions or attributes; the exact taxonomy and interpretation of scores remain open.
- Directly prompting a vision-language model to issue final sentiment scores is **not the preferred primary approach**. Learned representations and multimodal methods are candidates to study, not commitments.
- Google Maps-derived data may have licensing/use restrictions for ML training: confirm rights before building training datasets.

## 1. Representation — How does a model understand a location?

**Concept:** Translate images and human language into vectors (embeddings) that encode useful characteristics.

**Methods to study**
- Pretrained image encoders such as SigLIP2 and DINOv2.
- Pretrained text/sentence encoders for reviews.
- Latent or embedding spaces and similarity measures.

**Key question:** Does feature similarity capture emotional qualities, or merely visual and semantic resemblance?

## 2. Learning — How does the model learn emotions?

**Concept:** Learn relationships between observations and human-perceived emotional characteristics, rather than hard-coding adjective similarity.

**Methods to study**
- Supervised learning with independently rated emotions.
- Weak supervision using emotional evidence extracted from reviews.
- Self-supervised learning using structure and associations within the dataset.

**Key question:** How can sparse, subjective reviews provide useful labels without confusing *not mentioned* with *absent* or teaching the model simply to reproduce the weak-label extraction rule?

## 3. Multimodal reasoning — How can images and text cooperate?

**Concept:** Integrate complementary visual and textual evidence even though individual reviews do not match individual photos.

**Methods to study**
- Multiple Instance Learning (MIL): treat each location as sets of observations.
- Attention or set pooling: weight evidence differently for different emotions.
- Gated multimodal fusion: adjust how much each modality contributes.
- Location-level contrastive learning: a possible auxiliary way to align modalities.

**Key question:** How can we use complementary evidence without forcing agreement about qualities a photo cannot reliably reveal (for example, sound or lived experience)?

## 4. Prediction — How do representations become sentiment scores?

**Concept:** Convert learned signals into interpretable emotion measurements, then combine supporting emotions into the nine sentiments.

**Methods to study**
- Regression for continuous strengths.
- Ordinal models for ordered levels.
- Pairwise ranking to compare locations.
- Aggregation of supporting emotion scores, with separate uncertainty or evidence coverage.

**Key question:** Do scores express predicted visitor feeling, evidence-backed perception, or suitability for a desired experience? How can scores remain comparable between places?

## 5. Validation — How can we prove the model works?

**Concept:** Test whether predictions correspond to independent human assessments, not merely to weak labels or place-type shortcuts.

**Methods to study**
- Independent human ratings and inter-rater agreement.
- Hold out entire locations, not individual photo/review rows.
- Ablation: image-only, text-only, and fused systems.
- Generalization by geography/place type; robustness to missing/replaced observations and random seeds.
- Ranking correlation, prediction error, and calibration as appropriate.

**Key question:** Does the multimodal method improve real-world sentiment validity over simple baselines?

## How we will use this agenda

The five questions are linked: **representation** defines what evidence is available; **learning** establishes what can be learned from it; **multimodal reasoning** determines how evidence is combined; **prediction** defines the outputs; **validation** tests whether they mean anything.

**Suggested discussion order:** first understand representation and supervision together; then examine whether multimodal complexity is warranted; then choose prediction targets and independent tests. Compare concepts and methods before selecting an architecture.

## Decisions deliberately left open

- Exact nine sentiments and supporting attributes.
- Definition and scale of an emotion or sentiment score.
- Input modalities available at inference time.
- Human annotation and weak-label strategy.
- Whether MIL, attention, gating, or contrastive learning help beyond baselines.
- Permitted data sources and storage/training rights.
- Final architecture, loss functions, and experimental thresholds.

**Research principle:** The five topics are an inquiry framework, **not five frozen pipeline modules**. Experimental evidence should determine the implementation.

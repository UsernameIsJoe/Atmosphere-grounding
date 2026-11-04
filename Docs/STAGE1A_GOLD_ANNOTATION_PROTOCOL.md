# Stage 1A independent annotation protocol

## Purpose
Build a complete gold standard for **original review sentences** before comparing any ABSA system. The 29 previously authored partial lexical targets are **not gold** and must not be used as complete precision/recall labels.

## Corpus
Use `stage1a-real-review-gold-annotation-template` from the successful benchmark-packet Action. It contains 56 verbatim sentence spans from 20 original reviews selected before this experiment; retain `row`, `place_id`, `sentence_index`, source text and review offsets. Do not invent text or fill absent relations with model guesses.

## Annotation policy
1. **Target**: noun phrase / explicit referent being described, or a separately marked implicit target. Do not invent literal source offsets for implicit targets.
2. **Opinion**: minimal source-span expression that attributes a qualitative property or judgment to that target. Preserve modifiers that change sense, such as negation or quantifiers. If the model generates a paraphrase, distinguish it from the source wording.
3. **Link**: annotate each target–opinion relation, including multiple opinions on one target and one opinion applied to multiple targets.
4. **Polarity**: `positive`, `negative`, `neutral`, or `uncertain`; evaluate `uncertain` separately from established polarity classes.
5. **Atmosphere relevance**: mark whether each opinion describes the experienced environment of the place (spatial, sensory, social, comfort, perceived safety, etc.) rather than purely incidental matters (prices, logistics, commercial transactions). Record evidence in words, not infer one of the nine emotions yet.
6. **No-relations case**: an empty `triplets: []` is a complete annotation if the sentence genuinely has no target–opinion relation; it must not be encoded as `null`.
7. **Completeness**: annotate every eligible relation in the sentence, even when it does not match the existing 29 reference pairs. Keep spelling and punctuation from source even if erroneous.
8. **Ambiguity**: record disagreements and justified span variants; two independent passes and adjudication are preferable. Record `annotator` and notes and freeze the final file before comparing model candidates.

## Suggested complete JSONL structure
Each sentence row keeps its provided identifiers and uses:
- `triplets`: a complete list of objects containing `aspect`, `opinion`, `polarity`, `atmosphere_relevant`, and optional `implicit_aspect` or `notes`.
- `atmosphere_evidence`: list of source-supported descriptive phrases relevant to atmosphere; empty list is valid.
- `annotator`: nonempty provenance string.
- `notes`: ambiguity/adjudication rationale.

## Metrics and guardrails
Use exact triplet precision/recall/F1 only on completed gold, optionally separately calculate relaxed phrase-overlap / adjudicated semantic equivalence. Report polarity errors, recall on atmosphere-relevant evidence, false-positive rate on irrelevant reviews, and per-review failure cases. Split by **place**, not randomly by sentence, if used for supervised tuning. Never leak the held-out reference into prompt or decoding selection. Model-card examples are protocol smoke tests, not independent benchmark data.

## Scope restrictions
Current experiments may legitimately compare raw triplet counts, parse-rate, source anchoring, and previously registered partial-target recovery. These are **diagnostics only** and do not rank models by semantic accuracy. No model should be locked into Stage 1A without the completed gold benchmark.

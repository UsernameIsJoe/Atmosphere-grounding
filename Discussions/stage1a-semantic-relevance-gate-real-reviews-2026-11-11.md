# Stage 1A — Step 4A: Semantic relevance gate (first real-review benchmark)

**Executed:** 2026-11-11. [GitHub Actions run 43092641309](https://github.com/UsernameIsJoe/Atmosphere-grounding/actions/runs/43092641309) — both model jobs completed successfully.

## Frozen test conditions

- **Input:** five actual Google Places reviews, first review per each of five identified locations, source hashes verified against `data/processed/reviews.jsonl`.
- 20 deterministic original clauses × 3 category descriptions = **60 clause/category pairs per model**.
- Queries equally cover positive and negative evidence for Calm, Inviting and Safe.
- No synthetic comments, no LLM annotations, no model finetuning, no threshold selected.
- Two pretrained cross-encoder rerankers: `BAAI/bge-reranker-v2-m3`, `cross-encoder/ms-marco-MiniLM-L6-v2`.
- Scores are `sigmoid(raw_logit)` in [0,1], **not calibrated probabilities of atmospheric relevance**. Results and per-case scores uploaded as artifacts in linked run.
- Source code: `scripts/stage1a_crossencoder_gate_5.py`. Anchor checks: `data/evaluation/stage1a_gate_anchor_cases.json`; **these 19 hand-selected source anchors are regression/behavior probes, not independent gold labels**.

## Observed results

| Metric | BGE v2 m3 | MS MARCO MiniLM L6 |
|---|---:|---:|
| Pairs completed | 60/60 | 60/60 |
| Minimum score | 0.0000160 | 0.0000374 |
| Median score | 0.0000166 | 0.0003516 |
| Maximum score | 0.0041867 | 0.0078377 |
| Selected retain-above-reject pairwise fraction | 0.7708 | 0.4167 |

### Discriminative examples (reproduced from actual corpus)

| Original clause / category | BGE | MiniLM | Methodological observation |
|---|---:|---:|---|
| "Then the park is enveloped in trees and circulous paths that make you feel like you are being protected and comforted." / Safe | 0.0041867 | 0.0078377 | Top score both |
| "but poor consideration around how the different areas interact with one another makes this place a dirty, chaotic mess." / Calm | 0.0020387 | 0.0013407 | BGE recognizes negative evidence |
| "I spent like 3 hours and can say it was one of the best and quiet times I've spent before..." / Calm | 0.0012724 | 0.0012813 | Both rank moderately |
| "Nice place to unwind, jog, or dogwalk." / Calm | 0.0001337 | 0.0013903 | MiniLM ranks higher |
| "but the sand next to it makes the sides extremely slippery." / Safe | 0.0000165 | 0.0006735 | BGE misses concrete hazard, at noise floor |
| "It’s very easy for someone to slip and hit their head on any one of the hard elements." / Safe | 0.0000169 | 0.0010522 | BGE misses explicit injury-risk evidence |
| "My favorite spot for a meditative walk through a labyrinth" / Calm | 0.0000166 | 0.0008009 | BGE misses indirect calm |
| "There are quite a few seating areas." / Calm | 0.0000168 | 0.0009086 | Minilm wrongly ranks neutral amenity above many relevant cues |

## Assessment

**Neither reranker currently passes as a safe high-recall relevance gate.** BGE has a better rank-order on the hand-picked anchors, but its score distribution is collapsed near a floor, and it scores explicit safety hazards almost identically to irrelevant descriptions. Using a fixed threshold would silently remove crucial negative evidence. MiniLM is less collapsed but ranks several unrelated clauses higher than clear relevant examples.

These are not model capability claims in general: both rerankers were trained mainly for query-passage retrieval. Here we use one relatively long, handcrafted query per emotion. This pilot cannot distinguish model/task mismatch from wording/segmentation effects, and does not prove intrinsic lack of ability.

## Research boundary / next decision

**Stage 1A Step 4A remains OPEN.** Do not connect either score to a hard reject gate. No LLM downstream test or threshold tuning yet.

Next **controlled** evaluation would compare short, predeclared query variants and whole-sentence boundaries versus clause boundaries on original reviews; test positive AND negative cue recall, and inspect all false rejects. An independently assessed evaluation sample is needed before any calibration or accuracy claim. Alternatively investigate task-matched NLI models for relevance (entailment + contradiction) instead of passage retrieval rerankers. Avoid making a score `0.9` look like confidence without calibration.

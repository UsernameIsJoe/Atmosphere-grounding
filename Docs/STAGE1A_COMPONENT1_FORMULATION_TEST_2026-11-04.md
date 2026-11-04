# Stage 1A Component 1 — Controlled schema and review-context test (2026-11-04)

**Executed.** The hypothesis was that Stage 1A extraction might fail because our GLiNER schema emphasizes isolated entities instead of coherent claims, or because individual sentence inputs discard review context. This test holds the pretrained checkpoint, sample, inference implementation and decoding configuration fixed wherever possible; it tests exactly those two changes. It does **not** introduce a new model, synthetic reviews or revised emotion labels.

## Preregistered comparison

- **A — Existing schema:** original `JointIE` typed place / physical feature / spatial quality / descriptive quality / reported experience schema; original sentence as input, frozen [run 41923414224](https://github.com/UsernameIsJoe/Atmosphere-grounding/actions/runs/41923414224).
- **B — Claim-oriented schema:** same `fastino/gliner2.5-base-v1` and `JointIE` beam-32 decoding, original individual sentence as input. Entities: `place_or_subject`, `physical_feature`, `environmental_condition`, `reported_experience`. Relations: `contains`, `has_condition`, `induces_experience`.
- **C — Review context:** identical checkpoint, decoding and schema as B; **complete original review** input. Entity offsets and intra-sentence relations mapped to exactly the 56 frozen sentence boundaries. Cross-sentence/review-level edges not counted as within-sentence relationships.
- **D — Frozen GTS reconciliation:** the same previously run GTS-BERT original-sentence triplets are compared post hoc to the relationships from A/B/C. This is **not a fourth model inference condition** and does not establish semantic truth. We count source-span overlaps only.

Model inference: [run 41925913206](https://github.com/UsernameIsJoe/Atmosphere-grounding/actions/runs/41925913206) — successful. Audit: [run 41926049772](https://github.com/UsernameIsJoe/Atmosphere-grounding/actions/runs/41926049772), rerun after the inference artifact became available — successful. The earlier automatically triggered audit attempt failed because the dependency artifact was not yet available; it did not measure extraction performance.

## Matched results

| Measure | A | B | C |
|---|---:|---:|---:|
| Original source sentences compared | 56 | 56 | 56 |
| Sentences with at least one entity | 53 | 51 | 44 |
| Entity candidates | 134 | 113 | 82 |
| Sentences with intra-sentence relationship | 18 | 13 | 8 |
| Intra-sentence relationship candidates | 27 | 14 | 11 |
| Reported-experience entity candidates | 17 | 21 | 10 |
| Experience-directed relation candidates | 3 | 3 | 2 |
| GTS source-span-overlap with a candidate description | 4 | 0 | 0 |
| Frozen GTS triplets preserved separately | 23 | 27 | 27 |
| Sentences with a model relationship after preserving GTS | 31 | 29 | 26 |

C produced **25 relation candidates in the 20 complete review graphs**, of which **11** had both endpoints inside the same frozen original sentence. The other **14** are outside these sentence-level counts: they may be other-sentence edges or cross-sentence edges. They were not independently validated for meaning. **Do not infer a ranking from the number of edges**: schema definitions change what constitutes an extractable edge, and C has a larger inference scope.

## Fixed real-case audit

1. **Row 55, “A charming and cozy park ...”** A: `park → described_as → charming and cozy`, corroborated by GTS `park → cozy → positive`. B: no relationship, misses adjective phrase. C: no within-sentence relationship. **Changed schema loses a correct-looking key description; GTS carries one partial aspect/opinion link only.**
2. **Row 55, “A Torii ... unique vibe.”** A: `Torii → evokes_experience → unique vibe` and a descriptive link. B: `Torii → induces_experience → vibe` (loses `unique`). C: no within-sentence edge.
3. **Row 55, “park enveloped in trees and circulous paths ... protected and comforted.”** A: park→trees and park→paths; `comforted` entity, no experience-directed edge. B: also captures `protected` and `comforted`, and park→trees/paths; **no relation to either reported experience**. C: same two park/feature relations, `comforted`, still **no experiential relation**. GTS returns no triplet. **The central compositional extraction failure remains.**
4. **Row 74, “Ckean, well kept, and well patrolled by police.”** A incorrectly treats `Ckean` as a place, with two spurious graph links. B and C still wrongly type `Ckean` as `place_or_subject` but no longer create the same links; they also fail to capture the meaningful full observation. This is not simply a correction.
5. **Row 97, “loss of sunlight ... redesign of the garden ...”** B adds questionable `garden → contains → sunlight`, which ignores the statement about **loss** of sunlight. A and C do not generate this edge. **Negation/change-of-state remains a major issue.**
6. **Row 113, “Inspiring place with great location.”** A gives questionable `Inspiring place → has_feature → location`; B has no edge; C gives questionable `place → has_condition → location`. GTS independently has `place → Inspiring → positive`.

These are targeted, transparent qualitative observations on named original review rows, **not** a complete externally adjudicated gold benchmark.

## Decision

**Do not adopt claim-oriented schema B or full-review mode C as a superior default.** They did not recover the key environment→experience dependency; B loses an important descriptive relation and C often loses detailed same-sentence output. The result **does not prove GLiNER incapable**: we have tested one B schema and one C context choice, not a systematic validated search. It **does show that our simple claim-schema and full-review-context hypotheses did not fix the observed failure.**

**Keep A (existing typed JointIE + independent GTS + non-destructive reconciliation/source fallback) as the reproducible working baseline**, not as a scientifically validated Component 1 solution. Preserve B/C experimental artifacts for future comparison. Do not hard-filter unlinked explicit experiences.

**Technical boundary:** We tested model-side extraction schema/context and source-span reconciliation, not semantic accuracy or downstream Relevance/NLI improvement. The next defensible research milestone requires a small independently adjudicated *complete* reference of real observations and links (including negation, subject attribution and direct/reported experience), before claiming that additional schema tuning or another model improves extraction.

## Reproducibility

- `scripts/stage1a_component1_formulation_test.py`: runs B and C with same original reviews, same checkpoint, frozen schema, source validation; `.github/workflows/stage1a-component1-formulation.yml`.
- `scripts/stage1a_component1_formulation_audit.py`: matches A/B/C outputs by original review identity, exact sentence text and offsets, and adds frozen GTS comparison D; `.github/workflows/stage1a-component1-formulation-audit.yml`.
- Artifacts: `stage1a-component1-formulation` (`predictions.jsonl` and summary) and `stage1a-component1-formulation-audit` (`matched_cases.jsonl` and summary).

**No nine-emotion labels, relevance selection or NLI inference were introduced in Component 1.**

> **Follow-up formulation test (2026-11-04):** Same checkpoint tested on 56 original sentences with claim-oriented schema and whole-review context. Neither improved the key environment→experience linkage; the new schema lost some useful descriptions. **Retain the existing typed-graph + GTS reconciled baseline provisionally**, not as a validated semantic winner. Results: [STAGE1A_COMPONENT1_FORMULATION_TEST_2026-11-04.md](STAGE1A_COMPONENT1_FORMULATION_TEST_2026-11-04.md).\n\n# Stage 1A Component 1 — Parallel Extraction + Reconciliation, 2026-11-04

**Research architecture:** Component 1 = evidence extraction; Component 2 = emotion-specific relevance; Component 3 = NLI direction. **Only Component 1 is changed here.** Component 1 does not map text onto the nine emotion categories or assert emotion support, contradiction, or intensity.

## Agreed design

Input: Original review text, segmented into original source-matched sentences; full review is retained.

1. **Independent full-sentence inference.** GLiNER2.5 identifies places, objects, physical qualities, descriptive qualities, explicit lived experiences and candidate relationships. GTS-BERT independently extracts aspect→opinion→sentiment on the same original sentence. The pretrained GTS checkpoint has no native API for consuming GLiNER's annotations; feeding it GLiNER output instead of original text would change its intended inference task.
2. **Source-grounded reconciliation.** Align both outputs to the exact same original text and local offsets. An overlapping GTS aspect/opinion can corroborate a GLiNER `described_as` subject/quality pair; its sentiment is metadata, not one of nine emotion labels. Do not duplicate corroborated pairs. Preserve unmatched GTS relationships as candidate records and unlinked GLiNER mentions as unlinked observations. Do not construct new descriptive sentences or fabricate experience→environment connections when the model did not link them.
3. **Full original-source fallback.** No hard-filtering; all 56 sentences and full review text are transmitted. Relevance can evaluate graph-linked claims, unlinked spans, or original sentence. All are model candidates, not validated facts.

**Experimentally investigated refinement:** GLiNER's official `JointIE` typed-graph decoding (same `fastino/gliner2.5-base-v1` checkpoint) versus previous independent `extract_entities`/`extract_relations`. Documentation: https://github.com/fastino-ai/GLiNER2/blob/main/tutorial/15-joint_ie.md. This is a decoding/schema comparison, not a new pretrained-model search.

## Executed work

- Official typed JointIE run [41923414224](https://github.com/UsernameIsJoe/Atmosphere-grounding/actions/runs/41923414224): 20 original reviews, 56 original sentences, 56/56 feasible typed graphs, 0 runtime errors; **134 entity candidates, 27 relationship candidates**.
- Same source GTS comparison uses frozen [41908682135](https://github.com/UsernameIsJoe/Atmosphere-grounding/actions/runs/41908682135) (27 previously extracted triplets on 56 sentences).
- Validated reconciliation [41924151396](https://github.com/UsernameIsJoe/Atmosphere-grounding/actions/runs/41924151396): source identity, original offsets, relation-endpoint conservation, GTS candidate conservation and raw-text fallback assertions passed on all 56 sentences. Artifact `stage1a-component1-reconciled` contains `reconciled.jsonl`, `summary.json`.
- Scripts: `scripts/stage1a_component1_joint_gliner.py`, `scripts/stage1a_component1_reconcile.py`.
- Explicit no-emotion stage-1 output; downstream relevance and NLI methods are unchanged.

## Verified reconciliation counts

| Quantity | Observation |
|---|---:|
| Original sentences retained | 56/56 |
| JointIE candidate links | 27 |
| GTS aspect–opinion links (original prediction) | 27 |
| GTS links aligned to a JointIE `described_as` edge | 4 |
| GTS unmatched links retained independently | 23 |
| JointIE entity mentions not involved in a graph edge | 90 |
| JointIE reported experience mentions not linked to any graph edge | 14 |
| JointIE explicit `evokes_experience` edges | 3 |
| Sentences without a relation candidate | 25 |
| Previously independent GLiNER links | 34 |
| JointIE links matching a prior independently predicted GLiNER link | 11 |

**These counts are not accuracy, validated recall, or precision.** Neither type constraints nor source span matching can establish a semantic link's truth. We have no independently annotated complete gold, and coverage counts do not demonstrate downstream benefit.

## Examined real cases

- **“A charming and cozy park that is nestled in the heart of Cambridge.”** JointIE finds `park → described_as → charming and cozy`; GTS finds `park → cozy → positive`. The reconciler aligns these two into one candidate relation with GTS provenance/polarity. The prior independent `park → has_feature → Cambridge` false link was absent in the new typed graph; `Cambridge` is a detached place mention.
- **“A Torii ... welcomes you ... a unique vibe.”** JointIE found `Torii → evokes_experience → unique vibe`, keeping the original span.
- **“Then the park is enveloped in trees and circulous paths ... protected and comforted.”** JointIE links park to trees and paths, but does **not** link the environment to the comfort/protection experience. `comforted` is an unlinked explicit experience, and `protected` was omitted as a graph entity. No fabricated causal edge is added; source fallback remains essential.
- **“Ckean, well kept, and well patrolled by police.”** JointIE falsely tags `Ckean` as a place and links it to `well kept` and `police`. Typed decoding cannot guarantee semantic precision even with allowed endpoints.
- **“Inspiring place with great location.”** JointIE produces questionable `Inspiring place → has_feature → location`; the original GTS `place → Inspiring` remains separately available.

## Outcome, adoption criteria, and scientific limitations

**Adopt the provenance-preserving reconciliation mechanism and full-source fallback as the operational Component 1 refinement.** Its output is a traceable *candidate evidence representation*, not automatically summarized truth.

**Do NOT claim JointIE beats independent GLiNER**: in addition to eliminating some incorrect edges, it introduces wrong type assignments and misses experiential connections. The archived independent GLiNER output remains a comparator; the current reconciled experiment uses JointIE candidates. Before replacing the earlier independent GLiNER default conclusively, require independently audited source-claim truth, not link volume or graph-feasibility percentage.

**Do NOT claim improved relevance/NLI performance.** The downstream components have not been reevaluated using these units; the previous evidence ledger ran unchanged sentence NLI regardless of ABSA annotations.

The correct next scientific validation is a blinded, complete set of real-source claim/evidence annotations, including correct and incorrect subject–description links, negation, experience attribution and omitted observations. Hold Relevance and NLI constant when evaluating whether extraction metadata adds value.

## Operational rule

For every evidence unit, carry verbatim sentence, source offsets, source model(s), candidate type, and unresolved/error status. All `has_feature`, `described_as` and `evokes_experience` edges remain unverified until externally checked. In downstream use, do not silently convert model confidence or graph feasibility to factual correctness.

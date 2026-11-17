# Full segment audit — 2026-11-17

**All 71 source sentences, all 110 collected outputs and all 111 parsed claims were inspected.** There are 106 structurally valid outputs, including empty-claim outputs. Four invalid outputs are inspected/reported separately. All 32 unattempted model/sentence combinations are recorded explicitly. No additional inference, GPU rental or retries were performed.

This is an **assistant-authored, unblinded source audit against the existing v0.5 codebook**, not independent human ground truth. It supersedes the earlier selective source checks and five-example comparison as the basis for aggregate counts.

## Primary result: semantic correctness per valid sentence output

| Model | Valid outputs audited | Correct | Clearly incorrect | Borderline |
|---|---:|---:|---:|---:|
| Qwen3.8 27B | 68 | **39** | **16** | **13** |
| Gemma4 31B BF16 | 38 | **28** | **6** | **4** |

The two models have unequal coverage. For a fair comparison, use the **same 38 sentences with valid output from both**:

| Model | Same valid sentences | Correct | Clearly incorrect | Borderline |
|---|---:|---:|---:|---:|
| Qwen3.8 27B | 38 | **24** | **10** | **4** |
| Gemma4 31B BF16 | 38 | **28** | **6** | **4** |

A simple correct/all-shared fraction is 24/38 (63.2%) versus 28/38 (73.7%). Borderline cases remain visible rather than being silently counted as correct or incorrect. These fractions are agreement with this audit, not validated model accuracy.

## What correct and incorrect mean
- **Correct:** no clearly unsupported directional claim, all required emotion/direction combinations recovered, and no unresolved construct boundary for the sentence.
- **Clearly incorrect:** at least one unsupported directional claim or a missed required direction. An output can correctly identify inviting from one quote but still fail because it adds another unsupported inviting claim from an unrelated price/product quote.
- **Borderline:** reviewed, but the source/frozen codebook does not settle a scope or applicability boundary. Event outcome versus venue experience, educational signage versus exhibit quality, and activity presence versus actual attraction are recorded rather than forced.
- E/T and referent-only issues are logged separately and do **not** drive these primary emotion/grounding counts. The logged tag flags are selective diagnostics, not a complete tag-accuracy benchmark.
- No required direction was clearly missed in a valid output under this conservative reference. Potential omissions occur in borderline cases; do not turn this observation into a general recall claim.

The codebook's broad place-level appeal definition is retained. Generic praise of the **place** may support inviting; praise only of food or exhibits does not automatically do so. A known gate false positive is not itself proof that every scoped extraction from that review is wrong.

## Coverage and empty outputs
| Model | Invalid inspected | Not run | Valid empty outputs | Correct empty | Borderline empty |
|---|---:|---:|---:|---:|---:|
| Qwen | 1 | 2 | 10 | 10 | 0 |
| Gemma | 3 | 30 | 14 | 11 | 3 |

Invalid and missing results are never counted as empty or semantically correct. Each model has exactly 71 accounted-for source sentences: correct + incorrect + borderline + invalid + not run.

## Claim-level direction/grounding inspection
| Model | Claims in valid outputs | Supported | Unsupported | Borderline |
|---|---:|---:|---:|---:|
| Qwen | 74 | 41 | 16 | 17 |
| Gemma | 29 | 22 | 6 | 1 |

Eight additional parsed claims belong to Gemma's three invalid cases; they remain marked invalid_case, not added to the valid-output semantic denominator. Qwen's invalid case is a timeout with no parsed claims.

## Clear-error sentences
- **Qwen (16):** T06__04, T06__07, T10__02, T10__03, N04__04, N04__05, N04__10, N06__02, N06__04, N06__07, N07__03, N07__04, N07__05, N07__07, N09__02, N09__04.
- **Gemma (6):** T06__04, T10__02, N04__04, N04__05, N07__03, N07__04.

Shared failures include event-planning stress-free => calm, standalone entry-price => inviting, exhibit praise => inviting, and food/beer praise => inviting. Qwen additionally invents calm from AC or a nice patio, and non-calm from children doing an activity or waiting for staff coordination. The original records and per-claim reasons remain unchanged.

## Traceable files
- [All 142 model/sentence audit rows](full_segment_audit_2026-11-17.csv), including invalid and unattempted combinations.
- [All 111 parsed claims](full_claim_audit_2026-11-17.csv), with support status and reasons.
- [All 71 sentence references](full_audit_reference_2026-11-17.jsonl), with required/optional directions and boundary notes.
- [Machine-readable complete counts and method](full_audit_summary_2026-11-17.json).

Frozen extraction snapshot audited: commit `4f425f6d031d3680dcce25474627f769ea64746f`, `predictions.jsonl`. Original run files and original blank audit templates are preserved. This retrospective audit is not a new model run.

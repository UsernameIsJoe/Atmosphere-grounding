# Stage 1A experiment tranche — November 4, 2026

## Goal and experimental restrictions
Advance three workstreams: (1) valid real-review benchmark framework, (2) controlled improvements to current candidate(s), (3) independently reproducible new candidate inference. Use original reviews only and never fabricate scores or synthetic domain-review tests.

## Step 1: Evaluation framework
Workflow: https://github.com/UsernameIsJoe/Atmosphere-grounding/actions/runs/41913175895
- PASS: extracted 56 source-preserving sentence rows across 20 fixed real reviews and generated a blank annotation packet.
- Schema requires complete aspect, opinion, polarity, atmosphere relevance, provenance, and notes; see Docs/STAGE1A_GOLD_ANNOTATION_PROTOCOL.md.
- The score function refuses to claim precision/recall/F1 on incomplete gold. **No independent annotation has been completed yet**. The benchmark is prepared, not validated.
- Partial reference recovery from 29 previously authored lexical pairs remains diagnostic-only.

## Step 2: AOS-T5 decoding control
Workflow: https://github.com/UsernameIsJoe/Atmosphere-grounding/actions/runs/41913297763
Paired diagnostics: https://github.com/UsernameIsJoe/Atmosphere-grounding/actions/runs/41914064405

Same model checkpoint, same original 20 reviews/56 source sentences, same prompt, deterministic generation, max 250 new tokens.

| Beam width | Relations output | Source-grounded relations | Unparsed sentences | Prior partial pairs recovered |
|---|---:|---:|---:|---:|
| 1 | 57 | 43 | 11 | 13/29 |
| 3 | 59 | 45 | 10 | 13/29 |
| 5 | 58 | 45 | 11 | 13/29 |

Interim decoding decision: keep beam 1 as the simplest configuration. Do **not** infer equal semantic performance from equal lexical recovery.

## Step 3: New architecture / official PyABSA
- Code: scripts/stage1a_pyabsa_official_probe.py
- Workflow: https://github.com/UsernameIsJoe/Atmosphere-grounding/actions/runs/41913712642
- Official PyABSA ASTE extractor with documented `AspectSentimentTripletExtractor(checkpoint="multilingual").predict(sentence)` input.
- An initial import failure arose from 2026 update-checker 1.0.1 incompatibility with PyABSA's metric-visualizer; pinned update-checker 0.18.0 as compatible historical version. Subsequent workflow reached the checkpoint inference step.
- **Completed successfully:** actual model checkpoint loaded and processed 20 reviews / 56 original sentence calls; raw predictions stored as Action artifact (run 41913712642).
- **Raw audit (run 41914692717):** 54 normal responses and 2 internal `list index out of range` errors (the library returned an error dict rather than raising). The raw responses must be inspected; the package swallowed these two errors even with `ignore_error=False`.
- **Diagnostic comparison (run 41914824298):** 84 extracted triplets, 84 contain both aspect/opinion phrases somewhere in original review (phrase containment only), and 22/29 previously authored partial lexical reference pairs recovered. These are not precision, full recall, F1, or semantic-quality metrics.
- **Qualitative warning:** PyABSA generates combinatorial over-linking: in one review sentence it paired `park`, `trees`, and `circulous paths` with `enveloped`, `feel`, `protected`, and `comforted`, leading to 12 output triplets where several pairings are questionable. High diagnostic recovery may reflect high output volume rather than accurate relation extraction.

## Scientific status
- Step 1 infrastructure: COMPLETE. Actual gold labeling: NOT COMPLETE.
- Step 2 decoding sweep: COMPLETE. No convincing accuracy improvement established.
- Step 3 PyABSA: COMPLETE as official-inference/diagnostic study. It is a recall-oriented challenger only; semantic precision not measured.
- No production ABSA model is scientifically locked; GTS-BERT and dependency rules remain comparators.

## Interim Stage 1A selection status
Keep GTS-BERT as neural precision-oriented challenger, spaCy dependency as transparent high-recovery baseline, AOS-T5 as corrected-but-low-recovery generative comparator, and PyABSA/EMC-GCN as high-output challenger requiring false-positive screening. **Do not choose a winner on partial lexical recovery.** The independent full-reference annotation and adjudication remains the bottleneck.

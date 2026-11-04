# Stage 1A schema extraction candidates — 2026-11-04

## Experimental purpose
Compare non-ABSA, pretrained, general information extraction approaches on the *same original urban review source*. Do not treat entity count, relation count, source anchoring, or partial reference recovery as human-validated model precision.

## Official implementations
- GLiNER2.5 `fastino/gliner2.5-base-v1`: official `gliner2.AutoExtractor.from_pretrained`, `extract_entities` and `extract_relations`; source-offset annotations and confidence preserved. Model card https://huggingface.co/fastino/gliner2.5-base-v1.
- NuExtract 2.0 `numind/NuExtract-2.0-2B`: official `AutoModelForVision2Seq` / `AutoProcessor`, `processor.tokenizer.apply_chat_template(... template=...)` with typed JSON field specifications and greedy decoding. Model card https://huggingface.co/numind/NuExtract-2.0-2B.
- Both operate on real user review text; nothing is synthetically generated to simulate reviews. No in-context examples were synthesized.
- The schema is a proposed scientific representation, not a ground-truth label definition. Important task distinction: GLiNER outputs span-anchored graphs while NuExtract outputs schema-filled JSON. Do not compare raw relation counts directly.

## GLiNER2.5 results
- Workflow: https://github.com/UsernameIsJoe/Atmosphere-grounding/actions/runs/41916389316 — success.
- Raw-output inspection: https://github.com/UsernameIsJoe/Atmosphere-grounding/actions/runs/41917070768 — success.
- 20 original reviews, 56 real sentence spans, 112 extracted entities/qualities, 34 candidate relations, zero runtime errors.
- 9 `described_as`, 22 `has_feature`, 3 `induces_experience`.
- Correct-looking examples: `park → charming and cozy`, `park → trees`, `park → paths`, `Torii → unique vibe`.
- Incorrect / questionable: `park → Cambridge` under `has_feature` is a wrong semantic predicate. In the sentence about trees, paths, protection, and comfort, it extracted `protected` and `comforted` as feelings but did **not** link them to the park or its features under `induces_experience`. Thus it avoids PyABSA-style pair explosion on this example but still omits a crucial environmental-experiential relation.
- This single qualitative example is not global proof of high precision. The model was not trained specifically for urban-reviews.

## NuExtract 2.0 2B
- First workflow failed before prediction because transformers' AutoProcessor required torchvision. This is a dependency error, not a quality result. Corrected workflow: https://github.com/UsernameIsJoe/Atmosphere-grounding/actions/runs/41916932170.
- 8 predeclared sentence indices (0,2,5,10,18,24,36,50) from the frozen 56-sentence set for CPU-feasibility pilot, not a balanced or fully scored dataset.
- JSON template asks for `physical_feature`, `description`, `felt_experience` as verbatim strings; no model-side fine-tuning or label leakage.
- Report execution status separately when completed. Never infer predictions from a pending job.

## Next valid comparison
Develop complete independently annotated gold on the same original source, recording spatial features, descriptions, feelings, evidence spans, and directed links; then compare precision, recall, semantic fidelity, and downstream atmosphere-evidence coverage. Only then decide whether to replace ABSA.

# Stage 1A E/T independent local pilot — 50 real reviews

**Date:** 2026-11-11  
**Status:** Implemented local test runner. **No local model inference results or validated accuracy are claimed.**  
**Purpose:** Examine whether two local LLMs reliably find **explicit reported atmosphere (E)** while separately collecting **textual descriptions / indirect hypotheses (T)** for future comparison. This is a test of the *three-channel research idea*, not the previous LLM-panel consensus method.

## Fixed experiment design

- **Source:** original `data/processed/reviews.jsonl`, not fixtures or generated reviews.
- **Selection:** deterministic seed 42; 50 different reviews, one per distinct place first, then sampled additional reviews. Given the current corpus this is designed to span up to 43 places.
- **Processing unit:** existing deterministic segmenter applied to each complete source review. Every model call labels **one target segment**, with only immediately previous and following segments supplied for resolving context. Full reviews are **not fed** to the LLM. Literal source offsets, review/segment IDs and SHA-256 hashes are kept.
- **Local models:** `qwen3:8b` and `gemma3:4b`. These are practical comparison candidates from the prior panel, **not verified best-performing models**.
- **Categories:** initial pilot `calm`, `inviting`, `safe`. Do not treat this as evaluation of all 11 categories.
- **All segments are scored in both tasks**; no keyword gate, no reuse of old labels, no teacher/student training. The models run sequentially for laptop resource safety, but the tasks are *logically and informationally independent*. They never read each other's outputs.

### E — explicit evidence

The E prompt assesses only a reviewer's **explicitly reported** place experience or direct atmosphere characterization. It emits a list of exact source quotes with:
- category, `supports|opposes`, and attribution (`first_person`, `general_report`, `secondhand`, `uncertain`).
- `records: []` where no explicit evidence was identified.
- No categories from merely describing trees, facilities, activities or other indirect correlates.

**This is model-labeled evidence, not independently verified truth.** A source-exact quote proves textual provenance, not that the label or completeness is correct.

### T — independent text description and inference

The T prompt **does not read E's decisions** and does not use explicit feeling statements as inferential premises. It extracts source-quoted descriptions of physical, spatial, activity, social, sensory and access conditions. Each record identifies:
- description kind and whether it is plausibly observable in a still photo;
- optional `calm|inviting|safe` hypothesis, `supports|opposes`, and short reason;
- `category=none, direction=none` where no defensible atmosphere inference follows.

A hypothesis is **not** an emotion report. The visibility field is a text-side conjecture, not an image measurement.

## Local Windows PowerShell instructions

Run from your cloned `Atmosphere-grounding` folder:

```powershell
git pull origin master
ollama pull qwen3:8b
ollama pull gemma3:4b

# Prepare and inspect the SAME 50 reviews / segments for both tasks, no LLM calls:
python scripts/stage1a_dual_channel_50.py --prepare-only

# Small live connectivity/format test: first two segments for each model/task:
python scripts/stage1a_dual_channel_50.py --limit-segments 2

# Resume and finish ALL segments, skipping validated saved work:
python scripts/stage1a_dual_channel_50.py --resume
```

Ollama must be running locally at `http://127.0.0.1:11434`. On initial run **without** the smoke test, run `python scripts/stage1a_dual_channel_50.py` after prepare-only. To retry an interrupted/failed run use `--resume`. The default output path is deliberately fixed; use a **new** `--output` path for changed inputs, models or settings. For offline mechanics tests: `python -m pytest -q tests/test_stage1a_dual_channel_50.py`.

## Saved outputs (private local `reports/` folder)

```text
reports/stage1a_e_t_50_2026-11-11/
  input/
    manifest.json                # source hash, selection, prompt/schema versions
    segments.jsonl               # common segment/context/source IDs
    model_digests.json           # exact local model checkpoint digests
  evidence/
    qwen3_8b/
      annotations.jsonl          # explicit-only results
      raw_responses.jsonl        # all raw calls and mechanical failures
      summary.json
    gemma3_4b/                   # same independent files
  inference/
    qwen3_8b/
      annotations.jsonl          # descriptions and optional hypotheses only
      raw_responses.jsonl
      summary.json
    gemma3_4b/                   # same independent files
```

Each task uses **separate prompts, schemas, inference calls, raw traces, and prediction folders**. No cross-task model input, consensus, merging, or joint scores are generated. Both use common source `review_id` + `segment_id` for comparison *later*.

The runner automatically rejects malformed JSON, inconsistent fields and inexact evidence quotes, then tries once again with the **same prompt**, keeping the failures in the raw trace. An error is **not** converted to an empty-evidence annotation. All valid records are append-saved for resume; output includes incomplete counts. Interrupted runs are recoverable.

## What the experiment can and cannot establish

- **Can measure after output review:** source fidelity, the rate of unusable responses, evidence density, overlap/disagreement between models, possible missed evidence in the original segments, and qualitative differences between E and T.
- **Cannot infer automatically:** semantic accuracy, true recall, perceived place atmosphere, independence of E and T as evidence sources, or valid E–T–I association. Two models can agree and still both be wrong.
- **Needed next:** an independently inspected segment-level audit of a subset **including both predicted positives and predicted empty segments**; compare categories and directions without treating consensus as truth.
- **Ethics/data:** Review source permissions before distributing raw response files or scaling training on Google Places-derived text.

**Reproducibility note:** Earlier scripts (including `stage1a_panel_pilot.py`) are imported solely for their original-source loader and deterministic segmentation, not their prompts, rubrics, labels, or consensus.

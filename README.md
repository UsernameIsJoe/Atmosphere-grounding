> **Runpod first-model capability check (2026-11-13):** [12 complete real reviews × Qwen3:8B / Qwen3.6:27B BF16 / Gemma4:31B BF16, same prompt](Docs/STAGE1A_RUNPOD_FIRSTLOOK_12REVIEWS_2026-11-13.md). The 36-call test evaluates direct vs inferred evidence and calm/inviting/safe interpretation before choosing any segmentation or scoring architecture. **Prepared, not yet run on GPU.** The earlier 30-segment Runpod scripts are retained only as later-method experiments.

> **Executed gate experiment and audit (2026-11-12):** [30 real reviews / 123 source segments — adjective POS vs 3 NLI checkpoints × 3 hypotheses, Qwen/Gemma V2 and separate Gemma recovery](research_audit/stage1a_gate_adj_nli_30_2026-11-12/README.md). **Full findings:** [source audit](research_audit/stage1a_gate_adj_nli_30_2026-11-12/SOURCE_AUDIT.md) · [123-row audit data](research_audit/stage1a_gate_adj_nli_30_2026-11-12/audit_123_segments.csv). Adjective selects 91/123, NLI ≥0.6 selects 31/123, but neither establishes a reliable one-LLM fast path; 79 source-matched same-prompt LLM cases, 51 disagreements. **No E/T taxonomy adopted and no gate approved.**

> **Local E/T pilot (2026-11-11):** [Independent explicit-evidence and text-inference test on 50 segmented real reviews](Docs/STAGE1A_DUAL_CHANNEL_50_2026-11-11.md) uses `qwen3:8b` and `gemma3:4b` with separate prompts, calls and outputs. Run locally; no inference results are claimed yet.

> **Project research direction (2026-11-11):** [Three-Channel Triangle — Text Evidence (E), Text Inference/Description (T), Image Quality (I)](Docs/THREE_CHANNEL_RESEARCH_DIRECTION_2026-11-11.md) is the **current conceptual research hypothesis**. **E–I is the direct target**; E–T and T–I are potential indirect support, to be compared with—not automatically merged into—the direct estimate. This is not implemented or validated. The Stage 1A plan below is a candidate method for E only.

> **Stage 1A design decision (2026-11-11):** [Explicit-atmosphere evidence + recall-expansion research plan](Docs/STAGE1A_RESEARCH_PLAN_2026-11-11.md) is the **current Stage 1A architecture and execution plan**. The prior November 10 panel/NLI design and scripts remain historical experiments, **not the approved default workflow**. The new plan is documentation only, not implemented or validated.

# Atmosphere Grounding — Cambridge Pilot

> **Research design update (2026-11-10):** [Reviewed Sections 3–7: text grounding, visual grounding, association, validation/prediction](Docs/PROJECT_DESIGN_V2_REVIEWED_2026-11-10.md). This is the **current research-stage structure**, not an implemented or validated pipeline. **Stage 1A detailed refinement:** [no-human-label, clause-first, NLI-first method and Stage 2 robustness checks](Docs/STAGE1A_REFINED_DESIGN_2026-11-10.md). The older pilot workflow described below is retained for historical/operational context. Before new model training, resolve data-use permissions and independent reference evaluation.

Weakly supervised pipeline that **grounds urban atmosphere language** (place reviews + lexicon terms such as `inviting`, `safe`, `calm`) in **constructed visual features** from Google Place photos, then stores multimodal evidence as an inspectable knowledge graph.

**Project goal (short):** measure which visual structures co-occur with which words in *our* corpus — not rely on a generic vision–language prior alone. Longer term: from a text passage, report which of our ontology features are more prominent (and the reverse: image/features → keywords grounded in the same data). This is **not** text-to-image generation.

Full goals, stages, and non-goals: [`Docs/PROJECT.txt`](Docs/PROJECT.txt).  
**Architecture & design guide (flow + all decisions):** [`Docs/ARCHITECTURE.txt`](Docs/ARCHITECTURE.txt).  
Handoff / next steps: [`Docs/CONTINUE.txt`](Docs/CONTINUE.txt).

## Stage 1A (2026-11-10) — real-review, three-category pilot

The current taxonomy contains **11 categories** (`configs/lexicon.yaml`), with **calm, inviting, safe** active for the initial Stage 1A pilot. See [the refined research method](Docs/STAGE1A_REFINED_DESIGN_2026-11-10.md), [real-data provenance audit](data/PROVENANCE_STAGE1A_2026-11-10.md), and [archived synthetic fixtures](data/fixtures/README.md).

This runner uses only `data/processed/reviews.jsonl` (214 internally traced Google API-derived reviews / 43 places). The first offline step checks clause offsets without invoking models:

```bash
python scripts/stage1a_panel_pilot.py --prepare-only --max-reviews 12
```

After installing and starting Ollama, pull three distinct families:

```bash
ollama pull qwen3:8b
ollama pull gemma3:4b
ollama pull llama3.1:8b
python scripts/stage1a_panel_pilot.py --max-reviews 12
```

Outputs in `reports/stage1a_panel_pilot/`: source clauses, per-model A/B annotations, full-vote consensus and basic agreement diagnostics. A model run requires local Ollama and may be memory/time intensive. The model tags are initial defaults, not confirmed available on every machine; override with `--models` when needed. This is **not** NLI student fine-tuning and produces **no human-validated accuracy**. See [offline CI tests](.github/workflows/stage1a-panel-pilot-tests.yml).

## What this does

1. **Collect** parks/plazas via Places API (New), cache details + photos under free-tier caps  
2. **Pre-gate** images and comments; **soft-weight** review↔photo match (same place, not same caption)  
3. **Layer B — Visual categories** ontology v1 (DINO / seg / SigLIP / metrics) → **primary image feature data**  
4. **Pass A (LLM)** comment-only → map adj/atmosphere language to lexicons + nouns  
5. **Pass B (LLM)** comment + Layer B feature profile + comment visual add-ons → refined mentions  
6. **Co-occurrence learner** lexicon/adj ↔ image feature data (place-normalized ranks; not LLM-invented links)  
7. **Output** strength per lexicon + ranked supporting features; validate on held-out places  
8. **Graph / inspect** (pilot tooling) — NetworkX graph, browser `view`, CLI `inspect`  

Design lock: [`Docs/DESIGN_LOCK.txt`](Docs/DESIGN_LOCK.txt). Full guide: [`Docs/ARCHITECTURE.txt`](Docs/ARCHITECTURE.txt).

## Two layers + association

| Part | Role |
|------|------|
| **A — Text (Pass A/B)** | LLM extract-only: adj → lexicon umbrellas + nouns; Pass B adds Layer B context |
| **B — Visual ontology** | Measured feature vectors from photos (families + metrics) — primary image side |
| **Learner** | Weighted co-occurrence between text lexicons and image feature data |

See `Docs/PROJECT.txt` for Stage 0 (pilot) → Stage 1 (association maps) → Stage 2 (optional LoRA narrator on *measured* profiles).

## Setup

```bash
cd "/Users/tumenglun/Desktop/Extend study"
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
# Optional GPU/vision weights:
# pip install -e ".[vision]"
cp .env.example .env   # add GOOGLE_MAPS_API_KEY only when doing live collect
```

Ollama (optional for LLM extract): install + `ollama pull llama3.2`.

## Quota rules (live API)

Post–March 2025 Google Maps free usage is **per SKU**, not a pooled $200 credit. Bottlenecks:

| SKU | Assumed free/mo | Pilot hard cap | Soft budget (50%) |
|-----|-----------------|----------------|-------------------|
| Text Search | 5,000 | 20 | 10 |
| Place Details Enterprise (reviews/photos meta) | 1,000 | 60 | 50 |
| Place Photos (media) | 1,000 | 180 | 90 |

Engineering guarantees:

- Disk cache under `data/raw/` — **never** re-fetches if present  
- Ledger `data/quota_ledger.json` hard-stops past soft/hard caps  
- Prefer `--dry-run` or `--use-fixtures` until you are ready to spend quota  

## Commands

```bash
# Offline end-to-end (default; no API spend)
atmosphere run-all --use-fixtures --heuristic

# Live / research path (cached Google data; no re-billing)
atmosphere backup                 # snapshot data/raw → data/backup/google/
atmosphere detect                 # Grounding DINO image objects → objects.jsonl
atmosphere fuse                   # Pass-B LLM: comments + object lists → mentions_fused.jsonl
atmosphere ground                 # SigLIP match + ablation → evidence.jsonl
atmosphere visual-categories      # ontology feature vectors (DINO/seg/SigLIP/metrics)
atmosphere correlate              # place-level comment↔image alignment
atmosphere graph && atmosphere view

# Inspect
atmosphere inspect calm
open data/graph/view.html
```

Pass-A comment-only mentions stay in `mentions.jsonl`. Fusion does not overwrite them.

### Key outputs

| Path | Contents |
|------|----------|
| `data/backup/google/` | Timestamped backups of Google raw cache |
| `data/processed/objects.jsonl` | Image-first detections (Grounding DINO) |
| `data/processed/mentions.jsonl` | Pass-A LLM (comments only) |
| `data/processed/mentions_fused.jsonl` | Pass-B LLM (comments + objects) |
| `data/processed/evidence.jsonl` | Visual grounding / ablation |
| `data/processed/visual_features.jsonl` | Per-image visual-category feature rows |
| `data/processed/place_visual_features.json` | Place-aggregated category features |
| `data/processed/place_correlation.jsonl` | Per-place text↔image correlation |
| `data/graph/view.html` | Browser graph (open this, not GraphML) |

## Docs map

| Doc | Contents |
|-----|----------|
| [`Docs/PROJECT.txt`](Docs/PROJECT.txt) | Goals, non-goals, Layer A/B, research stages |
| [`Docs/CONTINUE.txt`](Docs/CONTINUE.txt) | Handoff / next actions |
| [`Docs/visual_categories/`](Docs/visual_categories/) | Ontology phases 1–4 |
| [`visuals of steps/README.md`](visuals%20of%20steps/README.md) | Pipeline step figures |

## Success bar

A human inspecting Cambridge `atmosphere → noun` chains (`atmosphere inspect …`) should find **locally plausible** links for inviting / safe / calm — not a generic CLIP prior. Next research bar: place-holdout checks that the **visual-category feature space** relates to held-out comments / atmospheres. Expand the remaining lexicon terms or other cities only after this pilot looks right.

Project-level stages and criteria: `Docs/PROJECT.txt`.

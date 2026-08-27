# Atmosphere Grounding — Cambridge Pilot

Weakly supervised pipeline that **grounds urban atmosphere language** (place reviews + lexicon terms such as `inviting`, `safe`, `calm`) in **constructed visual features** from Google Place photos, then stores multimodal evidence as an inspectable knowledge graph.

**Project goal (short):** measure which visual structures co-occur with which words in *our* corpus — not rely on a generic vision–language prior alone. Longer term: from a text passage, report which of our ontology features are more prominent (and the reverse: image/features → keywords grounded in the same data). This is **not** text-to-image generation.

Full goals, stages, and non-goals: [`Docs/PROJECT.txt`](Docs/PROJECT.txt). Handoff / next steps: [`Docs/CONTINUE.txt`](Docs/CONTINUE.txt).

## What this does

1. **Collect** parks/plazas via Places API (New), cache details + photos under free-tier caps  
2. **Extract (LLM Pass A)** lexicon atmospheres + visual nouns from reviews (Ollama, heuristic fallback)  
3. **Detect + Fuse (LLM Pass B)** image objects (Grounding DINO) fused with comments → refined mentions  
4. **Ground** phrases in images (SigLIP), noun boxes, scene vs object vs context ablation  
5. **Visual categories** locked ontology v1 (DINO / seg / SigLIP / metrics) → structured image feature vectors  
6. **Profile / correlate** cross-place recurrence and review↔photo alignment  
7. **Graph** NetworkX multimodal logic graph → GraphML + browser `view` / `inspect` CLI  

Street View is out of scope for this pilot (weaker pairing with place reviews). Ontology families are **not** pre-bound to atmosphere labels; links are discovered from data.

## Two layers

| Layer | Role |
|-------|------|
| **A — LLM text grounding** | Pass A/B turn reviews (+ optional object lists) into atmosphere / phrase / nouns for vision to localize |
| **B — Visual category ontology** | Stable descriptive feature space for images; used for analysis and (later) corpus prominence maps |

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

# Atmosphere Grounding — Cambridge Pilot

Weakly supervised pipeline that grounds curated urban atmosphere categories (`inviting`, `safe`, `calm`) in Google Place **photos + reviews** for Cambridge, MA public/open spaces, then stores multimodal evidence as an inspectable knowledge graph.

## What this does

1. **Collect** parks/plazas via Places API (New), cache details + photos under free-tier caps  
2. **Extract** lexicon atmospheres + visual nouns from reviews (Ollama, heuristic fallback)  
3. **Ground** phrases in images (SigLIP/CLIP), noun boxes (Grounding DINO), scene vs object vs context ablation  
4. **Profile** cross-place recurrence  
5. **Graph** NetworkX multimodal logic graph → GraphML + `inspect` CLI  

Street View is out of scope for this pilot (weaker pairing with place reviews).

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
| `data/processed/place_correlation.jsonl` | Per-place text↔image correlation |
| `data/graph/view.html` | Browser graph (open this, not GraphML) |

## Success bar

A human inspecting Cambridge `atmosphere → noun` chains (`atmosphere inspect …`) should find **locally plausible** links for inviting / safe / calm — not a generic CLIP prior. Expand the remaining 8 lexicon terms or other cities only after this pilot looks right.

# Stage 1A dataset provenance and synthetic-fixture quarantine

**Audit date:** 2026-11-10  
**Scope:** Repository-tracked text data and collection metadata, not an external Google API re-fetch.  
**Decision:** Real API-derived review corpus is the only eligible existing Stage 1A observational input. Synthetic fixtures are **archived in place** for legacy testing only.

## Source classification

| Repository path | Inventory | Status for research |
|---|---|---|
| `data/processed/reviews.jsonl` | **214 JSONL reviews across 43 unique place IDs** | **Eligible as internally verified Google Places API-derived observations**; original external review content not independently re-fetched |
| `data/processed/collect_summary.json` | 43 places / 214 reviews / 128 images; `dry_run: false` | Collection-run metadata corroborating real API pathway |
| `data/processed/images.jsonl` | **128 image metadata rows across 43 place IDs** | Google Places photo metadata; **not a claim the image binaries are in Git** |
| `research_audit/stage1a_final_2026-11-10/source/reviews.jsonl` | Audited 214-review snapshot | Preserve for audit reproducibility; **do not merge as new data or double count** |
| `data/fixtures/reviews.json` | **9 deliberately authored short reviews**, 3 mock place IDs | **ARCHIVED SYNTHETIC — EXCLUDE** |
| `data/fixtures/places_table.json` | 3 mock place rows | **ARCHIVED SYNTHETIC — EXCLUDE** |
| `data/fixtures/places/fixture_*.json` | 3 Places-shaped **mock responses** containing authored review text | **ARCHIVED SYNTHETIC — EXCLUDE** |
| `data/fixtures/images/` | 6 fixture image files | **ARCHIVED TEST IMAGES — EXCLUDE** |
| `data/evaluation/stage1a_absa_real_review_targets_v1.json` | Assistant-authored **partial targets over real review rows** | Source reviews are real-corpus references; the target judgments are **not independent gold**, and must not be treated as such |
| `data/evaluation/stage1a_absa_relation_controls_v1.json` | Control examples for historic ABSA experiments | Diagnostic/control data, **not verified observational reviews** |
| `data/processed/mentions*.jsonl`, `evidence.jsonl`, `atmosphere_profiles/` | Model-derived outputs | **Not source text and not independent labels** |
| `data/graph/` | Derived graph and visualization outputs | Historical model-derived artifacts, **not primary research text data** |

## Verification performed

1. Fetched and parsed the repository-tracked **214** JSONL review records and **128** image-metadata JSONL records.
2. Counted **43 unique review place IDs**; all 214 begin with Google-style `ChIJ`, and all sampled source fields contain text, IDs and `publish_time`.
3. Found **no records** with `fixture_`, `synthetic` or `test_` place identifiers, or exact known authored fixture phrases, in `data/processed/reviews.jsonl`.
4. Checked `configs/cambridge_pilot.yaml`: `collect.dry_run: false`, `collect.use_fixtures: false`. The collector (`src/atmosphere_grounding/collect/pipeline.py`) loads `details["reviews"]` and copies `rev["text"]["text"]` (fallback `originalText.text`) with `place_id`, `review_index`, `rating`, `publish_time`.
5. Confirmed the Places client in `src/atmosphere_grounding/collect/client.py` calls Google's Place Details endpoint when not in fixture/dry-run mode. `data/processed/collect_summary.json` reports the non-dry-run counts.
6. Historical Stage 1A audit also documents the same source and explicitly says raw Google API response caches are **not committed**. Thus **internal provenance is supported, but external Google-source verification has not been performed**.

**Important limitation:** Google-like identifiers and metadata could in principle be forged. The evidence above substantiates the tracked project's collector provenance, but does not cryptographically prove every review was fetched live from Google's servers. Do not describe this as independent Google attestation.

## Rules for new code

- Default Stage 1A input: **only** `data/processed/reviews.jsonl`, keyed by `(place_id, review_index)` with source offsets and hashes; do not accidentally include fixture, derived `mentions` or old audit output.
- Reject `fixture_` records and any `data/fixtures` input in research mode; preserve a separate **legacy test-only fixture mode** for smoke testing.
- Keep derived labels/targets separate from observed original review texts. Never substitute previous model outputs for raw reviews without recording them as student/teacher labels.
- Preserve spatial/place-level splits to prevent multiple reviews or clauses at one place leaking across evaluation partitions.
- Dataset size is a **pilot**, not a sufficient basis to assume balanced coverage of nine categories or adequate spatial holdouts. Check category prevalence and number of independent places before student training.

## Taxonomy note

The request states that the nine target emotions are already defined. The currently checked tracked configuration does **not yet expose one authoritative nine-entry rubric**: `configs/lexicon.yaml` lists **11** terms, and `configs/cambridge_pilot.yaml` activates **three** (`inviting`, `safe`, `calm`). Recent design documents refer to nine but do not enumerate them. **Locate/import the researcher's established nine-category definitions before coding annotation prompts**; don't arbitrarily cut two entries or mistake the 11-entry historical pilot lexicon for the nine-category rubric.

No datasets were deleted, rewritten, or moved. Archived synthetic test fixtures are explicitly identified in `data/fixtures/README.md`, retained in place to preserve older reproduction scripts.

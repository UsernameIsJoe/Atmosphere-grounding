# ARCHIVED — synthetic/offline fixture dataset (not research data)

**Archived status recorded:** 2026-11-10  
**Classification:** Synthetic, authored test fixtures only. These data **must not** be used as Stage 1A training examples, benchmark examples, LLM prompt few-shots, or Stage 2 observational evidence.

The files remain **in this historical fixture directory** for reproducibility and compatibility with the original `--use-fixtures` collector and offline smoke tests. "Archived" here means **quarantined from research datasets**, not removed from the repository or Git history. This is an intentional in-place archive: relocating the files would break older fixture-mode workflows.

Inventory:
- `reviews.json`: **9 authored/synthetic short reviews** linked to fixture place IDs.
- `places_table.json`: **3 synthetic fixture place records**.
- `places/fixture_cambridge_common.json`, `places/fixture_danehy_park.json`, `places/fixture_fresh_pond.json`: **mock Places-like response documents**, including authored review text. Real place names do not make these mocked payloads genuine Google review records.
- `images/`: **6 fixture image files**, not evidence of genuine Google Place Photos API provenance.

**Current research source instead:** `data/processed/reviews.jsonl` (**214 records / 43 place IDs**, verified internal collection provenance); `data/processed/collect_summary.json` reports `dry_run=false`. See `data/PROVENANCE_STAGE1A_2026-11-10.md`.

Safeguard when implementing new Stage 1A: reject `place_id` beginning with `fixture_`, reject any input path under `data/fixtures/`, and require the authoritative real-corpus manifest. No historical tests or scripts have been modified by this archival designation.

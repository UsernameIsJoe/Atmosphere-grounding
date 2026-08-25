================================================================================
INDEX — Visual category ontology documentation
Atmosphere Grounding project
================================================================================

Read in order:

  1. Docs/visual_categories/phase1_top_level.txt
     Top-level categories (12), theory support, citations, non-goals.

  2. Docs/visual_categories/phase2_subtype_families.txt
     Subtype families (~48), supports, counts.

  3. Docs/visual_categories/phase3_extractors.txt
     Extractor tags (dino / seg / siglip / metric) per family.

  4. Docs/visual_categories/phase4_extractor_benchmark.txt
     Pilot-image benchmark of extractors (OK / WEAK / FAIL) + recommendations.

Machine-readable freeze:

  configs/visual_categories_v1.yaml
    (phrases, seg_class_maps, metric_formulas populated from Phase 4)

Pipeline:
  src/atmosphere_grounding/ground/visual_categories.py
  CLI: atmosphere visual-categories
  Outputs: data/processed/visual_features.jsonl, place_visual_features.json

Design invariants:
  - Categories describe images; they do NOT pre-bind to atmosphere lexicon.
  - Image is primary unit; place aggregates images.
  - v1 taxonomy fixed; schema extensible for later versions.

Next work:
  - Full-corpus visual-features run (all pilot images)
  - Place-holdout verification using category feature space vs comments
  - Optional: tune remaining WEAK DINO families; stronger SigLIP checkpoint

================================================================================

================================================================================
INDEX — Visual category ontology documentation
Atmosphere Grounding project
================================================================================

Role in the overall project (see Docs/PROJECT.txt):
  This ontology is LAYER B — a locked descriptive feature space for images.
  It does NOT replace LLM Pass A/B text grounding (LAYER A). It upgrades the
  visual side so atmosphere↔visual links can be studied as structured features
  (Stage 0 holdout → Stage 1 corpus prominence maps).

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
  - Atmosphere links are discovered via the grounding pipeline + later
    association maps — not hand-coded into this ontology.

Next work:
  - Full-corpus visual-features run (all pilot images)
  - Place-holdout verification using category feature space vs comments
  - Optional: tune remaining WEAK DINO families; stronger SigLIP checkpoint

================================================================================

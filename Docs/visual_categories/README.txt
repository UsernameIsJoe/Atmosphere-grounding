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

Machine-readable freeze:

  configs/visual_categories_v1.yaml

Design invariants:
  - Categories describe images; they do NOT pre-bind to atmosphere lexicon.
  - Image is primary unit; place aggregates images.
  - v1 taxonomy fixed; schema extensible for later versions.
  - Phrase lists and metric formulas deferred.

Next work (not done yet):
  - Curate Grounding DINO / SigLIP phrase lists per dino/siglip family
  - Define metric formulas and segmentation class maps
  - Wire extractors into the pipeline
  - Place-holdout verification using category feature space vs comments

================================================================================

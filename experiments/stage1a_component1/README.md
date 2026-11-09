# Stage 1A — ABSA / Component 1 reproducibility index

**Latest code is in version control.** The historical GTS/AOS, PyABSA, GLiNER2.5, NuExtract, matched-audit, JointIE, reconciliation, schema/context tests and local Ollama tests live under `scripts/`; their GitHub Actions configurations live under `.github/workflows/`. The separate run output ZIPs were stored in **GitHub Actions artifacts**, rather than committed to Git by default.

This folder makes code, run IDs, artifact names, experiment descriptions and source links discoverable together.

- [manifest.json](manifest.json): exact tracked scripts, workflow paths, tested run IDs, and artifact names.
- [fetch_artifacts.py](fetch_artifacts.py): reproducibly download previous Actions outputs on your machine (requires GitHub CLI; run IDs and artifact retention still apply).
- [qwen3_8b_summary.json](qwen3_8b_summary.json): the latest local Ollama experiment summary supplied by the researcher, without exposing full original review texts.
- Existing experimental decisions: [Component 1 reconciliation](../../Docs/STAGE1A_COMPONENT1_RECONCILIATION_2026-11-04.md), [model/schema/context experiment](../../Docs/STAGE1A_COMPONENT1_FORMULATION_TEST_2026-11-04.md), [Ollama instructions](../../Docs/STAGE1A_COMPONENT1_OLLAMA_PILOT_2026-11-06.md).

## On your computer

From the repository root:

```powershell
git pull
python experiments/stage1a_component1/fetch_artifacts.py --list
```

To download the latest tracked ABSA reconciliation and formulation comparisons:

```powershell
python experiments/stage1a_component1/fetch_artifacts.py --id component1_reconcile --id component1_formulation_audit
```

For all available historical artifacts, omit the `--id` options. Results go in `reports/stage1a_archive/<experiment_id>/`. Existing files are not overwritten without `--overwrite`. Expired GitHub artifacts are **not** recoverable merely because a run ID is documented. The local Qwen3 JSONL generated on the researcher's laptop also has no GitHub Actions artifact; consult the local `reports/component1_ollama_qwen3_8b/` folder.

**Data handling:** Raw real-world review excerpts or model-generated line-level outputs can contain third-party text; they are intentionally not committed to a public repository automatically. A summary is retained in Git; original raw outputs remain local or within retrievable Actions artifacts.

## Interpretation

- `source_exact`, `quote_match_status=exact_unique`, typed-graph feasibility, and LLM self-verifier `supported` are **technical or model claims**, not independently validated semantic truth.
- Comparison should prioritize coverage of distinct source-grounded observations, relation correctness, attribution, negation, uncertainty, and hallucination.
- Component 1 must remain emotion-agnostic. Component 2 assesses emotion-specific relevance, Component 3 applies entailment/contradiction/neutral NLI. No downstream inference gains are implied by successful extraction tests.

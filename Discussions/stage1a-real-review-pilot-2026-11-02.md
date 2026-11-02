# Stage 1A — First Real-Review Pilot (2026-11-02)

**Scope:** 30 real reviews from 7 locations in the repository (rows 0–34 selected with a mix of direct cues, indirect cues, contradictions, and irrelevant material). Pilot atmospheres: calm, inviting, safe. The existing corpus collection summary reports 43 locations, 214 reviews, 128 image records.

**Important status:** Initial comparison of old extraction outputs against **provisional single-analyst judgments**, NOT verified human consensus. Pretrained NLI, pretrained semantic embedding, and a trained ABSA model have **NOT** been run in this session; no claims about their performance are made. The committed script provides an optional model evaluation path for a machine with dependency/model access.

## Evidence from actual reviews

- Basketball court descriptions received **safe** despite offering little evidence of physical safety.
- A negative review referring to people sleeping in the park was tagged **calm**, a poor inference of atmosphere from the word "sleeping."
- A restaurant meal/service complaint occurs under a park place_id. This shows a source-quality/off-topic problem **before** emotion inference.
- "A peaceful park right by the river" directly supports **calm**.
- "A steady stream of loud sirens" provides evidence **against calm** without explicitly saying "not calm."
- A review discussing slippery surfaces and risk of head injuries provides evidence **against safe**, which a positive-label-only extraction misses.
- The fixed nine-category target differs from the repository's currently listed **11** lexicon categories; this pilot intentionally uses only the three formerly active atmospheres.

## Preliminary legacy extraction score

Compare `data/processed/mentions.jsonl` against provisional labels on 30 sampled review rows, with three labels (S=support, C=contradict, U=insufficient/unknown) and X=off-topic. Existing extraction only exposes positive mentions; absence is treated as no positive prediction (NOT as a negative emotion).

| Atmosphere | Provisional support / contradict / unknown / off-topic | True positive | False positive (including unknown/contradict) | False negative | Precision | Recall |
|---|---|---:|---:|---:|---:|---:|
| Calm | 7 / 4 / 18 / 1 | 6 | 4 | 1 | 60.0% | 85.7% |
| Inviting | 9 / 8 / 12 / 1 | 3 | 0 | 6 | 100.0% | 33.3% |
| Safe | 3 / 3 / 23 / 1 | 2 | 10 | 1 | 16.7% | 66.7% |

Counts exclude the one off-topic review in each emotion's evaluation. Provisional review interpretation is disputable, especially inferred safety; compare multiple annotators before relying on these values. Sampling is deliberately diagnostic, not representative.

**Interpretation:** The old system is especially prone to unsupported *safe* mentions and misses much of the *inviting* evidence. This supports testing contextual evidence assessment, **not** a claim that NLI is already superior.

## Reproducible artifacts

- `scripts/stage1a_text_pilot.py` loads repo reviews and existing mention outputs, uses the 30 selected source rows and provisional annotations, writes case-level results and a summary.
- `python scripts/stage1a_text_pilot.py --mode baseline`: no pretrained models, performs legacy comparison and a **lexical aspect-indicator sanity check** (this is **not** trained ABSA).
- `pip install transformers torch sentence-transformers` followed by `python scripts/stage1a_text_pilot.py --mode full`: attempts **real pretrained BART-large-MNLI** for entailment/contradiction/neutral and **all-MiniLM-L6-v2** sentence embeddings. Requires model downloads, model-compatible runtime, and preferably adequate compute. This path has **not been executed** here.

## Next controlled experiment

1. Manually audit a stratified 20–30 review sample with at least two raters, noting location attribution and evidence spans.
2. Run pretrained NLI **directly on review–hypothesis pairs** with per-category, theory-grounded hypotheses; inspect predictions, not just aggregate metrics.
3. Test an aspect-extraction-first approach; distinguish a **real ABSA model** from the lexical proxy.
4. Evaluate embedding similarity as an auxiliary retrieval/baseline signal rather than assuming similarity = evidence.
5. Compare precision/recall across **support, contradict, insufficient evidence**, as well as handling off-topic reviews. Check wording sensitivity of NLI hypotheses.
6. Select the method only after results; do not yet train the cross-modal learner.

This report updates **research evidence only**, not the operational pipeline or design lock.

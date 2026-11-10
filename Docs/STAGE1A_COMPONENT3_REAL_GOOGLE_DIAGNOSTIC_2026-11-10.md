# Component 3 validity test — original Google Places review sentences (2026-11-10)

## Question
Does a standard three-way NLI checkpoint treat explicit place experiences, atmosphere descriptions, and indirect environmental indicators differently? In particular, is `neutral` on a factually related physical observation an expected distinction between *relevance* and *entailment*, rather than a failure of Component 2?

## Provenance requirement (no synthetic review text)
The input to NLI is exactly the `text` field of `data/processed/reviews.jsonl` sliced into exact contiguous sentences. The repository's Places API collector explicitly reads `rev['text']['text']` or `rev['originalText']['text']` from Google's Place Details `reviews` field, saves `place_id`, `review_index`, `rating`, `publish_time`, and the original text. `data/processed/collect_summary.json` reports **43 places, 214 reviews, `dry_run=false`**. The experiment validates counts, dry-run status, place IDs, timestamps, and original sentence offsets. It does **not** read or use `data/fixtures/reviews.json` or any authored diagnostic sentences. The raw API response caches are not committed, so source provenance is established from this repository's collection pipeline and retained metadata; external original-review verification is not claimed.

## Protocol
- Script: `scripts/stage1a_component3_real_google_diagnostic.py`.
- Workflow: `.github/workflows/stage1a-component3-real-google.yml`.
- Sample: up to ten source sentences from each of four heuristic lexical pools — reported place experience, explicit atmosphere description, environmental indicator, and general/unrelated control. Candidate pools are **not expert judgments**. Sample across distinct Google place IDs using deterministic round-robin order. This is an interpretable diagnostic, not an unbiased population estimate.
- Per real sentence, infer BART-MNLI `facebook/bart-large-mnli` with fixed hypothesis sentences: (1) direct atmosphere or perceived physical safety hypothesis, reused from previous M2c and Component 3 tests; (2) fixed metalinguistic relevance hypothesis, also reused from M2c. Each of calm, inviting, safe gets one of each. All predictions report native three-way probabilities, label and truncation flag. The only invented text is the **researcher-authored NLI hypotheses**; no invented review or premise.
- No generated LLM paraphrases are used as premises. Both hypothesis modes use identical original review sentences.
- Preserve per-case source, full NLI outputs, original review hash, Google place ID, row index, and character offsets.
- No reference labels, thus no accuracy, no calibration, no claims of inference validity based on counts alone. Human inspection of cases is required. Disagreement between relevance and directional NLI is a diagnostic signal, not itself a defect.

## Interpretation rubric for inspection
1. Direct report e.g. visitor explicitly feeling comfortable or protected: **plausibility** of directional entailment of relevant hypothesis; contradictions and double meaning need human reading.
2. Atmosphere adjective e.g. peaceful, quiet, cozy: does entailment follow from words, or misgeneralize?
3. Indirect observation e.g. lights, police, shade, crowd, access: compare source-based evidential relevance to **unsupported certainty** in the direct label; never infer objective visitor safety from an unlabeled NLI score.
4. Controls: monitor indiscriminate relevance/entailment on descriptions with no explicit emotion connection.
5. Check negation/hedging and provenance offsets case-by-case.
6. Decide whether an evidence-conditioned NLI hypothesis is adequate, or whether a distinct evidence-to-hypothesis reasoning component is needed; collect human reference judgments before accuracy evaluation.

## Output
A successful workflow uploads a downloadable artifact `stage1a-component3-real-google-diagnostic`, containing `results.jsonl`, `summary.json`, and `source_audit.json`. The full sample is versioned by review data SHA-256 and model checkpoint name. If workflow runs fail, inspect GitHub Actions job logs and fix the runner before interpreting results.

The earlier 12-sentence Component 2 v3 A/B/C test is an independent diagnostic: it evaluates selection effects, whereas this study keeps whole original sentence premises identical and changes only the hypothesis type.

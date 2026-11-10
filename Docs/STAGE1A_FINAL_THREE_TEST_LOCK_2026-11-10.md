# Final Stage 1A three-test lock protocol — 2026-11-10

**Researcher's constraint:** EXACTLY THREE user-operated tests and three complete report files. No fourth diagnostic, no new checkpoint search, no synthetic review premises, no output-driven prompt revisions after seeing the first report. Corrections may be made to failing execution plumbing before a test starts, but cannot rewrite the sample or retrospectively adjust the outcome. Rerunning the same interrupted script with its checkpoint is recovery, not a new method or test.

## Past results: what is and is not established
The earlier main Qwen3 Component 1/2 trials and A/B/C NLI integration used the real processed review corpus. HOWEVER earlier AOS/ABSA/M2c relevance experiments contained explicitly authored **synthetic diagnostic cases** (e.g. `SYNTHETIC` in `scripts/stage1a_relation_pilot.py`, `CASES` in `scripts/stage1a_m2c_relevance_gate.py`). Those demonstrations must **not** be cited as real-review accuracy. Previous model agreement and distribution summaries also lacked independent human correctness labels. Correct sample provenance alone does not confer validity.

## Precommitted inputs
- Data source: `data/processed/reviews.jsonl`, written by the Google Places API `src/atmosphere_grounding/collect/pipeline.py`, verified against `collect_summary.json` (214 reviews, 43 places, `dry_run=false`), Place IDs, timestamps, exact sentence offsets and content hashes. Raw API payloads have not been independently verified; provenance is from collection code and stored API-derived metadata.
- **18 fixed source sentences, all from different real review records and different places**. Select deterministically from the dataset before model inference: 6 per category based on *sampling-only* text patterns (reported-emotion words, physical/social-indicator words, other controls). Heuristic grouping is **not** human ground truth or a claim about actual emotion relevance.
- All 18 source rows are excluded from the original 20-review Component 1 pilot and the last 40-sentence Google NLI diagnostic. This protects against reusing earlier hand-inspected samples; not a statistical random sample.
- Same three pilot emotions: calm, inviting, safe. No unsourced move to nine.
- Local Qwen3 8B, structured JSON, `temperature=0`, `think=false`, no new model; existing extraction prompt, verification prompt and Component 2 v3 prompt retained. The verifier is the **same model**, hence dependent and fallible.
- Frozen `facebook/bart-large-mnli`, same previously used original atmosphere hypotheses and metalinguistic relevance hypotheses. Distinguish entailment vs contradiction vs neutral.

## Run sequence, one command per test

PowerShell first setup once:
```powershell
cd "$HOME\Desktop\Atmosphere-grounding"
git pull
python -m pip install torch transformers
```

**TEST 1: provenance and extracted-claim fidelity.**
```powershell
python scripts/stage1a_final_three_tests.py --test 1
```
Output: `reports/stage1a_final_three_tests/test1.json`.

Runner first validates and SHA-locks the Google review corpus, source record IDs and text offsets, detects repeated reviews and refuses the fixture corpus. It then extracts all 18 real excerpts using Qwen3 and runs the previously frozen second-pass check. All claims, original excerpts, quote offsets, and rejected claims are included. **Interpretation:** automatic exact quotation checks measure provenance, not paraphrase fidelity or extraction recall. Manually inspect every resulting case for omissions, invented relations, missing negation or hedging, and fabricated causality.

**TEST 2: place eligibility and relevance of the identical frozen claims.**
```powershell
python scripts/stage1a_final_three_tests.py --test 2
```
Output: `reports/stage1a_final_three_tests/test2.json`.

Requires complete SHA-matching Test 1. Calls the existing Component 2 v3 contract on those exact held-out claims and copies the full literal original text alongside raw classifications, evidence type, applicability for each pilot emotion, mechanical inconsistency flags and model routing. Human adjudication distinguishes invalid literal quotes, unexplained relevance to all emotions, false source exclusion, missed counterevidence, and context confusion. **Researcher policy:** source-grounded patrol/safety observations may count as direct evidence in this project; the v3's direct-vs-environmental type warning is advisory, not automatically a semantic mistake. Source veracity is separate from that policy.

**TEST 3: NLI inferential integrity on exactly the same original comments.**
```powershell
python scripts/stage1a_final_three_tests.py --test 3
```
Output: `reports/stage1a_final_three_tests/test3.json`.

Requires complete SHA-matching Tests 1 and 2. Tests BART three-way outputs on **the exact original sentence**, and on literal quotes selected by Component 2, using same frozen emotion hypotheses. Also tests BART's evidence-*relevance* hypothesis on that same original sentence. Records native probabilities; does not use any model-written text as NLI premise. Preserves conflicting claims, flagged candidates, nonselected original source, and 'no selected evidence' (which is neither neutral nor absence of emotion). This supports empirical examination of whether NLI distinguishes explicit vs indirect evidence, unjustified entailment, missed counterevidence, and sensitivity to shorter quoted premises. It does NOT establish model accuracy without independently reviewed labels.

## Precommitted lock conditions

**Technical integrity (non-negotiable):** all three scripts complete all 18 cases; same locked source manifest hash; each source quote exactly matches its review; all potential truncations rejected; all 18 original sentences retained; no synthetic review input; no invented/default labels for unselected cases; no unreported inference errors.

**Scientific validity (requires inspecting every actual source example):**
- **Test 1:** Source-faithful claims, correct attribution of visitor experiences and source-specific negation/causality. Independently mark every material omission or unsupported claim. Same-model verification is *not* the adjudicator.
- **Test 2:** Place-relatedness and emotion relevance make defensible, source-based distinctions without using generic praise as evidence for every emotion. Preserve potential negative/contradictory evidence; disagreements are reported, not overwritten.
- **Test 3:** Interpret each originally neutral/contradictory/entailed outcome against the text; do not call agreement with A accuracy. Separate whether a physical indicator is relevant from whether it logically entails the atmosphere hypothesis. Do not treat a softmax number as a measured atmosphere intensity.

**Decision after the three files:** Lock either (a) a qualified, human-audited candidate pipeline, (b) a degraded non-filtering source+quote pipeline with Component 2 marked advisory / NLI marked exploratory, or (c) a failed inference pipeline where emotion claims are not supported. No more prompt tuning or tests as part of this three-chance decision. **No claim of population-level accuracy is permitted without independent human gold, even if all technical checks pass.**

## Code and preflight
Script: `scripts/stage1a_final_three_tests.py`.
Source-integrity workflow: `.github/workflows/stage1a-final-three-preflight.yml`. CI only compiles and checks source selection and provenance; it does **not** perform any of the three model experiments, so it does not consume the user's 3-test budget.

# Controlled gate pilot — adjective POS vs 3 NLI checkpoints × 3 hypotheses

**Date:** 2026-11-12  
**Status:** Local executable experiment, not a completed inference result.  
**Question:** Can an inexpensive gate identify segments that need only one LLM judgment, without substantially increasing error?

This test deliberately **does not use or lock an E/T taxonomy**. It tests *routing difficulty*, not a final model for place emotions.

## Experimental setup

- **30 actual reviews**, selected with seed 42: one review from each of 30 different places, sampled from the original `data/processed/reviews.jsonl`; no synthetic reviews or model-derived training labels.
- **Original source segments**, with complete source offsets and full-review context stored.
- **POS gate:** spaCy English tagger detects any adjective (not a curated emotional vocabulary).
- **Triple NLI:** the three previously screened checkpoints, each run over **three paraphrased, category-agnostic hypotheses**. Output all 9 entailment probabilities and native label distributions; do not confuse entailment with calibrated human correctness:
  - `facebook/bart-large-mnli`
  - `MoritzLaurer/deberta-v3-large-zeroshot-v2.0`
  - `MoritzLaurer/ModernBERT-large-zeroshot-v2.0`
- **Same fresh LLM task on all segments:** `qwen3:8b` and `gemma3:4b`, both seeing the target segment **and the full original review** for interpretation. Both answer `calm`, `inviting`, `safe` with `supports / opposes / mixed / none / uncertain`, precise quotes and scope. No E/T claims or gate scores are shown to the LLM.
- **Post-hoc routing simulation:** compare adjective presence and NLI median thresholds (0.4 / 0.6 / 0.8), alongside adjective-OR-NLI and adjective-AND-NLI conditions. Thresholds are diagnostic guesses, **not optimized**.
- **Human audit queue:** compile disputed NLI/adjective, high NLI paraphrase sensitivity, LLM disagreements, and some easy agreement cases, **including the full reviews**. Accuracy will be audited against original text rather than assuming Qwen–Gemma consensus is truth.

**Why give both LLMs the full review?** To avoid confounding the routing comparison with different prompt/context setups. Later experiments can ask whether segment-only prompts save tokens without degrading comprehension.

**Why three checkpoints × three hypotheses?** That exposes both checkpoint variation and hypothesis-wording sensitivity; using different hypotheses with only different models would confound the two. Models are loaded **sequentially** to control laptop memory; each performs three paired NLI evaluations per segment. The hypotheses are predeclared in the script. This is not three independent LLM emotion graders.

**Prior caution:** Earlier repo tests of BART with meta-relevance hypotheses performed poorly in several explicit cases; this study tests that risk against both adjective routing and human judgments, not an assumed improvement.

## Windows PowerShell — from your cloned repository

```powershell
git pull origin master

# Only if these libraries/models are not already installed:
python -m pip install -U torch transformers sentencepiece spacy
python -m spacy download en_core_web_sm
ollama pull qwen3:8b
ollama pull gemma3:4b

# Inspect input and source sample; no model calls:
python scripts/stage1a_gate_adj_nli_30.py --stage prepare

# Run adjective gate (fast):
python scripts/stage1a_gate_adj_nli_30.py --stage adj

# Run 3 checkpoints × 3 hypotheses sequentially (first time downloads checkpoints):
python scripts/stage1a_gate_adj_nli_30.py --stage nli

# Run the two LLMs on ALL segments, independent of gate results:
python scripts/stage1a_gate_adj_nli_30.py --stage llm

# Join the results and produce comparison + human audit cases:
python scripts/stage1a_gate_adj_nli_30.py --stage report
```

Alternatively, once installed, `python scripts/stage1a_gate_adj_nli_30.py` runs all stages in order. Successful results are saved after each segment, and rerunning the same command resumes incomplete work. `--limit-segments 2` allows a small end-to-end live smoke test; omit it for the full run. Change `--output` to a fresh directory if the source corpus, prompts or sampled parameters change.

**Memory/time:** Three *large* NLI checkpoints may require several GB of disk and substantial CPU time, even though they run one at a time. The first run downloads weights from Hugging Face. PyTorch will use CUDA if available. **This cost must be counted** when evaluating whether NLI is worth using as a gate. The POS gate is far cheaper.

## Results to send back

Compress and upload:

`reports/stage1a_gate_adj_nli_30_2026-11-12`

The folder will include:

- `input/manifest.json`, `input/segments.jsonl` — frozen source review/segments
- `gates/pos.jsonl` — adjective details and offsets
- `gates/nli_{bart,deberta,modernbert}.jsonl` — NLI raw distributions for all three hypotheses
- `llm/qwen3_8b/` and `llm/gemma3_4b/` — predictions, raw traces and any errors
- `comparison/segment_gate_comparison.csv`, `summary.json`, `human_audit_blind.csv`

We'll then calculate **human-audited routing errors** (especially easy candidates mistakenly sent to a single LLM), compare predictive value of POS vs NLI, and add **actual measured processing time** for gate and LLM calls. A lower model-disagreement rate alone is not sufficient evidence of correctness.

All existing E/T experiments and files remain unchanged.


## Terminal progress bars (2026-11-12 update)

The runner now shows a live progress bar with percentage and completed/total segment counts for **spaCy adjective tagging**, **each of the three NLI checkpoints**, and **each Ollama model**. Bars reflect results already saved when a stage is resumed, and display the number of newly logged failures for each LLM. No new packages are required for the bars.

Update your checkout before the next run:

```powershell
git pull origin master
python scripts/stage1a_gate_adj_nli_30.py
```

If the script is already running, stop it with Ctrl+C **only when convenient**; the updated bars take effect when you restart the Python process. Already saved per-segment outputs remain reusable, and the prompts, data and experiment manifest are unchanged.


## Quotation-verification diagnosis (2026-11-12 patch)

The original progress output could misleadingly flag every category, including a **none** verdict that does not require any evidence quotation. The validator now distinguishes:

- **none**: no supporting quote required, any unnecessary model-supplied quote is logged separately.
- **uncertain**: quote optional; malformed optional quote does not invalidate the absence of a conclusion.
- **supports / opposes / mixed**: source quote must exactly match the target segment to be marked **verified**; missing and inexact quotes remain flagged and are NOT silently rewritten.

Existing saved model answers are **not deleted, rewritten, or assumed correct**. The report recomputes quote statuses from the original model strings rather than trusting older annotations.

**Run this before continuing inference if repeated warnings appear:**

```powershell
git pull origin master
python scripts/stage1a_gate_adj_nli_30.py --stage diagnose
```

It prints `DIAGNOSE` records for each model showing the actual distribution of verdicts, whether quotations match, and how many unnecessary quotes accompanied `none` verdicts. It also prints up to five `UNSUPPORTED_VERDICT_QUOTE` and `UNNECESSARY_NONE_QUOTE` examples with the target segment. **No NLI/Ollama model is loaded and no results are overwritten.**

After inspecting diagnostic results, normal inference can resume with `--stage llm`. If there are many unsupported nonempty verdicts, pause and inspect raw model outputs before deciding to revise the prompt; changing the prompt would require versioning/re-evaluating prior verdicts, not just hiding the warnings.


## LLM V2 corrective run — target-source leakage (2026-11-12)

A local Qwen diagnostic on 39 existing segments found 117 category judgments, of which 59 were supports/opposes. Only 33 of those quotations matched the exact target; 26 did not. These included (a) extra quote delimiters around a correctly copied substring and (b) **substantive context leakage**, e.g. target "My husband and I got eloped here." receiving emotion claims quoted from later sentences. There were also unnecessary quotes on 44 of 58 \`none\` decisions. A mere warning-suppression fix would not produce scientifically usable annotations.

**V2 is a new LLM run, not a patch to the prior verdicts.**

- The original LLM output remains at \`reports/stage1a_gate_adj_nli_30_2026-11-12/llm/\`.
- V2 is written separately to \`reports/stage1a_gate_adj_nli_30_2026-11-12/llm_v2/\`, with its own \`protocol_v2.json\`, raw attempts, valid judgments, and failures.
- Already completed **POS and NLI outputs are reused** from the existing \`gates/\` directory. **Do not rerun them.**
- V2 permits a mechanical repair for enclosing quotation marks **only if the remaining characters exactly match the target**. The raw quote is preserved. Paraphrases and text appearing only elsewhere in the review are not accepted as target evidence.
- A positive/negative/mixed verdict without a verifiable literal target quote triggers a context-aware retry and, after at most three attempts, a logged failure. Three consecutive failed segments stop the run to avoid wasting more inference.
- Both LLMs use the exact same V2 prompt: full original review is context for reference resolution **only**, not another source from which to extract evidence for the target.
- \`--stage report\` defaults to V2 and writes \`comparison_v2/\`; V1 comparisons remain under \`comparison/\`. Neither is treated as human ground truth.
- This fixes **data provenance**, but does not guarantee accurate semantics. Even an exact quote may be used to justify the wrong emotion; the audit must still assess the verdict.

**On Windows PowerShell, run:**

```powershell
# Stop the old runner before changing versions
git pull origin master

# Smoke-test the first 3 source segments under new protocol:
python scripts/stage1a_gate_adj_nli_30.py --stage llm --limit-segments 3

# If these pass, continue to the full 123-segment controlled V2 LLM run:
python scripts/stage1a_gate_adj_nli_30.py --stage llm

# Review source-faithfulness diagnostics and gate comparisons:
python scripts/stage1a_gate_adj_nli_30.py --stage diagnose
python scripts/stage1a_gate_adj_nli_30.py --stage report

# Optional: to inspect OLD, preserved V1 predictions:
python scripts/stage1a_gate_adj_nli_30.py --stage diagnose --llm-version v1
```

Please upload **both `llm_v2` and `comparison_v2`** alongside the existing gate scores when the run completes. V2 changes the task prompt and verification, so do not mix old and new LLM judgments into an apparent single 123-segment sample.


## Gemma model errors: case-only mismatches versus context leakage

In a local V2 run, Qwen completed; Gemma stopped after three segment failures belonging to the same long review (review key `39100290de48b1ca3cc9`). The reported failures had different causes:

- `It was completely dark.` vs target `...it was completely dark.`: source text exists except for initial capitalization. A narrowly defined case-only matching rule can recover the **actual** target substring, preserving the model's raw quote.
- `completely unclean, with tissues all over the place` vs target `Although the flush was operative, the hand washing station was not.`: source appears elsewhere in full review, not in target. This remains a genuine *context leakage* failure, not recovered or silently converted to a valid verdict.
- `It was clear that it had not been cleaned...` vs target starting `It was seeming that nobody had the responsibility...`: may contain a case-only match later in the target, but this must be checked against the complete segment; if absent it remains invalid.

**Post-run validator patch:** allow only case-insensitive *character-identical* quotations, with the exact source characters and offsets restored from the target and the raw model quote retained. This is labeled `case_only`, not a semantic/fuzzy rewrite. V2's model prompt and original gate scores are unchanged; this is a documented change to the output validation procedure. Reports recompute and count case-only repairs.

**Execution safeguard patch:** three failed segments inside one long review no longer halt all 123 segments. The run now stops only if failures arise in **three different reviews consecutively** without any successful segment in between. Rejected responses are still logged as failures and excluded from valid LLM rows.

The model verdict `calm=opposes` for a dirty or dark bathroom is **not automatically accepted as semantically correct**, even if the exact source quote is recovered. Audit whether it is genuinely related to calmness, rather than merely to negative conditions.

Resume without rerunning Qwen, adjective detection, or NLI:

```powershell
git pull origin master
python scripts/stage1a_gate_adj_nli_30.py --stage llm
```

Saved successful Gemma judgments are reused. Rejected segments are retried, and newly accepted case-only matches remain identifiable in `quote_raw`, `quote_normalization`, and `quote_offsets` fields. Only completed source-grounded judgments enter comparisons.

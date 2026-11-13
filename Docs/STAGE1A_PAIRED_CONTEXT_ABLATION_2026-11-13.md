# Stage 1A: paired segment-versus-context capability ablation (2026-11-13)

**Status: runner implemented; NO new GPU inference performed.** Keep the first 12-whole-review benchmark and its provisional blind audit separate. Do not merge them into this dataset's scores.

## The research question

Do Qwen3.6 27B BF16 and Gemma4 31B BF16 reliably interpret a **target segment** better when they see the original complete review alongside it? Does full-review context resolve scope, negation, and referents, or cause **evidence leakage** from non-target sentences?

A secondary question is whether a model improves when emotion scoring is handled independently of evidence extraction instead of folding extraction+scoring into one response. This runner preserves the earlier independent two-task protocol, but **does not isolate a joint-vs-split effect**; that would require a separate matched joint-response arm.

## Exactly what is held constant

- Frozen source: `research_audit/stage1a_gate_adj_nli_30_2026-11-12/audit_123_segments.csv`.
- Use the exact 30 previously selected segment indices: 10 D (direct-characterization screen), 10 I (indirect scene screen), 5 G (generic praise), 5 X (irrelevant), with **the same target segment in both input conditions**. The D/I/G/X screening codes are NOT gold labels.
- The 10 originally frozen context-stress indices are a **paired pilot subset**, not different examples: 9, 10, 24, 26, 27, 32, 53, 59, 74, 87.
- Primary models: `qwen3.6:27b-bf16` and `gemma4:31b-it-bf16`, using the precise already installed Ollama digests where possible. Optional same-prompt `qwen3:8b` baseline is supported; the blind A/B report compares the two larger models.
- Identical instructions, decoding, schemas, seeds, and target text for each input-mode pair; no prompt tuning after observing results.
- Input condition **segment**: target text only.
- Input condition **context**: same target text + complete original review, explicitly **for disambiguating context only**. Only the target may contribute evidence, judgments, or exact quotes. The model may misuse context; that is a measurable failure.
- Additional **repeat** control on the SAME 10 frozen stress targets: target appears twice, with no other review text. This controls for the target being repeated when supplied in the full-review condition. It must not be interpreted as a new independent segment or review.
- Independent task **evidence**: identify relevant claims with verbatim quotations; classify each `direct`, `inference`, or `both`, and give referent and explanation. No emotion score.
- Independent task **score**: `calm`, `inviting`, `safe` each gets **two independently reasoned channels** (direct and inferred), verdict supports/opposes/mixed/none/uncertain, signed ordinal textual support -2..+2, and justification. This is **not** a probability or an observed ground-truth emotional intensity.
- Both tasks operate on the *original review text*, not on another model's extraction. That avoids cascading extraction mistakes in this controlled comparison.

## Size and sequence

- First perform the frozen 10-segment pilot on each of two models, **three** conditions (segment/context/repeat) and two tasks: **120 responses**. Check valid JSON, complete GPU residency, and leaks. No tuning based on model outputs.
- Then complete the remaining 20 for segment/context only, giving **280 primary responses total** (30 x 2 x 2 x 2, plus 10 x 2 x 2 repetition controls). The runner resumes successful pilot records without duplicate inference.
- Optional 8B baseline: **+60 pilot** / **+140 total** under the exact same conditions. This is useful to estimate whether context effects differ by model size; don't compare it with the earlier differently prompted 12-review run as if it were a matched experiment.
- Each model is processed sequentially on one A100 80GB. Verify `ollama ps` shows full GPU residency, particularly for BF16 models. Stop the Pod when inference is complete, but confirm volume charges and restart availability.

## What to evaluate

1. **Paired context benefit:** whether providing the full review improves the *same segment* under the same model/task. Compare a case-by-case delta, not the two conditions' raw averages alone. On the 10 frozen stress cases, compare context against the **repetition-only control** to separate new context from target duplication.
2. **Leakage:** is a model quote absent from the target but present elsewhere in the review? The runner records a `quoted_only_in_full_review` diagnostic. Narrative-based leakage needs manual audit even if no out-of-segment quote appears.
3. **Direct-vs-inference and scope fidelity:** whether direct atmosphere assertions are distinguished from observations supporting weak hypotheses, and people/event/animal context from place-wide judgments.
4. **False-positive restraint:** especially G and X segments, restroom darkness, traffic sound, generic praise, and unsupported physical security claims.
5. **Emotion agreement on direct/inference channels:** compare against a separate gold-first annotation packet; ambiguous examples may remain uncertain rather than forced.
6. **Completeness, hallucinations, response-format errors, and cost:** report missing relevant claims and invented claims separately; include errors in denominator, time, tokens, and full-GPU loading checks.
7. **Statistical caution:** multiple segments may share a source review and three emotion categories are correlated. Report review-clustered and case-level results. This purposive 30-segment sample does not support population claims.

**Gold-first:** Run `--stage report` once before examining outputs to create `01_gold_first_BLANK.csv`, then freeze its independent human/AI-assisted annotation with researcher review of ambiguity. The script preserves this file. Never use archived provisional D/I/G/X or vague original labels as gold. Keep the blinding key private until blind comparison is frozen.

## Commands (Mac; Pod must be running and private SSH tunnel connected)

Pull code (skip if already up to date):

```bash
cd ~/Atmosphere-grounding
git pull --ff-only origin master
```

With the Pod running and Ollama reachable at local tunnel port 11435, check installed models:

```bash
python3 scripts/stage1a_runpod_paired_context_ablation_2026_11_13.py --stage check --base http://127.0.0.1:11435
```

Prepare the blank reference **without the Pod**:

```bash
python3 scripts/stage1a_runpod_paired_context_ablation_2026_11_13.py --stage report
```

Run the 10 frozen context-stress cases in all THREE modes for both tasks:

```bash
for model in qwen3.6:27b-bf16 gemma4:31b-it-bf16; do
  for mode in segment context repeat; do
    for task in evidence score; do
      python3 scripts/stage1a_runpod_paired_context_ablation_2026_11_13.py \
        --stage run --base http://127.0.0.1:11435 \
        --model "$model" --mode "$mode" --task "$task" --pilot-context-10
    done
  done
done
```

When pilot passes, finish the 30-case segment/context paired run (without the pilot flag); the 10 repeat controls are already complete:

```bash
for model in qwen3.6:27b-bf16 gemma4:31b-it-bf16; do
  for mode in segment context; do
    for task in evidence score; do
      python3 scripts/stage1a_runpod_paired_context_ablation_2026_11_13.py \
        --stage run --base http://127.0.0.1:11435 \
        --model "$model" --mode "$mode" --task "$task"
    done
  done
done
```

An optional 8B baseline uses the same two loops replacing the model list with `qwen3:8b`. Be aware the baseline is **Q4**, while the larger models are **BF16**.

Finally, generate blind A/B comparisons:

```bash
python3 scripts/stage1a_runpod_paired_context_ablation_2026_11_13.py --stage report
```

Inspect `reports/stage1a_paired_context_ablation_2026-11-13/`; **do not unblind** until reference and blinded semantic judgments are frozen. Do not perform a new GPU run just to make the report; reports are computed locally.

## Do we need a >31B model?

**Not yet as the main variable.** First find out whether context improves the two strong models on the SAME segment, whether evidence extraction and emotion scoring fail for different reasons, and where they fail by referent/scope. Add one pre-frozen `gpt-oss:120b` MXFP4 model as a **separate 10-case exploratory ceiling test** only if capacity/time make sense and the paired experiment leaves a stubborn capability failure. It has roughly a 65 GB download and is built to fit a single 80GB GPU, but it is a *different architecture and precision*, not a clean model-size-only ablation. It is NOT part of the current two-model blind scoring code.

A 200GB /workspace volume already holds approximately 122GB of existing models. Check actual Pod volume usage and quota before any further 65GB pull; the aggregate roughly 187GB plus temp/cache may exceed available space. If necessary, free space deliberately **after preserving results** rather than assuming the advertised shared-filesystem `df -h` value is the per-pod quota.

## Integrity

Only authentic preserved reviews, no synthetic labels. The user-reviewed 12-whole-review reference is not automatically a human gold standard for these 30 segments. The current script reuses prior experimental code and validates output structure and source-quote substring traceability; passing those checks is not proof of semantic correctness.

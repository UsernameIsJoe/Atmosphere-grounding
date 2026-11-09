# Stage 1A — Component 2 evidence selection pilot (2026-11-08)

## Exact responsibility

**Component 1** provides real source-grounded *candidate* observations, environmental–experience relationships, source quotes, and original review sentences. It has not been certified against complete independent gold.

**Component 2** is now designed as two coupled non-destructive decisions:
1. **Location eligibility**: yes/no/uncertain; is this observation attributable to the place, its social/physical environment, or a place-related personal experience, rather than an unrelated personal incident?
2. **Emotion-specific applicability**: for each defined target emotion, *direct* / *indirect* / *not_applicable* / *uncertain*, regardless of whether the observation favors or opposes that emotion.

**Component 3** is still separate NLI. It will judge *entailment/support vs contradiction vs neutral* for theory-defined hypotheses using evidence from the original source, not take Component 2 applicability as emotional polarity or intensity.

### Important limitations

- Component 2 uses the **frozen real Qwen3 A0 output**, and has no automatic hard deletion. Rejected/uncertain items and the original source are retained.
- The existing pilot evidence/NLI code only has three established active hypotheses: `calm`, `inviting`, and `safe`. The repository's older lexicon YAML lists **11** proposed atmospheres; these should **not** be misrepresented as nine newly theory-defined emotions. Until the actual definitions are explicitly frozen, this first real-data experiment tests just the three historical pilots. Do not invent six labels.
- The LLM's Component 2 output is a candidate labeling, **not validated relevance performance**. Self-confidence and eligibility counts are not accuracy.
- The existing BART M2c relevance test used authored cases, not independent human gold for real reviews. It is not a trusted baseline accuracy score.

## Run locally on the user's Windows laptop

From `C:\Users\tu\Desktop\Atmosphere-grounding`:

```powershell
git pull
python scripts/stage1a_component2_eligibility_pilot.py --check-only
python scripts/stage1a_component2_eligibility_pilot.py
```

Default: the same **12 fixed, hard real-review sentences** used in A1/A2 diagnosis, reading the **original A0 Qwen3** `reports/component1_ollama_qwen3_8b/predictions.jsonl`; writes `reports/stage1a_component2_eligibility_pilot/diagnostic/decisions.jsonl` and `summary.json`.

Resume if interrupted:

```powershell
python scripts/stage1a_component2_eligibility_pilot.py --resume
```

Optional after auditing the diagnostic: add `--all` to process all 56 previously extracted sentences (different output subfolder). Never mistake processing count or model agreement for relevance accuracy.

Review each output against *original source*, especially location attribution, emotional relevance when the clue is indirect or **contrary** to an emotion, and ambiguous text such as `circulous` and `Ckean`.

## First milestone

Not 'best relevance model'. Determine whether the two-stage eligibility/applicability distinction gives us inspectable, logically separate evidence selection that can be handed to Component 3 without silently dropping source-supported contrary/implicit evidence. Then compare with **no-filter** using the same NLI hypotheses and frozen NLI checkpoint on independently reviewed real cases.

The prompt, exact input, schema and code are in `scripts/stage1a_component2_eligibility_pilot.py`. GitHub Actions tests syntax and contract only, not localhost inference.

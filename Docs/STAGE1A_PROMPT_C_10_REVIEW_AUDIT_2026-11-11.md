# Stage 1A controlled threshold experiment — 10 real reviews (2026-11-11)

## Goal
Test whether the previous near-universal `not_relevant` predictions arise primarily from ambiguous evidence-threshold instructions or model capability. This is a prompt *intervention*, not a new model benchmark and not semantic validation.

## Frozen corpus
`configs/stage1a_prompt_c_10_place_ids.json` fixes ten distinct locations, all drawn from the first 20-review run. The selected reviews together have **38 existing clause units** (114 clause-emotion cases). The pre-existing A/B labels provide baseline outcomes. Do not alter the source or clause segmentation.

## Existing baseline, extracted from the 20-review annotations
Each model/prompt has **114 labels** for these 10 reviews:

| Model | A | B |
|---|---|---|
| Qwen3 8B | 113 not_relevant; 1 mixed | 111 not_relevant; 2 uncertain; 1 supports |
| Gemma3 4B | 104 not_relevant; 10 uncertain | 114 not_relevant |
| Llama3.2 3B | 114 not_relevant | 103 not_relevant; 11 uncertain |

These are observations, not accuracy or a verdict.

## Independent qualitative inspection queue (not gold labels)
Review all 38 clauses, not just disagreements. Focus on source language such as:
- `Nice place to unwind, jog, or dogwalk.` (relaxation activity vs directly experienced calm)
- `It's not super crowded` (conditional/noise/activity inference)
- `dirty, chaotic mess` and `very easy for someone to slip and hit their head` (negative experiential quality vs directly observed hazard)
- `without worrying for the car drivers` and `one of the best and quiet times` (direct place-attributed experience)
- `I would return again to read a book ... or chill and have lunch with a friend` (indirect social welcome)
- `a nice place to gather for the surrounding community` (social use)
- `favorite spot for a meditative walk` (strong activity–calm connection)
- `a Torii ... welcomes you in` and `make you feel like you are being protected and comforted` (attributed experience vs literal physical safety)
- `Cute park, but it does need a cleaning` (generic positivity and contextual counterevidence)

These are **audit questions**, not asserted truth. Do not manually convert these questions into training labels without a separate human judgment protocol.

## Controlled change
Prompt C explicitly distinguishes: (1) experience, (2) direct environmental indicator, (3) specifically justified indirect evidence, and (4) unrelated descriptions; clarifies `uncertain` vs `not_relevant`, and `mixed` requires both directions. Retain the exact same 3 model tags, 3 emotion definitions, original reviews, clause segmentation, JSON schema, evidence span validation, and decoding settings.

Prompt C is a *single* intervention and changes several linked explanations of the **same threshold**. It cannot identify which sentence caused any difference. More `supports` or `opposes` labels by itself is not a quality improvement.

## Metrics to inspect after run
1. Compare C with A and B for **the same 114 cases** for each model.
2. Count transition matrices (A→C, B→C) by model and emotion.
3. Review every new evidence-bearing label for source quote, plausible category relationship, direction, type, and unsupported inference.
4. Examine unchanged false negatives *as hypotheses*, separately from changes that look like false positives.
5. Compare cross-model agreement, but do not equate agreement with validity.
6. Report malformed response/fallback rates independently of semantic labels.
7. Avoid verdicts of accuracy without independent labels.

## Invocation
```powershell
git pull origin master

python scripts/stage1a_panel_pilot.py `
  --sample-mode diverse `
  --max-reviews 10 `
  --place-ids-file configs/stage1a_prompt_c_10_place_ids.json `
  --prompt-ids C `
  --models qwen3:8b gemma3:4b llama3.2:3b `
  --timeout 480 `
  --output reports/stage1a_prompt_c_10
```
This creates a separate output folder, preserving the baseline 20-review data. If interrupted, repeat with `--resume` and same arguments/output.

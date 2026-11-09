# Component 2 v2 — eligibility and applicability, controlled comparison (2026-11-09)

This is a focused repair of the earlier Qwen3 Component 2 pilot, not an optimization campaign or alteration of Component 1 or Component 3.

## What changed

1. **Simplified place eligibility.** Choose yes/no/uncertain, based on whether the original source describes the place, its environmental/social attributes, or an experience attributable to the place. Merely lacking emotion relevance **never** makes a place observation ineligible. Removed the contradictory secondary `attribution_type` field.
2. **More rigorous emotion applicability.** For each emotion, choose direct / indirect / not_applicable / uncertain. Direct needs explicit *place-related* emotional expression; indirect needs a specific relevant source feature/event that may support **or contradict** the emotion. Generic praise, location prestige, or proximity are not broadly applicable by default. Direct relevance to a person's feeling of protection is **not** proof of objective safety.
3. **Evidence/consistency checks.** Direct and indirect applicability must cite a literally matching original source span (`basis_quote`). A missing/nonliteral quote, or a confident relevance label paired with no/uncertain place eligibility, is flagged and routed to `needs_review`. Raw model labels and all Component 1 candidates remain unchanged in output. The deterministic checker never claims to verify semantic correctness.
4. **Same diagnostic real data and model.** The original frozen 56-sentence, 20-review Qwen3 A0 results are read without re-extraction; first run the same 12 difficult sentences. `qwen3:8b`, JSON schema, and place source text remain fixed. The earlier 12-sentence Component 2 decisions are carried in `prior_component2_v1` for paired manual comparisons.

### Execute on Windows

Ensure Ollama is running, then from the repository folder:

```powershell
cd "$HOME\Desktop\Atmosphere-grounding"
git pull
python scripts/stage1a_component2_v2.py --check-only
python scripts/stage1a_component2_v2.py
```

Default output:
- `reports/stage1a_component2_v2/diagnostic/decisions.jsonl`
- `reports/stage1a_component2_v2/diagnostic/summary.json`

If interrupted, run `python scripts/stage1a_component2_v2.py --resume`.
The default model request timeout is 900 seconds to accommodate local inference, but a stalled service should be diagnosed rather than repeatedly extending it. Use `--all` only after inspecting the diagnostic.

### How to evaluate

Review the **same 23 source-grounded candidate observations** from the prior diagnostic. Important existing errors to test:

- Row 55 (sentence 0), 'charming and cozy park': must be place-related, while emotion applicability is not automatically direct for all positive adjectives.
- Row 55 (sentence 2), 'circulous paths' and feeling protected/comforted: distinguish ambiguous description from place-related reported experience; no invented objectively safe property.
- Row 74 (sentence 0), Cambridge's little parks: consider whether this broad statement is attributable to the specific reviewed park; no forced certainty.
- Row 74 (sentence 1), police patrolling: physical/social observation applicable **indirectly** to perceived safety, not direct feeling of safety. The typo `Ckean` stays uncertain.
- Row 97 (sentence 0), a changed garden: place-related even when not clearly relevant to these emotions; source speculation about sunlight loss is not silently resolved.
- Row 113 (sentence 0), 'inspiring place' and 'great location': place-relatedness does not imply a direct link to calm/inviting/safe.
- Row 181 (sentence 0), 'happening place': is place-related, but emotion relevance must follow a defensible environmental interpretation.

The primary evaluation is **human review of correct labels, their reason, contradictions, omitted relevant evidence and traceable quotes**, not counts of candidates or number of `nli_candidate` routes. A false negative (missing indirect/contrary evidence) is more serious than conservative `needs_review` routing. Compare to original sentences and v1 for regressions.

No NLI has been run by this experiment. No final nine-emotion evaluation is claimed. The historical configured pilot has calm, inviting and safe; expansion requires authoritative definitions for all nine.

Source code: `scripts/stage1a_component2_v2.py`; structural tests: `tests/test_stage1a_component2_v2.py`.

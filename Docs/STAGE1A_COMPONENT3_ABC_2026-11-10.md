# Stage 1A — Controlled integration of Component 2 v3 with Component 3 NLI (2026-11-10)

**Objective:** test whether relevance selection adds interpretability and prevents unrelated evidence from dominating NLI. This is NOT a claim of model accuracy, not an emotion intensity score, and not a final nine-emotion implementation. The 12-sentence development sample was chosen for known problem cases; conclusions require further independent validation.

## Fixed experimental inputs and controls

- **Component 1:** original Qwen3 8B A0 pilot's 56 real sentences, with source and quote provenance untouched.
- **Component 2:** completed v3 12-sentence diagnostic `decisions.jsonl`; 23 model-proposed observations and routing decisions; raw results and flags preserved.
- **Component 3:** *same* `facebook/bart-large-mnli` checkpoint in all experimental conditions, three-way entailment/neutral/contradiction outputs, same `M2c` hypothesis texts for `calm`, `inviting`, `safe`. Do not equate probabilities with atmosphere/emotion intensity.
- Input is **original source text or literal source quotations**, never unsupported LLM paraphrases. This avoids laundering flawed Component 1 paraphrases through NLI.

For each of the 12 exact source sentences and 3 emotions:

**A — No filter:** one NLI evaluation of the entire original **sentence** for that emotion, even if Component 1 found zero observations.

**B — Component 2 selection:** independent NLI of all `nli_candidate` observations for the emotion. The NLI premise is the literal `basis_quote` selected by Component 2, de-duplicated when multiple claims produce the same phrase. If no candidates are selected, result is **no selected evidence**, NOT `neutral` or `contradiction`. Do not conflate claim-level NLI with a global sentence-level single-label result.

**C — Safeguarded selection:** B plus **verbatim whole original sentence fallback** for each `needs_review` case, independently de-duplicated. A fallback is an opportunity for NLI to inspect the original source, NOT acceptance of a suspicious extracted claim. Results retain the route and the reason for review. No source sentence is erased from the record.

Use a *set of claim-level NLI labels* per condition. Report any support, any contradiction, simultaneous support/contradiction, no selected evidence, source/selection disagreements, truncation and model-only effects. No sum/mean scores pretending to be calibrated emotion strength.

### Police patrol interpretation

The researcher explicitly agrees with the previous model's labeling of the police patrol example. **Do not silently downgrade the annotation or force a universal indirect-safety rule.** The v3 model's original `direct` label is preserved, and the v3 mechanical checker flag remains visible as an alternative rubric—not an authoritative semantic error. As currently routed by v3, this enters C as original-source review fallback, not B. That sensitivity of a hand-authored rubric is itself a finding to examine when interpreting the A/B/C outcome. If a future experiment adopts the researcher's preferred policy, it must version the change explicitly and rerun the same paired comparisons.

### Run locally, after Component 2 v3

From PowerShell in the repository root:

```powershell
git pull
python scripts/stage1a_component3_abc.py --check-only
python -m pip install torch transformers
python scripts/stage1a_component3_abc.py
```

The `--check-only` call verifies the frozen 56 sentences and v3 diagnostic alignment, and prints the 12×3 A/B/C inference plan without loading BART. The subsequent command downloads the frozen NLI checkpoint if it is not cached; it is **not an Ollama request** and may need significant memory. It prints `REQUEST NLI` / `OK NLI` per sentence and writes incrementally under `reports/stage1a_component3_abc/`. Resume after interruption using `--resume`. Do not use a new hypothesis set without versioning the experiment.

Outputs:
- `results.jsonl`: source, Component 2 routes, exact NLI premises, model probabilities and 3-way labels for A/B/C; no deleted claims.
- `summary.json`: coverage/disagreement diagnostics, per-emotion evidence presence and label distributions, limitations.

Upload both for human inspection of **actual review sentences**. Do not mistake relative counts or agreement with A for correctness. After the initial 12-case study, independently audit label fidelity and extend to a better-sampled set only if the procedure proves meaningful.

### Sources / prior code

- `scripts/stage1a_m2c_relevance_gate.py` — the historical fixed BART-MNLI hypotheses reused here.
- `scripts/stage1a_component2_v3.py` — non-destructive relevance routes and evidence types.
- `Docs/STAGE1A_COMPONENT2_V3_2026-11-09.md` — prompt and known case motivations.

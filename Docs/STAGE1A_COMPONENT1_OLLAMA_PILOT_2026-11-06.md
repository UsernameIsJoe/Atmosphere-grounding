# Local Ollama Component 1 experiment — A / B / C

This experiment changes **only Component 1 (source-grounded observation/relationship extraction)**. It does not score emotions, relevance or NLI.

**A = current GLiNER2.5 JointIE + GTS-BERT**, frozen real-review baseline:
- Reconciliation [run 41924151396](https://github.com/UsernameIsJoe/Atmosphere-grounding/actions/runs/41924151396); artifact `stage1a-component1-reconciled`.
- Use this same 20-review, 56-sentence sample for comparison. Do **not** compare counts as correctness.

**B = local instruction-tuned LLM** with the original review sentence, structured claim schema and one generation (`temperature=0`).

**C = the identical B output plus verification**, not a separate LLM generation of claims:
- require an exact **contiguous** original-source quote with exactly one occurrence,
- an independent second prompt to the **same frozen LLM** assesses whether claim and relation are supported by the entire original source sentence, including negation and causal attribution,
- mark failed/ambiguous verification as `flagged_not_accepted`, **never silently discard**;
- original sentence survives regardless.
- Such checks are **not independent human labels** or proof of semantic correctness.

## On the laptop

Requires Python 3.11+, Ollama installed/running at `http://127.0.0.1:11434`, and clone of this repository.

```bash
ollama list
ollama pull qwen3:8b
python -m pip install -U spacy
python -m spacy download en_core_web_sm
python scripts/stage1a_component1_ollama.py --model qwen3:8b --check-only
python scripts/stage1a_component1_ollama.py --model qwen3:8b --output reports/component1_ollama_qwen3_8b
```

The command uses the model's *exact* local Ollama name. If that model won't fit available RAM/VRAM, use an appropriate installed instruction model with structured-output support, recording its name. Do not compare runs from different model checkpoints as an A/B/C schema ablation.

To continue after an interrupted call:

```bash
python scripts/stage1a_component1_ollama.py --model qwen3:8b --output reports/component1_ollama_qwen3_8b --resume
```

For a fast connectivity check, add `--max-reviews 1 --output reports/component1_ollama_smoke`; **this still uses only original real reviews**, but does not constitute a complete evaluation.

Files written: `predictions.jsonl`, `summary.json`. Each row has (i) the exact full review and original sentence with offsets, (ii) B extraction, (iii) C verified/flagged candidate set with provenance, and (iv) future handoff that still retains source context. These files may contain raw user review content: inspect before publishing or sharing.

**Limitations:** A verified JSON schema is not a verified factual claim. An LLM can paraphrase incorrectly, leave out contextual observations or approve its own mistakes. We require independent manual annotations of real text to measure completeness, correctness of links, omissions, negation fidelity and hallucination rate; quantitative A/B/C accuracy claims are **not** supported until then. The other two components remain unchanged.

## Fixed diagnostic review cases

These rows are preselected in the 20-review pilot: `55, 74, 97, 113, 123, 139, 181, 187`. Compare the actual source-derived cases especially for (a) trees/paths/protection attribution, (b) park→charming/cozy, (c) loss of sunlight, (d) typo `Ckean`, (e) personal versus environmental feelings. The source grounding checks do not themselves prove that an extracted relationship is meaningful.

The runner deliberately halts on a transport or malformed response instead of treating missing predictions as empty observations, and supports a source-checked `--resume`. See the separate review-level audit after user runs this on their Ollama instance.

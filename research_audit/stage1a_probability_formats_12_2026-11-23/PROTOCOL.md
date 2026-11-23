# Qwen readout alternatives and offline Gemma evaluation

Frozen before new inference, November 23, 2026. Same twelve real reviews and target segments, calm only, fixed v0.5 codebook. Source commit `5557db9fe857438bda336b9cd1eb4c79b1fcde5e`.

## Qwen

Exact prior Qwen3.8 27B Q4_K_M digest and Ollama 0.40.17; same 96 GB RTX PRO 6000 Blackwell GPU class. Serial direct calls to Ollama's bundled llama-server, prompt-cache reuse disabled. Preserve temperature 0, seed 42, context 8192, pre-sampling native log probabilities and the original rendered chat format. Model/backend defaults, including enabled MTP, remain recorded.

Three response formats: original A–D; digits 1–4 with digit-appropriate return instructions; unmarked definition sentences embedding fixed meaningful state words (`none`, `support`, `opposition`, `both`). Verify every response string tokenizes as one token before scoring. No constrained grammar or logit bias. The semantic format removes arbitrary IDs, not the need for a defined output vocabulary.

**Preflight amendment before any scored review:** the initial proposed word `neither` tokenized as `ne` + `ither`. Replace only this verbalizer with the semantically equivalent `none`, and require one token for it. Keep the first preflight failure/tokenization record. This is a token-length control, selected before observing any new review verdict or probability.

For each coded format, test four cyclic code assignments with definition order fixed, and four cyclic definition orders with code assignment fixed. The canonical combination is shared: seven distinct inputs per coded format. The semantic format has fixed state words and four definition orders. Eighteen distinct input versions per review; 216 conditions overall. These are balanced cyclic changes, not all 24 permutations and not a full assignment-by-order factorial.

Reuse ten existing cold repetitions for the original three reviews under four letter assignments: twelve existing conditions. Add only the missing letter conditions (nine reviews' assignment baselines and newly tested orders) and both new formats. Three shuffled cold repetitions per new condition: 612 primary readouts. Three original-map runtime anchors compare the prior cold scores to the new environment. If any anchor's maximum state-probability difference exceeds 0.0001 (0.01 percentage point), do not mix the old baseline with the new runtime; add three current repetitions of those twelve conditions (36 extra calls). This threshold is an engineering rule for data reuse, not an accepted semantic-confidence tolerance.

Keep all native responses, timings, input and request hashes, candidate probability mass and exact-response compliance. Begin with the same top-20 readout as before. If a candidate is omitted, retain that response and request a logged top-200 readout; retain cutoff-based intervals if any candidate is still omitted. Do not treat an omitted candidate as zero or turn noncompliant free text into a valid constrained choice.

Evaluate within-input repeat ranges, code-assignment and order sensitivity separately, state changes, candidate-mass/readout compliance, and casewise behavior. Compare effects against the original baseline. There is no new independent gold-label set; cross-format agreement is not accuracy. Preserve known researcher adjudications as limited diagnostics only, rather than manufacturing labels for all cases.

## Gemma, no new model inference

Use all 64 saved direct readouts (48 unique review/mapping inputs, sixteen repeated inputs) and the 624 native readouts. Verify logits reproduce saved native softmax distributions and each saved T=1,2,4,6,8 vector. Analyze entropy, winning probability, probability/logit repeat differences, mapping sensitivity, ranking of casewise confidence, proximity to hard targets and ordinary fixed label smoothing. Repeated direct inputs should be assessed at every temperature; softening does not by itself prove stability or calibration.

Distinguish the finite test results from unmeasured calibration and downstream training value. No temperature is selected as optimal or calibrated using these twelve repeatedly inspected development cases. Compare variants and preserve them for a later independent training/annotation evaluation.

## Operations

One transient GPU at the catalog price of $2.69/hour; prepare source before leasing, target a lease below 30 minutes. Do not load Gemma weights. Preserve and hash-check all results locally before terminating the owned pod. Publish the protocol, scripts, reports, source and raw results to the project repository. Existing baseline artifacts remain unchanged.

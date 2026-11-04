# Stage 1A — ABSA-indexed clause NLI run audit, 2026-11-04

## Execution

- GitHub Actions [run 41893335588](https://github.com/UsernameIsJoe/Atmosphere-grounding/actions/runs/41893335588), commit `f54412686a9c0ddce48d02b93fde1329c49c867c`: **success**; all steps passed, including preflight tests and source-integrity validation.
- Artifact `13355341339` (`stage1a-absa-guided-nli`), `summary.json` and `review_evidence.jsonl`. 20 source reviews × 3 hypotheses = 60 records.
- These are descriptive observations on model output, **not measured accuracy**. Retain existing M1/M2/M2b/M2c results rather than declaring new model winners.

## Exact outcome

| Metric per emotion | Calm | Inviting | Safe |
|---|---:|---:|---:|
| Source-evidence units | 62 | 62 | 62 |
| Indexed by ABSA aspect/relation | 49 | 49 | 49 |
| Unmatched units retained | 13 | 13 | 13 |
| Clauses shorter than original sentence | 8 | 8 | 8 |
| Units with changed NLI class vs original sentence | **1** | **1** | **0** |
| Reviews with conflicting indexed labels | 0 | 1 | 0 |

Only **three reviews** had any contrastive clause splitting: source rows **2**, **7**, **97**. Most inputs and therefore most NLI classifications were unchanged. The result does not validate meaningful ABSA guidance over a blind segmentation baseline; ABSA tags the already-split evidence, not the act of splitting it.

## Difference audit

- **Row 2 (calm):** original sentence contained “It gets busy on summer weekends but you can usually find a a good space.” The post-contrast clause “but you can usually find a a good space.” received **neutral** whereas its original full sentence received **contradiction**. The earlier “It gets busy on summer weekends” clause remained contradiction. Decomposition separated different environmental observations, but neither class is a validated emotion judgment.
- **Row 97 (inviting):** original upstream segmentation split a parenthetical at a question mark, leaving the next source sentence beginning with `), but ...`. The contrast parser separated a standalone `)` (neutral), while the original sentence was entailment. **This is a segmentation artifact, not semantic progress.** The following clause “, but it is still a neat spot to visit to take a break from the urban hustle and bustle.” was entailment.
- **Row 7:** 4 refined clauses across two source sentences, but no NLI-class changes for the three emotions.
- The indexed `inviting` conflict in row 97 preserved original source observations but, given the upstream split artifact, should not be interpreted as validated contradiction resolution.

## Implementation bug fix after successful run

A defensive change in `scripts/stage1a_absa_guided_nli.py` rejects clause split boundaries whose left or right side has no alphanumeric content, preventing punctuation-only “evidence” units. Added a regression test in `tests/test_stage1a_absa_guided_nli.py` for the observed `), but ...` case. The change was committed **after** run 41893335588 and therefore **has not been verified by that historical execution**. Future runs will exercise it.

## Research conclusion and next practical decision

- **Engineering:** the ABSA annotation and literal source-subspan pipeline executes and retains unmatched evidence. AOS relation coverage on these reviews is sparse; the current design does not make aspect/opinion relationships materially influence the NLI decision process.
- **Evidence of added benefit:** **not established**. Only two original-sentence-versus-clause label changes, of which one is an artifact. The existing result is chiefly a successful source-preservation test.
- **Do not start another disconnected model screen.** Keep the integrated architecture, but only credit ABSA with an inferential role when the extracted relation actually selects or changes the evidence evaluated and that change is interpretable against the original passage. Better contrastive coverage and a source-grounded relevance/attribution audit would be needed to evaluate that contribution rather than asserting it.
- **Do not select a final place-level emotion score, ABSA checkpoint winner, or nine-emotion vocabulary from this run**.

This audit supersedes optimistic interpretations of clause-level label changes as improvement and does not negate previous model feasibility findings.

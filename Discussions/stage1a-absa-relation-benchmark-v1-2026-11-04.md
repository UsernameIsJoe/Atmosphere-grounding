# Stage 1A — ABSA relation model selection, first reproducible benchmark

**Date:** 2026-11-04. **Status:** benchmark code, 8 controlled references and Actions workflow committed. Local baseline evaluation executed; new GitHub Actions run not yet confirmed.

## Why prior model tests matter

- **DeBERTa end-to-end ABSA** and **SetFitABSA** evaluated mostly *aspect spans*, sentiment and sentence retention on 50 real reviews (run [41728835398](https://github.com/UsernameIsJoe/Atmosphere-grounding/actions/runs/41728835398)). Their span counts (98 and 372, respectively) do **not** measure opinion attachment correctness. **Neither is a directly comparable end-to-end aspect–opinion triplet extractor** in that original screen.
- **AOS T5** and **spaCy dependency rules** directly emitted aspect–opinion relationships on 20 source reviews + eight prespecified controlled sentences (corrected run [41861834607](https://github.com/UsernameIsJoe/Atmosphere-grounding/actions/runs/41861834607)). Their 15 versus 67 emitted real-review relationships **do not establish accuracy**.
- We therefore do **not** rerun the earlier model checkpoints. The immediate gap is a fixed test of *relationship correctness*, including source matching, target attachment and explicit negation.

## First controlled reference

- Data: [`data/evaluation/stage1a_absa_relation_controls_v1.json`](../data/evaluation/stage1a_absa_relation_controls_v1.json): eight existing controlled statements, **11 researcher-authored explicit target–opinion pairs**, one negated pair, one adjective-only implicit-evidence case, and one personal-event attribution negative control.
- Scorer: [`scripts/stage1a_absa_relation_benchmark.py`](../scripts/stage1a_absa_relation_benchmark.py), with [unit tests](../tests/test_stage1a_absa_relation_benchmark.py).
- Reproduction: [`stage1a-absa-relation-quality.yml`](../.github/workflows/stage1a-absa-relation-quality.yml) downloads the **frozen outputs from run 41861834607**, scores exact aspect/opinion pairs, emits per-case missed/false relations and negation indicator.
- **Not independent labels:** the benchmark reference pairs were created after some prior experiment findings were known; it is an explicit **diagnostic evaluation set**, not a held-out scientific accuracy measure.

## Local controlled result (will be verified on GitHub Actions)

| Metric | AOS T5 | spaCy dependency rules |
|---|---:|---:|
| Reference pairs correctly extracted | 4/11 | 7/11 |
| Extra incorrect pairs | 2 | 5 |
| Missed reference pairs | 7 | 4 |
| Diagnostic pair precision | 66.7% | 58.3% |
| Diagnostic pair recall | 36.4% | 63.6% |
| Diagnostic pair F1 | 47.1% | 60.9% |
| Explicit negation in opinion span | 0/1 | 0/1 |

These scores are intentionally strict about exact source spans and exact reference phrase matches. Some linguistically reasonable paraphrases or alternate targets are not credited, and one adjective-only sentence is explicitly outside nominal-pair scoring. Percentages on an eleven-pair reference are descriptive only, not generalizable.

## Inference and next decision

1. **No ABSA winner yet.** Dependency rules cover more expected links but also introduce more incorrect links; AOS is selective and misses many. Neither preserves explicit negation in the opinion span on the tested negation case. The prior source-only exact-match criterion is insufficient.
2. This is a **model capability and transfer** problem, not solved by adding more relevance prompts or NLI hypotheses. Keep those other components unchanged.
3. Next compare **a proper joint ASTE checkpoint** on the **same controlled set plus an independently annotated subset of actual place reviews**, rather than another extractor whose outputs are only aspects. A plausible available family is [GTS-BERT ASTE checkpoints](https://huggingface.co/collections/gauneg/aspect-sentiment-triple-extraction) (restaurant/laptop domain; domain transfer still unverified). See also [Hou et al. 2025](https://aclanthology.org/2025.findings-emnlp.355/) on joint aspect/opinion extraction and error propagation. Check checkpoint usability and code requirements before introducing it.
4. Success means verified **target/opinion relations and negation/scope** on the same examples, not more extracted spans. Only then integrate replacement ABSA into existing evidence ledger.

Keep task scope fixed: **ABSA improvement only.** Relevance and emotion NLI remain unchanged.

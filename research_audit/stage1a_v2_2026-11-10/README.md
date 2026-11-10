# Stage 1A v2 run order
1. `python scripts/stage1a_v2.py --split dev --check-only`
2. `python scripts/stage1a_v2.py --split dev --stage all`
3. `python scripts/judge_silver.py --split dev` (requires two installed non-Qwen Ollama judge families)
4. `python scripts/evaluate_v2.py --split dev`
5. `python scripts/stage1a_v2.py --split regression --stage all`
6. Review `reports/stage1a_v2/dev/ten_sample_records.json` and `reports/stage1a_v2/regression/regression_report.json`.
7. Do not run holdout until the researcher confirms the provisional gates.
8. After confirmation, repeat Steps 2–4 with `--split holdout --allow-holdout`.

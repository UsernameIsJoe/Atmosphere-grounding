#!/usr/bin/env python3
"""Generate the evaluated-format report; numeric results are read from artifacts."""
import json,statistics
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parent

def build():
    q=json.loads((ROOT/'qwen_analysis.json').read_text())
    details=json.loads((ROOT/'qwen_analysis_details.json').read_text())
    g=json.loads((ROOT/'gemma_evaluation.json').read_text())
    reuse=json.loads((ROOT/'reuse_decision.json').read_text())
    cases=sorted(q['canonical_states']);fmts=('letters','numbers','text')
    names={'letters':'Letters','numbers':'Numbers','text':'Semantic words'}
    colors={'letters':'#3069b0','numbers':'#248578','text':'#9250a5'}
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig,axs=plt.subplots(2,1,figsize=(11,7),layout='constrained')
    for ax,family,title in zip(axs,('assignment','order'),('Code assignment changes; definition order fixed','Definition order changes; state-to-response mapping fixed')):
        formats=fmts[:2] if family=='assignment' else fmts
        width=.72/len(formats);x=np.arange(len(cases));maximum=0.
        for j,fmt in enumerate(formats):
            vals=[next(r['max_spread_upper_pp'] for r in details if r['format']==fmt and r['family']==family and r['case_id']==cid) for cid in cases]
            maximum=max(maximum,max(vals));ax.bar(x+(j-(len(formats)-1)/2)*width,vals,width,color=colors[fmt],label=names[fmt])
        ax.set_xticks(x,cases);ax.set_ylabel('Largest state-probability spread (pp)');ax.set_title(title,loc='left',fontweight='bold')
        ax.set_ylim(0,maximum*1.24 if maximum else 1);ax.legend(frameon=False,ncols=len(formats),loc='upper right');ax.grid(axis='y',alpha=.15);ax.set_axisbelow(True)
    fig.suptitle('Qwen: response format and definition order under full recomputation',fontweight='bold',fontsize=14)
    fig.savefig(ROOT/'qwen_formats.png',dpi=180);plt.close(fig)
    ts=[r['temperature'] for r in g['temperatures']]
    fig,axs=plt.subplots(1,2,figsize=(11,4),layout='constrained')
    axs[0].plot(ts,[100*r['mean_winning_probability'] for r in g['temperatures']],'o-',color='#3069b0')
    axs[0].set_ylim(0,103);axs[0].set_ylabel('Mean winning probability (%)');axs[0].set_title('Softening spreads probability mass',loc='left',fontweight='bold')
    axs[1].plot(ts,[r['max_mapping_probability_spread_pp'] for r in g['temperatures']],'o-',color='#e78b40',label='Largest letter-mapping spread')
    axs[1].plot(ts,[r['max_direct_repeat_probability_difference_pp'] for r in g['temperatures']],'s--',color='#248578',label='Largest direct repeat difference')
    axs[1].set_ylabel('Percentage points');axs[1].set_title('Sensitivity hidden by saturation becomes visible',loc='left',fontweight='bold')
    axs[1].legend(frameon=False,fontsize=9)
    for ax in axs:ax.set_xticks(ts);ax.set_xlabel('Scoring temperature');ax.grid(alpha=.15);ax.set_axisbelow(True)
    fig.savefig(ROOT/'gemma_softening.png',dpi=180);plt.close(fig)
    table=[]
    for fmt in fmts:
        m=q['formats'][fmt];a=m['families'].get('assignment');o=m['families']['order']
        ac='—' if a is None else f"{a['max_spread_upper_pp']:.2f} / {a['median_case_spread_upper_pp']:.2f}"
        flips='—' if a is None else str(a['cases_with_changed_states'])
        table.append(f"| {names[fmt]} | {ac} | {o['max_spread_upper_pp']:.2f} / {o['median_case_spread_upper_pp']:.2f} | {flips} / {o['cases_with_changed_states']} | {100*m['mean_candidate_mass']:.3f}% | {m['valid_exact_response_count']}/{m['readouts']} |")
    compares=[]
    for family in ('assignment','order'):
        n=sum(r['numbers_less_sensitive'] for r in q['numbers_vs_letters'] if r['family']==family)
        compares.append(f'Numbers have a smaller maximum probability spread than letters on **{n}/12** cases for {family} changes.')
    gamma=[]
    for r in g['temperatures']:
        gamma.append(f"| {r['temperature']:g} | {100*r['mean_winning_probability']:.2f}% | {r['max_mapping_probability_spread_pp']:.2f} | {r['max_direct_repeat_probability_difference_pp']:.2f} | {100*r['mean_total_variation_from_matched_label_smoothing']:.2f}% |")
    canon=[]
    for cid in cases:canon.append('| '+cid+' | '+' | '.join(', '.join(q['canonical_states'][cid][f]) for f in fmts)+' |')
    scores=[]
    for fmt in fmts:
        m=q['formats'][fmt];scores.append(f"{names[fmt]}: {m['groups_with_identical_native_state_scores']}/{m['conditions']} conditions had identical returned state log probabilities across repeats; maximum probability-range upper bound {m['max_repeat_range_upper_pp']:.6g} pp.")
    original=g['temperatures'][0];t4=next(r for r in g['temperatures'] if r['temperature']==4)
    summary=f'''# Qwen response alternatives and Gemma softened-score evaluation

**Executed November 23, 2026.** Same twelve real reviews/target segments and calm-only v0.5 decision task. This is a representation/repeatability diagnostic; no new independent emotion labels or image-model training.

**November 24 discussion and figures:** [Gemma plausibility audit, researcher response, temperature/stability plots and mean-versus-median clarification](../../Discussions/gemma-probability-audit-temperature-and-stability-2026-11-24.md). The complete figure data and regeneration script are linked there.

## Findings

1. **Numbers improve typical code-assignment robustness, while order sensitivity remains.** Median assignment spread falls from {q['formats']['letters']['families']['assignment']['median_case_spread_upper_pp']:.2f} to {q['formats']['numbers']['families']['assignment']['median_case_spread_upper_pp']:.2f} pp, with no assignment-induced verdict changes for numbers. The largest numeric assignment spread is still {q['formats']['numbers']['families']['assignment']['max_spread_upper_pp']:.2f} pp, and reordering numbered definitions produces a {q['formats']['numbers']['families']['order']['max_spread_upper_pp']:.2f}-point spread.
2. **Semantic words improve typical order robustness, with remaining failures.** Median order spread is {q['formats']['text']['families']['order']['median_case_spread_upper_pp']:.2f} pp against {q['formats']['letters']['families']['order']['median_case_spread_upper_pp']:.2f} pp for letters. Their largest spread is {q['formats']['text']['families']['order']['max_spread_upper_pp']:.2f} pp, with changed chosen states in {q['formats']['text']['families']['order']['cases_with_changed_states']}/12 cases. None of the tested formats makes a single prompted probability vector robust to all tested changes.
3. **Gemma's softened distributions reveal previously compressed letter sensitivity.** T=4 lowers mean winning probability to {100*t4['mean_winning_probability']:.2f}%, while mapping differences reach {t4['max_mapping_probability_spread_pp']:.2f} pp. Its sixteen saved direct repeat pairs remain identical. Softening and computational repeatability answer different questions.

**Usefulness check added:** [Gemma probability signal versus fixed smoothing](GEMMA_SIGNAL_EVALUATION.md) evaluates the recorded reference judgments and case influence. No robust added usefulness is established; the reference remains provisional.

## Questions and what was actually done

- **Qwen:** compare A–D, 1–4 and meaningful semantic answers; distinguish code assignment from definition order; use full prompt recomputation throughout. Reuse previously measured cold letter conditions, rather than repeating the original letter study.
- **Gemma:** evaluate the already saved 64 direct readouts, 624 native readouts and temperature grid. **Zero new Gemma model calls.**

See the [frozen protocol and tokenization amendment](PROTOCOL.md), [run manifest](manifest.json) and [twelve exact inputs](inputs.jsonl).

## Qwen design

Same Qwen3.8 27B Q4_K_M checkpoint digest, Ollama 0.40.17 and 96 GB RTX PRO 6000 Blackwell GPU class as the earlier diagnostic. The private bundled backend uses `cache_prompt=false`, temperature 0, seed 42, serial requests, n_predict=1 and native probabilities before sampling. Actual backend flags and hardware are in [runtime.json](runtime.json); MTP remains at the recorded native default.

For letters and numbers, four cyclic code assignments are tested with definition order fixed, and four cyclic definition orders with code assignment fixed. The canonical input is shared, giving seven unique versions per coded format. Unmarked definition sentences embed fixed semantic state names (`none`, `support`, `opposition`, `both`), with four cyclic orders. **Eighteen versions per review, 216 unique inputs.** These are balanced cyclic tests, not all 24 permutations or a full assignment/order interaction test.

Three runtime anchors matched the prior cold probabilities exactly: **{max(a['max_probability_gap'] for a in reuse['anchors']):.9g} maximum difference**. Baseline reuse was **{reuse['reuse_old_cold_baselines']}**. The new run recorded **{q['new_readouts']} readouts**, including three runtime anchors, and reused **{q['reused_readouts']}** original cold readouts (three reviews × four letter assignments × ten repeats). New conditions receive three shuffled cold repetitions. Old and new candidate masses are averaged per unique condition so reused repetitions do not give a review extra weight.

Initial tokenizer preflight found `neither` was two tokens. Before any scored review, the word was replaced with `none`; all twelve response strings then passed the single-token check. This verbalizer choice was based only on tokenization, not review outcomes. The initial failure is retained. The semantic format removes arbitrary IDs, while still requiring a fixed vocabulary for measurable probabilities.

The original top-20 readout is retained. **{q['topk_expansion_calls']}** calls required an additional top-200 readout because a candidate was missing. These are additional completion calls beyond the readout-record count. The largest change in a shared native log probability between a top-20 and expanded readout was **{q['max_shared_logprob_difference_after_topk_expansion']:.9g}**. Missing candidates, if any, retain cutoff-based bounds. No grammar, logit bias, zero imputation or generated confidence scores were used.

## Qwen results

Spread columns are **maximum / median across the twelve cases**, in percentage points. All probabilities are conditional on the four exact response tokens; candidate mass also reports how much native probability belongs to those tokens. State-change columns count cases whose raw chosen semantic state changes within the corresponding family.

| Format | Code-assignment spread, max / median (pp) | Definition-order spread, max / median (pp) | Cases changing state: assignment / order | Mean native candidate mass | Valid exact responses |
|---|---:|---:|---:|---:|---:|
{chr(10).join(table)}

{' '.join(compares)}

The same tendency appears in score-space diagnostics. Median canonical-winner logit-margin ranges are **{q['formats']['letters']['families']['assignment']['median_canonical_winner_logit_margin_range']:.3f} for letter assignment versus {q['formats']['numbers']['families']['assignment']['median_canonical_winner_logit_margin_range']:.3f} for number assignment**. For order changes they are **{q['formats']['letters']['families']['order']['median_canonical_winner_logit_margin_range']:.3f}, {q['formats']['numbers']['families']['order']['median_canonical_winner_logit_margin_range']:.3f}, {q['formats']['text']['families']['order']['median_canonical_winner_logit_margin_range']:.3f}** for letters, numbers and semantic words respectively. Thus the typical improvements are also visible before probability saturation; they do not establish better semantic judgments.

{' '.join(scores)}

![Qwen formats under code and order changes](qwen_formats.png)

The case table prevents lower probability variation from being mistaken for unchanged interpretation. These are observed model decisions, **not newly adjudicated ground truth**:

| Case | Canonical letters | Canonical numbers | Canonical semantic words |
|---|---|---|---|
{chr(10).join(canon)}

For a concrete order failure, K06's letter readout changes from **opposition only to support only** under one reordered list. Its semantic-word readout changes from opposition only to neither under another order. The target and review context do not change.

The controlled assignment and order comparisons answer different questions. A format with lower code sensitivity can still depend on list order or change the underlying decision. Lower spread alone does not establish greater correctness or calibration; frozen semantic words may also produce saturated probabilities. [Full case comparisons](qwen_comparison.csv), [native-score margin diagnostics](qwen_analysis_details.json) and [analysis summary](qwen_analysis.json) preserve these distinctions.

## Gemma: evaluate existing scores rather than rerun

All **48 unique review/mapping inputs**, with **16 direct repeat pairs**, are evaluated at T=1,2,4,6,8. Recomputing softmax from the saved four logits reproduces every saved temperature vector with maximum absolute error **{g['max_saved_distribution_reconstruction_error']:.9g}**. Every direct repeat pair remains identical at every temperature; the winning state is unchanged. This verifies the algebra and observed repeatability in that direct backend, not universal invariance or calibrated confidence.

| Scoring temperature | Mean winning probability | Largest letter-mapping spread (pp) | Largest direct-repeat difference (pp) | Mean TV distance from matched uniform smoothing |
|---|---:|---:|---:|---:|
{chr(10).join(gamma)}

![Gemma softening and revealed mapping sensitivity](gemma_softening.png)

**The central finding:** at T=4, average winning probability falls from **{100*original['mean_winning_probability']:.2f}% to {100*t4['mean_winning_probability']:.2f}%**, but maximum letter-mapping variation rises from **{original['max_mapping_probability_spread_pp']:.2f} to {t4['max_mapping_probability_spread_pp']:.2f} pp**. K01's opposition probability ranges from approximately **68.20% to 82.40%** across the four mappings at T=4. Its verdict stays opposition, preserving the earlier attribution-error diagnosis. Softening reveals sensitivity hidden by saturation; it does not create evidence that the alternative probabilities are calibrated.

The native cached/reloaded data also contains computational variation: on the **{t4['native_complete_groups']} condition/phase groups** with all four candidates present on every repeat, the maximum within-payload range rises from **{original['native_complete_group_max_repeat_range_pp']:.2f} pp at T=1** to **{t4['native_complete_group_max_repeat_range_pp']:.2f} pp at T=4**. This is a different backend/cache condition from the repeated full-recomputation direct scores above; the two should not be pooled as interchangeable measurements.

**Practical extraction issue:** top-20 native probabilities omit some very unlikely state tokens. Those omissions become more consequential after softening: the maximum resulting state-probability interval width is **{t4['max_native_missingness_interval_width_pp']:.2f} pp at T=4**, and larger at T=6/8. The direct evaluation uses all four captured logits and therefore has no such missing-state ambiguity. Do not soften rounded percentages or replace omitted candidates with zero.

For the smoothing control, each temperature is compared with fixed uniform label smoothing matched to its mean winning probability: target `(1-epsilon)*one_hot(winner) + epsilon/4`. Total variation measures how much the full case-specific distribution differs from that control. Softened Gemma vectors contain case/alternative-specific information beyond one constant smoothing level; **qualitative plausibility and provisional-reference checks are documented in the follow-ups; downstream training benefit remains untested**.

## Decisions supported at this stage

- Use the Qwen casewise assignment and order results together; do not select a format from one favorable example or probability spread alone.
- Preserve full logits and the original distributions. The saved Gemma temperature grid is repeatable in the tested direct backend, but a softened single-mapping target retains appreciable mapping sensitivity.
- Four-mapping arithmetic averages are exported for comparison. They remove dependence on which of those four captured vectors is selected, while leaving the tested encoding, systematic errors and untested permutations unresolved. No downstream improvement is claimed.
- Do not select an optimal/calibrated temperature or adopt probability supervision from these development cases. Later compare hard targets, matched fixed smoothing and model-derived soft targets on independent annotation/training validation.

## Artifacts and reproduction

- [Qwen summary](qwen_analysis.json), [case comparisons](qwen_comparison.csv), [case/factor details](qwen_analysis_details.json).
- [Gemma evaluation](gemma_evaluation.json), [all temperature vectors](gemma_temperature_vectors.csv), [four-mapping averages and support/opposition marginals](gemma_mapping_averages.csv), [source hashes](gemma_source_integrity.json).
- [Raw bundle](raw_results_bundle.tar.gz), [bundle hash](BUNDLE.json), [download verification](archive_integrity.json), [pod cleanup](cleanup.json).
- [Runner](run_formats.py), [Qwen analysis](analyze_qwen.py), [Gemma evaluator](evaluate_gemma.py), [report generator](generate_report.py), [bootstrap](bootstrap.py), [packaging](package_results.py).

The raw bundle is self-contained for Qwen: frozen codebook/source helper, all twelve inputs, prior cold observations, prompt strings, new requests/responses, tokenization and runtime records. Gemma's existing full raw evidence remains in the [preceding experiment's bundle](../stage1a_probability_repeatability_12_2026-11-23/raw_results_bundle.tar.gz); the new evaluation is derived from those hashed inputs. To reproduce its evaluation, extract that earlier bundle and set `PROBABILITY_REPEAT_ROOT` to its directory before running `evaluate_gemma.py`.

The archive preserves execution-time code; files alongside it may contain later report formatting. Verify archived contents against `INTEGRITY.json` before changes. Offline analysis uses Python/NumPy and plots use Matplotlib. This experiment changes research artifacts only; no production extraction/training configuration is adopted.

The owned pod was terminated after approximately **14 minutes**. Estimated compute at the observed $2.69/hour rate was **$0.63**; all results and hashes were verified before deletion, and the post-termination pod list was empty. See [cleanup.json](cleanup.json) for timestamps and the billing qualification.
'''
    (ROOT/'README.md').write_text(summary)
    print('GENERATED report and two plots')

if __name__=='__main__':build()

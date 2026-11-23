#!/usr/bin/env python3
"""Exploratory usefulness checks with explicit reference provenance; no inference."""
import ast,csv,io,itertools,json,math,os,statistics
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parent
PRIOR=Path(os.environ.get('PROBABILITY_REPEAT_ROOT',str(ROOT.parent/'probability_repeat_2026_11_23')))
STATES=('neither','support_only','opposition_only','both')
REF={'none':0,'supports':1,'opposes':2,'both':3}
TEMPS=('1.0','2.0','4.0','6.0','8.0')

def metrics(q,y):
    n=len(y);pred=q.argmax(axis=1);confidence=q.max(axis=1);wrong=pred!=y
    error_auc=statistics.mean(float(a>b)+.5*float(a==b) for a in (1-confidence)[wrong] for b in (1-confidence)[~wrong]) if wrong.any() and (~wrong).any() else None
    return {'cases':n,'agreements':int((~wrong).sum()),'reference_disagreements':int(wrong.sum()),
        'nll':float(-np.log(q[np.arange(n),y].clip(1e-300)).mean()),
        'brier_sum_four_classes':float(np.sum((q-np.eye(4)[y])**2,axis=1).mean()),
        'error_detection_auroc':error_auc}

def compare(q,y):
    eps=float((1-q.max(axis=1).mean())/.75)
    smooth=np.full(q.shape,eps/4);smooth[np.arange(len(y)),q.argmax(axis=1)]+=1-eps
    return {'model_soft_targets':metrics(q,y),'matched_fixed_smoothing':metrics(smooth,y),'smoothing_epsilon':eps}

def evaluate():
    rows=[json.loads(l) for l in (PRIOR/'direct_gemma/readouts.jsonl').read_text().splitlines() if json.loads(l)['repeat']==0]
    assert len(rows)==48
    cases=sorted({r['case_id'] for r in rows})
    inputs={r['case_id']:r for r in map(json.loads,(PRIOR/'inputs.jsonl').read_text().splitlines())}
    source=json.loads((PRIOR/'frozen_source_snapshot/source/previous_claims_by_emotion.json').read_text())
    merged={}
    for r in source:
        if r['emotion']=='calm':
            if r['case_id'] in merged:assert merged[r['case_id']]==r['reference']
            merged[r['case_id']]=r['reference']
    tree=ast.parse((PRIOR/'frozen_source_snapshot/source/baseline_runner_v05.py').read_text())
    audit=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='AUDIT' for t in n.targets))
    explicit={k.split(':')[0]:v for k,v in audit.items() if k.endswith(':calm')}
    assert explicit=={'U06':'supports','K01':'none'}
    prov=json.loads((ROOT/'gemma_reference_provenance.json').read_text())
    legacy={r['case_id']:r['reference'] for r in csv.DictReader(io.StringIO(prov['legacy_reference_csv'])) if r['emotion']=='calm' and r['reference'] in REF}
    state={cid:next(r['selected_state'] for r in rows if r['case_id']==cid) for cid in cases}
    tables=[];all_case_rows=[]
    for t in TEMPS:
        per={cid:np.array([[next(r for r in rows if r['case_id']==cid and r['rotation']==f'rotation_{i}')['temperature_sensitivity'][t][s] for s in STATES] for i in range(4)]) for cid in cases}
        mean=np.array([per[cid].mean(axis=0) for cid in cases])
        y=np.array([REF[merged[c]] for c in cases]);result=compare(mean,y)
        omissions=[]
        for i,cid in enumerate(cases):
            keep=np.arange(len(cases))!=i;omissions.append({'omitted_case':cid,**compare(mean[keep],y[keep])})
        known_ids=[i for i,c in enumerate(cases) if c in explicit]
        old_ids=[i for i,c in enumerate(cases) if c in legacy]
        pairs=[]
        for a,b in itertools.combinations(cases,2):
            if state[a]!=state[b]:continue
            qa=per[a].max(axis=1);qb=per[b].max(axis=1);delta=qa-qb
            pairs.append({'a':a,'b':b,'ranking_reverses_under_common_mapping':bool(delta.min()<-1e-12 and delta.max()>1e-12),
                'confidence_intervals_disjoint':bool(qa.min()>qb.max() or qb.min()>qa.max()),
                'min_paired_difference_pp':float(100*delta.min()),'max_paired_difference_pp':float(100*delta.max())})
        summary={'temperature':float(t),'merged_provisional_twelve_case_check':result,
            'leave_one_case_out':omissions,
            'explicit_current_audit_two_cases':compare(mean[known_ids],np.array([REF[explicit[cases[i]]] for i in known_ids])),
            'older_conservative_reference_sensitivity':compare(mean[old_ids],np.array([REF[legacy[cases[i]]] for i in old_ids])),
            'same_winner_review_pairs':len(pairs),
            'same_winner_pair_rank_reversals':sum(p['ranking_reverses_under_common_mapping'] for p in pairs),
            'same_winner_pairs_with_disjoint_confidence_ranges':sum(p['confidence_intervals_disjoint'] for p in pairs),
            'pair_details':pairs}
        tables.append(summary)
        for i,cid in enumerate(cases):
            winning=per[cid].max(axis=1)
            all_case_rows.append({'case_id':cid,'temperature':float(t),'predicted_state':state[cid],
                'winning_probability_mean':float(winning.mean()),'winning_probability_min':float(winning.min()),'winning_probability_max':float(winning.max()),
                'explicit_current_reference':explicit.get(cid,''),'merged_provisional_reference':merged[cid],
                'older_conservative_reference':legacy.get(cid,''),'target':inputs[cid]['target_segment'],
                **{s:float(mean[i,j]) for j,s in enumerate(STATES)}})
    out={'source_commit':prov['source_commit'],'new_model_calls':0,'unique_cases':12,
        'explicit_current_calm_judgments':explicit,'merged_provisional_references':merged,
        'reference_conflicts_between_merged_and_older':{c:{'merged':merged[c],'older':legacy[c]} for c in legacy if merged[c]!=legacy[c]},
        'temperatures':tables,
        'qualification':'Post-hoc exploratory reference comparison, not calibration or independent evaluation. Four mappings averaged per review; twelve cases, not forty-eight independent observations. Current explicit audit has only two calm judgments. Legacy reference fields are inherited and partly disputed. No threshold or temperature is selected.'}
    (ROOT/'gemma_signal_check.json').write_text(json.dumps(out,indent=2))
    with (ROOT/'gemma_signal_cases.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(all_case_rows[0]));w.writeheader();w.writerows(all_case_rows)
    t4=next(r for r in tables if r['temperature']==4)
    table=[]
    for r in tables:
        a=r['merged_provisional_twelve_case_check']['model_soft_targets'];b=r['merged_provisional_twelve_case_check']['matched_fixed_smoothing']
        table.append(f"| {r['temperature']:g} | {a['nll']:.3f} | {b['nll']:.3f} | {a['brier_sum_four_classes']:.3f} | {b['brier_sum_four_classes']:.3f} | {a['error_detection_auroc']:.3f} |")
    a=t4['merged_provisional_twelve_case_check']['model_soft_targets'];b=t4['merged_provisional_twelve_case_check']['matched_fixed_smoothing']
    omission=next(r for r in t4['leave_one_case_out'] if r['omitted_case']=='K01')
    oa=omission['model_soft_targets'];ob=omission['matched_fixed_smoothing']
    case_table=[]
    for cid in ('K01','U03','U06','K04'):
        r=next(r for r in all_case_rows if r['temperature']==4 and r['case_id']==cid)
        case_table.append(f"| {cid} | {r['predicted_state']} | {100*r['winning_probability_mean']:.2f}% | {100*r['winning_probability_min']:.2f}–{100*r['winning_probability_max']:.2f}% |")
    text=f'''# Gemma: does softening provide a useful signal?

**Offline addendum, November 23, 2026. No new model inference.** The preceding evaluation established distribution shape, repeatability and sensitivity. Those observations did not establish that the probabilities identify dependable judgments or improve supervision. This addendum addresses that missing question as far as the existing reference data permits.

**Assessment: no robust added usefulness is established yet.** There are reproducible case-specific preferences, including lower confidence on K01's attribution failure. Against archived provisional reference fields, however, error detection is weak and any benefit over fixed smoothing is small, metric-dependent and sensitive to one case. This is insufficient to adopt the scores as validated confidence or training targets.

## Reference provenance limits the claim

The v0.5 runner's explicit `AUDIT` has only **two calm judgments**: K01 = none and U06 = supports. The other ten entries in the saved twelve-case reference are inherited/merged older labels. In particular, K03 and U01 are `opposes` in those merged fields but `none` in the older conservative target reference. The codebook and adjudications evolved. Neither twelve-case reference is independent current gold.

We retain separate checks for the two explicit judgments, all twelve merged provisional fields, and the older conservative reference (eleven determinate calm labels, excluding its uncertain U06). Results change with that reference choice. **Do not interpret the twelve-case numbers below as a validated calibration benchmark.** Source snapshots/paths are recorded in [reference provenance](gemma_reference_provenance.json); the [full numeric record](gemma_signal_check.json) preserves all reference variants.

## Actual comparison with a simple control

For each temperature, average the four captured mapping distributions per review; do not count mappings or repeats as independent examples. Compare those twelve model-specific vectors with fixed uniform label smoothing around the same model verdicts, choosing its single smoothing level to match their mean winning probability. This control asks whether case-specific confidence and alternative-state allocation help beyond simply making every label equally softer. It does not use the references to fit the smoothing level.

NLL and four-class Brier sum are reference-based probability losses (lower is better). Error AUROC uses `1 - winning probability` to rank reference disagreements (0.5 = chance ranking, 1 = perfect). All numbers use the **merged provisional twelve-case reference**; it disagrees with Gemma on K01, K03 and U01.

| T | Model NLL | Fixed-smoothing NLL | Model Brier | Fixed-smoothing Brier | Error-detection AUROC |
|---|---:|---:|---:|---:|---:|
{chr(10).join(table)}

At T=4, model-specific probabilities have essentially the same NLL as fixed smoothing (**{a['nll']:.3f} versus {b['nll']:.3f}**), a modest Brier improvement (**{a['brier_sum_four_classes']:.3f} versus {b['brier_sum_four_classes']:.3f}**), and weak error-ranking AUROC (**{a['error_detection_auroc']:.3f}**). T=6/8 improve both losses on this reference, but are not selected as optimal or calibrated.

**Case-influence check:** we calculated every leave-one-case-out comparison. Removing K01 reverses the model's Brier advantage at T=4: **{oa['brier_sum_four_classes']:.3f} versus {ob['brier_sum_four_classes']:.3f}**, and its NLL becomes worse: **{oa['nll']:.3f} versus {ob['nll']:.3f}**. The comparison rematches the control's mean softness on the retained eleven cases without using labels. The same direction of reversal occurs at T=6/8. The apparent benefit therefore depends heavily on the known K01 failure; it is not robust evidence of general added utility.

## What signal is visible in individual cases?

T=4 chosen-state confidence, averaged across mappings with the full mapping range:

| Case | Model verdict | Mean confidence | Mapping range |
|---|---|---:|---:|
{chr(10).join(case_table)}

K01 is the explicitly recorded personal-stress attribution failure. U03 is the explicit intrusive-traffic-noise example, aligned with the archived opposition reference. They share the same hard opposition verdict, yet the scores distinguish them strongly; this is a plausible coarse preference signal beyond the hard label. U06 is the other explicitly current calm adjudication (support). K04 remains highly confident despite the prior audit's low-crowding grounding concern; that concern is not a newly assigned error label here.

Fine confidence ordering is less robust: **{t4['same_winner_pair_rank_reversals']}/{t4['same_winner_review_pairs']}** pairs of reviews with the same winning state reverse their relative confidence under a common change of letter mapping. These are pairs, not independent new reviews. All six reversals concern high-confidence neither cases and have paired differences below one percentage point. Broad distinctions may survive while fine decimal differences do not.

## Practical interpretation

- **What is present:** stable model preferences, some coarse case distinctions and nonuniform alternative-state information beyond hard labels or one fixed smoothing level.
- **What is not established:** reliable identification of correct judgments, a calibrated confidence scale or better downstream image training. A transformed distribution is not validated merely because its values spread out.
- **Current use:** preserve the logits and candidate softened vectors as research artifacts. Their proper next comparison is against hard targets and fixed smoothing on codebook-aligned independent annotations or downstream held-out training; the present checks do not justify adopting them as reliable supervision.

The two explicit audit judgments are too few to validate an error detector. The wider provisional reference is useful for exploratory sensitivity checks, but its inherited conflicts materially change the evaluation. No model-generated judgments were introduced as ground truth, and no temperature or threshold was selected using these results.

Reproduce with [evaluate_gemma_signal.py](evaluate_gemma_signal.py), the original probability-repeat raw data, and the saved [reference snapshot](gemma_reference_provenance.json). The [case-level CSV](gemma_signal_cases.csv) exposes every target, reference source and temperature vector.
'''
    (ROOT/'GEMMA_SIGNAL_EVALUATION.md').write_text(text)
    print(json.dumps({'reference_conflicts':out['reference_conflicts_between_merged_and_older'],'T4_provisional':t4['merged_provisional_twelve_case_check'],'T4_without_K01':next(r for r in t4['leave_one_case_out'] if r['omitted_case']=='K01'),'T4_rank_reversals':t4['same_winner_pair_rank_reversals']},indent=2))

if __name__=='__main__':evaluate()

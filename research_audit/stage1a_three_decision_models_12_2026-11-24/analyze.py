#!/usr/bin/env python3
"""Analyze recorded native decisions. No inherited-label accuracy or calibration claims."""
import csv
import json
from pathlib import Path
import statistics

import numpy as np

ROOT=Path(__file__).resolve().parent
STATES=('neither','support_only','opposition_only','both')
MODELS=('mammoth','karpo','glide')


def vector(record):
    return record.get('probabilities_full_precision',record['probabilities'])


def csvwrite(path,rows):
    if not rows:return
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def winner(q):return STATES[int(np.argmax(q))]


def analyze(name):
    folder=ROOT/'results'/name;source=folder/'readouts.jsonl'
    if not source.exists():return {'model':name,'readouts':0,'complete':False},[],[],[]
    rows=[json.loads(l) for l in source.read_text().splitlines() if l.strip()]
    conditions=[];groups={}
    cases=sorted({r['case_id'] for r in rows})
    for case in cases:
        for w in range(3):
            for o in range(4):
                key=(case,f'wording_{w}',f'order_{o}')
                found=[r for r in rows if (r['case_id'],r['wording_id'],r['order_id'])==key and r['phase']!='reloaded']
                if not found:continue
                q=np.array([[vector(r)[s] for s in STATES] for r in found]);z=np.array([[r['raw_logits'][s] for s in STATES] for r in found])
                assert np.isfinite(q).all() and np.isfinite(z).all() and np.min(q)>=0 and np.max(q)<=1
                assert np.allclose(q.sum(axis=1),1,atol=2e-7,rtol=0)
                groups[key]={'records':found,'q':q,'z':z,'mean':q.mean(axis=0)}
                conditions.append({'model':name,'case_id':case,'wording_id':key[1],'order_id':key[2],
                    'repeats':len(found),'max_probability_repeat_range_pp':float(100*np.ptp(q,axis=0).max()),
                    'max_logit_repeat_range':float(np.ptp(z,axis=0).max()),
                    'distinct_probability_vectors':len({tuple(x) for x in q}),
                    'distinct_raw_logit_vectors':len({tuple(x) for x in z}),
                    'repeat_winners':len({r['selected_state'] for r in found})})
    primary=[r for r in rows if r['phase']=='main'];extra=[r for r in rows if r['phase']=='paraphrase'];reloaded=[r for r in rows if r['phase']=='reloaded']
    original=[r for r in conditions if r['wording_id']=='wording_0']
    complete=(len(primary)==480 and len(extra)==288 and len(reloaded)==12 and len(conditions)==144 and
              all(r['repeats']==(10 if r['wording_id']=='wording_0' else 3) for r in conditions))
    case_rows=[];word_rows=[];reload_rows=[]
    for case in cases:
        matrices={};means={}
        for w in range(3):
            keys=[(case,f'wording_{w}',f'order_{o}') for o in range(4)]
            if not all(k in groups for k in keys):continue
            matrix=np.array([groups[k]['mean'] for k in keys]);matrices[w]=matrix;means[w]=matrix.mean(axis=0)
            word_rows.append({'model':name,'case_id':case,'wording_id':f'wording_{w}',
                'selected_state':winner(means[w]),**dict(zip(STATES,map(float,means[w]))),
                'max_order_range_pp':float(100*np.ptp(matrix,axis=0).max()),
                'different_order_winners':len({winner(q) for q in matrix})})
        if 0 not in means:continue
        gap=float(100*np.ptp(matrices[0],axis=0).max())
        entry={'model':name,'case_id':case,'selected_state':winner(means[0]),
               **dict(zip(STATES,map(float,means[0]))),'max_order_range_pp':gap,
               'different_order_winners':len({winner(q) for q in matrices[0]})}
        if len(means)==3:
            q=np.array([means[w] for w in range(3)])
            entry.update({'wording_range_of_order_means_pp':float(100*np.ptp(q,axis=0).max()),
                'different_wording_mean_winners':len({winner(v) for v in q}),
                'matched_orders_with_wording_winner_flip':sum(len({winner(matrices[w][o]) for w in range(3)})>1 for o in range(4)),
                'max_matched_order_wording_range_pp':max(float(100*np.ptp(np.array([matrices[w][o] for w in range(3)]),axis=0).max()) for o in range(4)),
                'max_wording_mean_TV_from_original':max(float(.5*np.abs(means[w]-means[0]).sum()) for w in [1,2])})
        case_rows.append(entry)
    for row in reloaded:
        key=(row['case_id'],'wording_0','order_0')
        if key not in groups:continue
        original_row=groups[key]['records'][0]
        reload_rows.append({'model':name,'case_id':row['case_id'],
            'probabilities_identical':vector(row)==vector(original_row),
            'raw_logits_identical':row['raw_logits']==original_row['raw_logits'],
            'max_probability_shift_pp':max(100*abs(vector(row)[s]-vector(original_row)[s]) for s in STATES),
            'same_winner':row['selected_state']==original_row['selected_state']})
    q=np.array([[vector(r)[s] for s in STATES] for r in primary])
    order_gaps=[r['max_order_range_pp'] for r in case_rows]
    wording_gaps=[r['wording_range_of_order_means_pp'] for r in case_rows if 'wording_range_of_order_means_pp' in r]
    summary={'model':name,'complete':complete,'readouts':len(rows),'primary_readouts':len(primary),
        'paraphrase_readouts':len(extra),'reload_readouts':len(reloaded),
        'counted_model_forward_passes':sum(r['model_forward_passes'] for r in rows),
        'primary_repeatability':{'conditions':len(original),
            'identical_probability_groups':sum(r['distinct_probability_vectors']==1 for r in original),
            'identical_logit_groups':sum(r['distinct_raw_logit_vectors']==1 for r in original),
            'max_probability_range_pp':max((r['max_probability_repeat_range_pp'] for r in original),default=None),
            'max_logit_range':max((r['max_logit_repeat_range'] for r in original),default=None),
            'groups_with_winner_flips':sum(r['repeat_winners']>1 for r in original)},
        'all_wordings_repeatability':{'conditions':len(conditions),
            'identical_probability_groups':sum(r['distinct_probability_vectors']==1 for r in conditions),
            'identical_logit_groups':sum(r['distinct_raw_logit_vectors']==1 for r in conditions),
            'max_probability_range_pp':max((r['max_probability_repeat_range_pp'] for r in conditions),default=None),
            'groups_with_winner_flips':sum(r['repeat_winners']>1 for r in conditions)},
        'primary_order_sensitivity':{'median_review_gap_pp':statistics.median(order_gaps) if order_gaps else None,
            'mean_review_gap_pp':statistics.mean(order_gaps) if order_gaps else None,'maximum_review_gap_pp':max(order_gaps,default=None),
            'cases_with_winner_flips':sum(r['different_order_winners']>1 for r in case_rows)},
        'wording_sensitivity_after_order_averaging':{'cases':len(wording_gaps),
            'median_review_gap_pp':statistics.median(wording_gaps) if wording_gaps else None,
            'mean_review_gap_pp':statistics.mean(wording_gaps) if wording_gaps else None,
            'maximum_review_gap_pp':max(wording_gaps,default=None),
            'cases_with_mean_winner_flips':sum(r.get('different_wording_mean_winners',1)>1 for r in case_rows),
            'cases_with_matched_order_winner_flips':sum(r.get('matched_orders_with_wording_winner_flip',0)>0 for r in case_rows),
            'matched_order_conditions_with_wording_winner_flips':sum(r.get('matched_orders_with_wording_winner_flip',0) for r in case_rows),
            'max_matched_order_wording_gap_pp':max((r['max_matched_order_wording_range_pp'] for r in case_rows if 'max_matched_order_wording_range_pp' in r),default=None)},
        'reloaded':{'comparisons':len(reload_rows),'identical_probability_vectors':sum(r['probabilities_identical'] for r in reload_rows),
            'identical_logit_vectors':sum(r['raw_logits_identical'] for r in reload_rows),
            'max_probability_shift_pp':max((r['max_probability_shift_pp'] for r in reload_rows),default=None),
            'cases_with_winner_flips':sum(not r['same_winner'] for r in reload_rows)},
        'native_score_reconstruction_max_abs_error':max(r['native_reconstruction_max_abs_error'] for r in rows),
        'formatter_verification':json.loads((folder/'FORMATTER_VERIFICATION.json').read_text()) if (folder/'FORMATTER_VERIFICATION.json').exists() else None,
        'primary_mean_winning_probability':float(q.max(axis=1).mean()) if len(q) else None,
        'primary_winning_probability_ge_999':int((q.max(axis=1)>=.999).sum()) if len(q) else None,
        'primary_mean_entropy_bits':float((-q*np.log2(np.clip(q,1e-300,None))).sum(axis=1).mean()) if len(q) else None,
        'median_decision_seconds':statistics.median(r['elapsed_seconds'] for r in primary) if primary else None}
    (folder/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    csvwrite(folder/'condition_repeatability.csv',conditions);csvwrite(folder/'case_summary.csv',case_rows)
    csvwrite(folder/'wording_order_mean_vectors.csv',word_rows);csvwrite(folder/'reload_comparison.csv',reload_rows)
    return summary,case_rows,word_rows,conditions


def main():
    baseline=json.loads((ROOT/'baseline_vectors.json').read_text())['cases']
    decider=json.loads((ROOT/'decider_baseline.json').read_text())['cases']
    summaries={};all_cases=[];all_words=[];all_conditions=[]
    for name in MODELS:
        s,c,w,k=analyze(name);summaries[name]=s;all_cases+=c;all_words+=w;all_conditions+=k
    comparison=[]
    for row in all_cases:
        case=row['case_id'];other={**baseline[case],'decider_native_order_mean':decider[case]}
        for name,vector in other.items():
            state=max(vector,key=vector.get)
            comparison.append({'model':row['model'],'case_id':case,'native_state':row['selected_state'],
                'baseline':name,'baseline_state':state,'agreement':row['selected_state']==state})
    summary={'models':summaries,'complete':all(s.get('complete') for s in summaries.values()),
        'total_recorded_readouts':sum(s.get('readouts',0) for s in summaries.values()),
        'qualification':'Twelve development targets, one emotion; native runtimes, attention and temperatures differ. Original-wording primary means average four aligned state distributions. Mammoth analysis retains its same-forward unrounded native softmax; its native six-decimal display values are also saved. Wording extension is within each new model; saved Decider/Gemma/Qwen have no matched new paraphrase experiment. No task-accuracy, calibration or downstream-training claim.'}
    (ROOT/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    csvwrite(ROOT/'case_probability_comparison.csv',all_cases);csvwrite(ROOT/'wording_probability_vectors.csv',all_words)
    csvwrite(ROOT/'baseline_verdict_agreements.csv',comparison)
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()

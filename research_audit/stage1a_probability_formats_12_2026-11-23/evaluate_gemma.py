#!/usr/bin/env python3
"""Offline evaluation of saved Gemma logits; no model calls or new labels."""
import csv,hashlib,json,math,os,statistics
from collections import defaultdict
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parent
PRIOR=Path(os.environ.get('PROBABILITY_REPEAT_ROOT',str(ROOT.parent/'probability_repeat_2026_11_23')))
STATES=('neither','support_only','opposition_only','both')
TEMPS=(1.,2.,4.,6.,8.)

def softmax(z):
    a=np.asarray(z,dtype=np.float64);a=np.exp(a-a.max());return a/a.sum()

def native_intervals(record,t):
    m=record['measurement'];lp=m['native_state_logprobs']
    cutoff=min(a['logprob'] for a in record['response']['logprobs'][0]['top_logprobs'])
    ps={s:math.exp(v/t) for s,v in lp.items()};b=math.exp(cutoff/t)
    mass=sum(ps.values());n=4-len(ps)
    return {s:[ps[s]/(mass+n*b),ps[s]/mass] if s in ps else [0.,b/(mass+b)] for s in STATES}

def evaluate():
    ds=[json.loads(l) for l in (PRIOR/'direct_gemma/readouts.jsonl').read_text().splitlines()]
    native=[json.loads(l) for l in (PRIOR/'results/gemma4_31b-it-bf16/responses.jsonl').read_text().splitlines()]
    assert len(ds)==64 and len(native)==624
    unique=[r for r in ds if r['repeat']==0];assert len(unique)==48
    groups=defaultdict(list);ng=defaultdict(list)
    for r in ds:groups[(r['case_id'],r['rotation'])].append(r)
    for r in native:ng[(r['phase'],r['case_id'],r['rotation'])].append(r)
    repeats=[rs for rs in groups.values() if len(rs)>1];assert len(repeats)==16
    cases=sorted({r['case_id'] for r in unique})
    allrows=[];summary=[];max_reconstruction=0.
    for t in TEMPS:
        probs={}
        for r in ds:
            z=[r['capped_logits'][s] for s in STATES];q=softmax(np.array(z)/t)
            saved=np.array([r['temperature_sensitivity'][str(t)][s] for s in STATES])
            max_reconstruction=max(max_reconstruction,float(np.abs(q-saved).max()))
            assert np.allclose(q,saved,atol=1e-13,rtol=0)
            assert STATES[int(np.argmax(q))]==r['selected_state']
            probs[(r['case_id'],r['rotation'],r['repeat'])]=q
        u=np.array([probs[(r['case_id'],r['rotation'],0)] for r in unique])
        pmax=u.max(axis=1);entropy=-(u*np.log(u.clip(1e-300))).sum(axis=1)
        eps=float((1-pmax.mean())/.75)
        smooth=np.full(u.shape,eps/4);smooth[np.arange(len(u)),u.argmax(axis=1)]+=1-eps
        tv=.5*np.abs(u-smooth).sum(axis=1)
        maprows=[]
        for cid in cases:
            qs=np.array([probs[(cid,f'rotation_{i}',0)] for i in range(4)])
            spread=float(np.ptp(qs,axis=0).max())
            maprows.append({'case_id':cid,'max_mapping_spread_pp':100*spread,
                'winning_probability_min':float(qs.max(axis=1).min()),'winning_probability_max':float(qs.max(axis=1).max())})
        repmax=max(float(np.abs(probs[(rs[0]['case_id'],rs[0]['rotation'],0)]-probs[(rs[1]['case_id'],rs[1]['rotation'],1)]).max()) for rs in repeats)
        ranges=[];complete_ranges=[];width=[]
        for key,rs in ng.items():
            iv=[native_intervals(r,t) for r in rs]
            lo=max(max(0.,max(d[s][0] for d in iv)-min(d[s][1] for d in iv)) for s in STATES)
            hi=max(max(d[s][1] for d in iv)-min(d[s][0] for d in iv) for s in STATES)
            ranges.append((lo,hi))
            if all(len(r['measurement']['native_state_logprobs'])==4 for r in rs):complete_ranges.append(hi)
            width += [d[s][1]-d[s][0] for d in iv for s in STATES]
        row={'temperature':t,'unique_inputs':48,'mean_winning_probability':float(pmax.mean()),
            'min_winning_probability':float(pmax.min()),'max_winning_probability':float(pmax.max()),
            'winning_probability_ge_99_9_count':int((pmax>=.999).sum()),
            'mean_entropy_nats':float(entropy.mean()),'mean_effective_class_count':float(np.exp(entropy).mean()),
            'max_mapping_probability_spread_pp':max(r['max_mapping_spread_pp'] for r in maprows),
            'mapping_case_details':maprows,'max_direct_repeat_probability_difference_pp':100*repmax,
            'native_repeat_range_lower_pp':100*max(x[0] for x in ranges),
            'native_repeat_range_upper_pp':100*max(x[1] for x in ranges),
            'native_complete_groups':len(complete_ranges),
            'native_complete_group_max_repeat_range_pp':100*max(complete_ranges),
            'max_native_missingness_interval_width_pp':100*max(width),
            'matched_uniform_label_smoothing_epsilon':eps,
            'mean_total_variation_from_matched_label_smoothing':float(tv.mean()),
            'max_total_variation_from_matched_label_smoothing':float(tv.max())}
        summary.append(row)
        for r,q,p,e,dist in zip(unique,u,pmax,entropy,tv):
            rec={'case_id':r['case_id'],'rotation':r['rotation'],'temperature':t,'winner':r['selected_state'],
                'winning_probability':float(p),'entropy_nats':float(e),'tv_from_matched_uniform_smoothing':float(dist)}
            rec.update({s:float(q[i]) for i,s in enumerate(STATES)});allrows.append(rec)
    result={'source_commit':'5557db9fe857438bda336b9cd1eb4c79b1fcde5e','new_model_calls':0,
        'direct_readouts':64,'unique_direct_inputs':48,'direct_repeat_pairs':16,'native_readouts':624,
        'max_saved_distribution_reconstruction_error':max_reconstruction,
        'temperatures':summary,
        'qualification':'Descriptive reuse of development cases. No independent gold set, calibrated temperature selection or downstream training validation. Native softened distributions use intervals for missing codes, rather than zero imputation.'}
    (ROOT/'gemma_evaluation.json').write_text(json.dumps(result,indent=2))
    with (ROOT/'gemma_temperature_vectors.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(allrows[0]));w.writeheader();w.writerows(allrows)
    averaged=[]
    for t in TEMPS:
        for cid in cases:
            rs=[r for r in allrows if r['case_id']==cid and r['temperature']==t]
            means={s:statistics.mean(r[s] for r in rs) for s in STATES}
            averaged.append({'case_id':cid,'temperature':t,**means,
                'support_marginal':means['support_only']+means['both'],
                'opposition_marginal':means['opposition_only']+means['both']})
    with (ROOT/'gemma_mapping_averages.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(averaged[0]));w.writeheader();w.writerows(averaged)
    files=[PRIOR/'direct_gemma/readouts.jsonl',PRIOR/'results/gemma4_31b-it-bf16/responses.jsonl']
    (ROOT/'gemma_source_integrity.json').write_text(json.dumps({str(p.relative_to(PRIOR)):{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in files},indent=2))
    print(json.dumps({'new_model_calls':0,'repeat_pairs':16,'reconstruction_error':max_reconstruction,
        'temperatures':[{k:r[k] for k in ['temperature','mean_winning_probability','mean_entropy_nats','max_mapping_probability_spread_pp','max_direct_repeat_probability_difference_pp','native_complete_group_max_repeat_range_pp','max_native_missingness_interval_width_pp','mean_total_variation_from_matched_label_smoothing']} for r in summary]},indent=2))

if __name__=='__main__':evaluate()

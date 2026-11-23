#!/usr/bin/env python3
"""Offline analysis of frozen pilot outputs; no model calls or reference relabeling."""
import csv, hashlib, importlib.util, json, math, re, statistics
from pathlib import Path

P=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('pilot',P/'run_pilot.py'); pilot=importlib.util.module_from_spec(spec);spec.loader.exec_module(pilot)

def corrected_measurement(r):
    m=pilot.probability_readout(r['response'],pilot.MAPPINGS[r['condition']])
    if not m['valid']: return m
    # Raw float32 logprobs can round a dominant token's logprob to 0. Therefore
    # 1-sum(exp(logprob)) is not a safe missing-mass cap. Use top-k cutoff only.
    known=m['native_state_probabilities']; missing=m['missing_states']; mass=sum(known.values()); cap=m['topk_cutoff_probability']
    intervals={s:([known[s]/(mass+len(missing)*cap),known[s]/mass] if s in known else [0.,cap/(mass+cap)]) for s in pilot.STATES}
    bounds={}
    for name,sub in {'support':['support_only','both'],'opposition':['opposition_only','both'],'any':['support_only','opposition_only','both']}.items():
        num=sum(known.get(s,0.) for s in sub); n_in=sum(s in missing for s in sub); n_out=len(missing)-n_in
        bounds[name]=[num/(mass+n_out*cap),(num+n_in*cap)/(mass+n_in*cap)]
    m.update(state_probability_intervals=intervals,marginal_probability_intervals=bounds,
             max_state_interval_width=max(b-a for a,b in intervals.values()),
             bounds_analysis_version='topk-cutoff-only; no rounded residual-mass clipping')
    return m

def direction_likelihoods(r):
    response=r['response']; raw=response['message']['content']; tokens=response.get('logprobs') or []
    if ''.join(e['token'] for e in tokens)!=raw:return {'aligned':False,'fields':[]}
    spans=[];offset=0
    for e in tokens:spans.append((offset,offset+len(e['token']),e));offset+=len(e['token'])
    fields=[]
    for match in re.finditer(r'"direction"\s*:\s*"(supports|opposes)"',raw):
        a,b=match.span(1); selected=[(s,e,x) for s,e,x in spans if s<b and e>a]
        if not selected or selected[0][0]!=a or selected[-1][1]!=b:
            fields.append({'direction':match.group(1),'clean_value_token_span':False});continue
        lp=sum(float(x['logprob']) for s,e,x in selected)
        fields.append({'direction':match.group(1),'clean_value_token_span':True,
            'tokens':[x['token'] for s,e,x in selected], 'native_log_likelihood':lp,
            'native_selected_label_path_likelihood':math.exp(lp),
            'meaning':'likelihood of this canonical direction-token path given prior generated quote/context; not normalized against all alternative direction strings or claim validity'})
    return {'aligned':True,'fields':fields}

def main():
    records=[json.loads(x) for f in (P/'results').glob('*/responses.jsonl') for x in f.read_text().splitlines() if x.strip()]
    assert len(records)==72 and len({(r['model'],r['case_id'],r['condition']) for r in records})==72
    inputs={r['case_id']:r for r in pilot.inputs()}; manifest=json.loads((P/'manifest.json').read_text())
    assert pilot.sha(pilot.inputs())==manifest['cases_sha256']
    assert hashlib.sha256((P/'run_pilot.py').read_bytes()).hexdigest()==manifest['runner_sha256']
    by={}
    for r in records:
        assert r['request_sha256']==pilot.sha(r['request'])==pilot.sha(pilot.payload(r['model'],inputs[r['case_id']],r['condition']))
        key=(r['model'],r['case_id']);by.setdefault(key,{})[r['condition']]=r
        if r['condition']!='extract':r['analysis_measurement']=corrected_measurement(r)
        else:r['direction_token_path_analysis']=direction_likelihoods(r)
    summary={}; rows=[]; details=[]
    for model in pilot.MODELS:
        model_rows=[]
        for cid in inputs:
            d=by[(model,cid)]; a=d['canonical']['analysis_measurement'];b=d['rotated']['analysis_measurement'];e=d['extract']['measurement']
            assert a['valid'] and b['valid'] and a['tokens_reconstruct_content'] and b['tokens_reconstruct_content']
            assert a['decision_token_index']==b['decision_token_index']==0
            ai=a['state_probability_intervals'];bi=b['state_probability_intervals']
            tv_lo=.5*sum(max(0.,ai[s][0]-bi[s][1],bi[s][0]-ai[s][1]) for s in pilot.STATES)
            tv_hi=min(1.,.5*sum(max(abs(ai[s][0]-bi[s][1]),abs(ai[s][1]-bi[s][0])) for s in pilot.STATES))
            max_shift=max(max(abs(ai[s][0]-bi[s][1]),abs(ai[s][1]-bi[s][0])) for s in pilot.STATES)
            row={'model':model,'case_id':cid,'extraction_valid':e['valid'],'extraction_state':e.get('state'),
                 'canonical_state':a['selected_state'],'rotated_state':b['selected_state'],
                 'canonical_confidence_lower':ai[a['selected_state']][0],'canonical_confidence_upper':ai[a['selected_state']][1],
                 'rotated_confidence_lower':bi[b['selected_state']][0],'rotated_confidence_upper':bi[b['selected_state']][1],
                 'canonical_complete_distribution':a['complete_distribution'],'rotated_complete_distribution':b['complete_distribution'],
                 'mapping_state_flip':a['selected_state']!=b['selected_state'],
                 'mapping_total_variation_lower':tv_lo,'mapping_total_variation_upper':tv_hi,
                 'max_state_probability_shift_upper':max_shift}
            for label,m in [('canonical',a),('rotated',b)]:
                for side in ['support','opposition']:
                    row[label+'_'+side+'_lower'],row[label+'_'+side+'_upper']=m['marginal_probability_intervals'][side]
            rows.append(row);model_rows.append(row)
            details.append({'model':model,'case_id':cid,'target_segment':inputs[cid]['target_segment'],
                            'canonical':a,'rotated':b,'extraction':e,
                            'raw_extracted_claims':json.loads(d['extract']['response']['message']['content'])['assessments'][0]['claims'],
                            'direction_token_paths':d['extract']['direction_token_path_analysis']})
        probes=[r['analysis_measurement'] for r in records if r['model']==model and r['condition']!='extract']
        confidences=[x['state_probability_intervals'][x['selected_state']][0] for x in probes]
        summary[model]={'calls':36,'valid_extractions':sum(x['extraction_valid'] for x in model_rows),
            'valid_native_probability_readouts':len(probes),'complete_four_state_distributions':sum(x['complete_distribution'] for x in probes),
            'missing_alternative_readouts':sum(not x['complete_distribution'] for x in probes),
            'code_mapping_label_flips':sum(x['mapping_state_flip'] for x in model_rows),
            'selected_conditional_probability_min':min(confidences),'selected_conditional_probability_max':max(confidences),
            'readouts_at_least_99_9_percent':sum(x>=.999 for x in confidences),
            'max_semantic_state_probability_shift_pp':100*max(x['max_state_probability_shift_upper'] for x in model_rows),
            'mean_total_variation_lower':statistics.mean(x['mapping_total_variation_lower'] for x in model_rows),
            'mean_total_variation_upper':statistics.mean(x['mapping_total_variation_upper'] for x in model_rows),
            'minimum_native_candidate_mass_known':min(x['candidate_mass_known'] for x in probes),
            'maximum_missingness_interval_width':max(x['max_state_interval_width'] for x in probes),
            'nonempty_extractions':sum(x['extraction_state'] not in (None,'neither') for x in model_rows),
            'extract_vs_canonical_state_disagreements':[x['case_id'] for x in model_rows if x['extraction_valid'] and x['extraction_state']!=x['canonical_state']],
            'source_quote_failures':[x['case_id'] for x in model_rows if not x['extraction_valid']]}
    cross=[cid for cid in inputs if by[(list(pilot.MODELS)[0],cid)]['canonical']['analysis_measurement']['selected_state']!=by[(list(pilot.MODELS)[1],cid)]['canonical']['analysis_measurement']['selected_state']]
    output={'models':summary,'canonical_cross_model_disagreements':cross,'main_calls':72,'additional_failed_json_interface_calls':1,
            'reference_status':'Reused development data; no 12-case gold accuracy, AUROC, or calibration claim.',
            'bounds_note':'Top-k cutoff bounds recomputed offline to avoid zeroing omitted labels when float32 top logprob rounds to zero. Raw model outputs and frozen runner unchanged.'}
    (P/'analysis_summary.json').write_text(json.dumps(output,indent=2))
    (P/'analysis_details.json').write_text(json.dumps(details,ensure_ascii=False,indent=2))
    with (P/'comparison.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    print(json.dumps(output,indent=2))
    print('CASE_DETAILS',json.dumps([x for x in details if x['case_id'] in ['K01','K04','U06']],ensure_ascii=False)[:2000])

if __name__=='__main__':main()

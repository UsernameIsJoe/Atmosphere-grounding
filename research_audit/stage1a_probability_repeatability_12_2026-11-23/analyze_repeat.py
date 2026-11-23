#!/usr/bin/env python3
"""Offline analysis; interval arithmetic retains missing native alternatives."""
import csv, hashlib, itertools, json, math, statistics
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parent
STATES=('neither','support_only','opposition_only','both')
MAPS=[f'rotation_{i}' for i in range(4)]

def sha(x):
    return hashlib.sha256(json.dumps(x,ensure_ascii=False,sort_keys=True).encode()).hexdigest()

def stat_group(records):
    intervals={s:[r['measurement']['state_probability_intervals'][s] for r in records] for s in STATES}
    means={s:[statistics.mean(v[k] for v in pairs) for k in (0,1)] for s,pairs in intervals.items()}
    ranges={s:[max(0.,max(v[0] for v in pairs)-min(v[1] for v in pairs)),
        max(v[1] for v in pairs)-min(v[0] for v in pairs)] for s,pairs in intervals.items()}
    margins={}
    for pair in {p for r in records for p in r['measurement']['pairwise_logit_margins']}:
        v=[r['measurement']['pairwise_logit_margins'][pair] for r in records if pair in r['measurement']['pairwise_logit_margins']]
        margins[pair]={'coverage':len(v),'mean':statistics.mean(v),'range':max(v)-min(v),
            'sd':statistics.stdev(v) if len(v)>1 else None}
    return {'n':len(records),'states':sorted({r['measurement']['selected_state'] for r in records}),
        'mean_probability_intervals':means,'probability_range_intervals':ranges,
        'max_probability_range_upper':max(v[1] for v in ranges.values()),'margins':margins,
        'complete_probability_readouts':sum(r['measurement']['complete_distribution'] for r in records),
        'distinct_logprob_fingerprints':len({sha(r['measurement']['native_state_logprobs']) for r in records})}

def analyze():
    manifest=json.loads((ROOT/'manifest.json').read_text())
    records=[json.loads(l) for p in (ROOT/'results').glob('*/responses.jsonl') for l in p.read_text().splitlines() if l.strip()]
    assert len(records)==manifest['expected_native_readouts'],(len(records),manifest['expected_native_readouts'])
    keys=[(r['model'],r['phase'],r['repeat'],r['case_id'],r['rotation']) for r in records]
    assert len(keys)==len(set(keys)),'duplicate records'
    for r in records:
        assert not r.get('error') and r['measurement']['valid'],r
        assert sha(r['request'])==r['request_sha256']
        req={**r['request'],'model':'MODEL'}
        assert sha(req)==manifest['payload_hashes'][r['case_id']][r['rotation']]
        assert r['measurement']['decision_token_index']==0
    groups=defaultdict(list)
    for r in records:groups[(r['model'],r['phase'],r['case_id'],r['rotation'])].append(r)
    groupstats={key:stat_group(rs) for key,rs in groups.items()}
    cases=sorted({r['case_id'] for r in records})
    details=[];summary={};csvrows=[]
    for model in manifest['models']:
        mrecords=[r for r in records if r['model']==model]
        phases={}
        for phase,nrep in [('main',10),('reloaded',3)]:
            for cid in cases:
                gs={rot:groupstats[(model,phase,cid,rot)] for rot in MAPS}
                assert all(g['n']==nrep for g in gs.values())
                gap={s:[max(0.,max(g['mean_probability_intervals'][s][0] for g in gs.values())-min(g['mean_probability_intervals'][s][1] for g in gs.values())),
                    max(g['mean_probability_intervals'][s][1] for g in gs.values())-min(g['mean_probability_intervals'][s][0] for g in gs.values())] for s in STATES}
                two={s:[max(0.,gs['rotation_0']['mean_probability_intervals'][s][0]-gs['rotation_1']['mean_probability_intervals'][s][1],gs['rotation_1']['mean_probability_intervals'][s][0]-gs['rotation_0']['mean_probability_intervals'][s][1]),
                    max(abs(gs['rotation_0']['mean_probability_intervals'][s][1]-gs['rotation_1']['mean_probability_intervals'][s][0]),abs(gs['rotation_1']['mean_probability_intervals'][s][1]-gs['rotation_0']['mean_probability_intervals'][s][0]))] for s in STATES}
                within=max(g['max_probability_range_upper'] for g in gs.values())
                rec={'model':model,'phase':phase,'case_id':cid,'groups':gs,'mapping_mean_spread_intervals':gap,
                    'max_mapping_mean_spread_lower':max(v[0] for v in gap.values()),
                    'max_mapping_mean_spread_upper':max(v[1] for v in gap.values()),
                    'original_pair_mean_gap_lower':max(v[0] for v in two.values()),
                    'original_pair_mean_gap_upper':max(v[1] for v in two.values()),
                    'max_identical_request_range_upper':within,
                    'repeat_label_flip_groups':sum(len(g['states'])>1 for g in gs.values()),
                    'mapping_selected_states':{k:g['states'] for k,g in gs.items()}}
                rec['mapping_spread_exceeds_observed_repeat_range']=rec['max_mapping_mean_spread_lower']>within
                details.append(rec)
                csvrows.append({'model':model,'phase':phase,'case_id':cid,
                    'mapping_spread_lower_pp':100*rec['max_mapping_mean_spread_lower'],
                    'mapping_spread_upper_pp':100*rec['max_mapping_mean_spread_upper'],
                    'original_pair_gap_lower_pp':100*rec['original_pair_mean_gap_lower'],
                    'original_pair_gap_upper_pp':100*rec['original_pair_mean_gap_upper'],
                    'identical_request_range_upper_pp':100*within,'repeat_label_flip_groups':rec['repeat_label_flip_groups'],
                    'mapping_states':json.dumps(rec['mapping_selected_states'],sort_keys=True)})
            pd=[r for r in details if r['model']==model and r['phase']==phase]
            phases[phase]={'readouts':len([r for r in mrecords if r['phase']==phase]),
                'max_identical_request_range_upper_pp':100*max(r['max_identical_request_range_upper'] for r in pd),
                'max_mapping_mean_spread_lower_pp':100*max(r['max_mapping_mean_spread_lower'] for r in pd),
                'max_mapping_mean_spread_upper_pp':100*max(r['max_mapping_mean_spread_upper'] for r in pd),
                'max_original_pair_mean_gap_lower_pp':100*max(r['original_pair_mean_gap_lower'] for r in pd),
                'max_original_pair_mean_gap_upper_pp':100*max(r['original_pair_mean_gap_upper'] for r in pd),
                'cases_with_mapping_spread_exceeding_repeat_range':sum(r['mapping_spread_exceeds_observed_repeat_range'] for r in pd),
                'repeat_label_flip_groups':sum(r['repeat_label_flip_groups'] for r in pd),
                'cases_with_different_mapping_winners':sum(len({s for v in r['mapping_selected_states'].values() for s in v})>1 for r in pd)}
        reload_shifts=[]
        for cid in cases:
            for rot in MAPS:
                a=groupstats[(model,'main',cid,rot)]['mean_probability_intervals'];b=groupstats[(model,'reloaded',cid,rot)]['mean_probability_intervals']
                reload_shifts.append(max(max(abs(a[s][0]-b[s][1]),abs(a[s][1]-b[s][0])) for s in STATES))
        known_margin_ranges=[v['range'] for key,g in groupstats.items() if key[0]==model for v in g['margins'].values() if v['coverage']==g['n']]
        summary[model]={'readouts':len(mrecords),'phases':phases,
            'max_phase_mean_shift_same_payload_after_reload_upper_pp':100*max(reload_shifts),
            'max_observed_identical_request_logit_margin_range':max(known_margin_ranges,default=None),
            'complete_four_state_readouts':sum(r['measurement']['complete_distribution'] for r in mrecords),
            'chosen_probability_at_least_99_9_count':sum(r['measurement']['state_probability_intervals'][r['measurement']['selected_state']][0]>=.999 for r in mrecords),
            'max_probability_missingness_interval_width':max(hi-lo for r in mrecords for lo,hi in r['measurement']['state_probability_intervals'].values())}
    output={'native_readouts':len(records),'models':summary,
        'interpretation':'Observed repeatability in this environment; mappings are four cyclic assignments, not all 24; no calibration/accuracy claim.'}
    direct=ROOT/'direct_gemma/readouts.jsonl'
    if direct.exists():
        import numpy as np
        ds=[json.loads(l) for l in direct.read_text().splitlines() if l.strip()]
        rendered=json.loads((ROOT/'results/gemma4_31b-it-bf16/rendered_prompts.json').read_text())
        prompt_hashes={(r['case_id'],r['rotation']):hashlib.sha256(r['response']['_debug_info']['rendered_template'].encode()).hexdigest() for r in rendered}
        comparisons=[]
        vocab_code_winners=0
        for r in ds:
            assert r['prompt_sha256']==prompt_hashes[(r['case_id'],r['rotation'])]
            g=groupstats[('gemma4:31b-it-bf16','main',r['case_id'],r['rotation'])]
            native_counts={x['response']['prompt_eval_count'] for x in records if x['model']=='gemma4:31b-it-bf16' and x['case_id']==r['case_id'] and x['rotation']==r['rotation']}
            with np.load(ROOT/'direct_gemma'/f"{r['case_id']}_{r['rotation']}_{r['repeat']}.npz") as arrays:
                vocab_code_winners+=int(arrays['top20_ids'][0] in arrays['code_token_ids'])
            comparisons.append({'case_id':r['case_id'],'rotation':r['rotation'],'repeat':r['repeat'],
                'direct_token_count':r['token_count'],'native_token_counts':sorted(native_counts),
                'token_count_matches_native':native_counts=={r['token_count']},
                'same_selected_state':g['states']==[r['selected_state']],
                'max_conditional_probability_gap_upper':max(max(abs(r['conditional_probabilities'][s]-a),abs(r['conditional_probabilities'][s]-b)) for s,(a,b) in g['mean_probability_intervals'].items())})
        drgroups=defaultdict(list)
        for r in ds:drgroups[(r['case_id'],r['rotation'])].append(r)
        direct_repeat_diffs=[]
        for rs in drgroups.values():
            if len(rs)>1:direct_repeat_diffs.append(max(max(r['capped_logits'][s] for r in rs)-min(r['capped_logits'][s] for r in rs) for s in STATES))
        inverse=[r for r in ds if all(r['inverse_valid'].values())]
        output['direct_gemma']={'readouts':len(ds),'expected_readouts':64,'native_argmax_agreement':sum(r['same_selected_state'] for r in comparisons),
            'direct_prompt_hashes_verified':len(ds),
            'direct_token_count_matches_native_count':sum(r['token_count_matches_native'] for r in comparisons),
            'full_vocabulary_winner_is_a_code':vocab_code_winners,
            'max_native_vs_direct_probability_gap_upper_pp':100*max((r['max_conditional_probability_gap_upper'] for r in comparisons),default=0),
            'fully_invertible_four_code_readouts':len(inverse),
            'maximum_softcap_roundtrip_abs_error':max((r['softcap_roundtrip_max_abs_error'] for r in ds if r['softcap_roundtrip_max_abs_error'] is not None),default=None),
            'uncapping_does_not_reduce_chosen_probability':sum(r['without_softcap_conditional'][r['selected_state']]+1e-12>=r['conditional_probabilities'][r['selected_state']] for r in inverse),
            'max_direct_repeated_logit_difference':max(direct_repeat_diffs,default=None),
            'qualification':'Different inference binary on identical GGUF. Analytic pre-cap reconstruction; temperature grid is uncalibrated.'}
        (ROOT/'direct_gemma/native_alignment.json').write_text(json.dumps(comparisons,indent=2))
    (ROOT/'analysis_summary.json').write_text(json.dumps(output,indent=2))
    (ROOT/'analysis_details.json').write_text(json.dumps(details,indent=2))
    with (ROOT/'comparison.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(csvrows[0]));w.writeheader();w.writerows(csvrows)
    print(json.dumps(output,indent=2))

if __name__=='__main__':analyze()
